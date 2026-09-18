"""Deterministic mentor matching engine.

The displayed match percentage combines required skills, learning goals and
current-skill context. The LLM does not calculate this score.
"""

from __future__ import annotations

import re
from typing import Any


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_skill(
    skill: Any,
) -> str:
    """
    Normalize a skill phrase.
    """

    if skill is None:

        return ""

    value = str(skill).lower().strip()

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    value = re.sub(
        r"[^a-z0-9+#.\-/ ]+",
        " ",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


# ============================================================
# SPLIT SKILLS
# ============================================================

def split_skills(
    value: Any,
    split_space: bool = False,
) -> list[str]:
    """
    Split skill strings.

    Supports:

        comma
        semicolon
        pipe
        newline
    """

    if value is None:

        return []

    raw_value = str(value)
    parts = re.split(r"[,;|\n]+", raw_value)

    if split_space and len(parts) == 1 and " " in raw_value.strip():
        parts = raw_value.split()

    skills = []

    for part in parts:

        normalized = normalize_skill(
            part
        )

        if normalized:

            skills.append(
                normalized
            )

    return list(
        dict.fromkeys(skills)
    )


def category_match(
    mentee_skills: list[str],
    mentor_skills: set[str],
) -> tuple[float, list[str], list[str]]:
    """Calculate an exact matched-items percentage for one category."""

    if not mentee_skills:
        return 0.0, [], []

    matched = []
    missing = []
    for mentee_skill in mentee_skills:
        if mentee_skill in mentor_skills:
            matched.append(mentee_skill)
        else:
            missing.append(mentee_skill)

    percentage = len(matched) / len(mentee_skills) * 100
    return percentage, matched, missing


# ============================================================
# MATCH CALCULATION
# ============================================================

def calculate_match(
    mentee: dict[str, Any],
    mentor: dict[str, Any],
) -> dict[str, Any]:
    """Calculate the weighted exact-match score.

    Required skills = 60%, learning goals = 30%, current skills = 10%.
    Each category uses matched items divided by total items in that category.
    """

    required_skills = split_skills(
        mentee.get(
            "required_skills",
            "",
        ),
        split_space=True,
    )

    mentor_skills = split_skills(
        mentor.get(
            "skills",
            "",
        )
    )

    mentor_expertise = split_skills(
        mentor.get(
            "expertise",
            "",
        )
    )

    mentor_skill_set = set(
        mentor_skills
        + mentor_expertise
    )

    learning_goals = split_skills(
        mentee.get("learning_goals", ""),
    )
    current_skills = split_skills(
        mentee.get("skills", mentee.get("current_skills", "")),
        split_space=True,
    )

    required_percentage, matched, missing = category_match(
        required_skills,
        mentor_skill_set,
    )
    goal_percentage, matched_goals, missing_goals = category_match(
        learning_goals,
        mentor_skill_set,
    )
    current_percentage, matched_current, missing_current = category_match(
        current_skills,
        mentor_skill_set,
    )

    percentage = (
        required_percentage * 0.60
        + goal_percentage * 0.30
        + current_percentage * 0.10
    )

    return {
        "match_percentage": round(percentage, 1),
        "matched_skills": matched,
        "missing_skills": missing,
        "matched_goals": matched_goals,
        "missing_goals": missing_goals,
        "matched_current_skills": matched_current,
        "missing_current_skills": missing_current,
        "required_match_percentage": round(required_percentage, 1),
        "learning_goal_match_percentage": round(goal_percentage, 1),
        "current_skill_match_percentage": round(current_percentage, 1),
        "total_required_skills": len(required_skills),
        "matched_required_skills": len(matched),
    }


# ============================================================
# RANK MENTORS
# ============================================================

def rank_mentors(
    mentee: dict[str, Any],
    mentors: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Calculate matching information for retrieved mentors.

    Ranking priority:

        1. Match percentage
        2. Number of matched skills
        3. Retrieval score
        4. Experience

    Availability is NOT used to manipulate the match score.
    """

    results = []

    for mentor in mentors:

        match = calculate_match(
            mentee,
            mentor,
        )

        result = {
            "mentor": mentor,
            **match,
            "retrieval_score": mentor.get(
                "retrieval_score",
                0,
            ),
        }

        results.append(
            result
        )

    results.sort(
        key=lambda item: (
            item["match_percentage"],
            item["matched_required_skills"],
            item["retrieval_score"],
            item["mentor"].get(
                "experience",
                0,
            ),
        ),
        reverse=True,
    )

    return results