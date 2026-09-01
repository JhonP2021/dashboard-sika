from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


SILO_COLORS = ["#38bdf8", "#818cf8", "#34d399", "#fbbf24", "#fb7185", "#c084fc", "#ef4444", "#2dd4bf"]


def _style_figure(fig: go.Figure, *, height: int = 350) -> go.Figure:
    fig.update_layout(
        template="plotly_dark", height=height, paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
        font=dict(color="#f8fafc"), margin=dict(l=42, r=20, t=58, b=42),
        legend=dict(title="", bgcolor="rgba(14, 17, 23, .75)", orientation="h", y=-.24), barmode="relative",
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,.08)", color="#cbd5e1")
    fig.update_yaxes(gridcolor="rgba(255,255,255,.08)", zeroline=True, zerolinecolor="rgba(255,255,255,.3)", color="#cbd5e1")
    return fig


def _empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, x=.5, y=.5, showarrow=False, font={"size": 16})
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return _style_figure(fig, height=300)


def plot_silo_differences(df: pd.DataFrame, *, percentage: bool = False) -> go.Figure:
    suffix = "_pct" if percentage else "_kg"
    value_columns = [f"Silo {number}{suffix}" for number in range(1, 9)]
    present_columns = [column for column in value_columns if column in df]
    title = "DIFERENCIA DE PESAJES EN SILOS (%)" if percentage else "DIFERENCIA DE PESAJES EN SILOS (kg)"
    if df.empty or "NumberBatchDone1" not in df or not present_columns:
        return _empty_figure("No hay datos para los filtros seleccionados.")

    plot_data = df[["NumberBatchDone1", *present_columns]].copy().sort_values("NumberBatchDone1")
    plot_data = plot_data.melt("NumberBatchDone1", var_name="Silo", value_name="Diferencia")
    plot_data["Silo"] = plot_data["Silo"].str.replace(suffix, "", regex=False)
    fig = px.bar(
        plot_data, x="NumberBatchDone1", y="Diferencia", color="Silo", barmode="relative", title=title,
        color_discrete_sequence=SILO_COLORS, labels={"NumberBatchDone1": "Número de batch", "Diferencia": "%" if percentage else "kg"},
    )
    fig.update_yaxes(range=[-40, 20] if percentage else [-20, 40])
    return _style_figure(fig)


def plot_material_deviation(long: pd.DataFrame, *, top: int = 12) -> go.Figure:
    """Dispersión de la desviación por material, no por posición de silo.

    Un silo con desviación alta puede serlo por el equipo o por el polvo que
    dosifica; agrupando por material se distingue una cosa de la otra.
    """
    if long.empty or "material" not in long:
        return _empty_figure("No hay materiales mapeados para estos filtros.")

    ranking = long.groupby("material")["pct"].agg(["count", "std"]).dropna(subset=["std"])
    ranking = ranking[ranking["count"] >= 30].sort_values("std", ascending=False).head(top)
    if ranking.empty:
        return _empty_figure("Ningún material con muestras suficientes (mínimo 30).")

    fig = px.bar(
        ranking.reset_index(), x="std", y="material", orientation="h",
        title="DESVIACIÓN POR MATERIAL (σ %)", color="std",
        color_continuous_scale=["#34d399", "#fbbf24", "#ef4444"],
        labels={"std": "Desviación estándar (%)", "material": ""},
        hover_data={"count": ":,"},
    )
    fig.update_layout(coloraxis_showscale=False, yaxis={"categoryorder": "total ascending"})
    return _style_figure(fig, height=420)
