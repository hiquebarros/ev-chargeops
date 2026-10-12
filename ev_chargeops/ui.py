"""Identidade visual compartilhada (inspirada no portal do aluno FIAP)."""

import altair as alt
import streamlit as st


PINK = "#ED145B"
MUTED = "#9A9A9A"
GRID = "#2A2A2A"
FONT = "Montserrat, Helvetica, Arial, sans-serif"

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800&family=Roboto:wght@400;500&display=swap');
:root {
  --pink: #ED145B; --pink-dark: #B80F47; --bg: #121212; --panel: #1D1D1D; --panel-2: #252525;
  --line: #333333; --text: #F2F2F2; --muted: #9A9A9A;
}

/* Base */
.stApp { background: linear-gradient(115deg, #1b1d1d 0%, #0b0b0b 45%, #151717 100%) fixed; color: var(--text); font-family: 'Roboto', sans-serif; }
.stApp::before, .stApp::after {
  content: ""; position: fixed; width: 260px; height: 220px; pointer-events: none; z-index: 0;
  background-image: radial-gradient(circle, rgba(255,255,255,.55) 1px, transparent 1.6px);
  background-size: 34px 34px;
}
.stApp::before { top: 40px; right: 24px; -webkit-mask-image: radial-gradient(circle at 80% 20%, #000 0%, transparent 70%); mask-image: radial-gradient(circle at 80% 20%, #000 0%, transparent 70%); }
.stApp::after { bottom: 20px; left: 24px; -webkit-mask-image: radial-gradient(circle at 20% 80%, #000 0%, transparent 70%); mask-image: radial-gradient(circle at 20% 80%, #000 0%, transparent 70%); }
header[data-testid="stHeader"] { background: transparent; }
[data-testid="stDecoration"] { display: none; }
.block-container { padding-top: 2.5rem; max-width: 1320px; }

/* Tipografia */
h1, h2, h3, h4 { font-family: 'Montserrat', sans-serif !important; text-transform: uppercase; color: var(--text) !important; }
h1 { font-weight: 300 !important; letter-spacing: .04em !important; }
h3 {
  font-size: .95rem !important; font-weight: 600 !important; letter-spacing: .1em !important;
  padding-bottom: .7rem !important; margin-bottom: .6rem; border-bottom: 1px solid var(--line);
}
[data-testid="stHeaderActionElements"] { display: none; }
[data-testid="stCaptionContainer"], .stCaption { color: var(--muted) !important; }
.stApp p, .stApp li, [data-baseweb="select"] div { font-family: 'Roboto', sans-serif; }

/* Sidebar: grafite com barra rosa, como o menu lateral do portal */
[data-testid="stSidebar"] { background: #181818; border-right: 1px solid #262626; }
[data-testid="stSidebar"] [data-testid="stSidebarContent"] { box-shadow: inset 3px 0 0 var(--pink); }
[data-testid="stSidebar"] label p { font-family: 'Montserrat', sans-serif; text-transform: uppercase; font-size: 11px; font-weight: 600; letter-spacing: .12em; color: var(--muted); }
[data-testid="stSidebarNav"], [data-testid="stSidebarNavSeparator"] { display: none; }
[data-testid="stSidebarContent"] { padding-top: .5rem; }
[data-baseweb="select"] div { color: var(--text); }
[data-testid="stPageLink-NavLink"] { border-radius: 0; padding: .45rem .9rem; background: transparent !important; }
[data-testid="stPageLink-NavLink"] p { font-family: 'Montserrat', sans-serif; text-transform: uppercase; font-size: 12px; letter-spacing: .1em; color: var(--muted); }
[data-testid="stPageLink-NavLink"]:hover p { color: var(--text); }
.stPageLink { margin: -4px 0; }
.fiap-nav-active {
  font-family: 'Montserrat', sans-serif; text-transform: uppercase; font-size: 12px; letter-spacing: .1em; font-weight: 600;
  color: var(--pink); padding: .45rem .9rem; box-shadow: inset 3px 0 0 var(--pink); background: rgba(237,20,91,.08); margin: -4px 0;
}
.fiap-nav-gap { height: 1px; background: var(--line); margin: 14px 0 18px; }

/* Cartões de métrica */
[data-testid="stMetric"] {
  background: var(--panel); border: none; border-left: 3px solid var(--pink); border-radius: 0; padding: 18px 20px;
  min-height: 132px; box-sizing: border-box;
}
[data-testid="stMetricLabel"] p { font-family: 'Montserrat', sans-serif; text-transform: uppercase; font-size: 11px !important; font-weight: 600; letter-spacing: .12em; color: var(--muted); }
[data-testid="stMetricValue"], [data-testid="stMetricValue"] div { font-family: 'Montserrat', sans-serif; font-weight: 600; color: var(--text); font-size: 1.75rem; }

/* Botões: contorno rosa, caixa alta (estilo "VISUALIZAR"/"LOGAR") */
div.stButton button, div.stDownloadButton button {
  border-radius: 0; background: transparent; border: 1px solid var(--pink); color: var(--pink);
  font-family: 'Montserrat', sans-serif; font-weight: 600; text-transform: uppercase; letter-spacing: .12em; font-size: 12px;
  padding: .55rem 1.1rem; min-height: 44px; white-space: nowrap; transition: background .15s, color .15s;
}
div.stButton button p, div.stDownloadButton button p { font-family: 'Montserrat', sans-serif; font-size: 12px; }
div.stButton button:hover, div.stDownloadButton button:hover { background: var(--pink); color: #fff; border-color: var(--pink); }
div.stButton button:focus:not(:active), div.stDownloadButton button:focus:not(:active) { color: var(--pink); border-color: var(--pink); }
div.stButton button[kind="primary"] { background: var(--pink); color: #fff; }
div.stButton button[kind="primary"]:hover { background: var(--pink-dark); border-color: var(--pink-dark); }

/* Abas */
[data-baseweb="tab-list"] { gap: 28px; border-bottom: 1px solid var(--line); }
[data-baseweb="tab"] p { font-family: 'Montserrat', sans-serif; text-transform: uppercase; font-size: 13px !important; font-weight: 600; letter-spacing: .1em; color: var(--muted); }
[data-baseweb="tab"][aria-selected="true"] p { color: var(--text); }
[data-baseweb="tab-highlight"] { background: var(--pink); height: 3px; }
[data-baseweb="tab-border"] { display: none; }

/* Superfícies retas */
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 0 !important; }
div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) { border-color: var(--line); }
[data-testid="stAlert"] > div { border-radius: 0; background: var(--panel); border-left: 3px solid var(--muted); color: var(--text); }
[data-testid="stAlert"] p { color: var(--text) !important; }
[data-testid="stAlert"] > div:has([data-testid="stAlertContentWarning"]) { border-left-color: #F5A623; }
[data-testid="stAlert"] > div:has([data-testid="stAlertContentSuccess"]) { border-left-color: #3DBE6C; }
[data-testid="stAlert"] > div:has([data-testid="stAlertContentError"]) { border-left-color: var(--pink); }
[data-baseweb="select"] > div, [data-baseweb="input"] { border-radius: 0 !important; background: transparent; border-color: #4a4a4a; }
[data-testid="stDataFrame"], [data-testid="stDataFrame"] > div { border-radius: 0; }
hr { border-color: var(--line) !important; }

/* Scrollbar fina rosa */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-thumb { background: var(--pink); }
::-webkit-scrollbar-track { background: transparent; }

/* Componentes próprios */
.fiap-wordmark { font-family: 'Montserrat', sans-serif; font-weight: 300; font-size: 34px; letter-spacing: .14em; color: var(--pink); line-height: 1; }
.fiap-product { font-family: 'Montserrat', sans-serif; font-weight: 700; text-transform: uppercase; letter-spacing: .12em; font-size: 13px; color: var(--text); margin-top: 14px; }
.fiap-product-sub { color: var(--muted); font-size: 12px; margin: 4px 0 18px; }
.fiap-kicker { font-family: 'Montserrat', sans-serif; color: var(--pink); text-transform: uppercase; font-size: 12px; font-weight: 600; letter-spacing: .14em; }
.fiap-hero { font-family: 'Montserrat', sans-serif; text-transform: uppercase; font-weight: 300; font-size: clamp(30px, 4vw, 46px); line-height: 1.1; letter-spacing: .04em; color: var(--pink); margin: 10px 0 6px; }
.fiap-hero b { font-weight: 800; }
.fiap-lead { color: var(--muted); margin-bottom: 26px; }
.fiap-note { color: var(--muted); font-size: 13px; }
.fiap-tag { display: inline-block; background: var(--pink); color: #fff; font-family: 'Montserrat', sans-serif; font-weight: 600; font-size: 11px; letter-spacing: .1em; text-transform: uppercase; padding: 3px 10px; }
.fiap-footer { text-align: center; color: var(--muted); font-size: 13px; padding: 8px 0 4px; }
.fiap-footer span { color: var(--pink); }
</style>
"""


def apply_theme():
    st.markdown(_CSS, unsafe_allow_html=True)


PAGES = [("app.py", "Portal do gestor"), ("pages/2_Portal_do_morador.py", "Portal do morador")]


def sidebar_brand(subtitle, active):
    st.sidebar.markdown(
        "<div class='fiap-wordmark'>FIAP</div>"
        "<div class='fiap-product'>EV ChargeOps</div>"
        "<div class='fiap-product-sub'>%s</div>" % subtitle,
        unsafe_allow_html=True,
    )
    for path, label in PAGES:
        if path == active:
            st.sidebar.markdown("<div class='fiap-nav-active'>%s</div>" % label, unsafe_allow_html=True)
        else:
            st.sidebar.page_link(path, label=label)
    st.sidebar.markdown("<div class='fiap-nav-gap'></div>", unsafe_allow_html=True)


def hero(kicker, light, bold, lead=None):
    html = "<div class='fiap-kicker'>%s</div>" % kicker if kicker else ""
    html += "<div class='fiap-hero'>%s <b>%s</b></div>" % (light, bold)
    if lead:
        html += "<div class='fiap-lead'>%s</div>" % lead
    st.markdown(html, unsafe_allow_html=True)


def footer(text):
    st.markdown("---")
    st.markdown("<div class='fiap-footer'>%s</div>" % text, unsafe_allow_html=True)


def bar_chart(frame, category, value, height=290):
    chart = (
        alt.Chart(frame)
        .mark_bar(color=PINK, size=22)
        .encode(
            x=alt.X(category + ":N", sort="-y", title=category,
                    axis=alt.Axis(labelAngle=0, labelExpr="replace(datum.label, '%s ', '')" % category)),
            y=alt.Y(value + ":Q", title=value),
            tooltip=[category, alt.Tooltip(value + ":Q", format=".1f")],
        )
        .properties(height=height, background="transparent")
        .configure_view(strokeWidth=0)
        .configure_axis(
            labelColor=MUTED, titleColor=MUTED, gridColor=GRID, domainColor=GRID, tickColor=GRID,
            labelFont=FONT, titleFont=FONT, labelFontSize=11, titleFontSize=11, titleFontWeight=600,
        )
    )
    st.altair_chart(chart, use_container_width=True)
