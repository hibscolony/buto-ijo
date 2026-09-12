"""Show checkpoint provenance and research limitations without invented metrics."""

from html import escape
import json

import pandas as pd
import streamlit as st

from components.cards import page_heading
from core.settings import get_settings

MISSING = "Tidak tersedia pada metadata model."


def _display(value) -> str:
    if value is None or value == "" or value == []:
        return MISSING
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def render() -> None:
    page_heading("Tentang Model", "Transparansi checkpoint, label, dan batas interpretasi hasil analisis.", "BUTO IJO / MODEL CARD")
    info = st.session_state.get("model_info", {})
    error = st.session_state.get("model_error")
    if error:
        st.error(str(error))
        st.code(f'BUTO_IJO_MODEL_PATH={get_settings().model_path}', language="text")
        return
    config = info.get("config", {})
    metadata = info.get("metadata", {})
    mapping = info.get("mapping")
    base = metadata.get("indobert_model", metadata.get("base_model", config.get("_name_or_path")))
    architecture = ", ".join(config.get("architectures", [])) or config.get("model_type")
    pipeline_version = metadata.get("pipeline_version")
    version = metadata.get("model_version")
    if not version and isinstance(pipeline_version, str):
        version = pipeline_version.split("_", 1)[0]
    settings = get_settings()
    fields = [
        ("Base Model", base), ("Architecture", architecture),
        ("Runtime Inference", "IndoBERT binary classifier saja"),
        ("Number of Labels", len(mapping.id2label) if mapping else None),
        ("Maximum Sequence Length", f'{min(settings.max_length, info.get("max_length", settings.max_length))} token (aktif)'),
        ("Model Version", version), ("Training Dataset", metadata.get("training_dataset")),
        ("Training Label Source", metadata.get("label_source")),
    ]
    with st.container(border=True, key="about_card"):
        st.markdown('<div class="section-kicker">LOCAL CHECKPOINT</div><div class="section-title">IndoBERT Binary Classifier</div>', unsafe_allow_html=True)
        st.markdown('<div class="about-grid">' + ''.join(
            f'<div class="about-item"><div class="label">{escape(label)}</div><div class="value">{escape(_display(value))}</div></div>'
            for label, value in fields) + '</div>', unsafe_allow_html=True)
        st.caption(f'Folder model: `{info.get("path", settings.model_path)}`')
        st.caption("Checkpoint dipakai untuk inference lokal; bobot model tidak dilatih ulang.")
        st.info(
            "Aplikasi tidak memanggil Kimi atau Qwen saat digunakan. Metadata mencatat keduanya "
            "sebagai teacher offline dalam pembuatan pseudo-label training; hasilnya sudah dipelajari "
            "oleh checkpoint IndoBERT yang berjalan mandiri."
        )
    st.subheader("Mapping label yang digunakan")
    if mapping:
        label_rows = []
        for index, label in sorted(mapping.id2label.items()):
            label_rows.append({"Index": index, "Label checkpoint": label,
                               "Label aplikasi": "Potential Greenwashing" if index == mapping.greenwashing_index else "Low Indication"})
        st.dataframe(pd.DataFrame(label_rows), hide_index=True, width="stretch")
        st.caption(f"Sumber mapping: {mapping.source}")
    else:
        st.info(MISSING)
    for warning in info.get("warnings", []):
        st.warning(warning)
    st.subheader("Provenance data & evaluasi")
    if metadata:
        facts = {"Task": metadata.get("task"), "Jenis label": metadata.get("label_type"),
                 "Sumber label": metadata.get("label_source"), "Definisi risiko": metadata.get("risk_definition"),
                 "Jumlah pseudo-label": metadata.get("n_pseudo_labels"),
                 "Training / validation / test": (f'{metadata.get("n_train", "—")} / {metadata.get("n_val", "—")} / {metadata.get("n_test", "—")}'),
                 "Perusahaan training": metadata.get("train_companies"), "Perusahaan validation": metadata.get("val_companies"),
                 "Perusahaan test": metadata.get("test_companies")}
        st.dataframe(pd.DataFrame([{"Informasi": k, "Metadata model": _display(v)} for k, v in facts.items()]),
                     hide_index=True, width="stretch")
        validation_threshold = metadata.get("best_validation_threshold")
        if isinstance(validation_threshold, (int, float)):
            st.info(f"Metadata mencatat best validation threshold {validation_threshold:.2f}. Aplikasi menggunakan default 0.50 sesuai konfigurasi produk; Anda dapat mengubah threshold pada hasil dokumen tanpa inference ulang.")
    else:
        st.info(MISSING)
    st.markdown("**Evaluation Metrics**")
    metrics = metadata.get("evaluation_metrics", metadata.get("metrics", metadata.get("eval_metrics")))
    if metrics is not None:
        st.json(metrics)
    else:
        st.info(MISSING)
    st.subheader("Batas penggunaan riset")
    st.write("Label Potential Greenwashing pada aplikasi merepresentasikan kelas Higher Risk pada checkpoint, yakni risiko dukungan bukti suatu klaim. Hasil tersebut memerlukan peninjauan konteks dan bukti dari dokumen asli.")
    if metadata.get("limitation"):
        st.info(str(metadata["limitation"]))
    if metadata.get("strict_environmental_rule"):
        st.write("**Cakupan training:**", str(metadata["strict_environmental_rule"]))
    st.write("Pipeline melakukan segmentasi seluruh kalimat yang memenuhi panjang minimum. Kalimat sosial, tata kelola, atau teks lain di luar domain lingkungan dapat ikut dianalisis; validitas model pada domain tersebut belum ditetapkan. Label silver merupakan konsensus pseudo-label dan tidak menggantikan anotasi ahli atau audit.")
    with st.expander("Konfigurasi inference & agregasi"):
        st.json({"batch_size": settings.batch_size, "max_length": settings.max_length,
                 "min_char_length": settings.min_char_length, "default_threshold": settings.default_threshold,
                 "device": info.get("device"), "high_confidence_threshold": .8,
                 "risk_formula": "100 × (0.50 × mean_probability + 0.35 × flagged_ratio + 0.15 × high_confidence_flagged_ratio)"})
        st.caption("Cleaning ringan mempertahankan angka, tanda baca, persentase, dan istilah lingkungan. Tokenizer menggunakan padding dan truncation. Kalimat panjang dapat terpotong pada batas token.")
    with st.expander("config.json & metadata asli"):
        st.markdown("**config.json**")
        st.json(config)
        st.markdown("**buto_ijo_v4_metadata.json**")
        st.json(metadata) if metadata else st.info(MISSING)
