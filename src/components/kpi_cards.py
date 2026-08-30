from __future__ import annotations

import pandas as pd
import streamlit as st


def render_kpi_cards(metrics: list[tuple[str, str, str | None]]):
    columns = st.columns(min(len(metrics), 5))
    for index, (label, value, delta) in enumerate(metrics):
        with columns[index % len(columns)]:
            st.metric(label=label, value=value, delta=delta)


def render_silo_kpis(df: pd.DataFrame) -> None:
    columns = st.columns(8)
    for silo in range(1, 9):
        value_col = f"Silo {silo}_pct"
        stddev = pd.to_numeric(df[value_col], errors="coerce").std() if value_col in df else float("nan")
        with columns[silo - 1]:
            st.metric(
                f"Silo {silo}" + (" ⚠" if silo == 7 else ""),
                "—" if pd.isna(stddev) else f"{stddev:.2f}%",
                help="Desviación estándar de la diferencia porcentual en el filtro activo.",
            )
