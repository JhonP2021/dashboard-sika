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


def render_sidebar(*, formula_options: dict[str, str], available_operators: list[str], min_date, max_date) -> SidebarFilters:
    st.sidebar.header("Filtros globales")

    date_range = None
    if min_date is not None and max_date is not None:
        selected_dates = st.sidebar.date_input(
            "Rango de fechas",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )
        if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
            date_range = selected_dates

    selected_formula_labels = st.sidebar.multiselect(
        "Formulas",
        options=list(formula_options.keys()),
        default=list(formula_options.keys()),
        help="Filtra por fórmula/receta sin romper la relación entre tablas.",
    )
    formula_keys = [formula_options[label] for label in selected_formula_labels]

    operators = st.sidebar.multiselect(
        "Operadores",
        options=available_operators,
        default=available_operators[:],
    )

    st.sidebar.caption("La app usa CSV en DEV y Microsoft Access en PROD.")

    return SidebarFilters(date_range=date_range, formula_keys=formula_keys, operators=operators)
