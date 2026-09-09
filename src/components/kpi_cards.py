from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from src.components.charts import SILO_COLORS


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


def render_silo_kpis(df: pd.DataFrame, tolerance: float = 5.0, materials: list[str] | None = None) -> None:
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

    tiles = []
    no_target_total = 0
    missing_total = 0
    for silo, stddev in deviations.items():
        values = pd.to_numeric(df.get(f"Silo {silo}_pct", pd.Series(index=df.index, dtype=float)), errors="coerce")
        in_scope = pd.Series(True, index=df.index)
        material_col = f"Silo {silo}_material"
        if materials and material_col in df:
            in_scope = df[material_col].isin(materials)
        unused = pd.Series(False, index=df.index)
        no_target = pd.Series(False, index=df.index)
        target, actual = f"Silo{silo}Target", f"Silo{silo}Real"
        if target in df and actual in df:
            t = pd.to_numeric(df[target], errors="coerce")
            r = pd.to_numeric(df[actual], errors="coerce")
            unused = t.eq(0) & r.eq(0)
            no_target = t.eq(0) & r.notna() & r.ne(0)
        evaluated = in_scope & ~unused & ~no_target & values.notna()
        count = int(evaluated.sum())
        outside = int((evaluated & values.abs().gt(tolerance)).sum())
        high = int((evaluated & values.abs().gt(2 * tolerance)).sum())
        missing = int((in_scope & ~unused & values.isna()).sum())
        no_target_count = int((in_scope & no_target).sum())
        no_target_total += no_target_count
        missing_total += missing
        if high:
            level, label = "red", "● Desvíos altos"
        elif outside:
            level, label = "amber", "▲ Revisar"
        elif missing or no_target_count:
            level, label = "amber", "▲ Revisar datos"
        elif count:
            level, label = "green", "✓ En tolerancia"
        else:
            level, label = "gray", "— Sin pesajes"
        value = "—" if pd.isna(stddev) else f"{stddev:.2f}"
        width = round(stddev / peak * 100) if pd.notna(stddev) and peak else 0
        detail = f"{outside:,} / {count:,} fuera de ±{tolerance:g}%" if count else "Sin muestras evaluables"
        tiles.append(
            f'<div class="silo-tile" style="border-top:4px solid {SILO_COLORS[silo - 1]}">'
            f'<div class="silo-tile-label">Silo {silo:02d} · σ</div>'
            f'<div class="silo-tile-value">{html.escape(value)}<span>%</span></div>'
            f'<div class="silo-tile-track"><div style="width:{width}%;background:{SILO_COLORS[silo - 1]}"></div></div>'
            f'<div class="status-pill {level}">{label}</div><div class="silo-note">{detail}</div></div>'
        )
    st.markdown('<div class="section-label">Variabilidad por silo · σ de valores reportados, incluidos ceros (%)</div>'
                '<div class="silo-grid">' + ''.join(tiles) + '</div>', unsafe_allow_html=True)
    st.caption(f"Estado por pesajes: verde = ninguno fuera de ±{tolerance:g}%; ámbar = hay desvíos; "
               f"rojo = hay desvíos mayores de ±{2*tolerance:g}%. El estado no se calcula a partir de σ. "
               "Se excluyen del estado silos sin uso, sin objetivo o sin porcentaje válido.")
    if no_target_total:
        st.warning(f"{no_target_total:,} registros de silo tienen peso real sin objetivo. Su 0% reportado no permite evaluar tolerancia; revisa los pesos en la fuente.")
    if missing_total:
        st.warning(f"{missing_total:,} registros de silo no tienen porcentaje disponible dentro del filtro activo.")
