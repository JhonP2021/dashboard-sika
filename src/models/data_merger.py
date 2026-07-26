from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.models.data_cleaner import (
    build_formula_dimension,
    clean_bston,
    clean_m1,
    clean_m1_out,
    clean_table_date,
    long_format_m1,
)


@dataclass(frozen=True)
class DashboardData:
    table_date: pd.DataFrame
    m1: pd.DataFrame
    m1_out: pd.DataFrame
    bston: pd.DataFrame
    formula_dimension: pd.DataFrame
    m1_long: pd.DataFrame
    bston_summary: pd.DataFrame


def prepare_dashboard_data(raw_tables: dict[str, pd.DataFrame]) -> DashboardData:
    table_date = clean_table_date(raw_tables.get("table_date", pd.DataFrame()))
    m1 = clean_m1(raw_tables.get("table_report_m1", pd.DataFrame()))
    m1_out = clean_m1_out(raw_tables.get("table_report_m1_out", pd.DataFrame()))
    bston = clean_bston(raw_tables.get("table_report_bston", pd.DataFrame()))

    formula_dimension = build_formula_dimension(m1, bston)
    m1_long = pd.DataFrame()
    bston_summary = (
        bston.groupby("formula_key", dropna=False)
        .agg(
            records=("ID", "count") if "ID" in bston.columns else ("formula_key", "size"),
            avg_bston1=("B_ston1", "mean") if "B_ston1" in bston.columns else ("formula_key", "size"),
            avg_bston2=("B_ston2", "mean") if "B_ston2" in bston.columns else ("formula_key", "size"),
        )
        .reset_index()
    )

    return DashboardData(
        table_date=table_date,
        m1=m1,
        m1_out=m1_out,
        bston=bston,
        formula_dimension=formula_dimension,
        m1_long=m1_long,
        bston_summary=bston_summary,
    )


def apply_dashboard_filters(
    dataset: DashboardData,
    *,
    date_range: tuple | None = None,
    formula_keys: list[str] | None = None,
    operators: list[str] | None = None,
) -> DashboardData:
    m1 = dataset.m1.copy()
    bston = dataset.bston.copy()

    if date_range and "report_day" in m1.columns:
        start, end = date_range
        m1 = m1[(m1["report_day"] >= start) & (m1["report_day"] <= end)]

    if formula_keys:
        m1 = m1[m1["formula_key"].isin(formula_keys)]
        bston = bston[bston["formula_key"].isin(formula_keys)]

    if operators and "OperatorName" in m1.columns:
        m1 = m1[m1["OperatorName"].isin(operators)]

    filtered_long = long_format_m1(m1)
    filtered_bston_summary = (
        bston.groupby("formula_key", dropna=False)
        .agg(
            records=("ID", "count") if "ID" in bston.columns else ("formula_key", "size"),
            avg_bston1=("B_ston1", "mean") if "B_ston1" in bston.columns else ("formula_key", "size"),
            avg_bston2=("B_ston2", "mean") if "B_ston2" in bston.columns else ("formula_key", "size"),
        )
        .reset_index()
    )

    return DashboardData(
        table_date=dataset.table_date,
        m1=m1,
        m1_out=dataset.m1_out,
        bston=bston,
        formula_dimension=dataset.formula_dimension,
        m1_long=filtered_long,
        bston_summary=filtered_bston_summary,
    )
