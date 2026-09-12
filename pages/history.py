"""Session-local history and restoration of immutable probability snapshots."""

from copy import deepcopy
from datetime import datetime

import pandas as pd
import streamlit as st

from components.cards import empty_state, page_heading


def render() -> None:
    page_heading("Riwayat", "Kembali ke analisis yang telah dijalankan selama sesi ini. Data tidak disimpan ke database.")
    history = st.session_state.get("history", [])
    if not history:
        empty_state("Belum ada riwayat analisis", "Hasil analisis dokumen akan muncul di sini setelah proses selesai.")
        return
    records = list(reversed(history))
    table = []
    for record in records:
        summary = record["risk_summary"]
        try:
            date = datetime.fromisoformat(record["date"]).strftime("%d %b %Y · %H:%M:%S")
        except (ValueError, TypeError):
            date = str(record["date"])
        table.append({"Tanggal": date, "Nama Dokumen": record["document_metadata"].get("name", "—"),
                      "Jumlah Klaim": summary["total_claims"], "Flagged Claims": summary["flagged_claims"],
                      "Risk Score": round(summary["risk_score"], 1), "Risk Level": summary["risk_level"]})
    with st.container(border=True, key="history_card"):
        st.dataframe(pd.DataFrame(table), hide_index=True, width="stretch")
        st.caption("Riwayat menyimpan hasil dan threshold saat analisis awal. Perubahan threshold pada dashboard tidak menulis ulang catatan ini. Sesi baru atau restart server menghapus riwayat.")
        selected = st.selectbox("Buka kembali hasil analisis", options=range(len(records)),
                                format_func=lambda i: f'{table[i]["Tanggal"]} — {table[i]["Nama Dokumen"]}', key="history_selection")
        if st.button("Buka hasil analisis", icon=":material/open_in_new:", type="primary", key="restore_history"):
            record = records[selected]
            st.session_state["original_probabilities"] = deepcopy(record["original_probabilities"])
            st.session_state["document_metadata"] = deepcopy(record["document_metadata"])
            st.session_state["risk_summary"] = deepcopy(record["risk_summary"])
            st.session_state["analysis_results"] = deepcopy(record["original_probabilities"])
            st.session_state["truncated_claims"] = record.get("truncated_claims", 0)
            st.session_state["_analysis_threshold"] = float(record["risk_summary"].get("threshold", .5))
            st.session_state.pop("threshold_widget", None)
            st.session_state.pop("results_page", None)
            st.switch_page(st.session_state["_document_analysis_page"])
