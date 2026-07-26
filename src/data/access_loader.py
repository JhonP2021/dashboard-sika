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


try:
    import pyodbc
except Exception:  # pragma: no cover - optional dependency
    pyodbc = None


@cache_data(show_spinner=False)
def _cached_query(connection_string: str, query: str, table_mtime: float) -> pd.DataFrame:
    if pyodbc is None:
        raise ImportError(
            "pyodbc is not installed. Install it to read directly from Microsoft Access in production."
        )
    connection = pyodbc.connect(connection_string)
    try:
        return pd.read_sql(query, connection)
    finally:
        connection.close()


class AccessTableLoader(BaseLoader):
    def __init__(self, settings: AppSettings):
        self.settings = settings

    def _table_mtime(self) -> float:
        if self.settings.access_db_path and self.settings.access_db_path.exists():
            return self.settings.access_db_path.stat().st_mtime
        return 0.0

    def load_table(self, table_name: str) -> pd.DataFrame:
        if not self.settings.access_connection_string:
            raise ValueError("ACCESS_DB_PATH is not configured.")
        table = self.settings.access_tables[table_name]
        query = f"SELECT * FROM [{table}]"
        return _cached_query(self.settings.access_connection_string, query, self._table_mtime())

    def load_all(self) -> dict[str, pd.DataFrame]:
        return {name: self.load_table(name) for name in self.settings.access_tables}
