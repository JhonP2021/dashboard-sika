from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.models.data_cleaner import clean_m1, clean_table_date


@dataclass(frozen=True)
class DashboardData:
    table_date: pd.DataFrame
    m1: pd.DataFrame


def prepare_dashboard_data(raw_tables: dict[str, pd.DataFrame]) -> DashboardData:
    """Unifica las lecturas de M1 y conserva únicamente producción desde 2026."""
    sources = [raw_tables.get("table_report_m1", pd.DataFrame()), raw_tables.get("table_report_m1_out", pd.DataFrame())]
    frames = [frame for frame in sources if not frame.empty]
    raw_m1 = pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()
    raw_dedupe_columns = [column for column in ["ReportDate", "ReportTime", "RecipeBB1name", "NumberBatchDone1", "OperatorName"] if column in raw_m1]
    if raw_dedupe_columns:
        raw_m1 = raw_m1.drop_duplicates(subset=raw_dedupe_columns, keep="last")
    m1 = clean_m1(raw_m1)
    return DashboardData(table_date=clean_table_date(raw_tables.get("table_date", pd.DataFrame())), m1=m1)


def apply_dashboard_filters(
    dataset: DashboardData,
    *,
    date_range: tuple | None = None,
    formula_keys: list[str] | None = None,
    operators: list[str] | None = None,
    lots: list[str] | None = None,
    batch_range: tuple[int, int] | None = None,
) -> DashboardData:
    m1 = dataset.m1.copy()
    if date_range and "report_day" in m1:
        start, end = date_range
        m1 = m1[(m1["report_day"] >= start) & (m1["report_day"] <= end)]
    if formula_keys:
        m1 = m1[m1["formula_key"].isin(formula_keys)]
    if operators and "OperatorName" in m1:
        m1 = m1[m1["OperatorName"].astype(str).isin(operators)]
    if lots and "LOTE" in m1:
        m1 = m1[m1["LOTE"].astype(str).isin(lots)]
    if batch_range and "NumberBatchDone1" in m1:
        m1 = m1[m1["NumberBatchDone1"].between(*batch_range)]
    return DashboardData(table_date=dataset.table_date, m1=m1)
