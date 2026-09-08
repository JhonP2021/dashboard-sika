from __future__ import annotations

import html

import streamlit as st

CARD_CSS = """
<style>
.stApp { background: #0b0e14; color: #f9fafb; }
[data-testid="stSidebar"] { background: #111620; border-right: 1px solid rgba(255,255,255,.07); }
.block-container { padding-top: 1rem; padding-bottom: 1.4rem; max-width: 100%; }

/* Cada visual vive en su propia tarjeta, con el mismo cromado. */
div[data-testid="stVerticalBlockBorderWrapper"] {
  background: #141924;
  border: 1px solid rgba(255,255,255,.07);
  border-radius: 10px;
  box-shadow: 0 1px 2px rgba(0,0,0,.35);
  padding: .1rem .25rem .35rem;
}
.card-head { display: flex; align-items: baseline; justify-content: space-between; gap: .75rem;
             padding: .55rem .5rem .5rem; border-bottom: 1px solid rgba(255,255,255,.06); margin-bottom: .35rem; }
.card-title { font-size: .74rem; font-weight: 700; letter-spacing: .07em; text-transform: uppercase; color: #cbd5e1; }
.card-sub { font-size: .72rem; color: #64748b; white-space: nowrap; }

/* Tarjetas de silo: cifra grande y barra de severidad. */
.silo-tile { background: #141924; border: 1px solid rgba(255,255,255,.07); border-radius: 10px;
             box-shadow: 0 1px 2px rgba(0,0,0,.35); padding: .55rem .7rem;
             display: flex; flex-direction: column; gap: .4rem; }
.silo-tile-label { font-size: .72rem; letter-spacing: .04em; text-transform: uppercase; }
.silo-tile-value { font-size: 1.3rem; font-weight: 600; line-height: 1; font-variant-numeric: tabular-nums; }
.silo-tile-value span { font-size: .75rem; color: #64748b; }
.silo-tile-track { height: 3px; background: rgba(255,255,255,.06); border-radius: 2px; overflow: hidden; }
.silo-tile-track > div { height: 3px; border-radius: 2px; }

/* La tabla hereda el cromado de la tarjeta que la envuelve. */
div[data-testid="stDataFrame"] { border: none; }
h1 { font-size: 1.6rem !important; font-weight: 700 !important; letter-spacing: -.01em; }
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
