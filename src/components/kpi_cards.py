from __future__ import annotations

import html

import pandas as pd
import streamlit as st


def render_kpi_cards(metrics: list[tuple[str, str, str | None]]):
    columns = st.columns(min(len(metrics), 5))
    for index, (label, value, delta) in enumerate(metrics):
        with columns[index % len(columns)]:
            st.metric(label=label, value=value, delta=delta)


def _severity(stddev: float, tolerance: float) -> str:
    """Verde dentro de tolerancia, ámbar hasta el doble, rojo por encima."""
    if stddev > 2 * tolerance:
        return "#ef4444"
    if stddev > tolerance:
        return "#fbbf24"
    return "#34d399"


def render_silo_kpis(df: pd.DataFrame, tolerance: float = 5.0) -> None:
    """Una tarjeta por silo con barra de severidad relativa al peor del filtro.

    Con ocho cifras juntas la vista no distingue un 2,8 de un 19,7 sin leerlas
    una a una; la barra hace que el silo problemático salte antes de leer.
    """
    deviations = {}
    for silo in range(1, 9):
        column = f"Silo {silo}_pct"
        deviations[silo] = (
            pd.to_numeric(df[column], errors="coerce").std() if column in df else float("nan")
        )

    finite = [value for value in deviations.values() if pd.notna(value)]
    peak = max(finite) if finite else 0.0

    columns = st.columns(8)
    for silo, column in zip(range(1, 9), columns):
        stddev = deviations[silo]
        if pd.isna(stddev):
            value, color, width = "—", "rgba(255,255,255,.15)", 0
        else:
            value = f"{stddev:.2f}"
            color = _severity(stddev, tolerance)
            width = round(stddev / peak * 100) if peak else 0
        alert = color == "#ef4444"
        column.markdown(
            f"""<div class="silo-tile" style="border-color: {'rgba(239,68,68,.45)' if alert else 'rgba(255,255,255,.08)'}"
                     title="Desviación estándar de la diferencia porcentual en el filtro activo.">
                  <div class="silo-tile-label" style="color: {'#fca5a5' if alert else '#94a3b8'}">Silo {silo}</div>
                  <div class="silo-tile-value" style="color: {'#fecaca' if alert else '#f9fafb'}">{html.escape(value)}<span>%</span></div>
                  <div class="silo-tile-track"><div style="width: {width}%; background: {color}"></div></div>
                </div>""",
            unsafe_allow_html=True,
        )
