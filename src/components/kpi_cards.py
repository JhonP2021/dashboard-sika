from __future__ import annotations

import html
import os

import pandas as pd
import streamlit as st

from src.components.charts import SILO_COLORS
from src.models.silo_metrics import silo_incidents, valid_weighings

# Tasa de incumplimiento -- proporción de pesajes fuera de tolerancia -- a partir
# de la que el silo deja de estar en verde. Son umbrales provisionales, no un
# límite de proceso acordado con planta: se exponen por entorno para poder
# ajustarlos sin tocar código. Deliberadamente no reutilizan el ±5% de
# tolerancia de peso, que mide otra cosa (cuánto se desvía un pesaje, no cuántos
# pesajes pueden desviarse).
ALERT_RATE_AMBER = float(os.getenv("DASHBOARD_ALERT_RATE_AMBER", "2"))
ALERT_RATE_RED = float(os.getenv("DASHBOARD_ALERT_RATE_RED", "5"))
# Por debajo de esta muestra la tasa no significa nada: el Silo 5 tenía 110
# pesajes evaluables en el rango inicial, donde un solo evento mueve la tasa un
# punto entero.
ALERT_MIN_SAMPLES = int(os.getenv("DASHBOARD_ALERT_MIN_SAMPLES", "30"))

STATE_COLORS = {"green": "#34d399", "amber": "#fbbf24", "red": "#ef4444", "gray": "rgba(255,255,255,.15)"}


def render_kpi_cards(metrics: list[tuple[str, str, str | None]]):
    columns = st.columns(min(len(metrics), 5))
    for index, (label, value, delta) in enumerate(metrics):
        with columns[index % len(columns)]:
            st.metric(label=label, value=value, delta=delta)


def _state(stats: dict) -> str:
    """Estado del silo por tasa de incumplimiento, no por un único evento.

    La versión anterior pintaba el silo entero de rojo en cuanto existía un
    pesaje por encima de 2 × tolerancia. Con eso los ocho silos salían rojos en
    el histórico completo: cuanto más largo el período, más seguro es encontrar
    un extremo, aunque el 98% de los pesajes esté dentro. El estado mira ahora
    qué proporción incumple y sobre cuántas muestras; los eventos extremos no
    desaparecen, siguen contados en el tooltip y en rojo en la tabla de detalle.
    """
    if not stats["evaluated"] or stats["evaluated"] < ALERT_MIN_SAMPLES:
        return "gray"
    failure_rate = 100 - stats["compliance_pct"]
    if failure_rate > ALERT_RATE_RED:
        return "red"
    if failure_rate > ALERT_RATE_AMBER:
        return "amber"
    if stats["no_target"] or stats["invalid"]:
        return "amber"
    return "green"


def _tooltip(stats: dict, tolerance: float) -> str:
    if not stats["evaluated"]:
        return "Sin pesajes evaluables en el filtro activo."
    if stats["evaluated"] < ALERT_MIN_SAMPLES:
        muestra = f'Muestra corta: {stats["evaluated"]:,} pesajes, por debajo de {ALERT_MIN_SAMPLES:,}. '
    else:
        muestra = ""
    return (f'{muestra}{stats["compliance_pct"]:.2f}% en tolerancia · '
            f'{stats["outside"]:,} / {stats["evaluated"]:,} fuera de ±{tolerance:g}% · '
            f'{stats["extreme"]:,} eventos > ±{2 * tolerance:g}%')


def render_silo_kpis(df: pd.DataFrame, tolerance: float = 5.0, materials: list[str] | None = None) -> None:
    """Una tarjeta por silo: σ y una barra de desviación relativa al peor del filtro.

    Con ocho cifras juntas la vista no distingue un 2,8 de un 19,7 sin leerlas
    una a una; la barra hace que el silo problemático salte antes de leer. El
    ancho es σ contra el máximo del filtro y el color, el estado por tasa de
    incumplimiento: el desglose completo vive en el tooltip para que la rejilla
    se lea de un vistazo.

    La sigma sale sólo de los pesajes reales del silo. Incluir las filas en las
    que no dosificó (objetivo 0 y real 0, reportado como 0%) la diluía en
    proporción a lo poco que se use ese silo, y con eso invertía el orden: el
    Silo 5, que es el peor, salía a media tabla, y el Silo 8 -- el más usado,
    luego el menos diluido -- se llevaba el máximo y escalaba mal las ocho barras.
    """
    deviations = {}
    for silo in range(1, 9):
        column = f"Silo {silo}_pct"
        if column not in df:
            deviations[silo] = float("nan")
            continue
        values = pd.to_numeric(df[column], errors="coerce")[valid_weighings(df, silo)]
        deviations[silo] = values.std() if len(values) > 1 else float("nan")

    finite = [value for value in deviations.values() if pd.notna(value)]
    peak = max(finite) if finite else 0.0

    tiles = []
    zero_real_total = 0
    no_target_total = 0
    invalid_total = 0
    for silo, stddev in deviations.items():
        stats = silo_incidents(df, silo, tolerance, materials)
        zero_real_total += stats["zero_real"]
        no_target_total += stats["no_target"]
        invalid_total += stats["invalid"]
        value = "—" if pd.isna(stddev) else f"{stddev:.2f}"
        width = round(stddev / peak * 100) if pd.notna(stddev) and peak else 0
        color = STATE_COLORS[_state(stats)]
        tiles.append(
            f'<div class="silo-tile" style="border-top:4px solid {SILO_COLORS[silo - 1]}"'
            f' title="{html.escape(_tooltip(stats, tolerance))}">'
            f'<div class="silo-tile-label">Silo {silo:02d} · σ</div>'
            f'<div class="silo-tile-value">{html.escape(value)}<span>%</span></div>'
            f'<div class="silo-tile-track"><div style="width:{width}%;background:{color}"></div></div>'
            f'</div>'
        )
    st.markdown('<div class="section-label">Variabilidad por silo · σ de los pesajes en que el silo dosificó (%)</div>'
                '<div class="silo-grid">' + ''.join(tiles) + '</div>', unsafe_allow_html=True)
    st.caption(f"Ancho de barra: σ del silo contra la mayor del filtro. Color por tasa de incumplimiento sobre sus "
               f"pesajes: verde = hasta {ALERT_RATE_AMBER:g}% fuera de ±{tolerance:g}%; ámbar = más de "
               f"{ALERT_RATE_AMBER:g}%; gris = menos de {ALERT_MIN_SAMPLES:,} pesajes evaluables; rojo = más de "
               f"{ALERT_RATE_RED:g}%. El color no sale de σ ni de un único evento extremo. Umbrales provisionales, "
               "pendientes de acordar con planta. Pasa el puntero por una tarjeta para ver el desglose.")
    if zero_real_total:
        st.warning(f"{zero_real_total:,} registros de silo tienen objetivo positivo y peso real cero. Revisa si corresponden a falta de dosificación, arranque o captura parcial; no se han descartado.")
    if no_target_total:
        st.warning(f"{no_target_total:,} registros de silo tienen peso real positivo sin objetivo. No se incluyen en el porcentaje de cumplimiento; se conservan los valores originales para σ.")
    if invalid_total:
        st.warning(f"{invalid_total:,} registros de silo no tienen porcentaje o pesos válidos dentro del filtro activo.")
