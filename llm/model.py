"""
LangChain LLM integration.

The LLM is optional.

If LLM configuration is missing or the API call fails,
a deterministic fallback explanation is returned.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from llm.prompts import (
    build_match_explanation_prompt,
)


load_dotenv()


# ============================================================
# LLM CONFIGURATION
# ============================================================

def llm_is_configured() -> bool:
    """
    Check whether the required LLM configuration exists.
    """

    api_key = os.getenv(
        "LLM_API_KEY",
        "",
    ).strip()

    model = os.getenv(
        "LLM_MODEL",
        "",
    ).strip()

    return bool(
        api_key
        and model
        and api_key != "your_api_key_here"
        and model != "your_model_name_here"
    )


# ============================================================
# CREATE LLM
# ============================================================

def get_llm():
    """
    Create a LangChain ChatOpenAI instance.

    Supports OpenAI-compatible providers through
    an optional base URL.
    """

    if not llm_is_configured():

        return None

    api_key = os.getenv(
        "LLM_API_KEY"
    ).strip()

    model = os.getenv(
        "LLM_MODEL"
    ).strip()

    base_url = os.getenv(
        "LLM_BASE_URL",
        "",
    ).strip()

    kwargs = {
        "model": model,
        "api_key": api_key,
        "temperature": 0.2,
    }

    if base_url:

        kwargs["base_url"] = base_url

    return ChatOpenAI(
        **kwargs
    )


# ============================================================
# FALLBACK EXPLANATION
# ============================================================

def fallback_explanation(
    mentee: dict,
    recommendation: dict,
) -> str:
    """
    Generate a deterministic explanation when the LLM
    is unavailable.
    """

    mentor = recommendation["mentor"]

    matched = recommendation.get(
        "matched_skills",
        [],
    )

    missing = recommendation.get(
        "missing_skills",
        [],
    )

    mentor_name = mentor.get(
        "name",
        "This mentor",
    )

    expertise = mentor.get(
        "expertise",
        "",
    )

    experience = mentor.get(
        "experience",
        0,
    )

    if matched:

        skill_text = ", ".join(
            matched
        )

        explanation = (
            f"{mentor_name} is relevant because "
            f"their profile matches the required "
            f"skill(s): {skill_text}. "
        )

    else:

        explanation = (
            f"{mentor_name} was retrieved because "
            f"their profile contains relevant "
            f"domain or goal information. "
        )

    if expertise:

        explanation += (
            f"Their expertise includes "
            f"{expertise}. "
        )

    if experience:

        explanation += (
            f"They have {experience} years "
            f"of experience."
        )

    if missing:

        explanation += (
            f" Skills not found in the mentor "
            f"profile include: "
            f"{', '.join(missing)}."
        )

    return explanation


# ============================================================
# GENERATE EXPLANATION
# ============================================================

def generate_match_explanation(
    mentee: dict,
    recommendation: dict,
) -> str:
    """
    Generate an explanation using LangChain + LLM.

    Falls back to deterministic explanation if
    configuration/API is unavailable.
    """

    prompt = build_match_explanation_prompt(
        mentee,
        recommendation,
    )

    try:

        llm = get_llm()

        if llm is None:

            return fallback_explanation(
                mentee,
                recommendation,
            )

        response = llm.invoke(
            prompt
        )

        content = getattr(
            response,
            "content",
            "",
        )

        if isinstance(
            content,
            list,
        ):

            content = " ".join(
                str(item)
                for item in content
            )

        content = str(
            content
        ).strip()

        if not content:

            return fallback_explanation(
                mentee,
                recommendation,
            )

        return content

    except Exception:

        return fallback_explanation(
            mentee,
            recommendation,
        )