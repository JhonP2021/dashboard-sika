from __future__ import annotations

import csv
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


# Sin @cache_data a propósito: `load_dashboard_data` ya cachea el resultado ya
# limpio y proyectado durante 3 h, así que cachear además el crudo sólo retenía
# una copia de 826 MB del CSV grande que nadie vuelve a leer. Un fallo de la
# caché externa cuesta releer el fichero; tenerlo cacheado costaba la memoria
# todo el tiempo.
def _cached_read_csv(file_path: str, file_mtime: float) -> pd.DataFrame:
    with open(file_path, encoding="utf-8-sig", newline="") as source:
        sample = source.read(65536)
    try:
        # El prefijo puede cortar a mitad de registro y dejar al sniffer sin
        # criterio; la coma es el separador de todos los volcados actuales.
        delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        delimiter = ","
    return pd.read_csv(file_path, encoding="utf-8-sig", sep=delimiter, low_memory=False)


class CSVTableLoader(BaseLoader):
    def __init__(self, settings: AppSettings):
        self.settings = settings

    def load_table(self, table_name: str) -> pd.DataFrame:
        path = self.settings.csv_paths[table_name]
        resolved = self._ensure_path(path)
        return _cached_read_csv(str(resolved), resolved.stat().st_mtime)

    def load_all(self) -> dict[str, pd.DataFrame]:
        return {name: self.load_table(name) for name in self.settings.csv_paths}
