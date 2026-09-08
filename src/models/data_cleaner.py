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


def _canonical_formula_label(result: pd.DataFrame) -> pd.DataFrame:
    """Un solo nombre visible por producto.

    'CERAM 130 GRIS' y 'CERAM130 GRIS' comparten `formula_key` y filtran igual,
    pero el desplegable mostraba las dos y parecían productos distintos. Gana la
    grafía más usada, que es la que el operario escribe bien la mayoría de veces.
    """
    if result.empty or "formula_key" not in result:
        return result
    counts = result.groupby(["formula_key", "RecipeBB1name"]).size()
    canonical = counts.sort_values(ascending=False).reset_index().drop_duplicates("formula_key")
    labels = dict(zip(canonical["formula_key"], canonical["RecipeBB1name"]))
    result["RecipeBB1name"] = result["formula_key"].map(labels).fillna(result["RecipeBB1name"])
    return result


def clean_m1(df: pd.DataFrame, materials: dict[str, str] | None = None,
              min_year: int | None = None) -> pd.DataFrame:
    result = _coerce_numeric_columns(_parse_datetime_columns(df), exclude={"oiltarget"})
    # Recipe1Name es el nombre del producto; RecipeBB1name es el del big-bag 1 y
    # en el 88% de los batches dice "No BB1 in Formula". Preferir el segundo
    # dejaba el filtro de fórmula con 3 opciones en vez de las 159 reales.
    formula_source = "Recipe1Name" if "Recipe1Name" in result else "RecipeBB1name"
    result["RecipeBB1name"] = result.get(formula_source, pd.Series("", index=result.index)).map(_display_formula)
    result["formula_key"] = result["RecipeBB1name"].map(_formula_key)
    result = _canonical_formula_label(result)
    if "OperatorName" in result:
        # El operario teclea sus iniciales sin criterio de caja: 'OB' y 'ob' son
        # la misma persona y aparecían como dos entradas en el filtro.
        result["OperatorName"] = result["OperatorName"].map(_display_formula)
    if "LOTE" in result:
        result["LOTE"] = result["LOTE"].map(_display_formula)
    if {"ReportDate", "ReportTime"}.issubset(result.columns):
        result["report_datetime"] = result["ReportDate"] + result["ReportTime"]
    elif "ReportDate" in result:
        result["report_datetime"] = result["ReportDate"]
    else:
        result["report_datetime"] = pd.NaT
    result["report_day"] = pd.to_datetime(result["report_datetime"], errors="coerce").dt.date
    result = result[result["report_datetime"].notna()].copy()
    if min_year is not None:
        years = pd.to_datetime(result["report_datetime"], errors="coerce").dt.year
        result = result[years >= min_year]
    result = result.copy()

    for silo in range(1, 9):
        kg_source, pct_source = f"Differentiel_Silo_{silo}", f"Differentiel_Silo_{silo}_PC"
        result[f"Silo {silo}_kg"] = pd.to_numeric(result.get(kg_source), errors="coerce")
        result[f"Silo {silo}_pct"] = pd.to_numeric(result.get(pct_source), errors="coerce")
        target, actual = f"Silo{silo}Target", f"Silo{silo}Real"
        if target in result and actual in result:
            unused = (pd.to_numeric(result[target], errors="coerce").eq(0)
                      & pd.to_numeric(result[actual], errors="coerce").eq(0))
            result.loc[unused, [f"Silo {silo}_kg", f"Silo {silo}_pct"]] = float("nan")
    if materials is not None:
        # El operador teclea el material a mano en cada silo: sin canonizar,
        # 'ARENA  16/50' y 'ARENA 16/50' cuentan como polvos distintos.
        for silo in range(1, 9):
            source = result.get(f"Silo{silo}Des")
            result[f"Silo {silo}_material"] = (
                source.fillna("").map({value: canonical_material(value, materials)
                                     for value in source.fillna("").unique()})
                if source is not None else ""
            )
    if "NumberBatchDone1" in result:
        result["NumberBatchDone1"] = pd.to_numeric(result["NumberBatchDone1"], errors="coerce").round().astype("Int64")
    return _add_run_batch_counter(result)
