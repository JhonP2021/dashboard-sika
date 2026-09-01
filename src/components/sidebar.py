from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd
import streamlit as st


@dataclass(frozen=True)
class SidebarFilters:
    date_range: tuple[date, date] | None
    formula_keys: list[str]
    operators: list[str]
    lots: list[str]
    materials: list[str]
    batch_range: tuple[int, int] | None


def render_sidebar(*, formula_options: dict[str, str], available_operators: list[str], available_lots: list[str], min_date, max_date, batch_bounds: tuple[int, int] | None, available_materials: list[str] | None = None) -> SidebarFilters:
    st.sidebar.header("Filtros")

    date_range = None
    if min_date is not None and max_date is not None:
        default_start = max(min_date, date(2026, 5, 1))
        selected_dates = st.sidebar.date_input(
            "Rango de fechas",
            value=(default_start, max_date),
            min_value=min_date,
            max_value=max_date,
        )
        if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
            date_range = selected_dates

    selected_formula_labels = st.sidebar.multiselect(
        "Producto / fórmula",
        options=list(formula_options.keys()),
        default=list(formula_options.keys()),
    )
    formula_keys = [formula_options[label] for label in selected_formula_labels]

    operators = st.sidebar.multiselect(
        "Operario",
        options=available_operators,
        default=available_operators[:],
    )

    lots: list[str] = []
    if available_lots:
        lots = st.sidebar.multiselect("Lote", options=available_lots, default=available_lots)

    materials: list[str] = []
    if available_materials:
        # Por defecto ninguno: el filtro por material acota, no restringe de salida.
        materials = st.sidebar.multiselect(
            "Material", options=available_materials, default=[],
            help="Deja vacío para ver todos los batches.",
        )

    batch_range = None
    if batch_bounds is not None:
        batch_range = st.sidebar.slider(
            "Rango de batches", min_value=batch_bounds[0], max_value=batch_bounds[1],
            value=batch_bounds, step=1, help="Número de batch reportado por el mezclador.",
        )

    st.sidebar.caption("Datos desde 2026 · actualización automática cada 3 horas.")

    return SidebarFilters(date_range, formula_keys, operators, lots, materials, batch_range)
