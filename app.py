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
    return tuple(path.stat().st_mtime if path and path.exists() else 0.0 for path in paths)


# Filas que se pasan al Styler. Colorear celda a celda es caro y pandas corta en
# 262.144 celdas: con 11 columnas son ~23.800 filas, justo lo que había antes de
# levantar el recorte por año. La tabla es una vista de detalle de 430 px, así
# que pintar el histórico entero no aporta nada.
DETAIL_ROWS = 1000


def _detail_table(df: pd.DataFrame, tolerance: float) -> pd.io.formats.style.Styler:
    # Lo más reciente primero: el batch que acaba de salir mal es el que se mira.
    recent = df.sort_values("report_datetime", ascending=False, kind="stable").head(DETAIL_ROWS)
    result = pd.DataFrame()
    result["FECHA"] = pd.to_datetime(recent.get("report_datetime"), errors="coerce").dt.strftime("%Y-%m-%d %H:%M")
    result["OperatorName"] = recent.get("OperatorName", "")
    result["RecipeBB1name"] = recent.get("RecipeBB1name", "")
    for silo in range(1, 9):
        result[f"s{silo} dif %"] = pd.to_numeric(recent.get(f"Silo {silo}_pct"), errors="coerce")

    deviation_columns = [f"s{silo} dif %" for silo in range(1, 9)]
    def highlight(value):
        return "background-color: #7f1d1d; color: #ffffff; font-weight: 700" if pd.notna(value) and abs(value) > tolerance else ""
    return result.style.map(highlight, subset=deviation_columns).format({column: "{:.2f}%" for column in deviation_columns}, na_rep="—")


def main() -> None:
    settings = get_settings()
    st.title("Control de desviaciones de pesaje")

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

    st.sidebar.metric("Batches fabricados", f"{len(filtered):,}")
    tolerance = float(os.getenv("DASHBOARD_TOLERANCE_PCT", "5"))
    # Una sola línea de contexto: el detalle de tolerancia vive en la tarjeta.
    st.caption(
        f"{len(filtered):,} batches bajo el filtro activo · modo {settings.mode} · caché 3 h"
    )
    render_silo_kpis(filtered, tolerance)

    # La distribución va en bandas a ancho completo: primero el dato crudo
    # (la tabla, once columnas que necesitan el ancho entero) y debajo las
    # lecturas agregadas, emparejadas por la pregunta que responden. Dentro de
    # cada banda las columnas son iguales para que los dos gráficos compartan
    # geometría y no se vean corridos.
    shown = min(len(filtered), DETAIL_ROWS)
    subtitle = (f"{shown:,} más recientes de {len(filtered):,}" if len(filtered) > DETAIL_ROWS
                else f"{len(filtered):,} filas")
    with card("Detalle de batches", f"{subtitle} · rojo sobre ±{tolerance:g}%"):
        st.dataframe(_detail_table(filtered, tolerance), use_container_width=True, hide_index=True, height=430)

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
