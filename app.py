import base64
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

ASSETS_DIR = Path(__file__).parent / "assets"
HERO_IMAGE_PATH = ASSETS_DIR / "mentor_home_hero.png"


def get_base64_image(image_path: Path) -> str:
    """Convert a local image into a Base64 string for HTML rendering."""
    if not image_path.exists():
        return ""

    return base64.b64encode(image_path.read_bytes()).decode("utf-8")


hero_image_base64 = get_base64_image(HERO_IMAGE_PATH)

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

                width: 282px !important;
                min-width: 282px !important;
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

            [data-testid="stSidebar"] [data-testid="stRadio"] label::before {
                display: inline-block;
                width: 1.25rem;
                margin-right: .3rem;
                color: #7e91c0;
                text-align: center;
            }

            [data-testid="stSidebar"] [data-testid="stRadio"] label:nth-child(1)::before { content: "⌂"; }
            [data-testid="stSidebar"] [data-testid="stRadio"] label:nth-child(2)::before { content: "◉"; }
            [data-testid="stSidebar"] [data-testid="stRadio"] label:nth-child(3)::before { content: "⌕"; }
            [data-testid="stSidebar"] [data-testid="stRadio"] label:nth-child(4)::before { content: "▤"; }
            [data-testid="stSidebar"] [data-testid="stRadio"] label:nth-child(5)::before { content: "♙"; }
            [data-testid="stSidebar"] [data-testid="stRadio"] label:nth-child(6)::before { content: "▣"; }
            [data-testid="stSidebar"] [data-testid="stRadio"] label:nth-child(7)::before { content: "♙"; }

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

        /* Keep Streamlit's sidebar toggle compact when its icon font is unavailable. */
        [data-testid="stSidebarCollapseButton"],
        [data-testid="stSidebarCollapsedControl"] {
            overflow: hidden;
        }

        [data-testid="stSidebarCollapseButton"] button,
        [data-testid="stSidebarCollapsedControl"] button {
            width: 2rem;
            min-width: 2rem;
            height: 2rem;
            padding: 0;
            overflow: hidden;
            color: transparent !important;
            font-size: 0 !important;
            line-height: 0 !important;
        }

        [data-testid="stSidebarCollapseButton"] button::after,
        [data-testid="stSidebarCollapsedControl"] button::after {
            content: "‹";
            display: block;
            color: #aab9de;
            font-size: 1.35rem;
            line-height: 1;
        }

        [data-testid="stSidebarCollapseButton"] button [data-testid="stIconMaterial"],
        [data-testid="stSidebarCollapsedControl"] button [data-testid="stIconMaterial"],
        [data-testid="stSidebarCollapseButton"] button span[class*="material"],
        [data-testid="stSidebarCollapsedControl"] button span[class*="material"] {
            display: none !important;
        }

        [data-testid="stSidebarCollapseButton"] button::after,
        [data-testid="stSidebarCollapsedControl"] button::after {
            content: "‹" !important;
            display: block !important;
            width: 100%;
            color: #aab9de !important;
            font-family: sans-serif !important;
            font-size: 1.35rem !important;
            line-height: 1 !important;
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

        .role-entry {
            min-height: 360px;
            display: grid;
            place-items: center;
            padding: 2rem;
            border: 1px solid rgba(116, 148, 255, .2);
            border-radius: 12px;
            background:
                radial-gradient(circle at 50% 0%, rgba(69, 98, 214, .2), transparent 42%),
                linear-gradient(145deg, rgba(15, 28, 59, .98), rgba(8, 15, 32, .98));
        }

        .role-entry-content {
            width: min(100%, 650px);
            text-align: center;
        }

        .role-entry h1 {
            margin: .25rem 0 .55rem;
            font-size: clamp(2rem, 4vw, 3.1rem);
        }

        .role-entry p {
            max-width: 500px;
            margin: 0 auto 1.35rem;
            color: #98a8cf;
            font-size: .78rem;
        }

        .role-choice {
            min-height: 125px;
            display: grid;
            place-items: center;
            padding: 1rem;
            border: 1px solid rgba(119, 145, 241, .25);
            border-radius: 10px;
            background: linear-gradient(145deg, rgba(31, 51, 112, .72), rgba(20, 31, 67, .72));
            color: #f3f5ff;
            font-weight: 700;
        }

        .role-choice small {
            display: block;
            margin-top: .35rem;
            color: #9baad0;
            font-size: .64rem;
            font-weight: 400;
        }

        .mentor-dashboard-card {
            display: grid;
            grid-template-columns: 1.05fr .95fr;
            gap: .75rem;
            padding: .8rem;
            border: 1px solid rgba(117, 147, 240, .2);
            border-radius: 11px;
            background: linear-gradient(145deg, rgba(13, 29, 61, .98), rgba(9, 19, 40, .98));
        }

        .mentor-dashboard-profile {
            min-height: 210px;
            padding: .2rem .65rem .2rem .1rem;
            border-right: 1px solid rgba(119, 143, 213, .14);
        }

        .mentor-identity {
            display: flex;
            align-items: center;
            gap: .65rem;
        }

        .mentor-avatar {
            display: grid;
            place-items: center;
            width: 3.25rem;
            height: 3.25rem;
            flex: 0 0 3.25rem;
            border-radius: 50%;
            border: 2px solid #78a0ff;
            background: linear-gradient(135deg, #284892, #9c5fe8);
            color: white;
            font-size: 1.1rem;
            font-weight: 800;
        }

        .mentor-dashboard-profile h2 {
            margin: 0;
            font-size: 1.12rem;
        }

        .mentor-subline {
            margin-top: .2rem;
            color: #aab8d7;
            font-size: .62rem;
            line-height: 1.7;
        }

        .mentor-subline span {
            color: #7990bc;
        }

        .dashboard-status {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: .65rem;
            align-items: center;
            padding-left: .2rem;
        }

        .dashboard-ring {
            display: grid;
            place-items: center;
            width: 94px;
            height: 94px;
            margin: auto;
            border: 8px solid #42caff;
            border-right-color: #806bff;
            border-radius: 50%;
            color: #f5f7ff;
            font-size: 1rem;
            font-weight: 800;
        }

        .dashboard-ring small {
            display: block;
            color: #93a2c4;
            font-size: .48rem;
            font-weight: 500;
            text-align: center;
        }

        .dashboard-capacity {
            padding: .7rem;
            border: 1px solid rgba(106, 138, 228, .18);
            border-radius: 8px;
            color: #b8c4df;
            font-size: .62rem;
            line-height: 1.8;
        }

        .dashboard-capacity strong {
            color: #63efa4;
            font-size: .68rem;
        }

        .dashboard-details {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: .65rem;
            margin-top: .7rem;
        }

        .dashboard-detail-card {
            min-height: 105px;
            padding: .7rem;
            border: 1px solid rgba(111, 140, 230, .16);
            border-radius: 9px;
            background: rgba(14, 28, 57, .8);
        }

        .dashboard-detail-card h4 {
            margin: 0 0 .45rem;
            font-size: .7rem;
        }

        .dashboard-detail-card p {
            margin: 0;
            color: #aab8d5;
            font-size: .62rem;
            line-height: 1.55;
        }

        .dashboard-request-actions {
            display: flex;
            gap: .45rem;
            margin-top: .65rem;
        }

        .dashboard-shell {
            padding: .8rem;
            border: 1px solid rgba(117, 147, 240, .2);
            border-radius: 12px;
            background: linear-gradient(145deg, rgba(13, 29, 61, .98), rgba(9, 19, 40, .98));
        }

        .dashboard-column {
            min-height: 310px;
            padding: .8rem;
            border: 1px solid rgba(111, 140, 230, .16);
            border-radius: 9px;
            background: rgba(14, 28, 57, .72);
        }

        .dashboard-column h3 {
            margin: 0 0 .7rem;
            font-size: .78rem;
        }

        .dashboard-column h4 {
            margin: .8rem 0 .35rem;
            font-size: .65rem;
        }

        .progress-row { margin: .65rem 0; }

        .progress-label {
            display: flex;
            justify-content: space-between;
            gap: .5rem;
            color: #b8c5e3;
            font-size: .59rem;
        }

        .progress-track {
            height: 6px;
            margin-top: .28rem;
            overflow: hidden;
            border-radius: 999px;
            background: #1c2a4a;
        }

        .progress-fill { height: 100%; border-radius: inherit; }
        .progress-purple { background: linear-gradient(90deg, #7654ef, #a758ed); }
        .progress-blue { background: linear-gradient(90deg, #398cff, #62b9ff); }
        .progress-green { background: linear-gradient(90deg, #55d39c, #7aefb3); }

        .profile-score-label {
            margin-top: .4rem;
            color: #8fa0c5;
            font-size: .54rem;
            text-align: center;
        }

        .dashboard-action-row { margin-top: .75rem; }

        @media (max-width: 700px) {
            .mentor-dashboard-card, .dashboard-status { grid-template-columns: 1fr; }
            .mentor-dashboard-profile { border-right: 0; border-bottom: 1px solid rgba(119, 143, 213, .14); padding-bottom: .7rem; }
        }

        /* Home page reference layout */
        .mm-home {
            color: #f7f9ff;
        }

        .mm-topbar {
            min-height: 46px;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            margin: -.65rem -1rem .7rem;
            padding: 0 1rem;
            border-bottom: 1px solid rgba(105, 135, 220, .16);
        }

        .mm-home .mm-topbar {
            margin-top: -.65rem;
        }

        .mm-hero {
            position: relative;
            min-height: 270px;
            padding: 1.65rem 1.8rem;
            overflow: hidden;
            border: 1px solid rgba(105, 135, 220, .30);
            border-radius: 20px;
            background:
                radial-gradient(circle at 83% 20%, rgba(55, 200, 255, .30), transparent 23%),
                radial-gradient(circle at 58% 95%, rgba(114, 59, 255, .38), transparent 29%),
                linear-gradient(118deg, #172b8d 0%, #10245d 47%, #071733 100%);
            box-shadow: 0 20px 55px rgba(2, 13, 40, .35);
        }

        .mm-hero-grid {
            position: static;
            display: block;
            min-height: 235px;
        }

        .mm-hero-eyebrow {
            margin-bottom: .55rem;
            color: #9a9dff;
            font-size: .57rem;
            font-weight: 800;
            letter-spacing: .16em;
            text-transform: uppercase;
        }

        .mm-hero h1 {
            max-width: 580px;
            margin: 0 0 .7rem;
            color: #fbfcff;
            font-size: clamp(2.15rem, 4.3vw, 3.55rem);
            line-height: 1.02;
            letter-spacing: -.055em;
        }

        .mm-hero-copy {
            max-width: 470px;
            margin: 0;
            color: #c5d3f5;
            font-size: .78rem;
            line-height: 1.55;
        }

        .mm-hero-art {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            width: 100%;
            bottom: 0;
            height: auto;
            overflow: hidden;
            border-radius: inherit;
            z-index: 1;
        }

        .mm-hero-image {
            width: 100%;
            height: 100%;
            object-fit: cover;
            object-position: center right;
            display: block;
            -webkit-mask-image: linear-gradient(
                90deg,
                transparent 0%,
                rgba(0, 0, 0, .18) 10%,
                rgba(0, 0, 0, .72) 25%,
                #000 42%
            );
            mask-image: linear-gradient(
                90deg,
                transparent 0%,
                rgba(0, 0, 0, .18) 10%,
                rgba(0, 0, 0, .72) 25%,
                #000 42%
            );
        }

        .mm-hero-visual::before {
            content: "";
            position: absolute;
            inset: 0;
            z-index: 1;
            background:
                linear-gradient(180deg, #172b8d 0%, transparent 10%, transparent 88%, #071733 100%),
                linear-gradient(90deg, #172b8d 0%, #172b8d 22%, rgba(23, 43, 141, .92) 38%, rgba(23, 43, 141, .42) 57%, rgba(23, 43, 141, .08) 76%, transparent 100%);
            pointer-events: none;
        }

        .mm-hero-content {
            position: relative;
            z-index: 3;
            width: 58%;
        }

        .mm-hero-links {
            position: absolute;
            top: .1rem;
            right: .2rem;
            color: #dce6ff;
            font-size: .55rem;
        }

        .mm-hero-labels {
            position: absolute;
            right: .2rem;
            bottom: .25rem;
            color: #c7d7ff;
            font-size: .52rem;
            line-height: 1.55;
            text-align: right;
        }

        .mm-hero-right-top, .mm-hero-right-bottom {
            position: absolute;
            z-index: 4;
        }

        .mm-hero-right-top {
            top: 1.5rem;
            right: 2rem;
            color: #ffffff;
            font-size: .72rem;
        }

        .mm-hero-right-bottom {
            right: 2rem;
            bottom: 1.7rem;
            color: #dce5ff;
            font-size: .62rem;
            line-height: 1.8;
            letter-spacing: .04em;
        }

        .mm-metrics {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: .65rem;
            margin: .7rem 0 .9rem;
        }

        .mm-metric-card {
            min-height: 75px;
            padding: .7rem .8rem;
            border: 1px solid rgba(105, 135, 220, .22);
            border-radius: 9px;
            background: linear-gradient(145deg, #0d2341, #0a192f);
        }

        .mm-metric-icon {
            display: inline-grid;
            place-items: center;
            width: 1.45rem;
            height: 1.45rem;
            margin-bottom: .25rem;
            border-radius: 6px;
            font-size: .76rem;
        }

        .mm-metric-value {
            color: #f7f9ff;
            font-size: 1.25rem;
            font-weight: 800;
            line-height: 1;
        }

        .mm-metric-label {
            margin-top: .25rem;
            color: #9eaecc;
            font-size: .57rem;
        }

        .mm-step-title {
            margin: .5rem 0 .45rem;
            color: #f7f9ff;
            font-size: 1.05rem;
            font-weight: 800;
        }

        .mm-steps {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: .65rem;
        }

        .mm-step-card {
            display: flex;
            gap: .65rem;
            align-items: center;
            min-height: 75px;
            padding: .7rem;
            border: 1px solid rgba(105, 135, 220, .22);
            border-radius: 9px;
            background: linear-gradient(145deg, #0d2341, #0a192f);
        }

        .mm-step-number {
            display: grid;
            place-items: center;
            width: 2rem;
            height: 2rem;
            flex: 0 0 2rem;
            border-radius: 50%;
            background: linear-gradient(135deg, #246bfd, #37c8ff);
            color: white;
            font-size: .72rem;
            font-weight: 800;
        }

        .mm-step-card:last-child .mm-step-number {
            background: linear-gradient(135deg, #723bff, #c25cff);
        }

        .mm-step-card h4 {
            margin: 0 0 .2rem;
            color: #f7f9ff;
            font-size: .7rem;
        }

        .mm-step-card p {
            margin: 0;
            color: #9eaecc;
            font-size: .57rem;
            line-height: 1.4;
        }

        @media (max-width: 800px) {
            .mm-hero-grid { min-height: 400px; }
            .mm-hero-content { width: 100%; }
            .mm-hero-art { top: auto; bottom: 0; height: 54%; border-radius: 0 0 14px 14px; }
            .mm-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }

        @media (max-width: 560px) {
            .mm-hero { padding: 1.1rem; border-radius: 14px; }
            .mm-hero h1 { font-size: 2.05rem; }
            .mm-metrics, .mm-steps { grid-template-columns: 1fr; }
            .mm-topbar { margin-left: -.75rem; margin-right: -.75rem; }
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


def open_my_requests():
    st.session_state["next_workspace_page"] = "My Requests"


def open_mentor_login():
    st.session_state["workspace_page"] = "Home"
    st.session_state["home_role_login"] = "mentor"


def reset_home_role_login():
    st.session_state.pop("home_role_login", None)


# -------------------------------------------------------------------
# Sidebar
# -------------------------------------------------------------------

stats = get_database_stats()

if "next_workspace_page" in st.session_state:
    st.session_state["workspace_page"] = st.session_state.pop("next_workspace_page")

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
        st.button(
            "Mentor Login",
            key="sidebar_mentor_login",
            use_container_width=True,
            on_click=open_mentor_login,
        )
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



role_label = "Mentor" if is_mentor_logged_in() else "Mentee"
user_name = str(st.session_state.get("mentor_name", "User")) if is_mentor_logged_in() else "User"
avatar_letter = (user_name[:1] or "U").upper()
st.markdown(
    f'''
    <div class="mm-topbar">
        <div class="topbar-links">Learn&nbsp;&nbsp;•&nbsp;&nbsp;Grow&nbsp;&nbsp;•&nbsp;&nbsp;Connect</div>
        <div class="topbar-user"><span class="topbar-avatar">{escape(avatar_letter)}</span><span>{escape(user_name)}<br><small>{escape(role_label)}⌄</small></span></div>
    </div>
    ''',
    unsafe_allow_html=True,
)


# -------------------------------------------------------------------
# Home
# -------------------------------------------------------------------

def render_home():
    selected_role = st.session_state.get("home_role_login")
    if selected_role == "mentor" and not is_mentor_logged_in():
        st.markdown('<div class="eyebrow">MENTOR ACCESS</div>', unsafe_allow_html=True)
        st.title("Mentor Login")
        st.caption("Sign in to manage your mentor profile, capacity, and incoming requests.")
        with st.form("home_mentor_login_form"):
            mentor_email = st.text_input("Mentor email", key="home_mentor_email")
            mentor_password = st.text_input("Password", type="password", key="home_mentor_password")
            login_submitted = st.form_submit_button("Sign in as Mentor", type="primary", use_container_width=True)

        back_col, _ = st.columns([1, 3])
        with back_col:
            st.button("← Back", key="home_role_back", use_container_width=True, on_click=reset_home_role_login)

        if login_submitted:
            if login_mentor(mentor_email, mentor_password):
                st.session_state["next_workspace_page"] = "Mentor Dashboard"
                st.session_state["mentor_pending_landing"] = True
                st.session_state.pop("home_role_login", None)
                st.rerun()
            else:
                st.error("Invalid mentor email or password.")
        return

    stats = get_database_stats()
    if not hero_image_base64:
        st.warning("The Home hero image could not be loaded from assets/mentor_home_hero.png.")
    st.html(
        f"""
        <main class="mm-home">
            <section class="mm-hero">
                <div class="mm-hero-grid">
                    <div class="mm-hero-content">
                        <div class="mm-hero-eyebrow">AI mentorship intelligence</div>
                        <h1>Find the right mentor.<br>Build the next version of you.</h1>
                        <p class="mm-hero-copy">Connect with relevant mentors using explainable skill matching, lightweight retrieval and AI-generated recommendations.</p>
                    </div>
                    <div class="mm-hero-art mm-hero-visual">
                        <img class="mm-hero-image" src="data:image/png;base64,{hero_image_base64}" alt="Mountain path leading to a summit flag" />
                        <div class="mm-hero-right-top">Learn + Grow + Connect</div>
                        <div class="mm-hero-right-bottom">SKILLS<br>PEOPLE<br>OPPORTUNITIES<br>A BRIGHTER YOU</div>
                    </div>
                </div>
            </section>
        </main>
        """,
    )

    hero_action, hero_guide, _ = st.columns([1.05, 1.05, 2.4])
    with hero_action:
        st.button(
            "Get Started →",
            key="mm_home_get_started",
            type="primary",
            use_container_width=True,
            on_click=open_mentee_profile,
        )
    with hero_guide:
        if st.button("How it works", key="mm_home_how_it_works", use_container_width=True):
            st.session_state["home_show_guide"] = True
            st.rerun()

    metric_data = [
        ("◉", "#37c8ff", stats.get("mentors", 0), "Mentors"),
        ("✦", "#a56bff", stats.get("mentees", 0), "Mentees"),
        ("✓", "#2edb91", stats.get("available_mentors", 0), "Available Mentors"),
        ("▣", "#ff912e", stats.get("requests", 0), "Mentorship Requests"),
    ]
    metric_markup = "".join(
        f'<div class="mm-metric-card"><div class="mm-metric-icon" style="color:{color};background:{color}22">{icon}</div><div class="mm-metric-value">{escape(str(value))}</div><div class="mm-metric-label">{escape(label)}</div></div>'
        for icon, color, value, label in metric_data
    )
    st.markdown(f'<div class="mm-metrics">{metric_markup}</div>', unsafe_allow_html=True)

    if st.session_state.pop("home_show_guide", False):
        st.info("Create a mentee profile, generate skill-based matches, then send one request to an available mentor.")

    st.markdown('<div class="mm-step-title">How it works</div>', unsafe_allow_html=True)
    steps = [
        ("01", "Understand", "Capture your skills, learning goals and required skills."),
        ("02", "Match", "Our AI finds relevant mentors with explainable scores."),
        ("03", "Connect", "Send a request and start your mentorship journey."),
    ]
    step_markup = "".join(
        f'<div class="mm-step-card"><div class="mm-step-number">{number}</div><div><h4>{title}</h4><p>{text}</p></div></div>'
        for number, title, text in steps
    )
    st.markdown(f'<div class="mm-steps">{step_markup}</div>', unsafe_allow_html=True)
    return

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
            st.session_state.pop("matching_results", None)
            st.session_state.pop("last_match_mentee", None)
            st.session_state["next_workspace_page"] = "Find Mentor"
            st.toast("Mentee profile saved. Find a matching mentor next.", icon="✅")
            st.rerun()
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
    select_col, requests_col = st.columns([3, 1])
    with select_col:
        selected_label = st.selectbox("Select mentee", list(options.keys()), key="find_mentee_select")
    with requests_col:
        st.markdown('<div style="height:1.65rem"></div>', unsafe_allow_html=True)
        st.button(
            "My Requests",
            key="find_my_requests",
            use_container_width=True,
            on_click=open_my_requests,
        )
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
# Legacy Mentor Dashboard
# -------------------------------------------------------------------

def _legacy_render_mentor_dashboard():
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

    dashboard_notice = st.session_state.pop("mentor_dashboard_notice", None)
    if dashboard_notice:
        st.success(dashboard_notice)

    current = int(mentor.get("current_mentees", 0))
    maximum = int(mentor.get("max_mentees", 0))
    remaining = max(0, maximum - current)
    available = current < maximum

    requests = get_pending_requests_for_mentor(mentor_id)
    show_pending_landing = st.session_state.pop("mentor_pending_landing", False)

    mentor_name = display_name(mentor)
    initials = "".join(part[0] for part in mentor_name.split()[:2]).upper()
    utilization = round((current / maximum) * 100) if maximum else 0
    skills = safe_list(mentor.get("skills"))
    expertise = str(mentor.get("expertise", "Not specified"))
    experience = int(float(mentor.get("experience", mentor.get("experience_years", 0)) or 0))

    st.markdown(
        f'''
        <div class="mentor-dashboard-card">
            <div class="mentor-dashboard-profile">
                <div class="mentor-identity">
                    <div class="mentor-avatar">{escape(initials or "M")}</div>
                    <div>
                        <h2>{escape(mentor_name)} <span style="color:#42caff;font-size:.75rem">●</span></h2>
                        <div class="mentor-subline"><span>◉</span> {escape(str(mentor.get("domain", "Mentor")))}<br><span>♙</span> {experience} years experience<br><span>✦</span> {escape(", ".join(skills[:4]) or "Mentorship")}</div>
                    </div>
                </div>
                <div style="margin-top:1rem"><div class="mini-label">About</div><p class="explanation" style="margin-top:.35rem">{escape(str(mentor.get("bio", "Ready to support mentees with practical guidance.")))}</p></div>
                <div style="margin-top:.7rem"><div class="mini-label">Skills &amp; Expertise</div><div style="margin-top:.25rem">{skills_html(skills)}{skills_html(expertise)}</div></div>
            </div>
            <div class="dashboard-status">
                <div class="dashboard-ring">{utilization}%<small>CAPACITY USED</small></div>
                <div class="dashboard-capacity"><strong>● {"AVAILABLE" if available else "FULL"}</strong><br>Capacity<br><b>{current} / {maximum} mentees</b><br>Remaining slots: {remaining}</div>
            </div>
        </div>
        <div class="dashboard-details">
            <div class="dashboard-detail-card"><h4>Mentor Details</h4><p>Experience: {experience} years<br>Domain: {escape(str(mentor.get("domain", "Not specified")))}<br>Email: {escape(str(mentor.get("email", "")))}</p></div>
            <div class="dashboard-detail-card"><h4>Mentoring Skills</h4><div>{skills_html(skills)}</div></div>
        </div>
        ''',
        unsafe_allow_html=True,
    )

    if show_pending_landing and requests:
        st.markdown('<div class="section-title">Pending Requests</div>', unsafe_allow_html=True)
        st.caption("Review the mentees waiting for your response.")
    else:
        st.markdown('<div class="section-title">Mentor Dashboard</div>', unsafe_allow_html=True)

    if not requests:
        st.info("No requests found.")
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
                            st.session_state["mentor_dashboard_notice"] = "Request accepted and mentor capacity updated."
                            st.session_state["next_workspace_page"] = "Mentor Dashboard"
                        st.session_state["mentor_pending_landing"] = False
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
                            st.session_state["mentor_dashboard_notice"] = "Request rejected."
                            st.session_state["next_workspace_page"] = "Mentor Dashboard"
                        st.session_state["mentor_pending_landing"] = False
                        st.rerun()
                    except Exception as exc:
                        st.error("The request could not be rejected.")
                        st.exception(exc)


# -------------------------------------------------------------------
# Reference-style mentor dashboard
# -------------------------------------------------------------------

def render_mentor_dashboard():
    st.markdown('<div class="eyebrow">MENTOR WORKSPACE</div>', unsafe_allow_html=True)
    st.title("Mentor Dashboard")
    st.caption("Review your profile, availability, matching details, and incoming requests.")

    mentor_id = get_logged_in_mentor_id()
    mentor = get_mentor(mentor_id) if mentor_id else None
    if not mentor:
        st.warning("No mentors are available.")
        return

    notice = st.session_state.pop("mentor_dashboard_notice", None)
    if notice:
        st.success(notice)

    requests = get_pending_requests_for_mentor(mentor_id)
    current = int(mentor.get("current_mentees", 0) or 0)
    maximum = int(mentor.get("max_mentees", 0) or 0)
    remaining = max(0, maximum - current)
    available = current < maximum
    mentor_name = display_name(mentor)
    initials = "".join(part[0] for part in mentor_name.split()[:2]).upper()
    skills = safe_list(mentor.get("skills"))
    expertise = safe_list(mentor.get("expertise"))
    experience = int(float(mentor.get("experience", mentor.get("experience_years", 0)) or 0))

    selected_request = requests[0] if requests else None
    match = None
    if selected_request:
        request_mentee = {
            "required_skills": selected_request.get("required_skills", ""),
            "learning_goals": selected_request.get("learning_goals", ""),
            "skills": selected_request.get("current_skills", ""),
        }
        match = calculate_match(request_mentee, mentor)
        required_percentage = match["required_match_percentage"]
        goals_percentage = match["learning_goal_match_percentage"]
        current_percentage = match["current_skill_match_percentage"]
        display_score = match["match_percentage"]
        score_label = f"Match with {selected_request.get('mentee_name', 'mentee')}"
    else:
        completeness = [
            bool(skills),
            bool(expertise),
            min(experience / 10, 1),
            min(len(str(mentor.get("bio", "")).strip()) / 120, 1),
        ]
        display_score = round(sum(completeness) / len(completeness) * 100, 1)
        required_percentage = round(min(len(skills) / 8, 1) * 100, 1)
        goals_percentage = round(min(len(expertise) / 5, 1) * 100, 1)
        current_percentage = round(min(experience / 10, 1) * 100, 1)
        score_label = "Profile completeness score"

    def progress_row(label, percentage, color):
        value = max(0, min(100, float(percentage)))
        return (
            f'<div class="progress-row"><div class="progress-label">'
            f'<span>{escape(label)}</span><span>{value:.1f}%</span></div>'
            f'<div class="progress-track"><div class="progress-fill {color}" '
            f'style="width:{value:.1f}%"></div></div></div>'
        )

    st.markdown('<div class="dashboard-shell">', unsafe_allow_html=True)
    left, middle, right = st.columns([1.12, 1, .92], gap="small")

    with left:
        st.markdown(
            f'''
            <div class="dashboard-column">
                <div class="mentor-identity">
                    <div class="mentor-avatar">{escape(initials or "M")}</div>
                    <div><h2>{escape(mentor_name)} <span style="color:#42caff;font-size:.75rem">●</span></h2>
                    <div class="mentor-subline"><span>◉</span> {escape(str(mentor.get("domain", "Mentor")))}<br>
                    <span>♙</span> {experience} years experience<br>
                    <span>✦</span> {escape(", ".join(skills[:4]) or "Mentorship")}</div></div>
                </div>
                <h4>About</h4><p class="explanation">{escape(str(mentor.get("bio", "No bio available.")))}</p>
                <h4>Skills &amp; Expertise</h4><div>{skills_html(skills + expertise)}</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )

    with middle:
        st.markdown(
            f'''<div class="dashboard-column"><div class="dashboard-ring">{display_score:.1f}%<small>{"MATCH SCORE" if match else "PROFILE SCORE"}</small></div><div class="profile-score-label">{escape(score_label)}</div><h3 style="margin-top:1.1rem">Matching Details</h3>{progress_row("Required Skills Match", required_percentage, "progress-purple")}{progress_row("Learning Goals Match", goals_percentage, "progress-blue")}{progress_row("Current Skill Context", current_percentage, "progress-green")}</div>''',
            unsafe_allow_html=True,
        )

    with right:
        matching_skills = skills
        required_skills_matched = match["matched_skills"] if match else skills
        goal_alignment = match["matched_goals"] if match else expertise
        st.markdown(
            f'''<div class="dashboard-column"><h3><span style="color:{"#63efa4" if available else "#ff7777"}">●</span> {"AVAILABLE" if available else "FULL"}</h3><div class="dashboard-capacity">Capacity<br><b>{current} / {maximum} mentees</b><br>Remaining slots: {remaining}</div><h4>Matching Skills</h4><div>{skills_html(matching_skills)}</div><h4>Required Skills Matched</h4><div>{skills_html(required_skills_matched)}</div><h4>Goal Alignment</h4><div>{skills_html(goal_alignment)}</div></div>''',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)

    action_left, _ = st.columns(2)
    with action_left:
        if st.button("Edit Full Profile", key="mentor_edit_full_profile", use_container_width=True):
            st.session_state["next_workspace_page"] = "Mentor Profile"
            st.rerun()

    st.markdown('<div class="section-title">Pending Requests</div>', unsafe_allow_html=True)
    if not requests:
        st.info("No requests found.")
        return

    for request in requests:
        request_id = request["id"]
        request_status = str(request.get("status", "PENDING")).upper()
        request_mentee = {
            "required_skills": request.get("required_skills", ""),
            "learning_goals": request.get("learning_goals", ""),
            "skills": request.get("current_skills", ""),
        }
        request_match = calculate_match(request_mentee, mentor)
        st.markdown(
            f'''<div class="card" style="margin-bottom:.5rem"><div style="display:flex;justify-content:space-between;gap:.75rem"><div><h3 style="margin:0">{escape(str(request.get("mentee_name", "Mentee")))}</h3><div style="color:#8e9bad;font-size:.65rem">{escape(str(request.get("mentee_email", "")))}</div></div><div>{request_status_html(request_status)}</div></div><div style="margin-top:.6rem">{skills_html(request.get("current_skills"))}</div><div style="margin-top:.45rem;color:#aeb8c8;font-size:.65rem">Domain: {escape(str(request.get("current_domain", "Not specified")))} · Level: {escape(str(request.get("skill_level", "Not specified")))} · Match: {request_match["match_percentage"]:.1f}%</div><div style="margin-top:.35rem;color:#6f7b8e;font-size:.6rem">Goals: {skills_html(request.get("learning_goals"))}<br>Required: {skills_html(request.get("required_skills"))}<br>Created: {escape(str(request.get("created_at", "")))}</div></div>''',
            unsafe_allow_html=True,
        )
        accept_col, reject_col = st.columns(2)
        with accept_col:
            if st.button("Accept Request", key=f"accept_{request_id}", type="primary", use_container_width=True):
                result = accept_request(request_id, mentor_id)
                if isinstance(result, dict) and result.get("success") is False:
                    st.warning(result.get("message", "The request could not be accepted."))
                else:
                    st.session_state["mentor_dashboard_notice"] = "Request accepted and mentor capacity updated."
                    st.rerun()
        with reject_col:
            if st.button("Reject Request", key=f"reject_{request_id}", use_container_width=True):
                result = reject_request(request_id, mentor_id)
                if isinstance(result, dict) and result.get("success") is False:
                    st.warning(result.get("message", "The request could not be rejected."))
                else:
                    st.session_state["mentor_dashboard_notice"] = "Request rejected."
                    st.rerun()


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
