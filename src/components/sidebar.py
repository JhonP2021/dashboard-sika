from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

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
        default_start = max(min_date, max_date - timedelta(days=60))
        applied_key = "dashboard_applied_dates"
        previous = st.session_state.get(applied_key)
        if previous is None or not (min_date <= previous[0] <= previous[1] <= max_date):
            st.session_state[applied_key] = (default_start, max_date)
            st.session_state["dashboard_date_start"] = default_start
            st.session_state["dashboard_date_end"] = max_date

        if st.sidebar.button("Todo el histórico"):
            st.session_state[applied_key] = (min_date, max_date)
            st.session_state["dashboard_date_start"] = min_date
            st.session_state["dashboard_date_end"] = max_date

        with st.sidebar.form("dashboard_dates"):
            start = st.date_input(
                "Desde", min_value=min_date, max_value=max_date,
                key="dashboard_date_start", format="DD/MM/YYYY",
            )
            end = st.date_input(
                "Hasta", min_value=min_date, max_value=max_date,
                key="dashboard_date_end", format="DD/MM/YYYY",
            )
            submitted = st.form_submit_button("Aplicar fechas")
        if submitted:
            if start is None or end is None:
                st.sidebar.error("Completa las dos fechas. Se mantiene el rango anterior.")
            elif start > end:
                st.sidebar.error("Desde debe ser anterior o igual a Hasta. Se mantiene el rango anterior.")
            elif not (min_date <= start <= end <= max_date):
                st.sidebar.error("El rango debe estar dentro de las fechas disponibles.")
            else:
                st.session_state[applied_key] = (start, end)
        date_range = st.session_state[applied_key]
        st.sidebar.caption(
            f"Rango aplicado: {date_range[0]:%d/%m/%Y} – {date_range[1]:%d/%m/%Y} (ambos días incluidos)."
        )

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

    st.sidebar.caption("Actualización automática cada 3 horas.")

    return SidebarFilters(date_range, formula_keys, operators, lots, materials, batch_range)
