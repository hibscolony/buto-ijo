"""Escaped HTML presentation; uploaded document text is never trusted markup."""

from html import escape
from typing import Any

import streamlit as st

from core.model import HIGHER_EVIDENTIARY_RISK


def hero() -> None:
    st.markdown(
        '<div class="topline"><span class="eyebrow">Sustainability Intelligence</span>'
        '<span class="local-pill">Analisis lokal · Privasi terjaga</span></div>'
        '<section class="hero"><div class="hero-content">'
        '<span class="hero-badge">✦ &nbsp; AI Sustainability Audit</span>'
        '<div class="hero-title">BUTO IJO</div>'
        '<div class="hero-subtitle">Dashboard Deteksi Potensi Greenwashing<br>pada Sustainability Report</div>'
        '<div class="hero-description">Analisis berbasis IndoBERT untuk membantu mengidentifikasi '
        'klaim keberlanjutan yang berpotensi menyesatkan.</div></div>'
        '<div class="hero-art" aria-hidden="true"><div class="hero-ring"></div><div class="hero-ring r2"></div>'
        '<div class="hero-ring r3"></div><div class="hero-leaf"></div><div class="hero-leaf second"></div></div>'
        '<div class="hero-quote">“Bukan sekadar klaim hijau,<br>tapi dampak nyata.”</div></section>',
        unsafe_allow_html=True,
    )


def page_heading(title: str, description: str, kicker: str = "BUTO IJO / WORKSPACE") -> None:
    st.markdown(f'<div class="eyebrow">{escape(kicker)}</div>', unsafe_allow_html=True)
    st.title(title)
    st.markdown(f'<div class="section-note">{escape(description)}</div>', unsafe_allow_html=True)


def section_title(title: str, note: str = "") -> None:
    st.markdown(
        f'<div class="section-heading"><h2>{escape(title)}</h2><span>{escape(note)}</span></div>',
        unsafe_allow_html=True,
    )


def workflow() -> None:
    steps = ["Upload dokumen", "Ekstraksi klaim", "Analisis IndoBERT", "Risk dashboard"]
    fragments = []
    for number, label in enumerate(steps, 1):
        fragments.append(f'<div class="workflow-item"><span class="workflow-number">{number}</span>{label}</div>')
        if number < len(steps):
            fragments.append('<div class="workflow-line"></div>')
    st.markdown('<div class="workflow">' + ''.join(fragments) + '</div>', unsafe_allow_html=True)


def document_metadata(metadata: dict[str, Any]) -> None:
    size = int(metadata.get("size", 0))
    size_label = f"{size / 1024 / 1024:.2f} MB" if size >= 1024 * 1024 else f"{size / 1024:.1f} KB"
    fields = [
        ("Nama Dokumen", metadata.get("name", "—")),
        ("Jenis File", metadata.get("type", "—")),
        ("Ukuran File", size_label),
        ("Jumlah Halaman", metadata.get("page_count", "—")),
    ]
    st.markdown(
        '<dl class="file-meta">' + ''.join(
            f'<div><dt>{escape(str(label))}</dt><dd>{escape(str(value))}</dd></div>' for label, value in fields
        ) + '</dl>', unsafe_allow_html=True,
    )


def kpi_cards(summary: dict[str, Any]) -> None:
    level = str(summary["risk_level"]).lower()
    cards = [
        ("Risk Score", f'{summary["risk_score"]:.1f}', ' / 100', "Indeks agregasi dokumen", "◉", f"risk-{level}"),
        ("Claims Analyzed", f'{summary["total_claims"]:,}', "", "Klaim berhasil dianalisis", "≡", ""),
        ("Flagged Claims", f'{summary["flagged_claims"]:,}', "", "Higher Evidentiary Risk", "⚑", ""),
        ("Flagged Ratio", f'{summary["flagged_ratio"]:.1%}', "", "Dari seluruh klaim", "%", ""),
    ]
    fragments = [
        f'<div class="kpi {tone}"><div class="kpi-icon" aria-hidden="true">{icon}</div>'
        f'<div class="kpi-label">{title}</div><div class="kpi-value">{value}'
        f'<span class="kpi-unit">{unit}</span></div><div class="kpi-detail">{detail}</div></div>'
        for title, value, unit, detail, icon, tone in cards
    ]
    st.markdown('<div class="kpi-grid">' + ''.join(fragments) + '</div>', unsafe_allow_html=True)


def summary_card(summary: dict[str, Any]) -> None:
    level = summary["risk_level"]
    opening = {
        "LOW": "Dokumen menunjukkan indikasi agregat yang rendah pada klaim yang dianalisis.",
        "MODERATE": "Dokumen menunjukkan sejumlah klaim keberlanjutan yang perlu diverifikasi lebih lanjut.",
        "HIGH": "Dokumen memiliki indikasi agregat yang tinggi pada klaim yang dianalisis dan memerlukan verifikasi lebih lanjut.",
    }.get(level, "Klaim keberlanjutan telah dianalisis menggunakan IndoBERT.")
    st.markdown(
        '<div class="section-kicker">INSIGHT / CLAIM-LEVEL ANALYSIS</div><div class="section-title">Ringkasan Analisis</div>'
        f'<div class="summary-text">{opening}<br><br>Sebanyak <strong>{summary["flagged_claims"]:,} '
        f'dari {summary["total_claims"]:,} klaim</strong> berada pada kelas Higher Evidentiary Risk '
        'berdasarkan checkpoint IndoBERT.</div>'
        '<div class="summary-callout">Perlu Verifikasi · Tinjau bukti, cakupan target, metodologi, '
        'dan konteks pada laporan asli sebelum menarik kesimpulan.</div>'
        f'<div class="micro-copy">Threshold aktif: {summary.get("threshold", .36):.2f} · '
        'Ringkasan disusun secara rule-based dari hasil prediksi.</div>',
        unsafe_allow_html=True,
    )


def empty_state(title: str, description: str) -> None:
    st.markdown(
        '<div class="empty-state"><div class="empty-icon">♧</div>'
        f'<h3>{escape(title)}</h3><p>{escape(description)}</p></div>', unsafe_allow_html=True,
    )


def claim_table(results: list[dict[str, Any]]) -> None:
    rows = []
    for row in results:
        flagged = row["prediction"] == HIGHER_EVIDENTIARY_RISK
        css = "flagged" if flagged else ""
        prob = float(row["greenwashing_probability"])
        page = row.get("page")
        rows.append(
            f'<tr><td>{int(row["claim_id"])}</td><td class="claim-text">{escape(str(row["claim"]))}</td>'
            f'<td><span class="prediction-badge {css}">{escape(str(row["prediction"]))}</span></td>'
            f'<td>{prob:.1%}<div class="probability-track"><span class="{css}" style="width:{prob * 100:.2f}%"></span></div></td>'
            f'<td>{float(row["confidence"]):.1%}</td><td>{escape(str(page)) if page is not None else "—"}</td></tr>'
        )
    st.markdown(
        '<div class="claim-table-wrap"><table class="claim-table"><thead><tr><th>No.</th>'
        '<th>Claim / Sentence</th><th>Prediction</th><th>Higher-risk Probability</th>'
        '<th>Confidence</th><th>Page</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>',
        unsafe_allow_html=True,
    )


def top_risk_claims(results: list[dict[str, Any]]) -> None:
    fragments = []
    for rank, row in enumerate(sorted(results, key=lambda x: x["greenwashing_probability"], reverse=True)[:5], 1):
        page = f'Page {row["page"]}' if row.get("page") is not None else "Input teks"
        fragments.append(
            f'<div class="risk-claim"><div class="risk-rank">#{rank}</div><div style="flex:1;min-width:0">'
            f'<div class="risk-claim-top"><span>{escape(page)} · Klaim {int(row["claim_id"])}</span>'
            f'<span class="risk-claim-prob">{row["greenwashing_probability"]:.1%}</span></div>'
            f'<p>“{escape(str(row["claim"]))}”</p><span class="micro-copy">Higher-risk Probability</span></div></div>'
        )
    st.markdown(''.join(fragments), unsafe_allow_html=True)
