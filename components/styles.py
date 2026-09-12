"""Accessible, local-only visual system for the research dashboard."""

import streamlit as st


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
          --forest: #063D2B; --green: #0E5B3D; --medium: #258553;
          --soft: #EAF5EE; --canvas: #F7F9F7; --ink: #17342A;
          --muted: #6C8075; --line: #DFE8E1; --red: #E5483F; --orange: #F4A340;
        }
        html, body, [class*="css"], .stApp { font-family: "Segoe UI", Arial, sans-serif; }
        .stApp, [data-testid="stAppViewContainer"] { background: var(--canvas); color: var(--ink); }
        [data-testid="stHeader"] { background: rgba(247,249,247,.94); }
        [data-testid="stMainBlockContainer"] { max-width: 1440px; padding: 2.2rem 3rem 3rem; }
        .stMain h1, .stMain h2, .stMain h3 { color: var(--ink); letter-spacing: -.035em; }
        .stMain h1 { font-size: 2rem; font-weight: 750; }
        .stMain h2 { font-size: 1.4rem; }
        .stMain h3 { font-size: 1.06rem; font-weight: 700; }
        .stMain p { line-height: 1.6; }
        [data-testid="stSidebar"] { background: #063D2B; border-right: 0; }
        [data-testid="stSidebar"] > div:first-child { padding-top: 1.9rem; }
        [data-testid="stSidebar"] [data-testid="stSidebarContent"] { background: #063D2B; }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] { color: #D9EBDD; }
        [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] {
          padding: .8rem .95rem; margin: .14rem 0; border-radius: 10px;
          color: #C9DECF; font-weight: 500; font-size: .94rem; transition: background .15s;
        }
        [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover { background: #164E38; color: white; }
        [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][aria-current="page"] {
          background: #1C6446; color: #FFF; box-shadow: inset 3px 0 #A5D96B;
        }
        [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] p { color: inherit; }
        [data-testid="stSidebar"] hr { border-color: #28583F; }
        [data-testid="stSidebar"] button { color: #E6F2E9; }
        .brand { display:flex; gap:.75rem; align-items:center; padding: .25rem .15rem 1.7rem; }
        .brand-symbol { width:43px; height:43px; border-radius:13px; background:#B8E388;
          color:#063D2B; display:grid; place-items:center; font-size:25px; font-weight:800; }
        .brand-title { color:white; font-size:1.65rem; font-weight:850; letter-spacing:.035em; line-height:1.2; }
        .brand-tag { color:#A7C3AE; font-size:.57rem; font-weight:650; letter-spacing:.15em; margin-top:7px; }
        .sidebar-label { color:#83AD91; font-size:.66rem; letter-spacing:.14em; font-weight:700; margin:1.2rem .95rem .55rem; }
        .sidebar-model { background:#0C4732; border:1px solid #285C40; border-radius:13px; padding:1.05rem; margin-top:2rem; }
        .sidebar-model .model-name { color:#EAF4ED; font-size:.9rem; font-weight:650; margin:.4rem 0 1rem; }
        .model-label { color:#99BCA3; font-size:.63rem; font-weight:700; letter-spacing:.13em; }
        .model-row { display:flex; justify-content:space-between; align-items:center; gap:.5rem; margin:.8rem 0 0; }
        .model-value { font-size:.74rem; color:#E2EEE5; font-weight:600; text-align:right; }
        .status-dot { width:7px; height:7px; background:#AAD578; border-radius:50%; display:inline-block; margin-right:6px; }
        .status-dot.off { background:#F4A340; }
        .sidebar-foot { color:#96B69F; font-size:.67rem; line-height:1.6; padding:1.2rem .2rem; }
        .topline { display:flex; justify-content:space-between; gap:1rem; align-items:center; padding-bottom:1.2rem; }
        .eyebrow { font-size:.68rem; text-transform:uppercase; font-weight:750; letter-spacing:.16em; color:#74917E; }
        .local-pill { border:1px solid #DDE9DF; background:#EDF5EF; border-radius:100px; padding:5px 11px;
          color:#487352; font-size:.68rem; white-space:nowrap; }
        .local-pill:before { content:""; display:inline-block; width:6px; height:6px; background:#65A15D;
          border-radius:50%; margin-right:6px; vertical-align:middle; }
        .hero { position:relative; isolation:isolate; overflow:hidden; border-radius:20px; min-height:290px;
          padding:2.1rem 2.5rem 2rem; background:linear-gradient(110deg,#063D2B 0%,#0C5136 55%,#176340 100%);
          color:#FFF; margin-bottom:1.25rem; box-shadow:0 8px 30px #123C2510; }
        .hero-content { position:relative; z-index:2; max-width:72%; }
        .hero-badge { display:inline-flex; align-items:center; gap:.4rem; font-size:.65rem;
          color:#DBEDCD; background:#FFFFFF10; border:1px solid #FFFFFF25; padding:5px 10px; border-radius:99px; }
        .hero-title { font-size:3.3rem; font-weight:850; letter-spacing:.015em; margin:.65rem 0 .15rem; line-height:1.15; }
        .hero-subtitle { font-size:1.18rem; color:#EDF6ED; font-weight:550; line-height:1.45; margin-top:.45rem; }
        .hero-description { color:#B5D0BB; font-size:.82rem; max-width:450px; line-height:1.65; margin-top:.8rem; }
        .hero-quote { position:absolute; right:2.4rem; bottom:2rem; z-index:2; color:#D6EAC4;
          font-family:Georgia,serif; font-style:italic; font-size:1.05rem; text-align:right; line-height:1.55; }
        .hero-art { position:absolute; right:0; top:0; width:340px; height:100%; opacity:.7; overflow:hidden; }
        .hero-ring { position:absolute; width:330px; height:330px; border:1px solid #96C47025; border-radius:50%; top:-100px; right:-5px; }
        .hero-ring.r2 { width:270px; height:270px; top:-70px; right:25px; }
        .hero-ring.r3 { width:210px; height:210px; top:-40px; right:55px; }
        .hero-leaf { position:absolute; width:76px; height:135px; background:linear-gradient(145deg,#B4DD7650,#73B55A04);
          border:1px solid #B6D98B50; border-radius:90% 0 90% 0; right:110px; top:54px; transform:rotate(-10deg); }
        .hero-leaf.second { right:46px; top:91px; width:56px; height:96px; transform:rotate(32deg); opacity:.6; }
        .hero-leaf:after { content:""; position:absolute; height:85%; width:1px; background:#BDE48C60; top:15px; left:40%; transform:rotate(25deg); }
        .workflow { display:flex; align-items:center; justify-content:space-between; gap:.4rem; padding:.2rem 0 1rem; }
        .workflow-item { display:flex; align-items:center; gap:.55rem; color:#6B7F70; font-size:.72rem; }
        .workflow-number { display:grid; place-items:center; width:24px; height:24px; border-radius:50%;
          background:#E8F1E9; border:1px solid #D8E6DA; font-size:.65rem; font-weight:700; color:#3E7450; }
        .workflow-line { height:1px; flex:1; max-width:75px; background:#DCE7DE; }
        [data-testid="stVerticalBlockBorderWrapper"] > div { border-radius:15px; border-color:#E0E9E1; }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) { background:#FFF; }
        .st-key-document_upload, .st-key-input_quick, .st-key-risk_chart, .st-key-analysis_summary,
        .st-key-distribution_card, .st-key-results_card, .st-key-about_card, .st-key-history_card {
          background:#FFFFFF; border-radius:15px;
        }
        .section-kicker { color:#758D7C; font-size:.63rem; font-weight:750; letter-spacing:.13em; margin-bottom:.35rem; text-transform:uppercase; }
        .section-title { color:#17342A; font-size:1.02rem; font-weight:750; letter-spacing:-.025em; margin-bottom:.25rem; }
        .section-note { color:#778B7C; font-size:.77rem; line-height:1.6; margin-bottom:.9rem; }
        .section-heading { display:flex; justify-content:space-between; gap:1rem; align-items:center; margin:1.6rem 0 .7rem; }
        .section-heading h2 { margin:0; font-size:1.18rem; letter-spacing:-.02em; }
        .section-heading span { font-size:.7rem; color:#7F9385; }
        [data-testid="stFileUploader"] { background:#FAFCFA; border-radius:12px; }
        [data-testid="stFileUploaderDropzone"] { border:1.5px dashed #BBD4C1; background:#F7FBF8; border-radius:12px; min-height:138px; }
        [data-testid="stFileUploaderDropzone"] small { color:#829589; }
        .stButton>button, .stDownloadButton>button { border-radius:9px; min-height:42px; font-size:.83rem; font-weight:650; }
        .stButton>button[kind="primary"] { background:#0E5B3D; border-color:#0E5B3D; box-shadow:0 3px 7px #0E5B3D13; }
        .stButton>button[kind="primary"]:hover { background:#167447; border-color:#167447; }
        [data-testid="stTextInputRootElement"], [data-testid="stTextAreaRootElement"],
        [data-baseweb="select"]>div { border-radius:9px; border-color:#DDE7DF; background:#FAFCFA; }
        .stTabs [data-baseweb="tab-list"] { gap:1.3rem; border-bottom:1px solid #E1EAE2; margin-bottom:.75rem; }
        .stTabs [data-baseweb="tab"] { padding:0 .1rem .75rem; font-size:.85rem; color:#7B8E80; }
        .stTabs [aria-selected="true"] { color:#0E5B3D; font-weight:750; }
        .stTabs [data-baseweb="tab-highlight"] { background:#258553; height:3px; }
        .stTabs [data-baseweb="tab-border"] { background:none; }
        .file-meta { display:grid; grid-template-columns:2fr 1fr 1fr 1fr; gap:1rem; margin:.8rem 0 1.1rem;
          padding:.85rem 1rem; background:#F3F8F4; border:1px solid #E2ECE3; border-radius:10px; }
        .file-meta dt { font-size:.61rem; color:#7D9584; text-transform:uppercase; letter-spacing:.055em; }
        .file-meta dd { margin:.25rem 0 0; font-size:.77rem; font-weight:650; color:#315D40; overflow-wrap:anywhere; }
        .kpi-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:1rem; margin:.4rem 0 1.15rem; }
        .kpi { background:white; border:1px solid #DFE9E1; border-radius:13px; padding:1.05rem 1.25rem; position:relative; }
        .kpi-label { color:#708677; font-size:.72rem; font-weight:600; }
        .kpi-value { font-size:2rem; font-weight:760; line-height:1.35; letter-spacing:-.045em; color:#163D2B; margin:.25rem 0; }
        .kpi-unit { color:#9BAB9E; font-size:.9rem; font-weight:500; letter-spacing:normal; }
        .kpi-detail { color:#8AA08F; font-size:.65rem; }
        .kpi-icon { position:absolute; right:1rem; top:1rem; height:29px; width:29px; display:grid; place-items:center;
          background:#EFF6EF; border-radius:8px; color:#548661; font-size:.82rem; }
        .kpi.risk-high .kpi-value { color:#D95047; }
        .kpi.risk-moderate .kpi-value { color:#BE8229; }
        .risk-badge { display:inline-block; padding:5px 10px; border-radius:6px; font-size:.62rem;
          font-weight:750; letter-spacing:.07em; background:#EDF6ED; color:#258553; }
        .risk-badge.high { background:#FDECE9; color:#D44A42; }
        .risk-badge.moderate { background:#FEF4E3; color:#B8771F; }
        .summary-text { font-size:.87rem; color:#5B7565; line-height:1.8; margin:1rem 0; }
        .summary-callout { background:#F1F7F0; border-left:3px solid #8CB878; padding:.8rem 1rem;
          color:#42664D; font-size:.77rem; border-radius:0 8px 8px 0; line-height:1.7; }
        .micro-copy { font-size:.65rem; color:#879C8D; line-height:1.6; margin-top:.75rem; }
        .claim-table-wrap { overflow:auto; border:1px solid #E4EBE5; border-radius:10px; }
        .claim-table { width:100%; border-collapse:collapse; font-size:.75rem; background:#FFF; }
        .claim-table th { text-align:left; background:#F5F8F5; padding:.78rem .8rem; font-weight:650;
          color:#728676; white-space:nowrap; border-bottom:1px solid #E3ECE4; font-size:.65rem; }
        .claim-table td { padding:.86rem .8rem; border-bottom:1px solid #EDF1ED; color:#405C4A; vertical-align:top; line-height:1.65; }
        .claim-table tr:last-child td { border-bottom:none; }
        .claim-table tr:hover td { background:#FCFDFC; }
        .claim-table .claim-text { min-width:260px; max-width:650px; }
        .prediction-badge { display:inline-block; white-space:nowrap; border-radius:5px; padding:3px 7px;
          font-size:.61rem; font-weight:700; background:#ECF6EE; color:#367F4D; }
        .prediction-badge.flagged { background:#FEF0ED; color:#D05A4E; }
        .probability-track { height:4px; border-radius:4px; background:#F0F3F0; width:85px; margin-top:4px; }
        .probability-track span { display:block; height:4px; border-radius:4px; background:#71A879; }
        .probability-track span.flagged { background:#E58C7D; }
        .risk-claim { display:flex; gap:.8rem; padding:1rem 0; border-bottom:1px solid #E8EEE8; }
        .risk-claim:last-child { border-bottom:0; }
        .risk-rank { width:29px; height:29px; flex-shrink:0; display:grid; place-items:center;
          border:1px solid #F1DED7; background:#FFF5F0; color:#BA7D5A; border-radius:8px; font-size:.7rem; font-weight:700; }
        .risk-claim p { margin:.4rem 0; color:#4C6756; font-size:.77rem; line-height:1.65; }
        .risk-claim-top { display:flex; justify-content:space-between; gap:1rem; color:#8C9E91; font-size:.65rem; }
        .risk-claim-prob { color:#C66952; font-size:.74rem; font-weight:700; white-space:nowrap; }
        .empty-state { text-align:center; padding:1.75rem 1rem 1rem; color:#899B8C; }
        .empty-icon { margin:0 auto .7rem; height:42px; width:42px; display:grid; place-items:center;
          border:1px solid #DDE9DE; border-radius:12px; background:#EEF5EE; color:#74A279; font-size:1.2rem; }
        .empty-state h3 { font-size:.9rem; color:#65806C; margin:0; }
        .empty-state p { font-size:.76rem; margin:.3rem auto 0; max-width:420px; }
        .research-footer { display:flex; gap:.7rem; align-items:flex-start; margin:1.8rem 0 .4rem;
          border-top:1px solid #DDE8DF; padding-top:1.1rem; color:#8A9C8E; font-size:.66rem; line-height:1.65; }
        .research-footer .footer-mark { color:#679471; font-size:1rem; }
        .about-grid { display:grid; grid-template-columns:1fr 1fr; gap:.8rem; margin:.7rem 0 1rem; }
        .about-item { border:1px solid #E2EBE3; border-radius:10px; padding:.85rem 1rem; background:#FBFCFA; }
        .about-item .label { color:#859789; font-size:.64rem; margin-bottom:.3rem; }
        .about-item .value { color:#3A6347; font-size:.8rem; font-weight:650; overflow-wrap:anywhere; }
        [data-testid="stCaptionContainer"] { color:#849889; font-size:.72rem; }
        [data-testid="stAlert"] { border-radius:10px; }
        [data-testid="stDecoration"] { display:none; }
        @media (max-width: 1100px) {
          [data-testid="stMainBlockContainer"] { padding:1.5rem 1.5rem 2.5rem; }
          .hero { padding:1.8rem; } .hero-quote { right:1.5rem; font-size:.9rem; }
          .hero-content { max-width:72%; } .hero-art { width:260px; }
          .kpi { padding:1rem; } .kpi-icon { display:none; }
        }
        @media (max-width: 700px) {
          [data-testid="stMainBlockContainer"] { padding:1rem .9rem 2rem; }
          .topline { padding-bottom:.8rem; } .local-pill { font-size:.57rem; }
          .hero { padding:1.4rem; min-height:310px; border-radius:15px; }
          .hero-content { max-width:100%; } .hero-title { font-size:2.7rem; }
          .hero-subtitle { font-size:1rem; } .hero-description { max-width:90%; }
          .hero-art { opacity:.2; } .hero-quote { position:relative; right:auto; bottom:auto; text-align:left; margin-top:1rem; font-size:.82rem; }
          .kpi-grid { grid-template-columns:repeat(2,minmax(0,1fr)); gap:.65rem; }
          .kpi-value { font-size:1.7rem; } .file-meta { grid-template-columns:1fr 1fr; }
          .workflow-item { font-size:.58rem; gap:.3rem; } .workflow-number { width:20px; height:20px; }
          .workflow-line { max-width:18px; } .about-grid { grid-template-columns:1fr; }
        }
        @media (prefers-reduced-motion: reduce) { * { transition:none !important; } }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    st.markdown(
        '<div class="research-footer"><span class="footer-mark">♧</span>'
        '<span>BUTO IJO merupakan alat bantu analisis berbasis AI. Hasil prediksi tidak '
        'menggantikan audit independen, verifikasi regulator, maupun penilaian ahli.</span></div>',
        unsafe_allow_html=True,
    )
