import os
from pathlib import Path
from html import escape

import streamlit as st
from dotenv import load_dotenv

from database.db import initialize_database
from database.queries import (
    get_database_stats,
    get_all_mentees,
    get_all_mentors,
    get_available_mentors,
    get_mentee,
    get_mentor,
    update_mentee_profile,
    update_mentor_profile,
    send_request,
    get_mentee_requests,
    get_mentor_requests,
    accept_request,
    reject_request,
    is_mentor_available,
)
from graph.workflow import run_matching_workflow

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
            "Mentor Profile",
            "Mentor Dashboard",
        ],
        label_visibility="visible",
    )

    st.divider()
    st.markdown("### Database")

    stats = get_database_stats()
    metric_card("Mentors", stats.get("mentors", 0))
    metric_card("Mentees", stats.get("mentees", 0))
    metric_card("Available Mentors", stats.get("available_mentors", 0))
    metric_card("Requests", stats.get("requests", 0))

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


# -------------------------------------------------------------------
# Home
# -------------------------------------------------------------------

def render_home():
    st.markdown(
        """
        <div class="hero">
            <div class="eyebrow">AI mentorship workspace</div>
            <h1>Find the right mentor.<br>Build the next version of you.</h1>
            <p>
                Connect with relevant mentors using explainable skill matching,
                lightweight retrieval and AI-generated recommendations.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

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

    if not mentees:
        st.warning("No mentee profiles are available in SQLite.")
        return

    options = {user_label(m): m["id"] for m in mentees}
    selected_label = st.selectbox("Select mentee", list(options.keys()), key="mentee_profile_select")
    mentee_id = options[selected_label]
    mentee = get_mentee(mentee_id)

    if not mentee:
        st.error("The selected mentee could not be loaded.")
        return

    current_skills = safe_list(mentee.get("skills"))
    goals = safe_list(mentee.get("learning_goals"))
    required = safe_list(mentee.get("required_skills"))

    with st.form("mentee_profile_form"):
        c1, c2 = st.columns(2)

        with c1:
            name = st.text_input("Name", value=str(mentee.get("name", "")))
            email = st.text_input("Email", value=str(mentee.get("email", "")))
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
            )

        with c2:
            skills = st.text_input(
                "Current Skills",
                value=", ".join(current_skills),
                help="Separate skills with commas.",
            )
            learning_goals = st.text_input(
                "Learning Goals",
                value=", ".join(goals),
                help="Separate goals with commas.",
            )
            required_skills = st.text_input(
                "Required Skills",
                value=", ".join(required),
                help="Separate required skills with commas.",
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

    current = safe_list(mentee.get("skills"))
    goals = safe_list(mentee.get("learning_goals"))
    required = safe_list(mentee.get("required_skills"))

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

        score = float(rec.get("final_score", rec.get("score", 0)))
        required_matches = rec.get("required_skill_matches", rec.get("matching_required_skills", []))
        goal_matches = rec.get("learning_goal_matches", rec.get("goal_matches", []))
        current_matches = rec.get("current_skill_matches", rec.get("matching_current_skills", []))
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

        st.markdown(
            f"""
            <div class="card" style="margin-bottom:1rem">
                <div style="display:flex;justify-content:space-between;gap:1rem;align-items:flex-start">
                    <div>
                        <div class="eyebrow">MENTOR {idx + 1:02d}</div>
                        <h2 style="margin:.1rem 0 .2rem">{escape(display_name(mentor))}</h2>
                        <div style="color:#8e9bad">{escape(str(mentor.get("email", "")))}</div>
                    </div>
                    <div style="text-align:right">
                        <div class="score">{score:.1f}%</div>
                        <div class="score-caption">application-generated match indicator</div>
                    </div>
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
            unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(
                f'<div class="card"><div class="mini-label">Required Skill Matches</div><div style="margin-top:.5rem">{skills_html(required_matches)}</div></div>',
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f'<div class="card"><div class="mini-label">Learning Goal Matches</div><div style="margin-top:.5rem">{skills_html(goal_matches)}</div></div>',
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                f'<div class="card"><div class="mini-label">Current Skill Context</div><div style="margin-top:.5rem">{skills_html(current_matches)}</div></div>',
                unsafe_allow_html=True,
            )

        with st.expander("Why this mentor?"):
            st.markdown(
                f'<div class="explanation">{escape(str(explanation))}</div>',
                unsafe_allow_html=True,
            )

        if available:
            if st.button(
                f"Send Request → {display_name(mentor)}",
                key=f"send_request_{mentee_id}_{mentor_id}_{idx}",
                type="primary",
                use_container_width=True,
            ):
                try:
                    result = send_request(mentee_id, mentor_id)
                    if isinstance(result, dict) and result.get("success") is False:
                        st.warning(result.get("message", "The request could not be sent."))
                    else:
                        st.success("Mentorship request sent successfully.")
                    st.rerun()
                except Exception as exc:
                    st.error("The mentorship request could not be sent.")
                    st.exception(exc)
        else:
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


# -------------------------------------------------------------------
# Mentor Profile
# -------------------------------------------------------------------

def render_mentor_profile():
    st.markdown('<div class="eyebrow">MENTOR WORKSPACE</div>', unsafe_allow_html=True)
    st.title("Mentor Profile")
    st.caption("Manage your expertise, profile information and mentoring capacity.")

    mentors = get_all_mentors()

    if not mentors:
        st.warning("No mentor profiles are available.")
        return

    options = {user_label(m): m["id"] for m in mentors}
    selected_label = st.selectbox("Select mentor", list(options.keys()), key="mentor_profile_select")
    mentor_id = options[selected_label]
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

    mentors = get_all_mentors()

    if not mentors:
        st.warning("No mentors are available.")
        return

    options = {user_label(m): m["id"] for m in mentors}
    selected_label = st.selectbox("Select mentor", list(options.keys()), key="mentor_dashboard_select")
    mentor_id = options[selected_label]
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

    requests = get_mentor_requests(mentor_id)

    st.markdown('<div class="section-title">Mentorship Requests</div>', unsafe_allow_html=True)

    if not requests:
        st.info("No mentorship requests for this mentor.")
        return

    for request in requests:
        status = str(request.get("status", "PENDING")).upper()
        mentee_name = request.get("mentee_name", "Mentee")
        mentee_email = request.get("mentee_email", "")

        st.markdown(
            f"""
            <div class="card" style="margin-bottom:.75rem">
                <div style="display:flex;justify-content:space-between;gap:1rem">
                    <div>
                        <h3 style="margin:0">{escape(str(mentee_name))}</h3>
                        <div style="color:#8e9bad;margin-top:.2rem">{escape(str(mentee_email))}</div>
                    </div>
                    <div>{request_status_html(status)}</div>
                </div>
                <div style="margin-top:.6rem;color:#6f7b8e;font-size:.75rem">
                    Created: {escape(str(request.get("created_at", "")))}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
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
                        result = accept_request(request["id"])
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
                        result = reject_request(request["id"])
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
    elif page == "Mentor Profile":
        render_mentor_profile()
    elif page == "Mentor Dashboard":
        render_mentor_dashboard()
except Exception as exc:
    st.error("Something unexpected happened while rendering this page.")
    st.exception(exc)
