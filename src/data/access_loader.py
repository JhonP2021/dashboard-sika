from __future__ import annotations

import logging
import os
import time

import pandas as pd

from config.settings import AppSettings
from src.data.base_loader import BaseLoader


try:
    import pyodbc
except Exception:  # pragma: no cover - optional dependency
    pyodbc = None


log = logging.getLogger(__name__)


def _positive_int_env(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default


# Sin @cache_data a propósito, igual que en csv_loader: `load_dashboard_data`
# ya cachea el resultado limpio durante 3 h. Cachear además las tablas crudas
# por mtime guardaba una copia completa por cada escritura de la línea en el
# .accdb, sin desalojar ninguna.
def _query(connection_string: str, query: str) -> pd.DataFrame:
    if pyodbc is None:
        raise ImportError(
            "pyodbc is not installed. Install it to read directly from Microsoft Access in production."
        )
    timeout = _positive_int_env("ACCESS_TIMEOUT_SECONDS", 30)
    retries = max(0, _positive_int_env("ACCESS_RETRIES", 2))
    last_error = None
    for attempt in range(retries + 1):
        connection = None
        try:
            connection = pyodbc.connect(connection_string, timeout=timeout)
            return pd.read_sql(query, connection)
        except Exception as error:
            last_error = error
            if attempt >= retries:
                break
            delay = 2 ** attempt
            log.warning("Access query failed (attempt %s/%s); retrying in %ss", attempt + 1, retries + 1, delay)
            time.sleep(delay)
        finally:
            if connection is not None:
                connection.close()
    raise RuntimeError(f"No fue posible leer la base de Access después de {retries + 1} intentos.") from last_error


class AccessTableLoader(BaseLoader):
    def __init__(self, settings: AppSettings):
        self.settings = settings

    def load_table(self, table_name: str) -> pd.DataFrame:
        if not self.settings.access_connection_string:
            raise ValueError("ACCESS_DB_PATH is not configured.")
        table = self.settings.access_tables[table_name]
        return _query(self.settings.access_connection_string, f"SELECT * FROM [{table}]")

    def load_all(self) -> dict[str, pd.DataFrame]:
        return {name: self.load_table(name) for name in self.settings.access_tables}
