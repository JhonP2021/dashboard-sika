from __future__ import annotations

from pathlib import Path

import pandas as pd

from config.settings import AppSettings
from src.data.base_loader import BaseLoader

try:  # pragma: no cover - optional dependency
    import streamlit as st
    cache_data = st.cache_data
except Exception:  # pragma: no cover
    def cache_data(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

# Google Drive file IDs for Streamlit Cloud deployment
DRIVE_FILE_IDS = {
    "table_date": "1wLAji3EHZ7X7s58yihDzfB-LYPoyxpio",
    "table_report_m1": "1uZXgQ7UXdLI-x7JXdJgZV4P3G6Sf8vv3",
    "table_report_m1_out": "1cTknHzrHhkDjCNjZqFNRNVXl-RVjAbkL",
    "table_report_bston": "10qDy7in6ZhLRnbIhmB4-7ONWHRxxs0pA",
}


def _download_from_drive(file_id: str, output_path: Path) -> None:
    """Download file from Google Drive using gdown"""
    try:
        import gdown
        url = f"https://drive.google.com/uc?id={file_id}"
        gdown.download(url, str(output_path), quiet=True)
    except ImportError:
        raise ImportError("gdown is required to download from Google Drive")


@cache_data(show_spinner=False)
def _cached_read_csv(file_path: str, file_mtime: float) -> pd.DataFrame:
    return pd.read_csv(file_path, encoding="utf-8-sig", sep=None, engine="python")


class CSVTableLoader(BaseLoader):
    def __init__(self, settings: AppSettings):
        self.settings = settings

    def load_table(self, table_name: str) -> pd.DataFrame:
        path = self.settings.csv_paths[table_name]
        
        # If file doesn't exist, download from Google Drive
        if not path.exists():
            try:
                import streamlit as st
                st.info(f"📥 Descargando {table_name} desde Google Drive...")
            except:
                pass
            
            if table_name in DRIVE_FILE_IDS:
                _download_from_drive(DRIVE_FILE_IDS[table_name], path)
            else:
                raise FileNotFoundError(f"No Drive ID configured for {table_name}")
        
        resolved = self._ensure_path(path)
        return _cached_read_csv(str(resolved), resolved.stat().st_mtime)

    def load_all(self) -> dict[str, pd.DataFrame]:
        return {name: self.load_table(name) for name in self.settings.csv_paths}
