from __future__ import annotations

from datetime import datetime
import traceback

import pandas as pd
import streamlit as st

from config.settings import get_settings
from src.components.charts import (
    plot_batches_over_time,
    plot_bston_trend,
    plot_component_gap,
    plot_out_of_tolerance,
    plot_target_vs_real,
    plot_top_formulas,
)
from src.components.kpi_cards import render_kpi_cards
from src.components.sidebar import render_sidebar
from src.data.access_loader import AccessTableLoader
from src.data.csv_loader import CSVTableLoader
from src.models.data_merger import apply_dashboard_filters, prepare_dashboard_data


st.set_page_config(page_title="Dashboard Modular Sika", layout="wide")


@st.cache_data(show_spinner=True)
def load_dashboard_data(mode: str, source_fingerprint: tuple):
    try:
        settings = get_settings()
        loader = CSVTableLoader(settings) if mode == "DEV" else AccessTableLoader(settings)
        raw_tables = loader.load_all()
        return prepare_dashboard_data(raw_tables)
    except Exception as e:
        st.error(f"Error cargando datos: {str(e)}")
        st.write(traceback.format_exc())
        raise


def _format_number(value, decimals: int = 0):
    if pd.isna(value):
        return "-"
    return f"{value:,.{decimals}f}" if decimals else f"{int(round(value)):,}"


def main():
    try:
        settings = get_settings()
        st.title("Dashboard Modular de Producción")
        st.caption(f"Modo activo: {settings.mode} | Origen: CSV en DEV / Access en PROD")

        if settings.mode == "DEV":
            source_fingerprint = tuple(
                path.stat().st_mtime if path.exists() else 0.0 for path in settings.csv_paths.values()
            )
        else:
            source_fingerprint = (settings.access_db_path.stat().st_mtime if settings.access_db_path and settings.access_db_path.exists() else 0.0,)

        dataset = load_dashboard_data(settings.mode, source_fingerprint)

        if not dataset.formula_dimension.empty:
            formula_mapping = {
                row["display_name"]: row["formula_key"]
                for _, row in dataset.formula_dimension.fillna("").drop_duplicates(subset=["formula_key"]).iterrows()
                if row["formula_key"]
            }
        else:
            unique_formulas = sorted(dataset.m1["formula_key"].dropna().astype(str).unique().tolist())
            formula_mapping = {formula: formula for formula in unique_formulas if formula}
        operators = sorted(dataset.m1["OperatorName"].dropna().astype(str).unique().tolist()) if "OperatorName" in dataset.m1.columns else []

        min_date = dataset.m1["report_day"].min() if "report_day" in dataset.m1.columns and not dataset.m1.empty else None
        max_date = dataset.m1["report_day"].max() if "report_day" in dataset.m1.columns and not dataset.m1.empty else None

        filters = render_sidebar(
            formula_options=formula_mapping,
            available_operators=operators,
            min_date=min_date,
            max_date=max_date,
        )

        filtered = apply_dashboard_filters(
            dataset,
            date_range=filters.date_range,
            formula_keys=filters.formula_keys,
            operators=filters.operators,
        )

        total_records = len(filtered.m1)
        total_target = filtered.m1["total_target_components"].sum() if "total_target_components" in filtered.m1.columns else 0
        total_real = filtered.m1["total_real_components"].sum() if "total_real_components" in filtered.m1.columns else 0
        yield_pct = (total_real / total_target * 100) if total_target else 0
        out_rate = filtered.m1["out_of_tolerance_flag"].mean() * 100 if "out_of_tolerance_flag" in filtered.m1.columns and len(filtered.m1) else 0
        bston_rows = len(filtered.bston)

        render_kpi_cards(
            [
                ("Registros M1", _format_number(total_records), None),
                ("Target total", _format_number(total_target), None),
                ("Real total", _format_number(total_real), f"{yield_pct:.1f}%"),
                ("Desvío OT", f"{out_rate:.1f}%", None),
                ("Registros BSton", _format_number(bston_rows), None),
            ]
        )

        tab_overview, tab_bston, tab_data = st.tabs(["Resumen M1", "Detalle BSton", "Datos"])

        with tab_overview:
            col_left, col_right = st.columns(2)
            with col_left:
                st.plotly_chart(plot_batches_over_time(filtered.m1), use_container_width=True)
                st.plotly_chart(plot_out_of_tolerance(filtered.m1), use_container_width=True)
            with col_right:
                st.plotly_chart(plot_target_vs_real(filtered.m1), use_container_width=True)
                st.plotly_chart(plot_top_formulas(filtered.m1), use_container_width=True)
            st.plotly_chart(plot_component_gap(filtered.m1_long), use_container_width=True)

        with tab_bston:
            st.plotly_chart(plot_bston_trend(filtered.bston), use_container_width=True)
            if not filtered.bston_summary.empty:
                st.dataframe(filtered.bston_summary, use_container_width=True, hide_index=True)
            else:
                st.info("No hay datos de BSton para los filtros seleccionados.")

        with tab_data:
            if not dataset.table_date.empty:
                st.subheader("Tabla de control")
                st.dataframe(dataset.table_date, use_container_width=True, hide_index=True)
            st.subheader("M1 filtrado")
            st.dataframe(filtered.m1.head(1000), use_container_width=True, hide_index=True)
    
    except Exception as e:
        st.error("❌ Error en el Dashboard")
        st.error(f"Detalles del error: {str(e)}")
        st.write(traceback.format_exc())


if __name__ == "__main__":
    main()
