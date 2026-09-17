"""
Mentor authentication and Streamlit session management.
"""

from __future__ import annotations

import streamlit as st

from database.queries import authenticate_mentor


# ============================================================
# LOGIN
# ============================================================

def login_mentor(
    email: str,
    password: str,
) -> bool:
    """
    Authenticate a mentor and store login information
    in Streamlit session state.
    """

    mentor = authenticate_mentor(
        email,
        password,
    )

    if mentor is None:

        return False

    st.session_state["mentor_logged_in"] = True

    st.session_state["mentor_user_id"] = (
        mentor["user_id"]
    )

    st.session_state["mentor_name"] = (
        mentor["name"]
    )

    st.session_state["mentor_email"] = (
        mentor["email"]
    )

    return True


# ============================================================
# LOGOUT
# ============================================================

def logout_mentor() -> None:
    """
    Log out the current mentor.
    """

    st.session_state["mentor_logged_in"] = False

    st.session_state.pop(
        "mentor_user_id",
        None,
    )

    st.session_state.pop(
        "mentor_name",
        None,
    )

    st.session_state.pop(
        "mentor_email",
        None,
    )


# ============================================================
# LOGIN STATUS
# ============================================================

def is_mentor_logged_in() -> bool:
    """
    Return whether a mentor is logged in.
    """

    return bool(
        st.session_state.get(
            "mentor_logged_in",
            False,
        )
    )


# ============================================================
# CURRENT MENTOR
# ============================================================

def get_logged_in_mentor_id():
    """
    Return logged-in mentor user ID.
    """

    return st.session_state.get(
        "mentor_user_id"
    )