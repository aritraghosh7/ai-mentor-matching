"""
Lightweight deterministic RAG retrieval.

This implementation intentionally does NOT use:

- embeddings
- FAISS
- Pinecone
- Chroma
- Weaviate
- vector similarity
- vector databases

Instead, mentor profiles stored in SQLite are treated
as the knowledge base.

The mentee requirements become the retrieval query.

The retriever searches mentor profile information using
normalized skill phrases, keywords, domain, expertise and bio.
"""

from __future__ import annotations

import re
from typing import Any

from database.queries import get_all_mentors


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(
    text: Any,
) -> str:
    """
    Normalize text for matching.

    Keeps:
        letters
        numbers
        #
        +
        .
        -

    This helps preserve technical skills such as:

        C#
        C++
        .NET
        Node.js
    """

    if text is None:

        return ""

    value = str(text).lower().strip()

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
# SPLIT SKILL PHRASES
# ============================================================

def split_phrases(
    text: Any,
) -> list[str]:
    """
    Split comma/semicolon/pipe/newline-separated
    skills while preserving multi-word phrases.
    """

    if text is None:

        return []

    raw = str(text)

    parts = re.split(
        r"[,;|\n]+",
        raw,
    )

    result = []

    for part in parts:

        normalized = normalize_text(
            part
        )

        if normalized:

            result.append(
                normalized
            )

    return list(
        dict.fromkeys(result)
    )


# ============================================================
# TOKEN EXTRACTION
# ============================================================

STOP_WORDS = {
    "and",
    "or",
    "the",
    "a",
    "an",
    "to",
    "of",
    "in",
    "for",
    "with",
    "on",
    "my",
    "me",
    "learn",
    "learning",
    "want",
    "need",
    "needs",
    "from",
    "how",
    "be",
    "become",
    "using",
}


def extract_keywords(
    text: Any,
) -> list[str]:
    """
    Extract useful individual keywords.
    """

    normalized = normalize_text(
        text
    )

    tokens = re.findall(
        r"[a-z0-9+#.]+",
        normalized,
    )

    keywords = []

    for token in tokens:

        if len(token) < 2:
            continue

        if token in STOP_WORDS:
            continue

        keywords.append(token)

    return list(
        dict.fromkeys(keywords)
    )


# ============================================================
# SAFE PHRASE MATCHING
# ============================================================

def phrase_in_text(
    phrase: str,
    text: str,
) -> bool:
    """
    Check whether a phrase occurs as a meaningful
    phrase rather than as a substring.

    Example:

        sql

    should NOT match:

        nosql
    """

    phrase = normalize_text(
        phrase
    )

    text = normalize_text(
        text
    )

    if not phrase or not text:
        return False

    pattern = (
        r"(?<![a-z0-9])"
        + re.escape(phrase)
        + r"(?![a-z0-9])"
    )

    return bool(
        re.search(
            pattern,
            text,
        )
    )


# ============================================================
# MENTOR SEARCH DOCUMENT
# ============================================================

def build_mentor_document(
    mentor: dict[str, Any],
) -> str:
    """
    Build the searchable mentor knowledge document.
    """

    return normalize_text(
        " ".join(
            [
                str(
                    mentor.get(
                        "domain",
                        "",
                    )
                ),
                str(
                    mentor.get(
                        "skills",
                        "",
                    )
                ),
                str(
                    mentor.get(
                        "expertise",
                        "",
                    )
                ),
                str(
                    mentor.get(
                        "bio",
                        "",
                    )
                ),
            ]
        )
    )


# ============================================================
# RETRIEVAL SCORE
# ============================================================

def calculate_retrieval_score(
    mentee: dict[str, Any],
    mentor: dict[str, Any],
) -> tuple[float, list[str]]:
    """
    Calculate a lightweight retrieval relevance score.

    Retrieval priorities:

        Required skill exact match  -> high weight
        Current skill exact match   -> medium weight
        Goal keyword match          -> secondary
        Domain match                -> secondary

    This is NOT the final match percentage.
    """

    mentor_document = build_mentor_document(
        mentor
    )

    mentor_skill_text = normalize_text(
        mentor.get(
            "skills",
            "",
        )
    )

    mentor_expertise_text = normalize_text(
        mentor.get(
            "expertise",
            "",
        )
    )

    mentor_domain_text = normalize_text(
        mentor.get(
            "domain",
            "",
        )
    )

    mentor_skill_phrases = (
        split_phrases(
            mentor.get(
                "skills",
                "",
            )
        )
    )

    mentor_expertise_phrases = (
        split_phrases(
            mentor.get(
                "expertise",
                "",
            )
        )
    )

    required_skills = split_phrases(
        mentee.get(
            "required_skills",
            "",
        )
    )

    current_skills = split_phrases(
        mentee.get(
            "current_skills",
            "",
        )
    )

    goals = extract_keywords(
        mentee.get(
            "learning_goals",
            "",
        )
    )

    domain_keywords = extract_keywords(
        mentee.get(
            "current_domain",
            "",
        )
    )

    score = 0.0

    matched_terms = []

    # --------------------------------------------------------
    # REQUIRED SKILLS
    # --------------------------------------------------------

    for skill in required_skills:

        if (
            skill in mentor_skill_phrases
            or skill in mentor_expertise_phrases
            or phrase_in_text(
                skill,
                mentor_skill_text,
            )
            or phrase_in_text(
                skill,
                mentor_expertise_text,
            )
        ):

            score += 5

            matched_terms.append(
                skill
            )

    # --------------------------------------------------------
    # CURRENT SKILLS
    # --------------------------------------------------------

    for skill in current_skills:

        if (
            skill in mentor_skill_phrases
            or skill in mentor_expertise_phrases
        ):

            score += 2

            if skill not in matched_terms:

                matched_terms.append(
                    skill
                )

    # --------------------------------------------------------
    # LEARNING GOALS
    # --------------------------------------------------------

    for keyword in goals:

        if phrase_in_text(
            keyword,
            mentor_document,
        ):

            score += 0.5

            if keyword not in matched_terms:

                matched_terms.append(
                    keyword
                )

    # --------------------------------------------------------
    # DOMAIN
    # --------------------------------------------------------

    for keyword in domain_keywords:

        if phrase_in_text(
            keyword,
            mentor_domain_text,
        ):

            score += 1

    return (
        score,
        matched_terms,
    )


# ============================================================
# RAG RETRIEVAL
# ============================================================

def retrieve_relevant_mentors(
    mentee: dict[str, Any],
    top_k: int = 20,
) -> list[dict[str, Any]]:
    """
    Retrieve relevant mentors from SQLite.

    The returned mentors become the context for
    the matching stage.
    """

    mentors = get_all_mentors()

    results = []

    for mentor in mentors:

        score, terms = (
            calculate_retrieval_score(
                mentee,
                mentor,
            )
        )

        if score <= 0:
            continue

        mentor_copy = dict(
            mentor
        )

        mentor_copy[
            "retrieval_score"
        ] = round(
            score,
            2,
        )

        mentor_copy[
            "retrieved_terms"
        ] = terms

        results.append(
            mentor_copy
        )

    results.sort(
        key=lambda item: (
            item["retrieval_score"],
            item.get(
                "experience",
                0,
            ),
        ),
        reverse=True,
    )

    return results[:top_k]