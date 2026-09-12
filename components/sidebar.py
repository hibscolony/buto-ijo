"""Application navigation and an honest model/device status."""

from html import escape
from pathlib import Path

import streamlit as st


def render_sidebar(navigation: list, model_info: dict, model_error: str | None) -> None:
    with st.sidebar:
        logo = Path(__file__).resolve().parents[1] / "assets" / "logo.png"
        if logo.is_file():
            st.image(str(logo), width=64)
        st.markdown(
            '<div class="brand"><div class="brand-symbol">♧</div><div>'
            '<div class="brand-title">BUTO IJO</div><div class="brand-tag">AI FOR A GREENER TRUTH</div>'
            '</div></div><div class="sidebar-label">WORKSPACE</div>',
            unsafe_allow_html=True,
        )
        icons = [":material/home:", ":material/description:", ":material/manage_search:", ":material/history:", ":material/hub:"]
        for page, icon in zip(navigation, icons):
            st.page_link(page, label=page.title, icon=icon, width="stretch")
        error = model_error or st.session_state.get("model_load_error")
        ready = bool(st.session_state.get("model_ready")) and not error
        status = "Periksa konfigurasi" if error else ("Ready" if ready else "Tersedia · belum dimuat")
        device = str(st.session_state.get("model_device", model_info.get("device", "—"))).upper()
        dot = "" if ready else " off"
        st.markdown(
            '<div class="sidebar-model"><div class="model-label">MODEL</div>'
            '<div class="model-name">IndoBERT Binary Classifier</div>'
            f'<div class="model-row"><span class="model-label">STATUS</span><span class="model-value"><i class="status-dot{dot}"></i>{escape(status)}</span></div>'
            '<div class="model-row"><span class="model-label">VERSION</span><span class="model-value">v4</span></div>'
            f'<div class="model-row"><span class="model-label">DEVICE</span><span class="model-value">{escape(device)}</span></div></div>'
            '<div class="sidebar-foot">Dokumen diproses pada server lokal.<br>Riwayat tersedia selama sesi berjalan.</div>',
            unsafe_allow_html=True,
        )
