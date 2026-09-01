from __future__ import annotations

import re
import unicodedata
from typing import Iterable

import pandas as pd

from src.models.material_normalizer import canonical_material


def _display_formula(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value).strip()).upper()


def _formula_key(value: object) -> str:
    text = unicodedata.normalize("NFKD", _display_formula(value)).encode("ASCII", "ignore").decode("ASCII")
    return re.sub(r"[^A-Z0-9]", "", text)


def _parse_datetime_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    for column in result.columns:
        lower = column.lower()
        if lower in {"reportdate", "fecha", "startdate_m1", "enddate_m1"}:
            result[column] = pd.to_datetime(result[column], errors="coerce", dayfirst=False)
        elif lower in {"reporttime", "hora", "starttime_m1"}:
            result[column] = pd.to_timedelta(result[column].astype(str), errors="coerce")
    return result


def _coerce_numeric_columns(df: pd.DataFrame, exclude: Iterable[str] = ()) -> pd.DataFrame:
    result = df.copy()
    excluded = {col.lower() for col in exclude}
    for column in result.columns:
        if column.lower() in excluded or any(token in column.lower() for token in ("code", "des", "name", "formula", "operator", "lote")):
            continue
        if result[column].dtype == "object":
            converted = pd.to_numeric(result[column], errors="coerce")
            if converted.notna().sum() > 0:
                result[column] = converted
    return result


def clean_table_date(df: pd.DataFrame) -> pd.DataFrame:
    return _coerce_numeric_columns(_parse_datetime_columns(df))


def _add_run_batch_counter(result: pd.DataFrame) -> pd.DataFrame:
    if result.empty:
        result["batch_corrido"] = pd.Series(dtype="Int64")
        return result
    result = result.sort_values("report_datetime", kind="stable").reset_index(drop=True)
    formula_change = result["formula_key"].ne(result["formula_key"].shift())
    lot_change = result["LOTE"].ne(result["LOTE"].shift()) if "LOTE" in result else pd.Series(False, index=result.index)
    raw_batch = pd.to_numeric(result.get("NumberBatchDone1"), errors="coerce")
    batch_reset = raw_batch.lt(raw_batch.shift()) if raw_batch is not None else pd.Series(False, index=result.index)
    run_start = (formula_change | lot_change | batch_reset).fillna(True)
    result["corrida_id"] = run_start.cumsum()
    result["batch_corrido"] = result.groupby("corrida_id").cumcount() + 1
    return result


def clean_m1(df: pd.DataFrame, materials: dict[str, str] | None = None) -> pd.DataFrame:
    result = _coerce_numeric_columns(_parse_datetime_columns(df), exclude={"oiltarget"})
    formula_source = "RecipeBB1name" if "RecipeBB1name" in result else "Recipe1Name"
    result["RecipeBB1name"] = result.get(formula_source, pd.Series("", index=result.index)).map(_display_formula)
    result["formula_key"] = result["RecipeBB1name"].map(_formula_key)
    if {"ReportDate", "ReportTime"}.issubset(result.columns):
        result["report_datetime"] = result["ReportDate"] + result["ReportTime"]
    elif "ReportDate" in result:
        result["report_datetime"] = result["ReportDate"]
    else:
        result["report_datetime"] = pd.NaT
    result["report_day"] = pd.to_datetime(result["report_datetime"], errors="coerce").dt.date
    result = result[pd.to_datetime(result["report_datetime"], errors="coerce").dt.year >= 2026].copy()

    for silo in range(1, 9):
        kg_source, pct_source = f"Differentiel_Silo_{silo}", f"Differentiel_Silo_{silo}_PC"
        result[f"Silo {silo}_kg"] = pd.to_numeric(result.get(kg_source), errors="coerce")
        result[f"Silo {silo}_pct"] = pd.to_numeric(result.get(pct_source), errors="coerce")
    if materials is not None:
        # El operador teclea el material a mano en cada silo: sin canonizar,
        # 'ARENA  16/50' y 'ARENA 16/50' cuentan como polvos distintos.
        for silo in range(1, 9):
            source = result.get(f"Silo{silo}Des")
            result[f"Silo {silo}_material"] = (
                source.map(lambda v: canonical_material(v, materials))
                if source is not None else ""
            )
    if "NumberBatchDone1" in result:
        result["NumberBatchDone1"] = pd.to_numeric(result["NumberBatchDone1"], errors="coerce").round().astype("Int64")
    return _add_run_batch_counter(result)
