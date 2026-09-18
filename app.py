import os
from textwrap import dedent
from pathlib import Path
from html import escape

import streamlit as st
from dotenv import load_dotenv

from database.db import initialize_database, get_database_stats
from auth.authentication import (
    get_logged_in_mentor_id,
    is_mentor_logged_in,
    login_mentor,
    logout_mentor,
)
from database.queries import (
    get_all_mentees,
    get_all_mentors,
    get_available_mentors,
    get_mentee,
    delete_mentee,
    get_mentor,
    update_mentee_profile,
    update_mentor_profile,
    send_request,
    get_mentee_requests,
    get_enrolled_mentees,
    get_pending_requests_for_mentor,
    accept_request,
    reject_request,
    is_mentor_available,
)
from graph.workflow import run_matching_workflow
from matching.matcher import calculate_match

load_dotenv()

# -------------------------------------------------------------------
# App configuration
# -------------------------------------------------------------------

st.set_page_config(
    page_title="MentorMatch | AI Mentorship Platform",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------------------------------------------------
# Premium dark SaaS styling
# -------------------------------------------------------------------

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        .stApp {
            background:
                radial-gradient(circle at 10% 0%, rgba(99,102,241,.16), transparent 28%),
                radial-gradient(circle at 90% 10%, rgba(14,165,233,.12), transparent 25%),
                #080b12;
            color: #f5f7fb;
            font-family: 'Inter', sans-serif;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0c111c 0%, #080b12 100%);
            border-right: 1px solid rgba(255,255,255,.08);
        }

        [data-testid="stSidebar"] .block-container {
            padding: 1.5rem 1.25rem 2rem;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label {
            padding: .2rem 0;
        }

        .sidebar-panel {
            padding: .9rem;
            margin: .75rem 0 1rem;
            border: 1px solid rgba(255,255,255,.10);
            border-radius: 12px;
            background: rgba(17,24,39,.72);
        }

        .sidebar-panel-title {
            color: #f5f7fb;
            font-size: .9rem;
            font-weight: 700;
            margin-bottom: .7rem;
        }

        [data-testid="stSidebar"] * {
            font-family: 'Inter', sans-serif;
        }

        .block-container {
            max-width: 1400px;
            padding-top: 2rem;
            padding-bottom: 4rem;
        }

        .brand {
            font-size: 1.55rem;
            font-weight: 800;
            letter-spacing: -.04em;
            margin-bottom: 0;
        }

        .brand-sub {
            color: #8d99aa;
            font-size: .78rem;
            margin-top: -4px;
        }

        .hero {
            padding: 2.5rem;
            border-radius: 26px;
            border: 1px solid rgba(255,255,255,.10);
            background:
                linear-gradient(135deg, rgba(99,102,241,.22), rgba(15,23,42,.88) 55%, rgba(14,165,233,.10));
            box-shadow: 0 25px 70px rgba(0,0,0,.30);
            margin-bottom: 1.5rem;
        }

        .hero h1 {
            font-size: clamp(2.2rem, 5vw, 4.2rem);
            line-height: 1.02;
            letter-spacing: -.055em;
            margin: 0 0 .9rem 0;
        }

        .hero p {
            color: #aeb8c8;
            max-width: 760px;
            font-size: 1.05rem;
            line-height: 1.7;
            margin: 0;
        }

        .eyebrow {
            color: #a5b4fc;
            text-transform: uppercase;
            font-size: .73rem;
            font-weight: 700;
            letter-spacing: .13em;
            margin-bottom: .8rem;
        }

        .section-title {
            font-size: 1.45rem;
            font-weight: 750;
            letter-spacing: -.025em;
            margin: 1.8rem 0 .8rem;
        }

        .card {
            background: rgba(17,24,39,.72);
            border: 1px solid rgba(255,255,255,.08);
            border-radius: 18px;
            padding: 1.2rem;
            height: 100%;
            box-shadow: 0 14px 40px rgba(0,0,0,.16);
        }

        .metric-card {
            background: linear-gradient(145deg, rgba(20,28,43,.95), rgba(13,18,29,.95));
            border: 1px solid rgba(255,255,255,.08);
            border-radius: 18px;
            padding: 1.15rem 1.2rem;
        }

        .metric-label {
            color: #8e9bad;
            font-size: .78rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: .08em;
        }

        .metric-value {
            font-size: 2rem;
            font-weight: 800;
            letter-spacing: -.04em;
            margin-top: .25rem;
        }

        .skill {
            display: inline-block;
            padding: .34rem .65rem;
            margin: .2rem .18rem .2rem 0;
            border-radius: 999px;
            background: rgba(99,102,241,.13);
            border: 1px solid rgba(129,140,248,.25);
            color: #c7d2fe;
            font-size: .75rem;
            font-weight: 600;
        }

        .status {
            display: inline-block;
            padding: .34rem .62rem;
            border-radius: 999px;
            font-size: .72rem;
            font-weight: 750;
            letter-spacing: .04em;
        }

        .available {
            background: rgba(34,197,94,.12);
            color: #86efac;
            border: 1px solid rgba(34,197,94,.22);
        }

        .full {
            background: rgba(239,68,68,.12);
            color: #fca5a5;
            border: 1px solid rgba(239,68,68,.22);
        }

        .pending {
            background: rgba(234,179,8,.12);
            color: #fde68a;
            border: 1px solid rgba(234,179,8,.22);
        }

        .accepted {
            background: rgba(34,197,94,.12);
            color: #86efac;
            border: 1px solid rgba(34,197,94,.22);
        }

        .rejected {
            background: rgba(239,68,68,.12);
            color: #fca5a5;
            border: 1px solid rgba(239,68,68,.22);
        }

        .request-sent-banner {
            display: flex;
            align-items: center;
            gap: .75rem;
            padding: 1rem 1.1rem;
            margin: 0 0 1.25rem;
            border: 1px solid rgba(34,197,94,.35);
            border-radius: 14px;
            background: linear-gradient(90deg, rgba(34,197,94,.18), rgba(14,165,233,.10));
            color: #dcfce7;
            animation: request-sent-in .45s ease-out both;
        }

        .request-sent-icon {
            display: inline-grid;
            place-items: center;
            width: 2rem;
            height: 2rem;
            border-radius: 50%;
            background: #22c55e;
            color: #052e16;
            font-weight: 800;
            animation: request-sent-pop .55s cubic-bezier(.2,.8,.2,1.3) both;
        }

        @keyframes request-sent-in {
            from { opacity: 0; transform: translateY(-8px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes request-sent-pop {
            0% { transform: scale(.5); }
            70% { transform: scale(1.12); }
            100% { transform: scale(1); }
        }

        .score {
            font-size: 2.5rem;
            font-weight: 850;
            letter-spacing: -.06em;
        }

        .score-caption {
            color: #8e9bad;
            font-size: .75rem;
        }

        .mini-label {
            color: #7f8a9b;
            font-size: .72rem;
            text-transform: uppercase;
            font-weight: 700;
            letter-spacing: .08em;
        }

        .explanation {
            color: #b8c2d1;
            line-height: 1.65;
            font-size: .9rem;
        }

        .notice {
            padding: .85rem 1rem;
            border-radius: 12px;
            background: rgba(99,102,241,.08);
            border: 1px solid rgba(129,140,248,.18);
            color: #c7d2fe;
            font-size: .82rem;
            line-height: 1.5;
        }

        .footer-note {
            color: #6f7b8e;
            font-size: .73rem;
            line-height: 1.5;
            margin-top: 1.5rem;
        }

        div[data-testid="stButton"] > button {
            border-radius: 11px;
            font-weight: 650;
            border: 1px solid rgba(255,255,255,.10);
            min-height: 42px;
        }

        div[data-testid="stForm"] {
            background: rgba(17,24,39,.45);
            border: 1px solid rgba(255,255,255,.07);
            border-radius: 18px;
            padding: 1rem;
        }

        .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
            border-radius: 10px;
        }

        /* Reference dashboard visual system */
        :root {
            --navy-950: #070b18;
            --navy-900: #0b1224;
            --navy-800: #111a31;
            --line-blue: rgba(122, 151, 255, .18);
            --accent-blue: #6d8cff;
            --accent-violet: #8f5cff;
            --text-main: #f4f6ff;
            --text-muted: #8d9ab7;
        }

        .stApp {
            background:
                radial-gradient(circle at 82% 0%, rgba(35, 111, 255, .16), transparent 30%),
                radial-gradient(circle at 30% 18%, rgba(111, 65, 255, .10), transparent 24%),
                var(--navy-950);
            color: var(--text-main);
        }

        [data-testid="stSidebar"] {
            background: #080e1d;
            border-right: 1px solid rgba(145, 164, 220, .14);
        }

        [data-testid="stSidebar"] .block-container {
            padding: 1.1rem .85rem 1.5rem;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] > div {
            gap: .18rem;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label {
            min-height: 36px;
            padding: .5rem .65rem;
            border-radius: 7px;
            color: #aab5d2;
            font-size: .78rem;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
            background: rgba(103, 129, 255, .10);
            color: #ffffff;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
            background: linear-gradient(90deg, rgba(85, 112, 255, .28), rgba(85, 112, 255, .08));
            color: #ffffff;
            box-shadow: inset 3px 0 0 var(--accent-blue);
        }

        .brand {
            font-size: 1.15rem;
            letter-spacing: -.035em;
        }

        .brand-sub {
            color: #7f8bad;
            font-size: .68rem;
        }

        .sidebar-callout {
            margin-top: 1rem;
            padding: .85rem .75rem;
            border: 1px solid rgba(112, 143, 255, .22);
            border-radius: 9px;
            background: linear-gradient(145deg, rgba(61, 92, 207, .28), rgba(23, 35, 83, .46));
            color: #dbe3ff;
            font-size: .7rem;
            line-height: 1.4;
        }

        .topbar {
            display: flex;
            align-items: center;
            justify-content: flex-end;
            min-height: 34px;
            margin: -.5rem 0 .65rem;
            color: #9ba8c8;
            font-size: .68rem;
        }

        .topbar-links {
            margin-right: auto;
            color: #c4ceee;
            letter-spacing: .03em;
        }

        .topbar-user {
            display: inline-flex;
            align-items: center;
            gap: .5rem;
            padding: .25rem .55rem;
            border: 1px solid rgba(124, 147, 238, .18);
            border-radius: 999px;
            background: rgba(18, 31, 63, .72);
        }

        .topbar-avatar {
            display: inline-grid;
            place-items: center;
            width: 1.45rem;
            height: 1.45rem;
            border-radius: 50%;
            background: linear-gradient(135deg, #6d8cff, #9e60f4);
            color: white;
            font-size: .65rem;
            font-weight: 800;
        }

        .hero-grid {
            display: grid;
            grid-template-columns: minmax(0, 1.3fr) minmax(210px, .7fr);
            gap: 1rem;
            align-items: center;
        }

        .hero-art {
            min-height: 180px;
            border-left: 1px solid rgba(177, 196, 255, .22);
            background:
                linear-gradient(145deg, transparent 22%, rgba(130, 174, 255, .35) 23%, transparent 24%),
                linear-gradient(30deg, transparent 35%, rgba(124, 84, 255, .58) 36%, transparent 37%),
                radial-gradient(circle at 55% 20%, rgba(151, 222, 255, .9), transparent 2%, transparent 18%),
                linear-gradient(160deg, transparent 48%, rgba(43, 89, 229, .72) 49%, rgba(21, 47, 133, .36) 68%, transparent 69%);
            opacity: .9;
        }

        .profile-summary {
            display: grid;
            grid-template-columns: auto repeat(3, minmax(0, 1fr));
            gap: .8rem;
            align-items: center;
        }

        .profile-avatar {
            display: grid;
            place-items: center;
            width: 2.6rem;
            height: 2.6rem;
            border-radius: 50%;
            background: linear-gradient(135deg, #718cff, #a057ea);
            color: white;
            font-size: 1rem;
            font-weight: 800;
        }

        .profile-meta {
            color: #d8e0ff;
            font-size: .68rem;
            line-height: 1.4;
        }

        .profile-meta span {
            display: block;
            color: #8190b0;
            font-size: .58rem;
            text-transform: uppercase;
            letter-spacing: .08em;
        }

        .mentor-card-head {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto auto;
            gap: 1rem;
            align-items: center;
        }

        .score-ring {
            display: grid;
            place-items: center;
            width: 74px;
            height: 74px;
            border-radius: 50%;
            border: 7px solid #6d8cff;
            outline: 1px solid rgba(166, 183, 255, .28);
            color: #f7f8ff;
            font-size: 1.05rem;
            font-weight: 800;
            background: #111d39;
        }

        .mentor-side-status {
            min-width: 104px;
            color: #aab7d4;
            font-size: .68rem;
            line-height: 1.8;
        }

        .mentor-side-status strong {
            color: #6df2a5;
            font-size: .72rem;
        }

        @media (max-width: 800px) {
            .hero-grid, .profile-summary { grid-template-columns: 1fr 1fr; }
            .hero-art { display: none; }
        }

        .block-container {
            max-width: 1180px;
            padding-top: 1.25rem;
            padding-bottom: 3rem;
        }

        h1, h2, h3, h4 {
            letter-spacing: -.035em;
        }

        h1 {
            font-size: clamp(2rem, 4vw, 3rem);
            line-height: 1.08;
        }

        .hero {
            min-height: 245px;
            padding: 2rem 2.2rem;
            border-radius: 14px;
            border: 1px solid rgba(117, 150, 255, .26);
            background:
                linear-gradient(110deg, rgba(35, 57, 160, .88), rgba(19, 35, 97, .70) 52%, rgba(10, 28, 71, .88)),
                radial-gradient(circle at 82% 20%, rgba(54, 165, 255, .65), transparent 30%);
            box-shadow: 0 18px 45px rgba(0, 0, 0, .24);
        }

        .hero h1 {
            max-width: 560px;
            font-size: clamp(2.1rem, 4.2vw, 3.6rem);
            letter-spacing: -.055em;
        }

        .hero p {
            max-width: 510px;
            color: #d0d8ff;
            font-size: .88rem;
            line-height: 1.55;
        }

        .eyebrow {
            color: #829eff;
            font-size: .62rem;
            letter-spacing: .14em;
        }

        .section-title {
            margin: 1.35rem 0 .65rem;
            font-size: 1.1rem;
        }

        .card, .metric-card {
            background: linear-gradient(145deg, rgba(18, 29, 55, .96), rgba(12, 20, 39, .96));
            border: 1px solid var(--line-blue);
            border-radius: 12px;
            box-shadow: 0 12px 28px rgba(0, 0, 0, .16);
        }

        .card {
            padding: 1rem;
        }

        .metric-card {
            min-height: 84px;
            padding: .85rem 1rem;
        }

        .metric-label, .mini-label {
            color: #8492b2;
            font-size: .62rem;
        }

        .metric-value {
            color: #f6f8ff;
            font-size: 1.65rem;
        }

        .skill {
            padding: .28rem .54rem;
            margin: .14rem .12rem .14rem 0;
            border-radius: 7px;
            background: rgba(92, 112, 231, .16);
            border: 1px solid rgba(120, 145, 255, .27);
            color: #c7d2ff;
            font-size: .68rem;
        }

        .score {
            color: #f7f8ff;
            font-size: 2.35rem;
        }

        .score-caption {
            color: #8492b2;
            font-size: .64rem;
        }

        div[data-testid="stButton"] > button,
        div[data-testid="stFormSubmitButton"] > button {
            min-height: 36px;
            border-radius: 8px;
            border: 1px solid rgba(126, 143, 255, .3);
            background: linear-gradient(90deg, #7654ef, #a052ed);
            color: white;
            font-size: .78rem;
        }

        div[data-testid="stButton"] > button:hover,
        div[data-testid="stFormSubmitButton"] > button:hover {
            border-color: #b4c1ff;
            box-shadow: 0 0 0 3px rgba(112, 132, 255, .12);
        }

        div[data-testid="stForm"] {
            background: rgba(15, 25, 49, .62);
            border: 1px solid var(--line-blue);
            border-radius: 12px;
            padding: 1rem;
        }

        .stTextInput input, .stTextArea textarea,
        .stSelectbox div[data-baseweb="select"],
        .stNumberInput input {
            background: #15213b;
            border: 1px solid rgba(137, 159, 231, .18);
            color: #f4f6ff;
            border-radius: 7px;
        }

        [data-testid="stMetric"] {
            background: #111c35;
            border: 1px solid var(--line-blue);
            border-radius: 10px;
            padding: .65rem;
        }

        [data-testid="stDataFrame"] {
            border: 1px solid var(--line-blue);
            border-radius: 10px;
            overflow: hidden;
        }

        @media (max-width: 700px) {
            .block-container { padding: 1rem .75rem 2rem; }
            .hero { min-height: 220px; padding: 1.35rem; }
            .hero h1 { font-size: 2.1rem; }
        }

        /* High-fidelity reference layout overrides */
        .stApp, .stApp p, .stApp label, .stApp input, .stApp textarea,
        .stApp button, .stApp [data-baseweb="select"] {
            font-family: 'Inter', sans-serif;
        }

        [data-testid="stSidebar"] {
            width: 218px !important;
            min-width: 218px !important;
        }

        [data-testid="stSidebar"] .block-container {
            padding: .75rem .7rem 1rem;
        }

        [data-testid="stSidebar"] hr {
            margin: .65rem 0;
            border-color: rgba(121, 143, 208, .18);
        }

        .block-container {
            max-width: 1010px;
            padding: .65rem 1rem 2rem;
        }

        .brand {
            font-size: 1.05rem;
            line-height: 1.1;
        }

        .hero {
            min-height: 188px;
            margin-bottom: .7rem;
            padding: 1.25rem 1.45rem;
            border-radius: 9px;
            background:
                linear-gradient(100deg, rgba(42, 57, 178, .95), rgba(25, 64, 162, .72) 55%, rgba(20, 42, 104, .60)),
                radial-gradient(circle at 75% 18%, rgba(100, 213, 255, .75), transparent 14%),
                linear-gradient(145deg, #2732a6, #071a4a);
        }

        .hero-grid {
            grid-template-columns: minmax(0, 1fr) 38%;
            gap: .5rem;
        }

        .hero h1 {
            max-width: 520px;
            margin-bottom: .55rem;
            font-size: clamp(1.85rem, 4vw, 2.65rem);
            line-height: 1.04;
        }

        .hero p {
            max-width: 430px;
            font-size: .72rem;
            line-height: 1.42;
        }

        .hero .eyebrow {
            margin-bottom: .4rem;
            font-size: .55rem;
        }

        .hero-art {
            min-height: 150px;
        }

        .hero-tags {
            margin-top: .45rem;
        }

        .hero-tags .skill {
            background: transparent;
            border-color: transparent;
            color: #c9d9ff;
            padding: .1rem .25rem;
            font-size: .52rem;
        }

        .metric-card {
            min-height: 61px;
            padding: .55rem .7rem;
            border-radius: 7px;
        }

        .metric-label {
            font-size: .54rem;
        }

        .metric-value {
            margin-top: .08rem;
            font-size: 1.18rem;
        }

        .section-title {
            margin: .8rem 0 .4rem;
            font-size: .94rem;
        }

        .card {
            padding: .78rem;
            border-radius: 9px;
        }

        .skill {
            padding: .22rem .42rem;
            margin: .1rem .08rem .1rem 0;
            border-radius: 5px;
            font-size: .58rem;
        }

        .eyebrow, .mini-label {
            font-size: .54rem;
        }

        .topbar {
            min-height: 23px;
            margin: -.3rem 0 .2rem;
            font-size: .56rem;
        }

        .topbar-avatar {
            width: 1.15rem;
            height: 1.15rem;
            font-size: .52rem;
        }

        div[data-testid="stButton"] > button,
        div[data-testid="stFormSubmitButton"] > button {
            min-height: 30px;
            border-radius: 6px;
            font-size: .65rem;
        }

        div[data-testid="stForm"] {
            padding: .7rem;
            border-radius: 9px;
        }

        .mentor-card-head {
            gap: .55rem;
        }

        .score-ring {
            width: 63px;
            height: 63px;
            border-width: 6px;
            font-size: .83rem;
        }

        .mentor-side-status {
            min-width: 74px;
            font-size: .54rem;
            line-height: 1.45;
        }

        .mentor-side-status strong {
            font-size: .56rem;
        }

        .sidebar-callout {
            margin: .6rem .15rem;
            padding: .65rem .55rem;
        }

        .sidebar-db {
            margin-top: .6rem;
            color: #8492b2;
            font-size: .58rem;
            letter-spacing: .08em;
            text-transform: uppercase;
        }

        .sidebar-db-item {
            padding: .28rem .1rem;
            color: #9eabd0;
            font-size: .66rem;
        }

        .sidebar-db-item b {
            display: inline-block;
            width: 1.2rem;
            color: #6d8cff;
            font-size: .72rem;
        }

        .tips-panel {
            padding: .75rem;
            border: 1px solid rgba(104, 137, 255, .2);
            border-radius: 8px;
            background: rgba(24, 42, 91, .46);
            color: #b8c6ec;
            font-size: .64rem;
            line-height: 1.55;
        }

        .tips-panel strong {
            display: block;
            margin-bottom: .3rem;
            color: #f1f4ff;
            font-size: .7rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------------------------
# Initialization
# -------------------------------------------------------------------

@st.cache_resource
def initialize_app():
    """Create the database and seed CSV data once per Streamlit process."""
    return initialize_database()


try:
    initialize_app()
except Exception as exc:
    st.error("The application could not initialize its database.")
    st.exception(exc)
    st.stop()


def refresh_app():
    """Clear cached matching results after database mutations."""
    for key in ("matching_results", "last_match_mentee"):
        st.session_state.pop(key, None)
    st.rerun()


# -------------------------------------------------------------------
# Small UI helpers
# -------------------------------------------------------------------

def metric_card(label: str, value) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{escape(str(label))}</div>
            <div class="metric-value">{escape(str(value))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def skills_html(value) -> str:
    if value is None:
        return '<span class="skill">Not specified</span>'

    if isinstance(value, (list, tuple, set)):
        items = [str(x).strip() for x in value if str(x).strip()]
    else:
        items = [
            x.strip()
            for x in str(value).replace("|", ",").replace(";", ",").split(",")
            if x.strip()
        ]

    if not items:
        return '<span class="skill">Not specified</span>'

    return "".join(f'<span class="skill">{escape(item)}</span>' for item in items)


def status_html(available: bool) -> str:
    if available:
        return '<span class="status available">● AVAILABLE</span>'
    return '<span class="status full">● FULL</span>'


def request_status_html(status: str) -> str:
    status = str(status).upper()
    classes = {
        "PENDING": "pending",
        "ACCEPTED": "accepted",
        "REJECTED": "rejected",
    }
    icons = {
        "PENDING": "🟡",
        "ACCEPTED": "🟢",
        "REJECTED": "🔴",
    }
    cls = classes.get(status, "pending")
    icon = icons.get(status, "•")
    return f'<span class="status {cls}">{icon} {escape(status)}</span>'


def safe_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(x).strip() for x in value if str(x).strip()]
    return [
        x.strip()
        for x in str(value).replace("|", ",").replace(";", ",").split(",")
        if x.strip()
    ]


def display_name(record, fallback="Unknown"):
    if not record:
        return fallback
    return str(record.get("name") or fallback)


def user_label(record):
    return f"{display_name(record)} — {record.get('email', '')}"


def open_mentee_profile():
    st.session_state["workspace_page"] = "Mentee Profile"


# -------------------------------------------------------------------
# Sidebar
# -------------------------------------------------------------------

stats = get_database_stats()

with st.sidebar:
    st.markdown(
        """
        <div class="brand">🎓 MentorMatch</div>
        <div class="brand-sub">AI-powered mentorship platform</div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    page = st.radio(
        "WORKSPACE",
        [
            "Home",
            "Mentee Profile",
            "Find Mentor",
            "My Requests",
            "Enrolled Mentees",
        ] + (["Mentor Profile", "Mentor Dashboard"] if is_mentor_logged_in() else []),
        label_visibility="visible",
        key="workspace_page",
    )

    st.divider()
    if is_mentor_logged_in():
        st.markdown(
            f'''<div class="sidebar-panel"><div class="sidebar-panel-title">Mentor access</div><div class="brand-sub">{escape(str(st.session_state.get("mentor_email", "")))}</div></div>''',
            unsafe_allow_html=True,
        )
        if st.button("Sign out", use_container_width=True):
            logout_mentor()
            st.rerun()
    else:
        st.markdown('<div class="sidebar-panel-title">Mentor sign in</div>', unsafe_allow_html=True)
        with st.form("mentor_login_form"):
            mentor_email = st.text_input("Mentor email", key="sidebar_mentor_email")
            mentor_password = st.text_input("Password", type="password", key="sidebar_mentor_password")
            login_submitted = st.form_submit_button("Sign in", use_container_width=True)

        if login_submitted:
            if login_mentor(mentor_email, mentor_password):
                st.success("Mentor sign in successful.")
                st.rerun()
            else:
                st.error("Invalid mentor email or password.")

    st.markdown(
        """
        <div class="sidebar-db">Database</div>
        <div class="sidebar-db-item"><b>▦</b> Mentors</div>
        <div class="sidebar-db-item"><b>◉</b> Mentees</div>
        <div class="sidebar-db-item"><b>▥</b> Analytics</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="sidebar-callout"><strong>Growth happens</strong><br>faster together.</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="footer-note">
        Application-generated match scores are indicators, not objective
        measures of compatibility.<br><br>
        Capacity and availability are determined by SQLite, not the AI model.
        </div>
        """,
        unsafe_allow_html=True,
    )


role_label = "Mentor" if is_mentor_logged_in() else "Mentee"
avatar_letter = role_label[0]
st.markdown(
    f'''
    <div class="topbar">
        <div class="topbar-links">Learn&nbsp;&nbsp;•&nbsp;&nbsp;Grow&nbsp;&nbsp;•&nbsp;&nbsp;Connect</div>
        <div class="topbar-user"><span class="topbar-avatar">{avatar_letter}</span><span>{role_label}<br><small>Workspace</small></span></div>
    </div>
    ''',
    unsafe_allow_html=True,
)


# -------------------------------------------------------------------
# Home
# -------------------------------------------------------------------

def render_home():
    st.markdown(
        """
        <div class="hero">
            <div class="hero-grid">
                <div>
                    <div class="eyebrow">AI mentorship intelligence</div>
                    <h1>Find the right mentor.<br>Build the next version of you.</h1>
                    <p>Connect with relevant mentors using explainable skill matching, lightweight retrieval and AI-generated recommendations.</p>
                    <div class="hero-tags"><span class="skill">SKILLS</span><span class="skill">PEOPLE</span><span class="skill">OPPORTUNITIES</span></div>
                </div>
                <div class="hero-art" aria-hidden="true"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    action_col, guide_col, _ = st.columns([1.05, 1.05, 2.4])
    with action_col:
        st.button(
            "Get Started →",
            key="home_get_started",
            type="primary",
            use_container_width=True,
            on_click=open_mentee_profile,
        )
    with guide_col:
        if st.button("How it works", key="home_how_it_works", use_container_width=True):
            st.session_state["home_show_guide"] = True
            st.rerun()

    stats = get_database_stats()

    cols = st.columns(4)
    values = [
        ("Mentors", stats.get("mentors", 0)),
        ("Mentees", stats.get("mentees", 0)),
        ("Available Mentors", stats.get("available_mentors", 0)),
        ("Requests", stats.get("requests", 0)),
    ]

    for col, (label, value) in zip(cols, values):
        with col:
            metric_card(label, value)

    if st.session_state.pop("home_show_guide", False):
        st.info("Create a mentee profile, generate skill-based matches, then send one request to an available mentor.")

    st.markdown('<div class="section-title">How it works</div>', unsafe_allow_html=True)

    cols = st.columns(3)
    steps = [
        ("01", "Understand", "Capture current skills, skill level, learning goals and required skills."),
        ("02", "Match", "Retrieve relevant mentors and calculate an explainable match indicator."),
        ("03", "Connect", "Send a mentorship request and let the mentor respond based on capacity."),
    ]

    for col, (number, title, text) in zip(cols, steps):
        with col:
            st.markdown(
                f"""
                <div class="card">
                    <div class="eyebrow">{escape(number)}</div>
                    <h3>{escape(title)}</h3>
                    <p style="color:#9ba7b8;line-height:1.65">{escape(text)}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown('<div class="section-title">Matching model</div>', unsafe_allow_html=True)

    cols = st.columns(3)
    model = [
        ("60%", "Required Skills", "Direct overlap with skills the mentee needs."),
        ("30%", "Learning Goals", "Overlap between mentor expertise/skills and learning goals."),
        ("10%", "Current Skill Context", "Contextual overlap with the mentee's existing skills."),
    ]

    for col, (percentage, title, text) in zip(cols, model):
        with col:
            st.markdown(
                f"""
                <div class="card">
                    <div class="score">{percentage}</div>
                    <h4>{escape(title)}</h4>
                    <p style="color:#8f9bad;line-height:1.55">{escape(text)}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        """
        <div class="notice" style="margin-top:1.5rem">
        <strong>Business-rule guardrail:</strong>
        SQLite is the source of truth for mentor availability, capacity,
        requests and profile information. The LLM only explains application-generated results.
        </div>
        """,
        unsafe_allow_html=True,
    )


# -------------------------------------------------------------------
# Mentee Profile
# -------------------------------------------------------------------

def render_mentee_profile():
    st.markdown('<div class="eyebrow">MENTEE WORKSPACE</div>', unsafe_allow_html=True)
    st.title("Mentee Profile")
    st.caption("Create or update the learning profile used by the matching workflow.")

    mentees = get_all_mentees()

    if mentees:
        options = {user_label(m): m["id"] for m in mentees}
        create_label = "Create new mentee"
        selected_label = st.selectbox(
            "Select mentee",
            [create_label, *options.keys()],
            key="mentee_profile_select",
        )

        if selected_label == create_label:
            mentee_id = None
            mentee = {
                "name": "",
                "email": "",
                "skills": "",
                "skill_level": "Beginner",
                "learning_goals": "",
                "required_skills": "",
            }
        else:
            mentee_id = options[selected_label]
            mentee = get_mentee(mentee_id)

        if mentee is None:
            st.error("The selected mentee could not be loaded.")
            return
    else:
        st.info("Create the first mentee profile using the form below.")
        mentee_id = None
        mentee = {
            "name": "",
            "email": "",
            "skills": "",
            "skill_level": "Beginner",
            "learning_goals": "",
            "required_skills": "",
        }

    current_skills = safe_list(mentee.get("skills"))
    goals = safe_list(mentee.get("learning_goals"))
    required = safe_list(mentee.get("required_skills"))
    form_suffix = mentee_id if mentee_id is not None else "new"

    st.markdown(
        """
        <div class="tips-panel">
            <strong>Profile Tips</strong>
            • Be specific about your learning goals<br>
            • Add relevant skills and keywords<br>
            • A complete profile gives better match results<br><br>
            <em>“Invest in yourself. Your future self will thank you.”</em>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form(f"mentee_profile_form_{form_suffix}"):
        c1, c2 = st.columns(2)

        with c1:
            name = st.text_input(
                "Name",
                value=str(mentee.get("name", "")),
                key=f"mentee_name_{form_suffix}",
            )
            email = st.text_input(
                "Email",
                value=str(mentee.get("email", "")),
                key=f"mentee_email_{form_suffix}",
            )
            skill_level = st.selectbox(
                "Skill Level",
                ["Beginner", "Intermediate", "Advanced"],
                index=max(
                    0,
                    ["Beginner", "Intermediate", "Advanced"].index(
                        mentee.get("skill_level", "Beginner")
                    )
                    if mentee.get("skill_level", "Beginner") in
                    ["Beginner", "Intermediate", "Advanced"]
                    else 0,
                ),
                key=f"mentee_skill_level_{form_suffix}",
            )

        with c2:
            skills = st.text_input(
                "Current Skills",
                value=", ".join(current_skills),
                help="Separate skills with commas.",
                key=f"mentee_skills_{form_suffix}",
            )
            learning_goals = st.text_input(
                "Learning Goals",
                value=", ".join(goals),
                help="Separate goals with commas.",
                key=f"mentee_goals_{form_suffix}",
            )
            required_skills = st.text_input(
                "Required Skills",
                value=", ".join(required),
                help="Separate required skills with commas.",
                key=f"mentee_required_skills_{form_suffix}",
            )

        submitted = st.form_submit_button("Save Mentee Profile", type="primary", use_container_width=True)

    if submitted:
        if not name.strip():
            st.error("Name cannot be empty.")
            return
        if not email.strip() or "@" not in email:
            st.error("Please enter a valid email address.")
            return
        if not required_skills.strip():
            st.error("Required skills should not be empty.")
            return

        try:
            update_mentee_profile(
                mentee_id,
                name=name.strip(),
                email=email.strip(),
                skills=skills.strip(),
                skill_level=skill_level,
                learning_goals=learning_goals.strip(),
                required_skills=required_skills.strip(),
            )
            st.success("Mentee profile saved successfully.")
        except Exception as exc:
            st.error("Could not save the mentee profile.")
            st.exception(exc)

    if mentee_id is not None:
        st.markdown('<div class="section-title">Remove profile</div>', unsafe_allow_html=True)
        confirm_delete = st.checkbox(
            "I understand that this permanently deletes the mentee profile and requests.",
            key=f"confirm_delete_mentee_{mentee_id}",
        )
        if st.button(
            "Delete Mentee Profile",
            type="secondary",
            disabled=not confirm_delete,
            key=f"delete_mentee_{mentee_id}",
            use_container_width=True,
        ):
            result = delete_mentee(mentee_id)
            if result.get("success"):
                st.success(result["message"])
                st.rerun()
            else:
                st.error(result["message"])

    st.markdown('<div class="section-title">Current profile</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown('<div class="card"><div class="mini-label">Current Skills</div><div style="margin-top:.5rem">'
                    + skills_html(current_skills) + "</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="card"><div class="mini-label">Learning Goals</div><div style="margin-top:.5rem">'
                    + skills_html(goals) + "</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="card"><div class="mini-label">Required Skills</div><div style="margin-top:.5rem">'
                    + skills_html(required) + "</div></div>", unsafe_allow_html=True)


# -------------------------------------------------------------------
# Find Mentor
# -------------------------------------------------------------------

def render_find_mentor():
    st.markdown('<div class="eyebrow">MATCHING ENGINE</div>', unsafe_allow_html=True)
    st.title("Find Mentor")
    st.caption("Deterministic retrieval + explainable matching + optional AI explanation.")

    mentees = get_all_mentees()

    if not mentees:
        st.warning("No mentees found. Import mentee data into SQLite first.")
        return

    options = {user_label(m): m["id"] for m in mentees}
    selected_label = st.selectbox("Select mentee", list(options.keys()), key="find_mentee_select")
    mentee_id = options[selected_label]
    mentee = get_mentee(mentee_id)

    if not mentee:
        st.error("Unable to load the selected mentee.")
        return

    request_sent = st.session_state.pop("request_sent", None)
    if request_sent:
        st.balloons()
        st.markdown(
            f'''<div class="request-sent-banner"><span class="request-sent-icon">✓</span><div><strong>Request sent</strong><br><span style="color:#bbf7d0">{escape(request_sent)}</span></div></div>''',
            unsafe_allow_html=True,
        )

    active_requests = [
        request
        for request in get_mentee_requests(mentee_id)
        if str(request.get("status", "")).upper() in {"PENDING", "ACCEPTED"}
    ]
    if active_requests:
        active_mentor = active_requests[0].get("mentor_name", "another mentor")
        st.warning(
            f"You can't apply to more than one mentor. Your request with {active_mentor} is already active."
        )

    current = safe_list(mentee.get("skills"))
    goals = safe_list(mentee.get("learning_goals"))
    required = safe_list(mentee.get("required_skills"))

    initials = "".join(part[0] for part in display_name(mentee).split()[:2]).upper()
    st.markdown(
        f'''
        <div class="card profile-summary" style="margin-bottom:1rem">
            <div class="profile-avatar">{escape(initials or "M")}</div>
            <div class="profile-meta"><span>Mentee</span>{escape(display_name(mentee))}</div>
            <div class="profile-meta"><span>Current skills</span>{escape(", ".join(current) or "Not specified")}</div>
            <div class="profile-meta"><span>Learning goals</span>{escape(", ".join(goals) or "Not specified")}</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="card">
            <div class="mini-label">Current Skills</div>
            <div>{skills_html(current)}</div>
            <div class="mini-label" style="margin-top:1rem">Learning Goals</div>
            <div>{skills_html(goals)}</div>
            <div class="mini-label" style="margin-top:1rem">Required Skills</div>
            <div>{skills_html(required)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("✨ Find Matching Mentors", type="primary", use_container_width=True):
        if not required:
            st.warning("Add required skills to the mentee profile before matching.")
            return

        with st.spinner("Retrieving mentors, calculating match indicators and preparing explanations..."):
            try:
                result = run_matching_workflow(
                    mentee_requirements=mentee,
                    limit=12,
                )
                st.session_state["matching_results"] = result
                st.session_state["last_match_mentee"] = mentee_id
            except Exception as exc:
                st.error("The matching workflow failed.")
                st.exception(exc)
                return

    results = st.session_state.get("matching_results")
    last_mentee = st.session_state.get("last_match_mentee")

    if not results or last_mentee != mentee_id:
        st.info("Click “Find Matching Mentors” to generate recommendations.")
        return

    recommendations = results.get("recommendations", results.get("matched_mentors", []))
    skill_matched_recommendations = []
    for recommendation in recommendations:
        mentor = recommendation.get("mentor", recommendation)
        skill_match = calculate_match(mentee, mentor)
        enriched_recommendation = dict(recommendation)
        enriched_recommendation.update(skill_match)
        if skill_match["match_percentage"] > 30:
            skill_matched_recommendations.append(enriched_recommendation)
    ranked_recommendations = sorted(
        skill_matched_recommendations,
        key=lambda recommendation: (
            recommendation["match_percentage"],
            recommendation["matched_required_skills"],
            recommendation.get("retrieval_score", 0) or 0,
        ),
        reverse=True,
    )
    recommendations = []
    selected_mentor_ids = set()
    for minimum_percentage in (70, 50, 30):
        tier = [
            recommendation
            for recommendation in ranked_recommendations
            if recommendation["match_percentage"] > minimum_percentage
            and recommendation["mentor"].get("user_id") not in selected_mentor_ids
        ][:4]
        recommendations.extend(tier)
        selected_mentor_ids.update(
            recommendation["mentor"].get("user_id") for recommendation in tier
        )

    if not recommendations:
        st.warning("No mentors with meaningful skill relevance were found.")
        return

    st.markdown(
        f'<div class="section-title">{len(recommendations)} relevant mentors</div>',
        unsafe_allow_html=True,
    )

    for idx, rec in enumerate(recommendations):
        mentor = rec.get("mentor", rec)
        mentor_id = mentor.get("id") or mentor.get("mentor_id") or mentor.get("user_id")

        score = float(rec.get("match_percentage", 0))
        required_matches = rec.get(
            "required_skill_matches",
            rec.get("matching_required_skills", rec.get("matched_skills", [])),
        )
        goal_matches = rec.get(
            "learning_goal_matches",
            rec.get("goal_matches", rec.get("matched_goals", [])),
        )
        current_matches = rec.get(
            "current_skill_matches",
            rec.get("matching_current_skills", rec.get("matched_current_skills", [])),
        )
        explanation = rec.get("explanation") or rec.get("ai_explanation") or (
            "This mentor profile has relevant overlap with the supplied mentee requirements."
        )

        try:
            available = is_mentor_available(mentor_id)
        except Exception:
            available = (
                int(mentor.get("current_mentees", 0))
                < int(mentor.get("max_mentees", 0))
            )

        current_count = int(mentor.get("current_mentees", 0))
        max_count = int(mentor.get("max_mentees", 0))

        st.html(
            dedent(
                f"""
            <div class="card" style="margin-bottom:1rem">
                <div class="mentor-card-head">
                    <div>
                        <div class="eyebrow">MENTOR {idx + 1:02d}</div>
                        <h2 style="margin:.1rem 0 .2rem">{escape(display_name(mentor))}</h2>
                        <div style="color:#8e9bad">{escape(str(mentor.get("email", "")))}</div>
                    </div>
                    <div class="score-ring">{score:.1f}%</div>
                    <div class="mentor-side-status"><strong>● AVAILABLE</strong><br>Capacity<br>{current_count} / {max_count} mentees</div>
                </div>

                <div style="margin-top:1rem">{skills_html(mentor.get("skills"))}</div>

                <div style="margin-top:1rem">
                    <div class="mini-label">Expertise</div>
                    <div style="margin-top:.3rem;color:#c6cfdb">{escape(str(mentor.get("expertise", "Not specified")))}</div>
                </div>

                <div style="margin-top:1rem">
                    <div class="mini-label">Experience</div>
                    <div style="margin-top:.3rem;color:#c6cfdb">{escape(str(mentor.get("experience", mentor.get("experience_years", 0))))} years</div>
                </div>

                <div style="margin-top:1rem">
                    <div class="mini-label">Bio</div>
                    <div class="explanation" style="margin-top:.3rem">{escape(str(mentor.get("bio", "No bio available.")))}</div>
                </div>

                <div style="margin-top:1rem">
                    <div class="mini-label">Capacity</div>
                    <div style="margin-top:.3rem;color:#c6cfdb">{current_count} / {max_count} mentees</div>
                    <div style="margin-top:.5rem">{status_html(available)}</div>
                </div>
            </div>
            """,
            )
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            st.html(
                f'<div class="card"><div class="mini-label">Required Skill Matches</div><div style="margin-top:.5rem">{skills_html(required_matches)}</div></div>'
            )
        with c2:
            st.html(
                f'<div class="card"><div class="mini-label">Learning Goal Matches</div><div style="margin-top:.5rem">{skills_html(goal_matches)}</div></div>'
            )
        with c3:
            st.html(
                f'<div class="card"><div class="mini-label">Current Skill Context</div><div style="margin-top:.5rem">{skills_html(current_matches)}</div></div>'
            )

        with st.expander("Why this mentor?"):
            st.html(
                f'<div class="explanation">{escape(str(explanation))}</div>'
            )

        if available and not active_requests:
            if st.button(
                f"Send Request → {display_name(mentor)}",
                key=f"send_request_{mentee_id}_{mentor_id}_{idx}",
                type="primary",
                use_container_width=True,
            ):
                try:
                    with st.status("Sending mentorship request...", expanded=False) as request_status:
                        result = send_request(mentee_id, mentor_id)
                        if isinstance(result, dict) and result.get("success") is False:
                            request_status.update(
                                label="Request not sent",
                                state="error",
                            )
                            st.warning(result.get("message", "The request could not be sent."))
                        else:
                            request_status.update(
                                label="Request sent successfully",
                                state="complete",
                            )
                            st.session_state["request_sent"] = (
                                f"Your request is now waiting for {display_name(mentor)} to respond."
                            )
                            st.toast("Mentorship request sent successfully.", icon="✅")
                            st.rerun()
                except Exception as exc:
                    st.error("The mentorship request could not be sent.")
                    st.exception(exc)
        elif not active_requests:
            st.button(
                "Mentor Full — Request Unavailable",
                key=f"full_{mentee_id}_{mentor_id}_{idx}",
                disabled=True,
                use_container_width=True,
            )


# -------------------------------------------------------------------
# My Requests
# -------------------------------------------------------------------

def render_my_requests():
    st.markdown('<div class="eyebrow">MENTEE WORKSPACE</div>', unsafe_allow_html=True)
    st.title("My Requests")
    st.caption("Track mentorship requests submitted by the selected mentee.")

    mentees = get_all_mentees()

    if not mentees:
        st.warning("No mentees are available.")
        return

    options = {user_label(m): m["id"] for m in mentees}
    selected_label = st.selectbox("Select mentee", list(options.keys()), key="requests_mentee_select")
    mentee_id = options[selected_label]

    requests = get_mentee_requests(mentee_id)

    if not requests:
        st.info("No mentorship requests yet.")
        return

    for request in requests:
        status = str(request.get("status", "PENDING")).upper()
        mentor_name = request.get("mentor_name", request.get("name", "Mentor"))
        mentor_email = request.get("mentor_email", request.get("email", ""))
        skills = request.get("skills", "")
        expertise = request.get("expertise", "")
        current_count = request.get("current_mentees", 0)
        max_count = request.get("max_mentees", 0)

        st.markdown(
            f"""
            <div class="card" style="margin-bottom:1rem">
                <div style="display:flex;justify-content:space-between;gap:1rem">
                    <div>
                        <h3 style="margin:0 0 .25rem">{escape(str(mentor_name))}</h3>
                        <div style="color:#8e9bad">{escape(str(mentor_email))}</div>
                    </div>
                    <div>{request_status_html(status)}</div>
                </div>
                <div style="margin-top:1rem">{skills_html(skills)}</div>
                <div style="margin-top:.8rem;color:#aeb8c8">
                    <strong>Expertise:</strong> {escape(str(expertise))}
                </div>
                <div style="margin-top:.5rem;color:#8e9bad">
                    Capacity: {escape(str(current_count))} / {escape(str(max_count))}
                </div>
                <div style="margin-top:.5rem;color:#6f7b8e;font-size:.75rem">
                    Created: {escape(str(request.get("created_at", "")))}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_enrolled_mentees():
    st.markdown('<div class="eyebrow">ENROLLMENT DIRECTORY</div>', unsafe_allow_html=True)
    st.title("Enrolled Mentees")
    st.caption("View mentee details, assigned mentors, and the latest request status.")

    enrolled_mentees = get_enrolled_mentees()

    if not enrolled_mentees:
        st.info("No mentee requests have been submitted yet.")
        return

    st.dataframe(
        [
            {
                "Mentee": row.get("mentee_name", ""),
                "Mentee Email": row.get("mentee_email", ""),
                "Domain": row.get("current_domain", ""),
                "Skill Level": row.get("skill_level", ""),
                "Current Skills": row.get("current_skills", ""),
                "Learning Goals": row.get("learning_goals", ""),
                "Required Skills": row.get("required_skills", ""),
                "Mentor": row.get("mentor_name", ""),
                "Mentor Email": row.get("mentor_email", ""),
                "Status": str(row.get("status", "PENDING")).upper(),
                "Updated": row.get("updated_at", ""),
            }
            for row in enrolled_mentees
        ],
        use_container_width=True,
        hide_index=True,
    )


# -------------------------------------------------------------------
# Mentor Profile
# -------------------------------------------------------------------

def render_mentor_profile():
    st.markdown('<div class="eyebrow">MENTOR WORKSPACE</div>', unsafe_allow_html=True)
    st.title("Mentor Profile")
    st.caption("Manage your expertise, profile information and mentoring capacity.")

    mentor_user_id = get_logged_in_mentor_id()
    mentors = [
        mentor
        for mentor in get_all_mentors()
        if mentor["id"] == mentor_user_id
    ]

    if not mentors:
        st.warning("No mentor profiles are available.")
        return

    mentor_id = mentor_user_id
    mentor = get_mentor(mentor_id)

    if not mentor:
        st.error("The selected mentor could not be loaded.")
        return

    current_count = int(mentor.get("current_mentees", 0))

    with st.form("mentor_profile_form"):
        c1, c2 = st.columns(2)

        with c1:
            name = st.text_input("Name", value=str(mentor.get("name", "")))
            email = st.text_input("Email", value=str(mentor.get("email", "")))
            skills = st.text_input(
                "Skills",
                value=", ".join(safe_list(mentor.get("skills"))),
                help="Separate skills with commas.",
            )
            expertise = st.text_input(
                "Expertise",
                value=str(mentor.get("expertise", "")),
            )

        with c2:
            experience = st.number_input(
                "Years of Experience",
                min_value=0,
                max_value=100,
                value=int(float(mentor.get("experience", mentor.get("experience_years", 0)) or 0)),
                step=1,
            )
            max_mentees = st.number_input(
                "Maximum Mentees",
                min_value=current_count,
                max_value=1000,
                value=max(current_count, int(mentor.get("max_mentees", current_count) or current_count)),
                step=1,
                help="Cannot be lower than current mentees.",
            )
            bio = st.text_area(
                "Bio",
                value=str(mentor.get("bio", "")),
                height=150,
            )

        submitted = st.form_submit_button("Save Mentor Profile", type="primary", use_container_width=True)

    if submitted:
        if not name.strip():
            st.error("Name cannot be empty.")
            return
        if not email.strip() or "@" not in email:
            st.error("Please enter a valid email address.")
            return
        if int(max_mentees) < current_count:
            st.error("Maximum Mentees cannot be less than Current Mentees.")
            return

        try:
            update_mentor_profile(
                mentor_id,
                name=name.strip(),
                email=email.strip(),
                domain=str(mentor.get("domain", "")),
                skills=skills.strip(),
                expertise=expertise.strip(),
                experience=int(experience),
                bio=bio.strip(),
                max_mentees=int(max_mentees),
            )
            st.success("Mentor profile saved successfully.")
            st.rerun()
        except Exception as exc:
            st.error("Could not save the mentor profile.")
            st.exception(exc)

    remaining = max(0, int(mentor.get("max_mentees", 0)) - current_count)
    available = current_count < int(mentor.get("max_mentees", 0))

    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("Current Mentees", current_count)
    with c2:
        metric_card("Maximum", mentor.get("max_mentees", 0))
    with c3:
        metric_card("Remaining Slots", remaining)

    st.markdown(
        f'<div style="margin-top:1rem">{status_html(available)}</div>',
        unsafe_allow_html=True,
    )


# -------------------------------------------------------------------
# Mentor Dashboard
# -------------------------------------------------------------------

def render_mentor_dashboard():
    st.markdown('<div class="eyebrow">MENTOR WORKSPACE</div>', unsafe_allow_html=True)
    st.title("Mentor Dashboard")
    st.caption("Review mentorship requests and manage capacity safely.")

    mentor_user_id = get_logged_in_mentor_id()
    mentors = [
        mentor
        for mentor in get_all_mentors()
        if mentor["id"] == mentor_user_id
    ]

    if not mentors:
        st.warning("No mentors are available.")
        return

    mentor_id = mentor_user_id
    mentor = get_mentor(mentor_id)

    if not mentor:
        st.error("Unable to load the selected mentor.")
        return

    current = int(mentor.get("current_mentees", 0))
    maximum = int(mentor.get("max_mentees", 0))
    remaining = max(0, maximum - current)
    available = current < maximum

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Current Mentees", current)
    with c2:
        metric_card("Maximum", maximum)
    with c3:
        metric_card("Remaining Slots", remaining)
    with c4:
        metric_card("Status", "AVAILABLE" if available else "FULL")

    requests = get_pending_requests_for_mentor(mentor_id)

    st.markdown('<div class="section-title">Mentorship Requests</div>', unsafe_allow_html=True)

    if not requests:
        st.info("No mentorship requests for this mentor.")
        return

    for request in requests:
        status = str(request.get("status", "PENDING")).upper()
        mentee_name = request.get("mentee_name", "Mentee")
        mentee_email = request.get("mentee_email", "")
        mentor_name = mentor.get("name", "Mentor")
        mentor_email = mentor.get("email", "")
        mentee_skills = request.get("current_skills", "")
        mentee_goals = request.get("learning_goals", "")
        mentee_required = request.get("required_skills", "")
        mentee_level = request.get("skill_level", "")
        mentee_domain = request.get("current_domain", "")

        st.html(
            f"""
            <div class="card" style="margin-bottom:.75rem">
                <div style="display:flex;justify-content:space-between;gap:1rem">
                    <div>
                        <h3 style="margin:0">{escape(str(mentee_name))}</h3>
                        <div style="color:#8e9bad;margin-top:.2rem">{escape(str(mentee_email))}</div>
                        <div style="color:#8e9bad;margin-top:.2rem">Mentor: {escape(str(mentor_name))} · {escape(str(mentor_email))}</div>
                    </div>
                    <div>{request_status_html(status)}</div>
                </div>
                <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.75rem;margin-top:1rem">
                    <div><div class="mini-label">Current Domain</div><div>{escape(str(mentee_domain or "Not specified"))}</div></div>
                    <div><div class="mini-label">Skill Level</div><div>{escape(str(mentee_level or "Not specified"))}</div></div>
                    <div><div class="mini-label">Current Skills</div><div>{skills_html(mentee_skills)}</div></div>
                    <div><div class="mini-label">Learning Goals</div><div>{skills_html(mentee_goals)}</div></div>
                    <div style="grid-column:1 / -1"><div class="mini-label">Required Skills</div><div>{skills_html(mentee_required)}</div></div>
                </div>
                <div style="margin-top:.6rem;color:#6f7b8e;font-size:.75rem">
                    Created: {escape(str(request.get("created_at", "")))}
                </div>
            </div>
            """
        )

        if status == "PENDING":
            c1, c2 = st.columns(2)

            with c1:
                if st.button(
                    "✓ Accept",
                    key=f"accept_{request['id']}",
                    type="primary",
                    use_container_width=True,
                ):
                    try:
                        result = accept_request(request["id"], mentor_id)
                        if isinstance(result, dict) and result.get("success") is False:
                            st.warning(result.get("message", "The request could not be accepted."))
                        else:
                            st.success("Request accepted and mentor capacity updated.")
                        st.rerun()
                    except Exception as exc:
                        st.error("The request could not be accepted.")
                        st.exception(exc)

            with c2:
                if st.button(
                    "✕ Reject",
                    key=f"reject_{request['id']}",
                    use_container_width=True,
                ):
                    try:
                        result = reject_request(request["id"], mentor_id)
                        if isinstance(result, dict) and result.get("success") is False:
                            st.warning(result.get("message", "The request could not be rejected."))
                        else:
                            st.success("Request rejected.")
                        st.rerun()
                    except Exception as exc:
                        st.error("The request could not be rejected.")
                        st.exception(exc)


# -------------------------------------------------------------------
# Router
# -------------------------------------------------------------------

try:
    if page == "Home":
        render_home()
    elif page == "Mentee Profile":
        render_mentee_profile()
    elif page == "Find Mentor":
        render_find_mentor()
    elif page == "My Requests":
        render_my_requests()
    elif page == "Enrolled Mentees":
        render_enrolled_mentees()
    elif page == "Mentor Profile":
        render_mentor_profile()
    elif page == "Mentor Dashboard":
        render_mentor_dashboard()
except Exception as exc:
    st.error("Something unexpected happened while rendering this page.")
    st.exception(exc)
