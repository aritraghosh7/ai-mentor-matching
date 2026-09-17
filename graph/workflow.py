"""
LangGraph orchestration for mentor matching.

Workflow:

START
  ↓
Receive Mentee Requirements
  ↓
Retrieve Mentor Profiles
  ↓
Calculate Skill Matches
  ↓
Check Mentor Capacity
  ↓
Filter Available Mentors
  ↓
Generate AI Explanations
  ↓
Return Recommendations
  ↓
END
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import (
    END,
    START,
    StateGraph,
)

from database.queries import (
    get_mentor_by_user_id,
)
from llm.model import (
    generate_match_explanation,
)
from matching.matcher import (
    rank_mentors,
)
from rag.retriever import (
    retrieve_relevant_mentors,
)

from graph.state import MatchingState


# ============================================================
# RETRIEVE
# ============================================================

def retrieve_node(
    state: MatchingState,
) -> dict[str, Any]:
    """
    Retrieve relevant mentors from the mentor knowledge base.
    """

    mentee = state[
        "mentee_requirements"
    ]

    mentors = retrieve_relevant_mentors(
        mentee,
        top_k=20,
    )

    return {
        "retrieved_mentors": mentors,
    }


# ============================================================
# MATCH
# ============================================================

def match_node(
    state: MatchingState,
) -> dict[str, Any]:
    """
    Calculate deterministic skill matches.
    """

    mentee = state[
        "mentee_requirements"
    ]

    mentors = state.get(
        "retrieved_mentors",
        [],
    )

    matched = rank_mentors(
        mentee,
        mentors,
    )

    return {
        "matched_mentors": matched,
    }


# ============================================================
# CAPACITY
# ============================================================

def capacity_node(
    state: MatchingState,
) -> dict[str, Any]:
    """
    Refresh mentor data from SQLite and calculate
    real-time availability.
    """

    updated_matches = []

    for item in state.get(
        "matched_mentors",
        [],
    ):

        mentor = item[
            "mentor"
        ]

        fresh_mentor = (
            get_mentor_by_user_id(
                mentor["user_id"]
            )
        )

        if fresh_mentor is None:

            item["available"] = False

            item["capacity_error"] = True

            updated_matches.append(
                item
            )

            continue

        item["mentor"] = fresh_mentor

        current = int(
            fresh_mentor[
                "current_mentees"
            ]
        )

        maximum = int(
            fresh_mentor[
                "max_mentees"
            ]
        )

        item["available"] = (
            current < maximum
        )

        item["remaining_slots"] = max(
            0,
            maximum - current,
        )

        item["capacity_text"] = (
            f"{current} / {maximum}"
        )

        updated_matches.append(
            item
        )

    return {
        "matched_mentors": updated_matches,
    }


# ============================================================
# FILTER AVAILABLE
# ============================================================

def filter_available_node(
    state: MatchingState,
) -> dict[str, Any]:
    """
    Filter mentors according to the deterministic
    capacity rule.
    """

    available = [
        item
        for item in state.get(
            "matched_mentors",
            [],
        )
        if item.get(
            "available",
            False,
        )
    ]

    return {
        "available_mentors": available,
    }


# ============================================================
# EXPLANATIONS
# ============================================================

def explanation_node(
    state: MatchingState,
) -> dict[str, Any]:
    """
    Generate explanations for the top recommendations.

    The explanation is generated after matching and
    capacity information have already been calculated.
    """

    mentee = state[
        "mentee_requirements"
    ]

    matches = state.get(
        "matched_mentors",
        [],
    )

    explanations = {}

    # Limit LLM calls for a responsive MVP.
    for item in matches[:10]:

        mentor = item["mentor"]

        explanation = (
            generate_match_explanation(
                mentee,
                item,
            )
        )

        explanations[
            mentor["user_id"]
        ] = explanation

    return {
        "explanations": explanations,
    }


# ============================================================
# FINALIZE
# ============================================================

def recommendation_node(
    state: MatchingState,
) -> dict[str, Any]:
    """
    Build the final recommendation list.
    """

    explanations = state.get(
        "explanations",
        {},
    )

    recommendations = []

    for item in state.get(
        "matched_mentors",
        [],
    ):

        recommendation = dict(
            item
        )

        mentor = recommendation[
            "mentor"
        ]

        recommendation[
            "explanation"
        ] = explanations.get(
            mentor["user_id"],
            (
                "This mentor was retrieved "
                "as relevant based on the "
                "mentor knowledge base."
            ),
        )

        recommendations.append(
            recommendation
        )

    return {
        "recommendations": recommendations,
    }


# ============================================================
# BUILD GRAPH
# ============================================================

def build_matching_graph():
    """
    Build and compile the LangGraph workflow.
    """

    graph = StateGraph(
        MatchingState
    )

    graph.add_node(
        "retrieve",
        retrieve_node,
    )

    graph.add_node(
        "match",
        match_node,
    )

    graph.add_node(
        "capacity",
        capacity_node,
    )

    graph.add_node(
        "filter_available",
        filter_available_node,
    )

    graph.add_node(
        "explanations",
        explanation_node,
    )

    graph.add_node(
        "recommendations",
        recommendation_node,
    )

    graph.add_edge(
        START,
        "retrieve",
    )

    graph.add_edge(
        "retrieve",
        "match",
    )

    graph.add_edge(
        "match",
        "capacity",
    )

    graph.add_edge(
        "capacity",
        "filter_available",
    )

    graph.add_edge(
        "filter_available",
        "explanations",
    )

    graph.add_edge(
        "explanations",
        "recommendations",
    )

    graph.add_edge(
        "recommendations",
        END,
    )

    return graph.compile()


# ============================================================
# SINGLE COMPILED GRAPH
# ============================================================

matching_graph = build_matching_graph()