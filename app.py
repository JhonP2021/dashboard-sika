from __future__ import annotations

import os
import traceback

import pandas as pd
import streamlit as st

from config.settings import get_settings
from src.components.charts import (
    plot_material_deviation, plot_operator_deviation, plot_silo_differences,
)
from src.components.kpi_cards import render_silo_kpis
from src.components.layout import CARD_CSS, card
from src.components.sidebar import render_sidebar
from src.data.access_loader import AccessTableLoader
from src.data.csv_loader import CSVTableLoader
from src.models.data_merger import (
    apply_dashboard_filters, material_long, operator_long, prepare_dashboard_data,
    status_canonicals,
)


st.set_page_config(page_title="Control de Pesajes · Sika", layout="wide")
st.markdown(CARD_CSS, unsafe_allow_html=True)


@st.cache_data(ttl=3 * 60 * 60, show_spinner="Actualizando datos de producción...")
def load_dashboard_data(mode: str, source_fingerprint: tuple):
    settings = get_settings()
    loader = CSVTableLoader(settings) if mode == "DEV" else AccessTableLoader(settings)
    return prepare_dashboard_data(loader.load_all())


def _source_fingerprint(settings) -> tuple:
    paths = settings.csv_paths.values() if settings.mode == "DEV" else [settings.access_db_path]
    return ("reported-silo-values-v2", settings.min_year,
            settings.materials_map_path.stat().st_mtime if settings.materials_map_path.exists() else 0,
            *(path.stat().st_mtime if path and path.exists() else 0.0 for path in paths))


# Filas que se pasan al Styler. Colorear celda a celda es caro y pandas corta en
# 262.144 celdas: con 11 columnas son ~23.800 filas, justo lo que había antes de
# levantar el recorte por año. La tabla es una vista de detalle de 430 px, así
# que pintar el histórico entero no aporta nada.
DETAIL_ROWS = 1000


def _detail_values(recent: pd.DataFrame, materials: list[str] | None = None) -> pd.DataFrame:
    result = pd.DataFrame()
    result["FECHA"] = pd.to_datetime(recent.get("report_datetime"), errors="coerce").dt.strftime("%Y-%m-%d %H:%M")
    result["OperatorName"] = recent.get("OperatorName", "")
    result["RecipeBB1name"] = recent.get("RecipeBB1name", "")
    for silo in range(1, 9):
        values = pd.to_numeric(recent.get(f"Silo {silo}_pct", pd.Series(index=recent.index, dtype=float)), errors="coerce")
        display = values.map({value: f"{value:.2f}%" for value in values.dropna().unique()}).fillna("Sin dato")
        material_column = f"Silo {silo}_material"
        if material_column in recent:
            # Un valor anulado por el filtro de material tampoco es un dato perdido.
            selected = materials or []
            if selected:
                display.loc[~recent[material_column].isin(selected)] = "Fuera del filtro"
        result[f"s{silo} dif %"] = display

    return result


def _detail_table(result: pd.DataFrame, tolerance: float) -> pd.io.formats.style.Styler:
    deviation_columns = [f"s{silo} dif %" for silo in range(1, 9)]
    def highlight(value):
        if value == "Sin dato":
            return "background-color: rgba(251,191,36,.15); color: #fcd34d; font-weight: 600"
        if value == "Fuera del filtro":
            return "background-color: rgba(255,255,255,.05); color: #8f9bab"
        if isinstance(value, str) and value.endswith("%"):
            magnitude = abs(float(value[:-1]))
            if magnitude > 2 * tolerance:
                return "background-color: rgba(239,68,68,.18); color: #fca5a5; font-weight: 700"
            if magnitude > tolerance:
                return "background-color: rgba(251,191,36,.15); color: #fcd34d; font-weight: 700"
        return ""
    return result.style.map(highlight, subset=deviation_columns)


def main() -> None:
    settings = get_settings()
    st.markdown('<div class="hero"><div><h1>Control de desviaciones de pesaje</h1></div></div>', unsafe_allow_html=True)

    dataset = load_dashboard_data(settings.mode, _source_fingerprint(settings))
    data = dataset.m1
    if data.empty:
        st.warning("La fuente actual no tiene registros de producción.")
        return

    formula_mapping = {
        label: key for label, key in data[["RecipeBB1name", "formula_key"]].drop_duplicates().sort_values("RecipeBB1name").itertuples(index=False, name=None)
        if label and key
    }
    operators = sorted(o for o in data["OperatorName"].dropna().astype(str).unique() if o) if "OperatorName" in data else []
    lots = sorted(l for l in data["LOTE"].dropna().astype(str).unique() if l) if "LOTE" in data else []
    batch_series = pd.to_numeric(data.get("NumberBatchDone1"), errors="coerce").dropna()
    batch_bounds = (int(batch_series.min()), int(batch_series.max())) if not batch_series.empty else None
    hidden = status_canonicals()
    material_columns = [f"Silo {silo}_material" for silo in range(1, 9) if f"Silo {silo}_material" in data]
    available_materials = sorted(
        {m for column in material_columns for m in data[column].dropna().unique() if m and m not in hidden}
    )
    filters = render_sidebar(
        formula_options=formula_mapping, available_operators=operators, available_lots=lots,
        min_date=data["report_day"].min(), max_date=data["report_day"].max(), batch_bounds=batch_bounds,
        available_materials=available_materials,
    )
    filtered = apply_dashboard_filters(
        dataset, date_range=filters.date_range, formula_keys=filters.formula_keys,
        operators=filters.operators, lots=filters.lots, batch_range=filters.batch_range,
        materials=filters.materials,
    ).m1

    tolerance = float(os.getenv("DASHBOARD_TOLERANCE_PCT", "5"))
    period = (f"{filters.date_range[0]:%d/%m/%Y} — {filters.date_range[1]:%d/%m/%Y}"
              if filters.date_range else "Todo el histórico")
    st.markdown(
        f'<div class="summary"><div><div class="summary-number">{len(filtered):,}</div>'
        f'<div class="summary-label">Batches en el período</div></div>'
        f'<div class="summary-period">{period}<div class="summary-label">Tolerancia de pesaje ±{tolerance:g}%</div></div></div>',
        unsafe_allow_html=True,
    )
    render_silo_kpis(filtered, tolerance, filters.materials)

    # La distribución va en bandas a ancho completo: primero el dato crudo
    # (la tabla, once columnas que necesitan el ancho entero) y debajo las
    # lecturas agregadas, emparejadas por la pregunta que responden. Dentro de
    # cada banda las columnas son iguales para que los dos gráficos compartan
    # geometría y no se vean corridos.
    with card("Detalle de batches", f"{len(filtered):,} registros · hasta {DETAIL_ROWS:,} más recientes"):
        recent = filtered.sort_values("report_datetime", ascending=False, kind="stable").head(DETAIL_ROWS)
        detail = _detail_values(recent, filters.materials)
        st.caption(f"Ámbar: más de ±{tolerance:g}% · Rojo: más de ±{2*tolerance:g}% · Gris: fuera del filtro. Se conservan los ceros reportados de silos sin uso.")
        st.dataframe(_detail_table(detail, tolerance), use_container_width=True, hide_index=True, height=430)

    st.caption("Gráficos de silos: hasta 500 bloques cronológicos; punto = promedio, barra = mínimo–máximo. Incluyen todo el filtro activo.")
    kg_column, pct_column = st.columns(2, gap="medium")
    with kg_column, card("Diferencia de pesajes en silos", "kg"):
        st.plotly_chart(plot_silo_differences(filtered), use_container_width=True)
    with pct_column, card("Diferencia de pesajes en silos", "%"):
        st.plotly_chart(plot_silo_differences(filtered, percentage=True), use_container_width=True)

    material_column, operator_column = st.columns(2, gap="medium")
    with material_column, card("Desviación por material", "σ %"):
        st.plotly_chart(plot_material_deviation(material_long(filtered, exclude=hidden)), use_container_width=True)
    with operator_column, card("Desviación por operario", "σ %"):
        st.plotly_chart(plot_operator_deviation(operator_long(filtered)), use_container_width=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        st.error("No fue posible cargar el dashboard.")
        st.exception(error)
