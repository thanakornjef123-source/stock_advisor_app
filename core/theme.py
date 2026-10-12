# -*- coding: utf-8 -*-
"""
Visual system for the terminal.

One place defines every colour, the Plotly template and the CSS, so the whole
application stays consistent and can be re-skinned by editing this file alone.
"""
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# ---------------------------------------------------------------- palette
BG = "#0B0E14"        # page background
PANEL = "#141A23"     # cards, tables, sidebar
PANEL_2 = "#1B2330"   # hover / raised surface
BORDER = "#232C3B"
TEXT = "#DCE3EC"
MUTED = "#7C8797"
ACCENT = "#2D8CFF"    # primary blue
UP = "#26A69A"        # gains
DOWN = "#EF5350"      # losses
WARN = "#F0A22E"
GRID = "#1B2330"

# categorical palette for sectors / series
SERIES = ["#2D8CFF", "#26A69A", "#F0A22E", "#EF5350", "#A78BFA",
          "#4DD0E1", "#F06292", "#9CCC65", "#FFB74D", "#7986CB",
          "#4DB6AC", "#DCE775"]

MONO = "'SFMono-Regular', 'JetBrains Mono', Consolas, 'Roboto Mono', monospace"
SANS = "'Inter', -apple-system, 'Segoe UI', Roboto, sans-serif"


def register_template():
    """Register the Plotly template used by every chart."""
    t = go.layout.Template()
    t.layout = go.Layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.012)",
        font=dict(family=SANS, size=12, color=TEXT),
        title=dict(font=dict(size=14, color=TEXT), x=0, xanchor="left"),
        xaxis=dict(gridcolor=GRID, zerolinecolor=BORDER, linecolor=BORDER,
                   tickfont=dict(family=MONO, size=11, color=MUTED),
                   title=dict(font=dict(size=11, color=MUTED))),
        yaxis=dict(gridcolor=GRID, zerolinecolor=BORDER, linecolor=BORDER,
                   tickfont=dict(family=MONO, size=11, color=MUTED),
                   title=dict(font=dict(size=11, color=MUTED))),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11, color=MUTED),
                    orientation="h", yanchor="bottom", y=1.02, x=0),
        hoverlabel=dict(bgcolor=PANEL_2, bordercolor=BORDER,
                        font=dict(family=MONO, size=11, color=TEXT)),
        colorway=SERIES,
        margin=dict(l=8, r=8, t=28, b=8),
    )
    pio.templates["terminal"] = t
    pio.templates.default = "terminal"


CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {{ font-family: {SANS}; }}

/* ---------- the canvas ----------
   A flat dark rectangle reads as empty. Real terminals sit on a faint
   engineering grid with a little ambient light in the corners, which gives the
   eye something to rest on without competing with the data. Everything here is
   deliberately near the threshold of visibility. */
.stApp {{
    background-color: {BG};
    background-image:
        radial-gradient(1250px 620px at 88% -6%, rgba(45,140,255,.15), transparent 60%),
        radial-gradient(980px 560px at -6% 104%, rgba(38,166,154,.10), transparent 58%),
        radial-gradient(760px 460px at 46% 44%, rgba(124,135,151,.07), transparent 68%),
        linear-gradient(rgba(255,255,255,.036) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.036) 1px, transparent 1px),
        linear-gradient(rgba(255,255,255,.014) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.014) 1px, transparent 1px);
    background-size: auto, auto, auto, 184px 184px, 184px 184px, 46px 46px, 46px 46px;
    background-position: 0 0, 0 0, 0 0, -1px -1px, -1px -1px, -1px -1px, -1px -1px;
    background-attachment: fixed;
}}
/* a hairline of brand colour along the very top edge */
.stApp::before {{
    content: ""; position: fixed; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, {ACCENT} 0%, {UP} 42%, transparent 78%);
    opacity: .55; z-index: 999999; pointer-events: none;
}}

/* Streamlit's header floats over the page and holds the Deploy button, which
   was covering the first row of content. Hide the toolbar itself, but keep the
   header box — the control that reopens a collapsed sidebar lives inside it,
   and zeroing the header made that button unreachable. */
header[data-testid="stHeader"] {{
    background: transparent;
    pointer-events: none;            /* let clicks fall through to the page */
}}
header[data-testid="stHeader"] * {{ pointer-events: auto; }}
[data-testid="stToolbar"], .stAppDeployButton, [data-testid="stDecoration"],
[data-testid="stStatusWidget"] {{ display: none !important; }}

/* Streamlit's own expand control is unreliable across versions, so it is left
   alone here and a custom toggle is injected instead (see sidebar_toggle). */
[data-testid="stSidebarCollapseButton"] button {{
    background: {PANEL_2} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 5px !important;
    color: {TEXT} !important;
}}
[data-testid="stSidebarCollapseButton"] button:hover {{
    background: {ACCENT} !important;
    border-color: {ACCENT} !important;
    color: #fff !important;
}}

.block-container {{ padding-top: 1.15rem; padding-bottom: 4rem; max-width: 1640px; }}

/* ---------- density ---------- */
div[data-testid="stVerticalBlock"] {{ gap: 0.72rem; }}
div[data-testid="stHorizontalBlock"] {{ gap: 0.62rem; }}
div[data-testid="stElementContainer"] {{ margin-bottom: 0 !important; }}
hr {{ margin: 0.75rem 0; }}
.stTabs [data-baseweb="tab-panel"] {{ padding-top: 0.85rem; }}
div[data-testid="stExpander"] details summary p {{ font-size: 0.86rem; }}
label[data-testid="stWidgetLabel"] p {{
    font-size: 0.74rem !important; color: {MUTED} !important;
    text-transform: uppercase; letter-spacing: 0.045em; font-weight: 500;
    margin-bottom: 2px;
}}
div[data-testid="stCaptionContainer"] p {{ font-size: 0.76rem; color: {MUTED}; }}

/* ---------- sidebar ---------- */
section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #10161F 0%, {PANEL} 42%);
    border-right: 1px solid {BORDER};
    width: 268px !important;
}}
section[data-testid="stSidebar"] > div {{ padding-top: 0.9rem; }}
section[data-testid="stSidebar"] hr {{ margin: 0.7rem 0; border-color: {BORDER}; }}

/* brand */
.brand {{
    display: flex; align-items: center; gap: 10px;
    padding: 2px 4px 14px 4px;
}}
.brand .mark {{
    width: 34px; height: 34px; border-radius: 6px; flex: 0 0 34px;
    background: linear-gradient(135deg, {ACCENT} 0%, #1B4FA8 100%);
    display: flex; align-items: center; justify-content: center;
    font-family: {MONO}; font-weight: 700; font-size: 0.95rem; color: #fff;
    box-shadow: 0 2px 10px rgba(45,140,255,.35);
}}
.brand .name {{ font-size: 0.92rem; font-weight: 700; color: {TEXT};
                letter-spacing: -0.01em; line-height: 1.15; }}
.brand .sub {{ font-size: 0.6rem; color: {MUTED}; font-family: {MONO};
               letter-spacing: 0.14em; margin-top: 2px; }}

/* section label */
.navlabel {{
    font-size: 0.6rem; color: {MUTED}; font-family: {MONO};
    letter-spacing: 0.16em; margin: 12px 0 5px 6px; font-weight: 500;
}}

/* nav buttons */
section[data-testid="stSidebar"] .stButton > button {{
    background: transparent; color: {MUTED}; border: 1px solid transparent;
    border-radius: 5px; font-weight: 500; font-size: 0.83rem;
    text-align: left; justify-content: flex-start;
    padding: 7px 11px; margin: 1px 0; width: 100%;
    transition: background .12s ease, color .12s ease;
}}
section[data-testid="stSidebar"] .stButton > button:hover {{
    background: {PANEL_2}; color: {TEXT}; border-color: {BORDER};
}}
section[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
    background: rgba(45,140,255,.13); color: {TEXT};
    border: 1px solid rgba(45,140,255,.4);
    box-shadow: inset 3px 0 0 {ACCENT};
}}
section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {{
    background: rgba(45,140,255,.2); color: #fff;
}}

/* status card in the sidebar */
.sidecard {{
    background: {PANEL_2}; border: 1px solid {BORDER};
    border-radius: 5px; padding: 9px 11px; margin-top: 4px;
}}
.sidecard .k {{ font-size: 0.6rem; color: {MUTED}; font-family: {MONO};
                letter-spacing: 0.12em; }}
.sidecard .v {{ font-family: {MONO}; font-size: 0.9rem; color: {TEXT}; margin-top: 3px; }}
.sidecard .s {{ font-family: {MONO}; font-size: 0.68rem; color: {MUTED}; margin-top: 1px; }}
.sidefoot {{ font-family: {MONO}; font-size: 0.62rem; color: {MUTED};
             letter-spacing: 0.08em; line-height: 1.7; }}
.dot {{ display:inline-block; width:6px; height:6px; border-radius:50%;
        background:{UP}; margin-right:6px; vertical-align:middle; }}

/* ---------- headings ---------- */
h1, h2, h3, h4, h5 {{ color: {TEXT}; font-weight: 650; letter-spacing: -0.018em; }}
h1 {{ font-size: 1.52rem; }}
h2 {{ font-size: 1.16rem; margin: 0.5rem 0 0.2rem 0; }}
h3 {{ font-size: 1.0rem; margin: 0.4rem 0 0.15rem 0; }}
h4 {{ font-size: 0.92rem; margin: 0.35rem 0 0.1rem 0; }}
h5 {{
    font-size: 0.74rem !important; color: {MUTED} !important;
    text-transform: uppercase; letter-spacing: 0.09em; font-weight: 600;
    margin: 0.7rem 0 0.25rem 0; padding-bottom: 4px;
    border-bottom: 1px solid {BORDER};
}}

/* ---------- top bar ---------- */
.topbar {{
    display: flex; align-items: center; justify-content: space-between;
    background: linear-gradient(90deg, {PANEL} 0%, {BG} 100%);
    border: 1px solid {BORDER}; border-left: 3px solid {ACCENT};
    border-radius: 4px; padding: 11px 16px; margin: 0 0 14px 0;
    flex-wrap: wrap; gap: 6px;
}}
.topbar .t-title {{ font-size: 1.05rem; font-weight: 600; color: {TEXT}; }}
.topbar .t-sub {{ font-size: 0.75rem; color: {MUTED}; font-family: {MONO}; }}

/* ---------- microinteractions ---------- */
.stButton > button, .stDownloadButton > button,
div[data-baseweb="select"] > div, div[data-testid="stDataFrame"],
.panel, .feature, .stat, .lp-card {{
    transition: background-color .15s ease, border-color .15s ease,
                transform .15s ease, box-shadow .15s ease;
}}
.stButton > button:active {{ transform: translateY(1px); }}
.stat:hover {{ border-left-color: {ACCENT}; }}
.panel:hover {{ border-color: rgba(255,255,255,.10); }}
@keyframes fadeUp {{ from {{ opacity: 0; transform: translateY(5px); }}
                     to {{ opacity: 1; transform: none; }} }}
.stat-row, .topbar, .panel {{ animation: fadeUp .22s ease both; }}

/* ---------- metric cards ---------- */
div[data-testid="stMetric"] {{
    background: {PANEL}; border: 1px solid {BORDER}; border-radius: 4px;
    padding: 10px 12px;
}}
div[data-testid="stMetricLabel"] p {{
    font-size: 0.7rem !important; color: {MUTED} !important;
    text-transform: uppercase; letter-spacing: 0.05em; font-weight: 500;
}}
div[data-testid="stMetricValue"] {{
    font-family: {MONO} !important; font-size: 1.25rem !important;
    color: {TEXT} !important; font-weight: 500;
}}
div[data-testid="stMetricDelta"] {{ font-family: {MONO} !important; font-size: 0.8rem !important; }}

/* ---------- stat strip ---------- */
.stat-row {{ display: flex; gap: 8px; flex-wrap: wrap; margin: 4px 0 12px 0; }}
.stat {{
    flex: 1 1 128px; background: rgba(20,26,35,.86);
    border: 1px solid {BORDER}; border-left: 2px solid {BORDER};
    border-radius: 3px; padding: 8px 11px 9px 11px;
}}
.stat .k {{ font-size: 0.63rem; color: {MUTED}; text-transform: uppercase;
            letter-spacing: 0.07em; margin-bottom: 2px; font-weight: 500; }}
.stat .v {{ font-family: {MONO}; font-size: 1.12rem; color: {TEXT};
            font-weight: 600; letter-spacing: -0.02em; }}
.stat .v.up {{ color: {UP}; }}
.stat .v.down {{ color: {DOWN}; }}
.stat .s {{ font-family: {MONO}; font-size: 0.68rem; color: {MUTED}; margin-top: 2px; }}

/* ---------- chart surfaces ---------- */
div[data-testid="stPlotlyChart"] {{
    background: linear-gradient(180deg, rgba(20,26,35,.72) 0%, rgba(20,26,35,.42) 100%);
    border: 1px solid {BORDER};
    border-radius: 7px;
    padding: 6px 8px 2px 8px;
    transition: border-color .15s ease;
}}
div[data-testid="stPlotlyChart"]:hover {{ border-color: rgba(45,140,255,.30); }}

/* panels get a touch more presence against the textured canvas */
.panel {{ backdrop-filter: blur(2px); }}
div[data-testid="stExpander"] {{ backdrop-filter: blur(2px); }}
div[data-testid="stDataFrame"] {{ background: rgba(20,26,35,.55); }}

/* ---------- tables ---------- */
div[data-testid="stDataFrame"] {{
    border: 1px solid {BORDER}; border-radius: 6px; overflow: hidden;
    transition: border-color .15s ease;
}}
div[data-testid="stDataFrame"]:hover {{ border-color: rgba(45,140,255,.35); }}
div[data-testid="stDataFrame"] * {{ font-family: {MONO}; font-size: 0.785rem; }}
div[data-testid="stDataFrame"] [role="columnheader"] {{
    background: {PANEL_2} !important;
    text-transform: uppercase; letter-spacing: 0.05em;
    font-size: 0.68rem !important; font-weight: 600; color: {MUTED} !important;
}}
div[data-testid="stDataFrame"] [role="row"]:hover [role="gridcell"] {{
    background: rgba(255,255,255,.028);
}}

/* ---------- tabs ---------- */
button[data-baseweb="tab"] {{
    background: transparent; color: {MUTED};
    font-size: 0.85rem; font-weight: 500; padding: 6px 14px;
}}
button[data-baseweb="tab"][aria-selected="true"] {{ color: {ACCENT}; }}
div[data-baseweb="tab-highlight"] {{ background: {ACCENT}; }}
div[data-baseweb="tab-border"] {{ background: {BORDER}; }}

/* ---------- inputs ---------- */
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {{
    background: {PANEL_2}; border-color: {BORDER}; font-size: 0.85rem;
}}
.stButton > button {{
    background: {ACCENT}; color: #fff; border: none; border-radius: 3px;
    font-weight: 600; font-size: 0.85rem;
}}
.stButton > button:hover {{ background: #1F7BEC; color: #fff; }}
.stDownloadButton > button {{
    background: transparent; color: {ACCENT}; border: 1px solid {ACCENT};
    border-radius: 3px; font-weight: 500; font-size: 0.82rem;
}}

/* ---------- badges ---------- */
.badge {{
    display: inline-block; padding: 1px 7px 2px 7px; border-radius: 2px;
    font-family: {MONO}; font-size: 0.68rem; font-weight: 500; margin-right: 5px;
    background: transparent; border: 1px solid {BORDER}; color: {MUTED};
    letter-spacing: 0.02em;
}}
.badge.b-up {{ color: {UP}; border-color: rgba(38,166,154,.45); }}
.badge.b-down {{ color: {DOWN}; border-color: rgba(239,83,80,.45); }}
.badge.b-warn {{ color: {WARN}; border-color: rgba(240,162,46,.45); }}
.badge.b-neutral {{ color: {MUTED}; border-color: {BORDER}; }}
.badge.b-accent {{ color: {ACCENT}; border-color: rgba(45,140,255,.45); }}

/* ---------- landing backdrop ----------
   The line behind the hero is the actual cap-weighted market index for
   2021-2025, drawn from the same file the rest of the terminal reads. It is
   decoration, but it is not invented decoration. */
.lp-bg {{
    position: fixed; inset: 0; z-index: 0; pointer-events: none;
    overflow: hidden;
}}
/* The line is drawn at a strength where it actually reads. Legibility is then
   protected by darkening only the patch of canvas the hero text sits on,
   rather than veiling the whole viewport — which is what made the line vanish. */
.lp-bg svg {{ width: 100%; height: 100%; display: block; opacity: .65; }}
.lp-bg::after {{
    content: ""; position: absolute; inset: 0;
    background:
        radial-gradient(820px 430px at 21% 31%,
            rgba(11,14,20,.97) 0%, rgba(11,14,20,.88) 40%,
            rgba(11,14,20,.45) 66%, rgba(11,14,20,0) 82%),
        radial-gradient(560px 300px at 20% 62%,
            rgba(11,14,20,.80) 0%, rgba(11,14,20,.30) 55%,
            rgba(11,14,20,0) 80%),
        linear-gradient(180deg, rgba(11,14,20,.55) 0%,
            rgba(11,14,20,.08) 22%, rgba(11,14,20,0) 100%);
}}

/* ---------- landing page ---------- */
.lp-wrap {{ padding: 26px 0 8px 0; }}
.lp-num {{
    font-size: 4.6rem; font-weight: 800; color: {ACCENT};
    letter-spacing: -0.045em; line-height: 0.98; margin-bottom: 2px;
    text-shadow: 0 0 46px rgba(45,140,255,.28);
}}
.lp-head {{
    font-size: 3.05rem; font-weight: 800; color: {TEXT};
    letter-spacing: -0.045em; line-height: 1.0; margin-bottom: 16px;
}}
.lp-sub {{
    font-size: 1.16rem; font-weight: 600; color: {TEXT};
    margin-bottom: 8px; letter-spacing: -0.01em;
}}
.lp-lede {{ font-size: 0.94rem; color: {MUTED}; line-height: 1.62; max-width: 560px; }}

.lp-awards {{ display: flex; gap: 0; margin: 26px 0 4px 0; flex-wrap: wrap; }}
.lp-award {{ padding: 0 22px; border-left: 1px solid {BORDER}; }}
.lp-award:first-child {{ padding-left: 0; border-left: none; }}
.lp-award .n {{ font-family: {MONO}; font-size: 1.42rem; font-weight: 700;
                color: {TEXT}; line-height: 1.1; letter-spacing: -0.02em; }}
.lp-award .t {{ font-size: 0.7rem; color: {MUTED}; letter-spacing: 0.06em;
                text-transform: uppercase; margin-top: 3px; }}

.lp-card {{
    background: {PANEL}; border: 1px solid {BORDER};
    border-radius: 12px; padding: 18px 20px 12px 20px; margin-bottom: 16px;
}}
.lp-card-h {{
    display: flex; align-items: baseline; justify-content: space-between;
    margin-bottom: 6px;
}}
.lp-card-h .t {{ font-size: 1.0rem; font-weight: 600; color: {TEXT}; }}
.lp-card-h .m {{ font-size: 0.72rem; color: {MUTED}; font-family: {MONO}; }}

.lp-row {{
    display: flex; align-items: center; gap: 12px;
    padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,.045);
}}
.lp-row:last-child {{ border-bottom: none; }}
.lp-tick {{
    width: 30px; height: 30px; flex: 0 0 30px; border-radius: 50%;
    background: linear-gradient(135deg, {ACCENT} 0%, #1B4FA8 100%);
    color: #fff; font-family: {MONO}; font-size: 0.66rem; font-weight: 700;
    display: flex; align-items: center; justify-content: center;
}}
.lp-nm {{ flex: 1 1 auto; min-width: 0; }}
.lp-nm .s {{ font-family: {MONO}; font-size: 0.9rem; font-weight: 600; color: {TEXT}; }}
.lp-nm .c {{ font-size: 0.7rem; color: {MUTED}; white-space: nowrap;
             overflow: hidden; text-overflow: ellipsis; max-width: 210px; }}
.lp-px {{ font-family: {MONO}; font-size: 0.9rem; color: {TEXT}; text-align: right;
          flex: 0 0 90px; }}
.lp-ch {{ font-family: {MONO}; font-size: 0.86rem; text-align: right; flex: 0 0 76px; }}
.lp-ch.up {{ color: {UP}; }}
.lp-ch.dn {{ color: {DOWN}; }}

.lp-news {{ padding: 9px 0; border-bottom: 1px solid rgba(255,255,255,.045); }}
.lp-news:last-child {{ border-bottom: none; }}
.lp-news .h {{ font-size: 0.86rem; color: {TEXT}; line-height: 1.45; }}
.lp-news .m {{ font-family: {MONO}; font-size: 0.68rem; color: {MUTED}; margin-top: 3px; }}
.lp-tag {{
    display: inline-block; padding: 1px 6px; border-radius: 3px; margin-right: 6px;
    font-family: {MONO}; font-size: 0.62rem;
    background: rgba(45,140,255,.14); color: {ACCENT};
}}
.lp-tag.neg {{ background: rgba(239,83,80,.15); color: {DOWN}; }}

/* ---------- welcome screen ---------- */
.hero {{
    background:
      radial-gradient(900px 380px at 12% -10%, rgba(45,140,255,.18), transparent 62%),
      radial-gradient(700px 320px at 92% 8%, rgba(38,166,154,.12), transparent 58%),
      linear-gradient(160deg, {PANEL} 0%, {BG} 72%);
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 46px 46px 40px 46px;
    margin: 6px 0 20px 0;
}}
.hero .eyebrow {{
    font-family: {MONO}; font-size: 0.68rem; color: {ACCENT};
    letter-spacing: 0.22em; margin-bottom: 14px;
}}
.hero h1 {{
    font-size: 2.5rem; font-weight: 700; color: {TEXT};
    letter-spacing: -0.035em; line-height: 1.06; margin: 0 0 14px 0;
}}
.hero .lede {{
    font-size: 1.02rem; color: {MUTED}; line-height: 1.65;
    max-width: 780px; margin-bottom: 26px;
}}
.hero .rule {{
    height: 2px; width: 62px; margin-bottom: 22px;
    background: linear-gradient(90deg, {ACCENT}, transparent);
}}
.kpi-row {{ display: flex; gap: 12px; flex-wrap: wrap; margin-top: 4px; }}
.kpi {{
    flex: 1 1 150px; background: rgba(255,255,255,.026);
    border: 1px solid {BORDER}; border-radius: 7px; padding: 13px 15px;
}}
.kpi .n {{ font-family: {MONO}; font-size: 1.32rem; color: {TEXT}; font-weight: 600; }}
.kpi .l {{ font-size: 0.7rem; color: {MUTED}; text-transform: uppercase;
           letter-spacing: 0.07em; margin-top: 4px; }}

.feature {{
    background: {PANEL}; border: 1px solid {BORDER};
    border-radius: 8px; padding: 18px 20px; height: 100%;
    transition: border-color .15s ease, transform .15s ease;
}}
.feature:hover {{ border-color: rgba(45,140,255,.45); transform: translateY(-2px); }}
.feature .ico {{
    font-family: {MONO}; font-size: 0.72rem; color: {MUTED};
    letter-spacing: 0.1em; margin-bottom: 10px; display: block;
    padding-bottom: 8px; border-bottom: 1px solid {BORDER};
}}
.feature .h {{ font-size: 0.95rem; font-weight: 600; color: {TEXT}; margin-bottom: 6px; }}
.feature .b {{ font-size: 0.82rem; color: {MUTED}; line-height: 1.6; }}

.onboard {{
    background: linear-gradient(90deg, rgba(45,140,255,.10) 0%, rgba(20,26,35,.86) 55%);
    border: 1px solid rgba(45,140,255,.32);
    border-left: 3px solid {ACCENT};
    border-radius: 6px; padding: 15px 18px; margin-bottom: 16px;
}}
.onboard .h {{ font-size: 0.95rem; font-weight: 600; color: {TEXT}; margin-bottom: 5px; }}
.onboard .b {{ font-size: 0.85rem; color: {MUTED}; line-height: 1.6; }}

/* clearer separation between the big blocks of a page */
.sect {{ margin: 34px 0 10px 0; }}
/* the first section on a page sits right under the title bar */
.stat-row + div .sect, .topbar + div .sect {{ margin-top: 18px; }}
.sect .t {{
    font-size: 0.98rem; font-weight: 650; color: {TEXT};
    letter-spacing: -0.015em; display: flex; align-items: baseline; gap: 10px;
}}
.sect .t::before {{
    content: ""; width: 3px; height: 14px; background: {ACCENT};
    border-radius: 2px; display: inline-block;
}}
.sect .s {{ font-size: 0.79rem; color: {MUTED}; margin: 4px 0 0 13px; line-height: 1.55; }}
.sect-rule {{ height: 1px; background: {BORDER}; margin: 8px 0 12px 0; }}

.dlg-note {{
    background: rgba(45,140,255,.08); border: 1px solid rgba(45,140,255,.28);
    border-radius: 7px; padding: 13px 15px; margin: 4px 0 14px 0;
    font-size: 0.85rem; color: {TEXT}; line-height: 1.6;
}}

/* ---------- misc ---------- */
hr {{ border-color: {BORDER}; }}
.caption {{ color: {MUTED}; font-size: 0.78rem; line-height: 1.5; }}
.panel {{
    background: rgba(20,26,35,.80); border: 1px solid {BORDER};
    border-radius: 4px; padding: 14px 16px; margin-bottom: 12px;
}}
div[data-testid="stExpander"] {{ border: 1px solid {BORDER}; border-radius: 4px; background: {PANEL}; }}
#MainMenu, footer {{ visibility: hidden; }}
</style>
"""


TOGGLE_JS = """
<script>
(function () {
  var pdoc = window.parent.document;
  if (pdoc.getElementById('setx-sb-toggle')) { return; }

  var btn = pdoc.createElement('button');
  btn.id = 'setx-sb-toggle';
  btn.type = 'button';
  btn.setAttribute('aria-label', 'Show or hide the sidebar');
  btn.title = 'Show / hide sidebar';
  var css = {
    position: 'fixed', top: '12px', left: '12px', zIndex: '2147483647',
    width: '46px', height: '46px', lineHeight: '1',
    fontSize: '21px', fontWeight: '600', cursor: 'pointer',
    background: '__PANEL2__', color: '__TEXT__',
    border: '1px solid __BORDER__', borderRadius: '8px',
    boxShadow: '0 3px 14px rgba(0,0,0,.5)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    transition: 'background .12s ease, transform .12s ease'
  };
  for (var k in css) { btn.style[k] = css[k]; }
  btn.onmouseenter = function () {
    btn.style.background = '__ACCENT__'; btn.style.color = '#fff';
    btn.style.borderColor = '__ACCENT__'; btn.style.transform = 'scale(1.06)';
  };
  btn.onmouseleave = function () {
    btn.style.background = '__PANEL2__'; btn.style.color = '__TEXT__';
    btn.style.borderColor = '__BORDER__'; btn.style.transform = 'none';
  };
  pdoc.body.appendChild(btn);

  function sidebar() { return pdoc.querySelector('section[data-testid="stSidebar"]'); }

  function collapsed() {
    var s = sidebar();
    if (!s) { return true; }
    if (s.getAttribute('aria-expanded') === 'false') { return true; }
    return s.getBoundingClientRect().width < 40;
  }

  function press(sel) {
    var e = pdoc.querySelector(sel);
    if (!e) { return false; }
    var b = (e.tagName === 'BUTTON') ? e : e.querySelector('button');
    if (!b) { return false; }
    b.click();
    return true;
  }

  function open_() {
    if (press('[data-testid="stExpandSidebarButton"]')) { return; }
    if (press('[data-testid="stSidebarCollapsedControl"]')) { return; }
    if (press('[data-testid="collapsedControl"]')) { return; }
    var s = sidebar();               // last resort: force it back by hand
    if (s) {
      s.style.transform = 'none';
      s.style.visibility = 'visible';
      s.style.width = '268px';
      s.style.minWidth = '268px';
      s.style.marginLeft = '0px';
      s.setAttribute('aria-expanded', 'true');
    }
  }

  function close_() {
    if (press('[data-testid="stSidebarCollapseButton"]')) { return; }
    var s = sidebar();
    if (s) {
      s.style.transform = 'translateX(-100%)';
      s.style.minWidth = '0px';
      s.style.width = '0px';
      s.setAttribute('aria-expanded', 'false');
    }
  }

  btn.addEventListener('click', function (ev) {
    ev.preventDefault();
    if (collapsed()) { open_(); } else { close_(); }
    setTimeout(paint, 260);
  });

  function paint() { btn.innerHTML = collapsed() ? '&#9776;' : '&#10005;'; }
  paint();
  setInterval(paint, 700);
})();
</script>
"""


def sidebar_toggle():
    """Inject a floating sidebar toggle we control ourselves.

    Streamlit renames the test id of its own expand control between versions,
    and on this build it never became reachable, so the sidebar could be closed
    but not reopened. This button talks to whichever control exists and falls
    back to moving the sidebar directly.
    """
    js = (TOGGLE_JS.replace("__PANEL2__", PANEL_2).replace("__TEXT__", TEXT)
                   .replace("__BORDER__", BORDER).replace("__ACCENT__", ACCENT))
    # st.iframe is the current API; components.html is kept as a fallback so the
    # file still runs on older Streamlit releases.
    try:
        st.iframe(js, height=1)                       # current API
    except Exception:
        import streamlit.components.v1 as components  # older releases
        components.html(js, height=0)


def apply():
    """Call once at the top of app.py."""
    register_template()
    st.markdown(CSS, unsafe_allow_html=True)
    sidebar_toggle()


# ---------------------------------------------------------------- helpers
def topbar(title: str, subtitle: str = ""):
    st.markdown(
        f'<div class="topbar"><div class="t-title">{title}</div>'
        f'<div class="t-sub">{subtitle}</div></div>', unsafe_allow_html=True)


def fmt_num(v, dp=2, suffix=""):
    if v is None or (isinstance(v, float) and (v != v)):
        return "—"
    return f"{v:,.{dp}f}{suffix}"


def fmt_big(v):
    """Compact money formatting: 1.2B, 340M, 12.5K."""
    if v is None or (isinstance(v, float) and (v != v)):
        return "—"
    v = float(v)
    for div, sfx in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(v) >= div:
            return f"{v/div:,.2f}{sfx}"
    return f"{v:,.0f}"


def stat_cards(items):
    """items: list of (label, value_str, sub_str, tone) where tone in up/down/''."""
    html = ['<div class="stat-row">']
    for label, value, sub, tone in items:
        cls = f" {tone}" if tone else ""
        html.append(f'<div class="stat"><div class="k">{label}</div>'
                    f'<div class="v{cls}">{value}</div>'
                    f'<div class="s">{sub}</div></div>')
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def badge(text, kind="neutral"):
    return f'<span class="badge b-{kind}">{text}</span>'


def tone(v):
    if v is None or (isinstance(v, float) and (v != v)):
        return ""
    return "up" if v > 0 else ("down" if v < 0 else "")


def section(title, subtitle=""):
    """A consistent block heading, so every page separates its parts the same way."""
    sub = f'<div class="s">{subtitle}</div>' if subtitle else ""
    st.markdown(f'<div class="sect"><div class="t">{title}</div>{sub}</div>'
                f'<div class="sect-rule"></div>', unsafe_allow_html=True)


def caption(text):
    st.markdown(f'<div class="caption">{text}</div>', unsafe_allow_html=True)
