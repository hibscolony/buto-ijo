"""BUTO IJO — local IndoBERT sustainability research dashboard.

Run with: streamlit run app.py
"""

import logging

import streamlit as st

st.set_page_config(page_title="BUTO IJO", page_icon="🌿", layout="wide")

from components.cards import hero, workflow
from components.sidebar import render_sidebar
from components.styles import inject_styles, render_footer
from core.model import inspect_model
from core.settings import get_settings
from pages import about_model, document_analysis, history, quick_test

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def _initialize_session() -> None:
    defaults = {"analysis_results": [], "document_metadata": {}, "original_probabilities": [],
                "risk_summary": {}, "history": [], "_analysis_threshold": .5,
                "quick_draft": "", "model_ready": False}
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def home() -> None:
    hero()
    workflow()
    document_analysis.render_workspace()


def main() -> None:
    inject_styles()
    _initialize_session()
    try:
        settings = get_settings()
    except ValueError as exc:
        st.error(f"Konfigurasi aplikasi tidak valid: {exc}")
        st.stop()
    if st.session_state.get("_inspected_model_path") != settings.model_path:
        try:
            st.session_state["model_info"] = inspect_model(settings.model_path)
            st.session_state["model_error"] = None
        except Exception as exc:
            st.session_state["model_info"] = {}
            st.session_state["model_error"] = str(exc)
        st.session_state["_inspected_model_path"] = settings.model_path
        st.session_state["model_ready"] = False
        st.session_state.pop("model_device", None)
        st.session_state.pop("model_load_error", None)
    navigation = [
        st.Page(home, title="Beranda", icon=":material/home:", default=True),
        st.Page(document_analysis.render, title="Analisis Dokumen", icon=":material/description:", url_path="analisis-dokumen"),
        st.Page(quick_test.render, title="Uji Teks Cepat", icon=":material/manage_search:", url_path="uji-teks-cepat"),
        st.Page(history.render, title="Riwayat", icon=":material/history:", url_path="riwayat"),
        st.Page(about_model.render, title="Tentang Model", icon=":material/hub:", url_path="tentang-model"),
    ]
    current_page = st.navigation(navigation, position="hidden")
    st.session_state["_document_analysis_page"] = navigation[1]
    if st.session_state.get("model_error"):
        st.error(f'Model lokal belum siap: {st.session_state["model_error"]}')
        st.caption("Atur BUTO_IJO_MODEL_PATH ke folder checkpoint dan restart Streamlit setelah memperbaiki konfigurasi.")
    current_page.run()
    # Page actions can change model status; reflect that state on the same rerun.
    render_sidebar(navigation, st.session_state.get("model_info", {}), st.session_state.get("model_error"))
    render_footer()


if __name__ == "__main__":
    main()
