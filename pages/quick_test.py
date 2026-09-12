"""Real-model inference on a manually entered claim."""

from html import escape
import logging

import streamlit as st

from components.cards import page_heading
from components.charts import probability_bars
from core.inference import predict_text
from core.model import ModelError, load_model
from core.settings import get_settings

LOGGER = logging.getLogger(__name__)


def _persist_draft() -> None:
    st.session_state["quick_draft"] = st.session_state.get("quick_text_widget", "")


def render_input() -> None:
    settings = get_settings()
    with st.container(border=True, key="input_quick"):
        st.markdown('<div class="section-title">Uji klaim keberlanjutan</div><div class="section-note">'
                    'Masukkan satu kalimat atau paragraf untuk memperoleh probabilitas dari model IndoBERT lokal.</div>',
                    unsafe_allow_html=True)
        # Widgets with the same key still have a different identity on each
        # Streamlit page. Rehydrate from non-widget state before every render,
        # including direct navigation between pages that both show this input.
        st.session_state["quick_text_widget"] = st.session_state.get("quick_draft", "")
        text = st.text_area("Masukkan klaim keberlanjutan...", height=135, key="quick_text_widget",
                            placeholder="Masukkan klaim keberlanjutan...", on_change=_persist_draft)
        button, caption = st.columns([1.3, 3])
        run = button.button("Analisis Klaim", type="primary", width="stretch",
                            icon=":material/manage_search:", key="analyze_quick")
        caption.caption("Diproses sebagai satu input · Threshold 0.50 · Tanpa API eksternal")
        if run:
            if not text.strip():
                st.warning("Masukkan klaim keberlanjutan terlebih dahulu.")
            else:
                st.session_state["quick_draft"] = text
                try:
                    with st.spinner("Menjalankan IndoBERT pada klaim..."):
                        bundle = load_model(settings.model_path)
                        st.session_state.pop("model_load_error", None)
                        st.session_state["model_ready"] = True
                        st.session_state["model_device"] = str(bundle.device)
                        result = predict_text(text, bundle=bundle, settings=settings, threshold=.5)
                    st.session_state["quick_result"] = result
                    st.session_state["quick_result_text"] = text
                    st.rerun()
                except Exception as exc:
                    LOGGER.exception("Quick inference failed")
                    if isinstance(exc, ModelError):
                        st.session_state["model_load_error"] = str(exc)
                        st.session_state["model_ready"] = False
                    st.error(f"Analisis klaim gagal: {exc}")
        result = st.session_state.get("quick_result")
        if result:
            if text.strip() != st.session_state.get("quick_result_text", "").strip():
                st.info("Hasil di bawah berasal dari input sebelumnya. Tekan Analisis Klaim untuk menganalisis perubahan.")
            st.divider()
            flagged = result["prediction"] == "Potential Greenwashing"
            css = "flagged" if flagged else ""
            st.markdown('<div class="section-kicker">HASIL INDO BERT / SOFTMAX</div>'
                        f'<span class="prediction-badge {css}" style="font-size:.82rem;padding:.5rem .8rem">'
                        f'{escape(result["prediction"])}</span>', unsafe_allow_html=True)
            st.caption("Klaim yang dianalisis")
            st.markdown(f'<div style="white-space:pre-wrap;overflow-wrap:anywhere">{escape(result["claim"])}</div>', unsafe_allow_html=True)
            first, second = st.columns(2)
            first.metric("Greenwashing Probability", f'{result["greenwashing_probability"]:.1%}')
            second.metric("Confidence", f'{result["confidence"]:.1%}')
            st.plotly_chart(probability_bars(result["greenwashing_probability"], result["probabilities"]["Low Indication"]), width="stretch",
                            config={"displayModeBar": False}, key="quick_probability_chart")
            st.caption("Confidence adalah probabilitas kelas yang dipilih. Probabilitas softmax tidak membuktikan kebenaran klaim.")
            if result.get("truncated"):
                st.warning(f"Input melewati batas {settings.max_length} token. Model hanya menilai bagian awal setelah truncation; gunakan analisis dokumen untuk segmentasi kalimat.")


def render() -> None:
    page_heading("Uji Teks Cepat", "Dari satu klaim menuju bukti yang perlu ditinjau. Hasil langsung dari model lokal.")
    render_input()
