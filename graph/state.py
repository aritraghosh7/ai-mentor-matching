"""
LangGraph state definition.
"""

from __future__ import annotations

from typing import Any, TypedDict


class MatchingState(TypedDict, total=False):
    """
    State passed through the mentor matching workflow.
    """

    mentee_requirements: dict[str, Any]

    retrieved_mentors: list[dict[str, Any]]

    matched_mentors: list[dict[str, Any]]

    available_mentors: list[dict[str, Any]]

    recommendations: list[dict[str, Any]]

    explanations: dict[int, str]