from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import base64
import html

import streamlit as st

LOGO_PATH = Path(__file__).resolve().parents[2] / "assets" / "sika-logo.png"


@lru_cache(maxsize=1)
def logo_data_uri() -> str:
    """El logo va embebido: Streamlit no sirve ficheros estáticos del repo.

    Si falta el asset se devuelve cadena vacía y la marca cae al texto, en vez
    de dejar una imagen rota en la barra lateral.
    """
    if not LOGO_PATH.exists():
        return ""
    return "data:image/png;base64," + base64.b64encode(LOGO_PATH.read_bytes()).decode()


def brand_markup() -> str:
    logo = logo_data_uri()
    mark = (f'<img class="brand-logo" src="{logo}" alt="Sika">' if logo
            else '<span class="brand-mark">Sika</span>')
    return (f'<div class="brand">{mark}'
            '<span class="brand-label">CONTROL<br>DE PRODUCCIÓN</span></div>')

CARD_CSS = """
<style>
.stApp { background: #0b0e14; color: #f0f2f5; }
[data-testid="stHeader"] { background: #0b0e14; }
[data-testid="stSidebar"] { background: #111620; border-right: 1px solid rgba(255,255,255,.07); }
/* La barra lateral queda siempre desplegada: se oculta el botón de plegado y
   se colapsa la franja que Streamlit le reservaba encima del contenido, para
   que el logo arranque pegado al borde superior. */
[data-testid="stSidebarCollapseButton"], [data-testid="stSidebarCollapsedControl"] { display:none !important; }
[data-testid="stSidebarHeader"] { padding:0; min-height:0; height:0; overflow:hidden; }
[data-testid="stSidebarUserContent"] { padding-top:0; }
.block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1600px; }
.brand { display:flex; align-items:center; gap:12px; padding:0 0 16px; border-bottom:1px solid rgba(255,255,255,.07); margin-bottom:20px; }
.brand-logo { width:46px; height:46px; object-fit:contain; display:block; }
.brand-mark { background:#ffcc00; color:#20262e; font-weight:900; font-size:22px; padding:8px 12px; border-radius:6px; letter-spacing:-1px; }
.brand-label { font-size:11px; color:#8f9bab; letter-spacing:1.5px; font-weight:700; }
.hero { margin-bottom:20px; overflow:visible; }
/* line-height explícito con holgura: con padding 0 y el line-height ajustado
   de Streamlit, la caja de línea queda más corta que el ascendente de la
   fuente a 32px y recorta los trazos altos y los puntos de las íes. */
.hero h1 { font-size:32px !important; font-weight:750 !important; letter-spacing:-1px;
           line-height:1.3 !important; margin:0; padding:2px 0 0 !important; color:#f7f9fb; }
.summary { display:flex; align-items:center; gap:28px; background:#1a212c; color:#f7f9fb; padding:18px 24px; border-radius:12px; margin:0 0 24px; border-left:5px solid #ffcc00; }
.summary-number { font-size:28px; font-weight:750; line-height:1.1; font-variant-numeric:tabular-nums; }
.summary-label { color:#9aa6b5; font-size:12px; margin-top:4px; }
.summary-period { margin-left:auto; color:#e9edf2; font-size:13px; text-align:right; }
.section-label { font-size:13px; font-weight:650; color:#c3ccd8; margin-bottom:12px; }
.silo-grid { display:grid; grid-template-columns:repeat(8,minmax(0,1fr)); gap:12px; margin-bottom:24px; }
.silo-tile { background:#141924; border:1px solid rgba(255,255,255,.07); border-radius:10px; padding:16px 14px; }
.silo-tile-label { color:#8f9bab; font-size:12px; font-weight:600; }
.silo-tile-value { font-size:26px; font-weight:700; letter-spacing:-1px; color:#f7f9fb; margin:8px 0 12px; font-variant-numeric:tabular-nums; }
.silo-tile-value span { font-size:13px; color:#7c8899; margin-left:3px; }
.silo-tile-track { height:4px; background:rgba(255,255,255,.08); border-radius:4px; overflow:hidden; }
.silo-tile-track > div { height:4px; border-radius:4px; }
.status-pill { display:inline-block; font-size:10px; font-weight:700; padding:5px 7px; border-radius:6px; margin-top:12px; }
.status-pill.green { background:rgba(52,211,153,.14); color:#6ee7b7; }
.status-pill.amber { background:rgba(251,191,36,.15); color:#fcd34d; }
.status-pill.red { background:rgba(239,68,68,.16); color:#fca5a5; }
.status-pill.gray { background:rgba(255,255,255,.06); color:#8f9bab; }
.silo-note { font-size:10px; color:#8f9bab; margin-top:7px; line-height:1.5; }
.card-head { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:4px 2px 14px; border-bottom:1px solid rgba(255,255,255,.07); margin-bottom:8px; }
.card-title { font-size:15px; font-weight:650; color:#f7f9fb; }
.card-sub { font-size:11px; color:#8f9bab; text-align:right; }
[data-testid="stVerticalBlockBorderWrapper"] { border-radius:12px; }
[data-testid="stVerticalBlockBorderWrapper"]:has(.card-head) { background:#141924; border-color:rgba(255,255,255,.07); }
[data-testid="stForm"] { background:#141924; border-color:rgba(255,255,255,.07); border-radius:10px; }
[data-testid="stSidebar"] h2 { font-size:16px; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] { font-size:11px; }
@media(max-width:1100px) { .silo-grid { grid-template-columns:repeat(4,minmax(0,1fr)); } }
@media(max-width:600px) { .hero h1 { font-size:26px !important; } .summary { gap:12px; padding:16px; } .silo-grid { grid-template-columns:repeat(2,minmax(0,1fr)); } }
</style>
"""


def card(title: str, subtitle: str | None = None):
    """Contenedor con cabecera propia, al estilo de un visual de Power BI.

    El título va en la cabecera y no dentro del gráfico: así queda anclado al
    borde de la tarjeta en vez de al área de trazado, que se mueve según lo que
    midan las etiquetas del eje.
    """
    container = st.container(border=True)
    container.markdown(
        f'<div class="card-head"><span class="card-title">{html.escape(title)}</span>'
        f'<span class="card-sub">{html.escape(subtitle) if subtitle else ""}</span></div>',
        unsafe_allow_html=True,
    )
    return container
