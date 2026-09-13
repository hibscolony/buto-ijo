"""Upload, explicit inference, and state-preserving document dashboard."""

from copy import deepcopy
from datetime import datetime
from hashlib import sha256
from html import escape
import logging
from math import ceil
from pathlib import Path
from typing import Any

import streamlit as st

from components.cards import (
    claim_table, document_metadata, empty_state, kpi_cards, page_heading,
    section_title, summary_card, top_risk_claims,
)
from components.charts import distribution_donut, risk_gauge
from core.document_parser import DocumentError, ScanPDFError, parse_document
from core.inference import analyze_document
from core.model import HIGHER_EVIDENTIARY_RISK, LOWER_EVIDENTIARY_RISK, ModelError, load_model
from core.risk import apply_threshold, calculate_document_risk
from core.export import results_to_csv, safe_export_name, summary_to_json
from core.settings import get_settings
from pages.quick_test import render_input as render_quick_input

LOGGER = logging.getLogger(__name__)


def _upload_signature(uploaded: Any, data: bytes | None = None) -> str:
    # Streamlit recreates UploadedFile wrappers on reruns but keeps file_id for
    # the same upload. Cache only the digest, privately in this browser session.
    file_id = getattr(uploaded, "file_id", None)
    key = (file_id, uploaded.name, getattr(uploaded, "size", None))
    cached = st.session_state.get("_upload_signature_cache")
    if file_id and cached and cached["key"] == key:
        return cached["signature"]
    digest = sha256(uploaded.name.encode("utf-8"))
    digest.update(uploaded.getvalue() if data is None else data)
    signature = digest.hexdigest()
    # Generic streams can be edited in place, so always hash their current data.
    if file_id:
        st.session_state["_upload_signature_cache"] = {"key": key, "signature": signature}
    return signature


def _prepare_upload(uploaded: Any, settings: Any) -> dict:
    data = uploaded.getvalue()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise DocumentError(f"Ukuran dokumen melebihi batas {settings.max_upload_mb} MB.")
    signature = _upload_signature(uploaded, data)
    prepared = st.session_state.get("_prepared_upload")
    if prepared and prepared.get("signature") == signature:
        return prepared
    pages = parse_document(data, uploaded.name)
    extension = Path(uploaded.name).suffix.lower().lstrip(".").upper()
    prepared = {
        "signature": signature,
        "pages": pages,
        "metadata": {"name": uploaded.name, "type": extension, "size": len(data),
                     "page_count": len(pages) if extension == "PDF" else "Tidak tersedia",
                     "source": "upload", "signature": signature},
    }
    st.session_state["_prepared_upload"] = prepared
    return prepared


def _save_analysis(payload: dict, metadata: dict) -> None:
    originals = deepcopy(payload.get("original_probabilities", payload["results"]))
    st.session_state["analysis_results"] = deepcopy(payload["results"])
    st.session_state["original_probabilities"] = originals
    st.session_state["document_metadata"] = deepcopy(metadata)
    st.session_state["risk_summary"] = deepcopy(payload["risk_summary"])
    st.session_state["truncated_claims"] = int(payload.get("truncated_claims", 0))
    st.session_state["_analysis_threshold"] = get_settings().default_threshold
    st.session_state.pop("threshold_widget", None)
    for key in ("results_page", "claim_filter", "claim_search", "claim_sort"):
        st.session_state.pop(key, None)
    st.session_state["analysis_completed"] = datetime.now().astimezone().isoformat(timespec="seconds")
    history = st.session_state.setdefault("history", [])
    history.append({
        "id": f'{metadata.get("signature", "text")[:12]}-{len(history)}',
        "date": st.session_state["analysis_completed"],
        "document_metadata": deepcopy(metadata),
        "original_probabilities": deepcopy(originals),
        "risk_summary": deepcopy(payload["risk_summary"]),
        "truncated_claims": int(payload.get("truncated_claims", 0)),
    })


def render_upload() -> None:
    settings = get_settings()
    with st.container(border=True, key="document_upload"):
        st.markdown('<div class="section-title">Mulai analisis dokumen</div><div class="section-note">'
                    'Unggah Sustainability Report untuk meninjau risiko kecukupan bukti pada setiap klaim.</div>',
                    unsafe_allow_html=True)
        uploaded = st.file_uploader("Upload Sustainability Report", type=["pdf", "docx", "txt"],
                                    accept_multiple_files=False, label_visibility="collapsed", key="document_file")
        prepared = None
        if uploaded:
            try:
                with st.spinner("Membaca informasi dokumen..."):
                    prepared = _prepare_upload(uploaded, settings)
                document_metadata(prepared["metadata"])
                if prepared["metadata"]["type"] in ("DOCX", "TXT"):
                    st.caption("DOCX dan TXT tidak memiliki nomor halaman yang stabil. Page 1 menandai satu unit dokumen, bukan halaman cetak.")
                else:
                    empty_pages = sum(not page["text"].strip() for page in prepared["pages"])
                    if empty_pages:
                        st.warning(f"{empty_pages} dari {len(prepared['pages'])} halaman tidak memiliki teks. Hanya halaman dengan text layer yang dianalisis; OCR belum tersedia.")
            except ScanPDFError as exc:
                st.warning(str(exc))
            except DocumentError as exc:
                st.error(str(exc))
            except Exception as exc:
                LOGGER.exception("Document parsing failed")
                st.error(f"Dokumen tidak dapat dibaca: {exc}")
        button, help_text = st.columns([1.35, 3])
        completed_metadata = st.session_state.get("document_metadata", {})
        already_analyzed = bool(
            prepared
            and st.session_state.get("original_probabilities")
            and prepared["signature"] == completed_metadata.get("signature")
        )
        clicked = button.button(
            "Analisis Selesai" if already_analyzed else "Analisis Dokumen",
            type="primary", width="stretch",
            icon=":material/check_circle:" if already_analyzed else ":material/analytics:",
            disabled=prepared is None or already_analyzed, key="analyze_document",
        )
        help_text.caption(f"PDF, DOCX, TXT · Maks. {settings.max_upload_mb} MB · PDF memerlukan text layer")
        if already_analyzed:
            claim_count = len(st.session_state["original_probabilities"])
            st.success(
                f"Analisis selesai: {claim_count:,} klaim diproses. "
                "Dashboard hasil ditampilkan di bawah area upload."
            )
        if clicked and prepared:
            progress = st.progress(0, text="1/4 · Extracting document")
            status = st.empty()
            def report(fraction: float, message: str) -> None:
                progress.progress(max(0., min(1., float(fraction))), text=message)
            try:
                with st.spinner("Memproses Sustainability Report..."):
                    progress.progress(.04, text="1/4 · Extracting document")
                    status.caption("Memuat model lokal. Pemuatan pertama dapat memerlukan beberapa saat.")
                    bundle = load_model(settings.model_path)
                    st.session_state.pop("model_load_error", None)
                    st.session_state["model_ready"] = True
                    st.session_state["model_device"] = str(bundle.device)
                    status.empty()
                    result = analyze_document(prepared["pages"], settings=settings, bundle=bundle, progress_callback=report)
                    _save_analysis(result, prepared["metadata"])
                    progress.progress(1., text="4/4 · Aggregating results — selesai")
                st.rerun()
            except Exception as exc:
                LOGGER.exception("Document inference failed")
                if isinstance(exc, ModelError):
                    st.session_state["model_load_error"] = str(exc)
                    st.session_state["model_ready"] = False
                progress.empty()
                status.empty()
                st.error(f"Analisis dokumen gagal: {exc}")


def _remember_threshold() -> None:
    st.session_state["_analysis_threshold"] = float(st.session_state["threshold_widget"])
    st.session_state.pop("results_page", None)


def _result_view(originals: list[dict], threshold: float) -> dict:
    # Save and history restore replace the immutable original-probability list.
    # Retain it here so identity remains safe even after the current list changes.
    # Keep just the current view per session, without hashing or globally caching
    # private document text on every widget event.
    cached = st.session_state.get("_result_view_cache")
    if cached and cached["originals"] is originals and cached["threshold"] == threshold:
        return cached
    results = apply_threshold(originals, threshold)
    view = {
        "originals": originals, "threshold": threshold, "results": results,
        "summary": calculate_document_risk(results, threshold=threshold),
        "csv": results_to_csv(results),
    }
    st.session_state["_result_view_cache"] = view
    return view


def render_results() -> None:
    originals = st.session_state.get("original_probabilities")
    if not originals:
        empty_state("Dashboard Anda dimulai dari sebuah dokumen", "Unggah laporan dan tekan Analisis Dokumen. Risk Index, distribusi, dan hasil per klaim akan tampil di sini.")
        return
    metadata = st.session_state.get("document_metadata", {})
    section_title("Analysis Overview", metadata.get("name", "Dokumen"))
    selected_upload = st.session_state.get("document_file")
    # A failed parse leaves the previous prepared document cached. Compare the
    # currently selected upload, so old results remain clearly attributed.
    selected_signature = (
        _upload_signature(selected_upload)
        if selected_upload is not None else None
    )
    if selected_upload is not None and selected_signature != metadata.get("signature"):
        st.info(f'Hasil yang ditampilkan berasal dari “{metadata.get("name", "dokumen sebelumnya")}”. Tekan Analisis Dokumen untuk memproses unggahan baru.')
    # A same-key widget gets a new identity on Beranda vs Analisis Dokumen.
    # Explicitly hydrate on every run, not only after widget-state cleanup;
    # otherwise direct page navigation can reset this slider to its minimum.
    st.session_state["threshold_widget"] = float(st.session_state.get("_analysis_threshold", get_settings().default_threshold))
    with st.expander("Pengaturan threshold & metodologi", expanded=False):
        threshold = st.slider("Higher-risk Threshold", min_value=0.0, max_value=1.0, step=.01,
                              key="threshold_widget", on_change=_remember_threshold,
                              help="Klaim ditandai jika probabilitas Higher Evidentiary Risk ≥ threshold. Mengubah threshold tidak menjalankan model ulang.")
        st.caption("Probabilitas tersimpan tetap sama. Prediction, Confidence, Risk Index, dan ekspor mengikuti threshold aktif.")
        st.markdown("**Risk Index** = 100 × (0.50 × rata-rata probabilitas + 0.35 × rasio klaim ditandai + 0.15 × rasio klaim ditandai dengan confidence tinggi).")
        st.caption("Confidence tinggi: probabilitas Higher Evidentiary Risk ≥ 0.80 dan klaim ditandai. Semua rasio menggunakan seluruh klaim sebagai penyebut. LOW ≤ 30; MODERATE > 30 hingga 60; HIGH > 60.")
        st.caption("Confidence adalah probabilitas kelas yang dipilih berdasarkan threshold; nilainya dapat di bawah 50% jika threshold diubah.")
        st.caption("Input dokumen mengikuti format training: CLAIM + dua klaim sebelum/sesudah sebagai evidence context. Model dilatih pada klaim lingkungan dengan label silver Rule–Qwen; validitas di luar domain tersebut belum ditetapkan.")
    view = _result_view(originals, float(threshold))
    results, summary = view["results"], view["summary"]
    st.session_state["analysis_results"] = results
    st.session_state["risk_summary"] = summary
    kpi_cards(summary)
    risk_col, summary_col = st.columns([1.02, 1.65], gap="medium")
    with risk_col, st.container(border=True, key="risk_chart"):
        st.markdown('<div class="section-title">Evidentiary Risk Index</div>', unsafe_allow_html=True)
        st.plotly_chart(risk_gauge(summary["risk_score"], summary["risk_level"]), width="stretch",
                        config={"displayModeBar": False}, key="document_risk_gauge")
        st.markdown(f'<div style="text-align:center"><span class="risk-badge {summary["risk_level"].lower()}">{summary["risk_level"]} RISK</span></div>', unsafe_allow_html=True)
        st.caption("Risk Index merupakan agregasi claim-level predictions dan bukan kelas langsung dari model atau bukti pelanggaran.")
    with summary_col, st.container(border=True, key="analysis_summary"):
        summary_card(summary)
        st.caption(f'Dokumen: {metadata.get("name", "—")} · Threshold {threshold:.2f}')
    truncated = st.session_state.get("truncated_claims", 0)
    if truncated:
        st.warning(f"{truncated:,} klaim melewati batas token dan dipotong untuk inference. Tinjau konteks lengkap pada dokumen sumber.")
    render_claim_results(results)
    distribution_col, top_col = st.columns([1.02, 1.65], gap="medium")
    with distribution_col, st.container(border=True, key="distribution_card"):
        st.markdown('<div class="section-title">Distribusi Hasil</div><div class="section-note">Komposisi prediksi pada threshold aktif</div>', unsafe_allow_html=True)
        st.plotly_chart(distribution_donut(summary), width="stretch",
                        config={"displayModeBar": False}, key="document_distribution")
        st.caption(f'Higher Evidentiary Risk: {summary["flagged_claims"]:,} klaim ({summary["flagged_ratio"]:.1%})')
        st.caption(f'Lower Evidentiary Risk: {summary["total_claims"] - summary["flagged_claims"]:,} klaim ({1 - summary["flagged_ratio"]:.1%})')
    with top_col, st.container(border=True):
        st.markdown('<div class="section-title">Klaim dengan Risiko Bukti Tertinggi</div><div class="section-note">Top 5 berdasarkan higher-risk probability · Perlu Verifikasi</div>', unsafe_allow_html=True)
        top_risk_claims(results)
    section_title("Ekspor hasil analisis", "Seluruh klaim · mengikuti threshold aktif")
    csv_col, json_col, _ = st.columns([1, 1, 1.5])
    filename = safe_export_name(metadata.get("name", "document"))
    csv_col.download_button("Download CSV", data=view["csv"], on_click="ignore",
                            file_name=f"BUTO_IJO_analysis_{filename}.csv", mime="text/csv",
                            icon=":material/download:", width="stretch")
    json_col.download_button("Download JSON Summary", data=summary_to_json(summary, metadata.get("name", "document")),
                             file_name=f"BUTO_IJO_summary_{filename}.json", mime="application/json",
                             icon=":material/data_object:", width="stretch", on_click="ignore")


@st.fragment
def render_claim_results(results: list[dict]) -> None:
    section_title("Hasil Analisis Klaim", "Prediksi per kalimat")
    with st.container(border=True, key="results_card"):
        filter_col, search_col, sort_col = st.columns([1.2, 1.8, 1])
        prediction_filter = filter_col.selectbox("Filter prediksi", ["Semua Klaim", HIGHER_EVIDENTIARY_RISK, LOWER_EVIDENTIARY_RISK], key="claim_filter")
        query = search_col.text_input("Cari klaim...", placeholder="Cari klaim...", key="claim_search")
        sorting = sort_col.selectbox("Urutkan", ["Highest Risk", "Lowest Risk", "Page"], key="claim_sort")
        normalized_query = query.casefold().strip()
        visible = [row for row in results if (prediction_filter == "Semua Klaim" or row["prediction"] == prediction_filter)
                   and normalized_query in row["claim"].casefold()]
        if sorting == "Highest Risk":
            visible.sort(key=lambda row: row["greenwashing_probability"], reverse=True)
        elif sorting == "Lowest Risk":
            visible.sort(key=lambda row: row["greenwashing_probability"])
        else:
            visible.sort(key=lambda row: (row.get("page") if row.get("page") is not None else float("inf"), row["claim_id"]))
        per_page = 20
        max_page = max(1, ceil(len(visible) / per_page))
        if st.session_state.get("results_page", 1) > max_page:
            st.session_state["results_page"] = 1
        pagination_col, count_col = st.columns([1, 3])
        current_page = pagination_col.number_input("Halaman tabel", min_value=1, max_value=max_page, value=1, step=1, key="results_page")
        count_col.caption(f"{len(visible):,} dari {len(results):,} klaim · {per_page} klaim per halaman · Halaman {current_page}/{max_page}")
        if visible:
            claim_table(visible[(current_page - 1) * per_page:current_page * per_page])
        else:
            st.info("Tidak ada klaim yang sesuai dengan filter dan pencarian.")


def render_workspace() -> None:
    upload_tab, text_tab = st.tabs(["Upload Dokumen", "Input Teks"])
    with upload_tab:
        render_upload()
    with text_tab:
        render_quick_input()
    render_results()


def render() -> None:
    page_heading("Analisis Dokumen", "Tinjau Sustainability Report dari klaim per kalimat hingga indeks risiko agregat.")
    render_workspace()
