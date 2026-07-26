from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR

TABLE_FILES = {
    "table_date": "_TableDate__202607252000.csv",
    "table_report_m1": "_TableReport_M1__202607252000.csv",
    "table_report_m1_out": "_TableReport_M1_out__202607252000.csv",
    "table_report_bston": "_Table_report_BSton__202607252000.csv",
}


@dataclass(frozen=True)
class AppSettings:
    mode: str
    data_dir: Path
    csv_paths: dict[str, Path]
    access_db_path: Path | None
    access_connection_string: str | None
    access_tables: dict[str, str]


def _build_access_connection_string(database_path: str | None) -> str | None:
    if not database_path:
        return None
    driver = os.getenv("ACCESS_ODBC_DRIVER", "Microsoft Access Driver (*.mdb, *.accdb)")
    read_only = os.getenv("ACCESS_READ_ONLY", "1").strip() not in {"0", "false", "False"}
    readonly_clause = "READONLY=1;" if read_only else ""
    return (
        f"Driver={{{driver}}};"
        f"Dbq={database_path};"
        f"{readonly_clause}"
        "ExtendedAnsiSQL=1;"
    )


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    mode = os.getenv("DASHBOARD_MODE", "DEV").upper().strip()
    csv_paths = {name: DATA_DIR / filename for name, filename in TABLE_FILES.items()}

    access_db = os.getenv("ACCESS_DB_PATH")
    access_path = Path(access_db).expanduser().resolve() if access_db else None
    access_tables = {
        "table_date": os.getenv("ACCESS_TABLE_DATE", "TableDate"),
        "table_report_m1": os.getenv("ACCESS_TABLE_REPORT_M1", "TableReport_M1"),
        "table_report_m1_out": os.getenv("ACCESS_TABLE_REPORT_M1_OUT", "TableReport_M1_out"),
        "table_report_bston": os.getenv("ACCESS_TABLE_REPORT_BSTON", "Table_report_BSton"),
    }

    return AppSettings(
        mode=mode,
        data_dir=DATA_DIR,
        csv_paths=csv_paths,
        access_db_path=access_path,
        access_connection_string=_build_access_connection_string(str(access_path) if access_path else None),
        access_tables=access_tables,
    )


def build_access_connection_string(database_path: str) -> str:
    connection_string = _build_access_connection_string(database_path)
    if connection_string is None:
        raise ValueError("database_path is required to build an Access connection string.")
    return connection_string

