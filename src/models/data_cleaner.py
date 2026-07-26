from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

import pandas as pd


def _normalize_text(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = text.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    return text


def _parse_datetime_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    for column in result.columns:
        lower = column.lower()
        if lower in {"reportdate", "fecha", "startdate_m1", "enddate_m1"}:
            result[column] = pd.to_datetime(result[column], errors="coerce", dayfirst=False)
        elif lower in {"reporttime", "hora", "starttime_m1"}:
            time_values = result[column].astype(str).str.strip()
            result[column] = pd.to_datetime(time_values, errors="coerce", format="%H:%M:%S").dt.time
    return result


def _coerce_numeric_columns(df: pd.DataFrame, exclude: Iterable[str] = ()) -> pd.DataFrame:
    result = df.copy()
    excluded = {col.lower() for col in exclude}
    for column in result.columns:
        if column.lower() in excluded:
            continue
        if any(token in column.lower() for token in ("code", "des", "name", "formula")):
            continue
        if result[column].dtype == "object":
            converted = pd.to_numeric(result[column], errors="coerce")
            if converted.notna().sum() > 0:
                result[column] = converted
    return result


def _add_normalized_formula(df: pd.DataFrame, source_column: str) -> pd.DataFrame:
    result = df.copy()
    if source_column in result.columns:
        result["formula_key"] = result[source_column].map(_normalize_text)
    else:
        result["formula_key"] = ""
    return result


def clean_table_date(df: pd.DataFrame) -> pd.DataFrame:
    result = _parse_datetime_columns(df)
    return _coerce_numeric_columns(result)


def clean_m1(df: pd.DataFrame) -> pd.DataFrame:
    result = _parse_datetime_columns(df)
    result = _coerce_numeric_columns(result, exclude={"oiltarget"})
    result = _add_normalized_formula(result, "Recipe1Name")
    if {"ReportDate", "ReportTime"}.issubset(result.columns):
        report_date = pd.to_datetime(result["ReportDate"], errors="coerce")
        report_time = pd.to_timedelta(result["ReportTime"].astype(str), errors="coerce")
        result["report_datetime"] = report_date + report_time
        result["report_day"] = result["report_datetime"].dt.date
    target_cols = [col for col in result.columns if re.fullmatch(r"SiloP?\d+Target", col)]
    real_cols = [col for col in result.columns if re.fullmatch(r"SiloP?\d+Real", col)]
    diff_cols = [col for col in result.columns if "Differentiel_" in col and not col.endswith("_PC")]
    out_tol_cols = [col for col in result.columns if col.startswith("Out_of_Tol_")]
    if target_cols:
        result["total_target_components"] = result[target_cols].apply(pd.to_numeric, errors="coerce").sum(axis=1)
    if real_cols:
        result["total_real_components"] = result[real_cols].apply(pd.to_numeric, errors="coerce").sum(axis=1)
    if diff_cols:
        result["total_difference"] = result[diff_cols].apply(pd.to_numeric, errors="coerce").sum(axis=1)
    if out_tol_cols:
        result["out_of_tolerance_count"] = result[out_tol_cols].apply(pd.to_numeric, errors="coerce").sum(axis=1)
        result["out_of_tolerance_flag"] = (result["out_of_tolerance_count"] > 0).astype(int)
    else:
        result["out_of_tolerance_count"] = 0
        result["out_of_tolerance_flag"] = 0
    return result


def clean_m1_out(df: pd.DataFrame) -> pd.DataFrame:
    return clean_m1(df)


def clean_bston(df: pd.DataFrame) -> pd.DataFrame:
    result = _parse_datetime_columns(df)
    result = _coerce_numeric_columns(result)
    result = _add_normalized_formula(result, "Formula")
    if {"Fecha", "Hora"}.issubset(result.columns):
        fecha_dt = pd.to_datetime(result["Fecha"], errors="coerce")
        result["snapshot_datetime"] = pd.to_datetime(
            fecha_dt.dt.strftime("%Y-%m-%d").fillna(result["Fecha"].astype(str)) + " " + result["Hora"].astype(str),
            errors="coerce",
        )
    return result


def build_formula_dimension(m1_df: pd.DataFrame, bston_df: pd.DataFrame) -> pd.DataFrame:
    left = m1_df[["formula_key", "Recipe1Name"]].rename(columns={"Recipe1Name": "formula_m1"}) if "Recipe1Name" in m1_df else pd.DataFrame(columns=["formula_key", "formula_m1"])
    right = bston_df[["formula_key", "Formula"]].rename(columns={"Formula": "formula_bston"}) if "Formula" in bston_df else pd.DataFrame(columns=["formula_key", "formula_bston"])
    merged = pd.merge(left, right, on="formula_key", how="outer")
    if merged.empty:
        return pd.DataFrame(columns=["formula_key", "formula_m1", "formula_bston", "display_name"])
    merged = merged[merged["formula_key"].fillna("").astype(str).str.strip() != ""]
    merged["display_name"] = merged["formula_m1"].fillna(merged["formula_bston"]).fillna(merged["formula_key"])
    return merged.drop_duplicates(subset=["formula_key"]).reset_index(drop=True)


def long_format_m1(df: pd.DataFrame) -> pd.DataFrame:
    component_rows = []
    for index, component in enumerate(range(1, 13), start=1):
        target_col = f"Silo{component}Target"
        real_col = f"Silo{component}Real"
        code_col = f"Silo{component}Code"
        des_col = f"Silo{component}Des"
        diff_col = f"Differentiel_Silo_{component}"
        diff_pc_col = f"Differentiel_Silo_{component}_PC"
        out_col = f"Out_of_Tol_Silo_{component}"
        present = [col for col in [target_col, real_col] if col in df.columns]
        if not present:
            continue
        piece = df[[c for c in [target_col, real_col, code_col, des_col, diff_col, diff_pc_col, out_col, "report_datetime", "report_day", "Recipe1Name", "formula_key"] if c in df.columns]].copy()
        piece["component"] = f"Silo{component}"
        piece["target"] = pd.to_numeric(piece.get(target_col), errors="coerce")
        piece["real"] = pd.to_numeric(piece.get(real_col), errors="coerce")
        piece["difference"] = pd.to_numeric(piece.get(diff_col), errors="coerce")
        piece["difference_pc"] = pd.to_numeric(piece.get(diff_pc_col), errors="coerce")
        piece["out_of_tolerance"] = pd.to_numeric(piece.get(out_col), errors="coerce")
        piece["code"] = piece.get(code_col)
        piece["description"] = piece.get(des_col)
        component_rows.append(piece.drop(columns=[c for c in [target_col, real_col, diff_col, diff_pc_col, out_col, code_col, des_col] if c in piece.columns]))
    if not component_rows:
        return pd.DataFrame()
    return pd.concat(component_rows, ignore_index=True)
