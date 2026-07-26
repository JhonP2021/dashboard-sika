from __future__ import annotations

import streamlit as st


def render_kpi_cards(metrics: list[tuple[str, str, str | None]]):
    columns = st.columns(min(len(metrics), 5))
    for index, (label, value, delta) in enumerate(metrics):
        with columns[index % len(columns)]:
            st.metric(label=label, value=value, delta=delta)

