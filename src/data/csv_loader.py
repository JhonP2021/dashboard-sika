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


@cache_data(show_spinner=False)
def _cached_read_csv(file_path: str, file_mtime: float) -> pd.DataFrame:
    return pd.read_csv(file_path, encoding="utf-8-sig", sep=None, engine="python")


class CSVTableLoader(BaseLoader):
    def __init__(self, settings: AppSettings):
        self.settings = settings

    def load_table(self, table_name: str) -> pd.DataFrame:
        path = self.settings.csv_paths[table_name]
        resolved = self._ensure_path(path)
        return _cached_read_csv(str(resolved), resolved.stat().st_mtime)

    def load_all(self) -> dict[str, pd.DataFrame]:
        return {name: self.load_table(name) for name in self.settings.csv_paths}
