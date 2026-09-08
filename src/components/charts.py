from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


SILO_COLORS = ["#38bdf8", "#818cf8", "#34d399", "#fbbf24", "#fb7185", "#c084fc", "#ef4444", "#2dd4bf"]


# Margen izquierdo por banda. Plotly lo calcula por gráfico según lo que midan
# las etiquetas del eje, así que dos gráficos vecinos con etiquetas de distinto
# largo ('OMYACARB' contra 'MG') arrancan el trazado en x distintos y la fila se
# ve descuadrada. Fijándolo por banda, las áreas de trazado quedan alineadas.
BAND_LEFT_MARGIN = 52
RANKING_LEFT_MARGIN = 132


def _style_figure(fig: go.Figure, *, height: int = 340, left: int = BAND_LEFT_MARGIN) -> go.Figure:
    fig.update_layout(
        template="plotly_dark", height=height, paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
        font=dict(color="#f8fafc"), margin=dict(l=left, r=16, t=10, b=40),
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


# Limita el trabajo del navegador, sin descartar registros del histórico.
SILO_PLOT_BLOCKS = 500


def plot_silo_differences(df: pd.DataFrame, *, percentage: bool = False) -> go.Figure:
    suffix = "_pct" if percentage else "_kg"
    columns = [f"Silo {number}{suffix}" for number in range(1, 9) if f"Silo {number}{suffix}" in df]
    if df.empty or "report_datetime" not in df or not columns:
        return _empty_figure("No hay datos para los filtros seleccionados.")

    data = df[["report_datetime", *columns]].dropna(subset=["report_datetime"])
    data = data.sort_values("report_datetime", kind="stable").reset_index(drop=True)
    if data.empty:
        return _empty_figure("No hay datos para los filtros seleccionados.")
    block_size = max(1, (len(data) + SILO_PLOT_BLOCKS - 1) // SILO_PLOT_BLOCKS)
    groups = data.groupby(data.index // block_size)
    dates = groups["report_datetime"].agg(["first", "last"])
    fig = go.Figure()
    for column in columns:
        stats = groups[column].agg(["mean", "min", "max", "count"])
        silo = int(column.split()[1].split("_")[0])
        fig.add_trace(go.Scatter(
            x=dates["first"], y=stats["mean"], name=f"Silo {silo}",
            mode="markers", marker=dict(size=4, color=SILO_COLORS[silo - 1]),
            error_y=dict(type="data", symmetric=False,
                         array=stats["max"] - stats["mean"],
                         arrayminus=stats["mean"] - stats["min"], thickness=1, width=2),
            customdata=pd.DataFrame({"end": dates["last"].astype(str),
                                     "count": stats["count"], "min": stats["min"], "max": stats["max"]}).to_numpy(),
            hovertemplate="Desde %{x}<br>Hasta %{customdata[0]}<br>Promedio: %{y:.2f}"
                          "<br>Mínimo: %{customdata[2]:.2f}<br>Máximo: %{customdata[3]:.2f}"
                          "<br>Pesajes: %{customdata[1]}<extra>%{fullData.name}</extra>",
        ))
    fig.update_xaxes(title="Fecha · bloques cronológicos")
    fig.update_yaxes(title="%" if percentage else "kg")
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
        ranking.reset_index(), x="std", y="material", orientation="h", color="std",
        color_continuous_scale=["#34d399", "#fbbf24", "#ef4444"],
        labels={"std": "Desviación estándar (%)", "material": ""},
        hover_data={"count": ":,"},
    )
    fig.update_layout(coloraxis_showscale=False, yaxis={"categoryorder": "total ascending", "automargin": False})
    return _style_figure(fig, height=300, left=RANKING_LEFT_MARGIN)


def plot_operator_deviation(long: pd.DataFrame) -> go.Figure:
    """Desviación por operario, con el nº de pesajes detrás de cada barra.

    Contraparte de `plot_material_deviation`: si un material se desvía con todos
    los operarios es del polvo, y si sólo con uno es de operación.
    """
    if long.empty or "operario" not in long:
        return _empty_figure("No hay operarios en los filtros seleccionados.")

    ranking = long.groupby("operario")["pct"].agg(["count", "std"]).dropna(subset=["std"])
    ranking = ranking[ranking["count"] >= 30].sort_values("std", ascending=False)
    if ranking.empty:
        return _empty_figure("Ningún operario con muestras suficientes (mínimo 30).")

    fig = px.bar(
        ranking.reset_index(), x="std", y="operario", orientation="h", color="std",
        color_continuous_scale=["#34d399", "#fbbf24", "#ef4444"],
        labels={"std": "Desviación estándar (%)", "operario": ""},
        hover_data={"count": ":,"},
    )
    fig.update_layout(coloraxis_showscale=False, yaxis={"categoryorder": "total ascending", "automargin": False})
    return _style_figure(fig, height=300, left=RANKING_LEFT_MARGIN)
