"""
Deterministic mentor matching engine.

The displayed match percentage is based primarily on:

    matched required skills
    -----------------------
    total required skills

The LLM does not calculate this score.
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

    parts = re.split(
        r"[,;|\n]+",
        str(value),
    )

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


# ============================================================
# MATCH CALCULATION
# ============================================================

def calculate_match(
    mentee: dict[str, Any],
    mentor: dict[str, Any],
) -> dict[str, Any]:
    """
    Calculate deterministic skill matching.

    Formula:

        matched required skills
        ----------------------- x 100
        total required skills

    Required skills are compared against the mentor's
    skills and expertise.
    """

    required_skills = split_skills(
        mentee.get(
            "required_skills",
            "",
        )
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

    matched = []

    missing = []

    for required in required_skills:

        if required in mentor_skill_set:

            matched.append(
                required
            )

        else:

            missing.append(
                required
            )

    total = len(
        required_skills
    )

    if total == 0:

        percentage = 0.0

    else:

        percentage = (
            len(matched)
            / total
            * 100
        )

    return {
        "match_percentage": round(
            percentage,
            1,
        ),
        "matched_skills": matched,
        "missing_skills": missing,
        "total_required_skills": total,
        "matched_required_skills": len(
            matched
        ),
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