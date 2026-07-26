from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def _empty_figure(message: str):
    fig = go.Figure()
    fig.add_annotation(text=message, x=0.5, y=0.5, showarrow=False, font={"size": 16})
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(template="plotly_white", height=320)
    return fig


def plot_batches_over_time(df: pd.DataFrame):
    if df.empty or "report_day" not in df.columns:
        return _empty_figure("No hay datos suficientes para la serie temporal.")
    grouped = df.groupby("report_day", as_index=False).agg(
        records=("report_day", "size"),
        target=("total_target_components", "sum") if "total_target_components" in df.columns else ("report_day", "size"),
        real=("total_real_components", "sum") if "total_real_components" in df.columns else ("report_day", "size"),
    )
    fig = px.line(grouped, x="report_day", y=["records", "target", "real"], markers=True, title="Evolución diaria")
    fig.update_layout(template="plotly_white", legend_title_text="")
    return fig


def plot_target_vs_real(df: pd.DataFrame):
    if df.empty or "report_day" not in df.columns:
        return _empty_figure("No hay datos suficientes para comparar target vs real.")
    grouped = df.groupby("report_day", as_index=False).agg(
        target=("total_target_components", "sum") if "total_target_components" in df.columns else ("report_day", "size"),
        real=("total_real_components", "sum") if "total_real_components" in df.columns else ("report_day", "size"),
    )
    melted = grouped.melt(id_vars="report_day", value_vars=["target", "real"], var_name="serie", value_name="valor")
    fig = px.bar(melted, x="report_day", y="valor", color="serie", barmode="group", title="Target vs real")
    fig.update_layout(template="plotly_white", legend_title_text="")
    return fig


def plot_top_formulas(df: pd.DataFrame, n: int = 10):
    if df.empty or "Recipe1Name" not in df.columns:
        return _empty_figure("No hay fórmulas para rankear.")
    grouped = df.groupby("Recipe1Name", as_index=False).agg(
        records=("Recipe1Name", "size"),
        real=("total_real_components", "sum") if "total_real_components" in df.columns else ("Recipe1Name", "size"),
    )
    grouped = grouped.sort_values("records", ascending=False).head(n)
    fig = px.bar(grouped, x="records", y="Recipe1Name", orientation="h", title="Top fórmulas por volumen")
    fig.update_layout(template="plotly_white", yaxis_title="")
    return fig


def plot_out_of_tolerance(df: pd.DataFrame):
    if df.empty or "out_of_tolerance_flag" not in df.columns:
        return _empty_figure("No hay señal de tolerancia.")
    grouped = df.groupby("report_day", as_index=False).agg(rate=("out_of_tolerance_flag", "mean"))
    fig = px.area(grouped, x="report_day", y="rate", title="% de lotes con desvío de tolerancia")
    fig.update_layout(template="plotly_white", yaxis_tickformat=".0%")
    return fig


def plot_bston_trend(df: pd.DataFrame):
    if df.empty or not {"snapshot_datetime", "B_ston1", "B_ston2"}.issubset(df.columns):
        return _empty_figure("B_ston no tiene suficientes datos temporales.")
    grouped = df.sort_values("snapshot_datetime")[["snapshot_datetime", "B_ston1", "B_ston2"]].dropna(how="all")
    fig = px.line(grouped, x="snapshot_datetime", y=["B_ston1", "B_ston2"], markers=True, title="Tendencia B_ston")
    fig.update_layout(template="plotly_white", legend_title_text="")
    return fig


def plot_component_gap(df: pd.DataFrame):
    if df.empty or not {"component", "difference"}.issubset(df.columns):
        return _empty_figure("No hay componentes desglosados.")
    grouped = df.groupby("component", as_index=False).agg(avg_difference=("difference", "mean"))
    fig = px.bar(grouped.sort_values("avg_difference"), x="component", y="avg_difference", title="Desvío promedio por componente")
    fig.update_layout(template="plotly_white")
    return fig

