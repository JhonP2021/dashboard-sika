from __future__ import annotations

import os
import traceback

import pandas as pd
import streamlit as st

from config.settings import get_settings
from src.components.charts import plot_silo_differences
from src.components.kpi_cards import render_silo_kpis
from src.components.sidebar import render_sidebar
from src.data.access_loader import AccessTableLoader
from src.data.csv_loader import CSVTableLoader
from src.models.data_merger import apply_dashboard_filters, prepare_dashboard_data


st.set_page_config(page_title="Control de Pesajes · Sika", layout="wide")
st.markdown("""
<style>
.stApp { background: linear-gradient(180deg, #0e1117 0%, #111827 100%); color: #f9fafb; }
[data-testid="stSidebar"] { background: #121722; border-right: 1px solid rgba(255,255,255,.08); }
.block-container { padding-top: 1.2rem; padding-bottom: 1.5rem; }
div[data-testid="stMetric"] { background: #151a24; border: 1px solid rgba(255,255,255,.08); border-radius: 12px; padding: .7rem .8rem; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=3 * 60 * 60, show_spinner="Actualizando datos de producción...")
def load_dashboard_data(mode: str, source_fingerprint: tuple):
    settings = get_settings()
    loader = CSVTableLoader(settings) if mode == "DEV" else AccessTableLoader(settings)
    return prepare_dashboard_data(loader.load_all())


def _source_fingerprint(settings) -> tuple:
    paths = settings.csv_paths.values() if settings.mode == "DEV" else [settings.access_db_path]
    return tuple(path.stat().st_mtime if path and path.exists() else 0.0 for path in paths)


def _detail_table(df: pd.DataFrame, tolerance: float) -> pd.io.formats.style.Styler:
    result = pd.DataFrame()
    result["FECHA"] = pd.to_datetime(df.get("report_datetime"), errors="coerce").dt.strftime("%Y-%m-%d %H:%M")
    result["OperatorName"] = df.get("OperatorName", "")
    result["RecipeBB1name"] = df.get("RecipeBB1name", "")
    for silo in range(1, 9):
        result[f"s{silo} dif %"] = pd.to_numeric(df.get(f"Silo {silo}_pct"), errors="coerce")

    deviation_columns = [f"s{silo} dif %" for silo in range(1, 9)]
    def highlight(value):
        return "background-color: #7f1d1d; color: #ffffff; font-weight: 700" if pd.notna(value) and abs(value) > tolerance else ""
    return result.style.map(highlight, subset=deviation_columns).format({column: "{:.2f}%" for column in deviation_columns}, na_rep="—")


def main() -> None:
    settings = get_settings()
    st.title("Control de desviaciones de pesaje")
    st.caption(f"Modo {settings.mode} · Datos desde 2026 · Recarga de caché cada 3 horas")

    dataset = load_dashboard_data(settings.mode, _source_fingerprint(settings))
    data = dataset.m1
    if data.empty:
        st.warning("No hay registros de producción desde 2026 en la fuente actual.")
        return

    formula_mapping = {
        label: key for label, key in data[["RecipeBB1name", "formula_key"]].drop_duplicates().sort_values("RecipeBB1name").itertuples(index=False, name=None)
        if label and key
    }
    operators = sorted(data["OperatorName"].dropna().astype(str).unique()) if "OperatorName" in data else []
    lots = sorted(data["LOTE"].dropna().astype(str).unique()) if "LOTE" in data else []
    batch_series = pd.to_numeric(data.get("NumberBatchDone1"), errors="coerce").dropna()
    batch_bounds = (int(batch_series.min()), int(batch_series.max())) if not batch_series.empty else None
    filters = render_sidebar(
        formula_options=formula_mapping, available_operators=operators, available_lots=lots,
        min_date=data["report_day"].min(), max_date=data["report_day"].max(), batch_bounds=batch_bounds,
    )
    filtered = apply_dashboard_filters(
        dataset, date_range=filters.date_range, formula_keys=filters.formula_keys,
        operators=filters.operators, lots=filters.lots, batch_range=filters.batch_range,
    ).m1

    st.sidebar.metric("Batches fabricados", f"{len(filtered):,}")
    tolerance = float(os.getenv("DASHBOARD_TOLERANCE_PCT", "5"))
    st.caption(f"{len(filtered):,} batches bajo el filtro activo · celdas rojas: desvío superior a ±{tolerance:g}%.")
    render_silo_kpis(filtered)

    left, right = st.columns((1.12, 1), gap="large")
    with left:
        st.subheader("Detalle de batches")
        st.dataframe(_detail_table(filtered, tolerance), use_container_width=True, hide_index=True, height=710)
    with right:
        st.plotly_chart(plot_silo_differences(filtered), use_container_width=True)
        st.plotly_chart(plot_silo_differences(filtered, percentage=True), use_container_width=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        st.error("No fue posible cargar el dashboard.")
        st.exception(error)
