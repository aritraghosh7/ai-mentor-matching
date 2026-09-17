"""
Application database queries and business rules.

The LLM is never used here.

Business rules are controlled by SQLite and Python:

- Mentor availability
- Request creation
- Duplicate request prevention
- Request acceptance
- Request rejection
- Capacity updates
"""

from __future__ import annotations

import hashlib
import sqlite3

from database.db import get_connection


# ============================================================
# PASSWORD VERIFICATION
# ============================================================

def verify_password(
    password: str,
    stored_hash: str,
) -> bool:
    """
    Verify PBKDF2 password hash.
    """

    if not password or not stored_hash:
        return False

    try:

        salt, expected_hash = (
            stored_hash.split("$", 1)
        )

        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100_000,
        ).hex()

        return actual_hash == expected_hash

    except Exception:

        return False


# ============================================================
# MENTOR AUTHENTICATION
# ============================================================

def authenticate_mentor(
    email: str,
    password: str,
):
    """
    Authenticate a mentor.

    Returns mentor information if successful,
    otherwise None.
    """

    connection = get_connection()

    try:

        mentor = connection.execute(
            """
            SELECT
                u.id AS user_id,
                u.name,
                u.email,

                mp.id AS mentor_profile_id,
                mp.domain,
                mp.skills,
                mp.expertise,
                mp.experience,
                mp.bio,
                mp.max_mentees,
                mp.current_mentees,

                ma.password_hash

            FROM users u

            INNER JOIN mentor_profiles mp
                ON u.id = mp.user_id

            INNER JOIN mentor_auth ma
                ON u.id = ma.user_id

            WHERE LOWER(u.email) = LOWER(?)
              AND u.role = 'MENTOR'

            LIMIT 1
            """,
            (email.strip(),),
        ).fetchone()

        if mentor is None:

            return None

        if not verify_password(
            password,
            mentor["password_hash"],
        ):

            return None

        return dict(mentor)

    finally:

        connection.close()


# ============================================================
# CREATE / UPDATE MENTEE
# ============================================================

def create_or_update_mentee(
    name: str,
    email: str,
    current_domain: str,
    current_skills: str,
    skill_level: str,
    learning_goals: str,
    required_skills: str,
) -> int:
    """
    Create or update a mentee profile.

    The same email updates the existing mentee.

    Mentor accounts cannot be converted into mentees.
    """

    name = name.strip()
    email = email.strip().lower()

    if not name:
        raise ValueError(
            "Name is required."
        )

    if not email:
        raise ValueError(
            "Email is required."
        )

    if not required_skills.strip():
        raise ValueError(
            "At least one required skill is required."
        )

    valid_levels = {
        "Beginner",
        "Intermediate",
        "Advanced",
    }

    if skill_level not in valid_levels:
        raise ValueError(
            "Invalid skill level."
        )

    connection = get_connection()

    try:

        connection.execute(
            "BEGIN"
        )

        existing = connection.execute(
            """
            SELECT id, role
            FROM users

            WHERE LOWER(email) = LOWER(?)

            LIMIT 1
            """,
            (email,),
        ).fetchone()

        if existing:

            if existing["role"] == "MENTOR":

                raise ValueError(
                    "This email belongs to a mentor account."
                )

            user_id = int(
                existing["id"]
            )

            connection.execute(
                """
                UPDATE users

                SET name = ?

                WHERE id = ?
                """,
                (
                    name,
                    user_id,
                ),
            )

        else:

            cursor = connection.execute(
                """
                INSERT INTO users (
                    name,
                    email,
                    role
                )
                VALUES (?, ?, 'MENTEE')
                """,
                (
                    name,
                    email,
                ),
            )

            user_id = int(
                cursor.lastrowid
            )

        profile = connection.execute(
            """
            SELECT id
            FROM mentee_profiles

            WHERE user_id = ?

            LIMIT 1
            """,
            (user_id,),
        ).fetchone()

        if profile:

            connection.execute(
                """
                UPDATE mentee_profiles

                SET
                    current_domain = ?,
                    current_skills = ?,
                    skill_level = ?,
                    learning_goals = ?,
                    required_skills = ?

                WHERE user_id = ?
                """,
                (
                    current_domain.strip(),
                    current_skills.strip(),
                    skill_level,
                    learning_goals.strip(),
                    required_skills.strip(),
                    user_id,
                ),
            )

        else:

            connection.execute(
                """
                INSERT INTO mentee_profiles (
                    user_id,
                    current_domain,
                    current_skills,
                    skill_level,
                    learning_goals,
                    required_skills
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    current_domain.strip(),
                    current_skills.strip(),
                    skill_level,
                    learning_goals.strip(),
                    required_skills.strip(),
                ),
            )

        connection.commit()

        return user_id

    except Exception:

        connection.rollback()

        raise

    finally:

        connection.close()


# ============================================================
# GET MENTEE
# ============================================================

def get_mentee_by_user_id(
    user_id: int,
):
    """
    Retrieve a mentee profile.
    """

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT
                u.id AS user_id,
                u.name,
                u.email,

                mp.current_domain,
                mp.current_skills,
                mp.skill_level,
                mp.learning_goals,
                mp.required_skills

            FROM users u

            INNER JOIN mentee_profiles mp
                ON u.id = mp.user_id

            WHERE u.id = ?
              AND u.role = 'MENTEE'

            LIMIT 1
            """,
            (user_id,),
        ).fetchone()

        return dict(row) if row else None

    finally:

        connection.close()


# ============================================================
# GET ALL MENTORS
# ============================================================

def get_all_mentors():
    """
    Retrieve all mentor profiles.

    This becomes the RAG knowledge base.
    """

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT
                u.id AS user_id,
                u.name,
                u.email,

                mp.id AS mentor_profile_id,
                mp.domain,
                mp.skills,
                mp.expertise,
                mp.experience,
                mp.bio,
                mp.max_mentees,
                mp.current_mentees

            FROM users u

            INNER JOIN mentor_profiles mp
                ON u.id = mp.user_id

            WHERE u.role = 'MENTOR'

            ORDER BY u.name
            """
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        connection.close()


# ============================================================
# GET MENTOR
# ============================================================

def get_mentor_by_user_id(
    user_id: int,
):
    """
    Retrieve a mentor profile.
    """

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT
                u.id AS user_id,
                u.name,
                u.email,

                mp.id AS mentor_profile_id,
                mp.domain,
                mp.skills,
                mp.expertise,
                mp.experience,
                mp.bio,
                mp.max_mentees,
                mp.current_mentees

            FROM users u

            INNER JOIN mentor_profiles mp
                ON u.id = mp.user_id

            WHERE u.id = ?
              AND u.role = 'MENTOR'

            LIMIT 1
            """,
            (user_id,),
        ).fetchone()

        return dict(row) if row else None

    finally:

        connection.close()


# ============================================================
# UPDATE MENTOR PROFILE
# ============================================================

def update_mentor_profile(
    user_id: int,
    name: str,
    email: str,
    domain: str,
    skills: str,
    expertise: str,
    experience: int,
    bio: str,
    max_mentees: int,
) -> dict:
    """
    Update a mentor's profile.

    Current mentees cannot exceed the new maximum capacity.
    """

    name = name.strip()
    email = email.strip().lower()

    if not name:
        return {
            "success": False,
            "message": "Name is required.",
        }

    if not email:
        return {
            "success": False,
            "message": "Email is required.",
        }

    if experience < 0:
        return {
            "success": False,
            "message": "Experience cannot be negative.",
        }

    if max_mentees <= 0:
        return {
            "success": False,
            "message": "Maximum capacity must be greater than zero.",
        }

    connection = get_connection()

    try:

        connection.execute(
            "BEGIN IMMEDIATE"
        )

        mentor = connection.execute(
            """
            SELECT
                mp.current_mentees

            FROM users u

            INNER JOIN mentor_profiles mp
                ON u.id = mp.user_id

            WHERE u.id = ?
              AND u.role = 'MENTOR'

            LIMIT 1
            """,
            (user_id,),
        ).fetchone()

        if mentor is None:

            connection.rollback()

            return {
                "success": False,
                "message": "Mentor not found.",
            }

        current_mentees = int(
            mentor["current_mentees"]
        )

        if max_mentees < current_mentees:

            connection.rollback()

            return {
                "success": False,
                "message": (
                    f"Maximum capacity cannot be "
                    f"less than current mentees "
                    f"({current_mentees})."
                ),
            }

        email_owner = connection.execute(
            """
            SELECT id
            FROM users

            WHERE LOWER(email) = LOWER(?)
              AND id != ?

            LIMIT 1
            """,
            (
                email,
                user_id,
            ),
        ).fetchone()

        if email_owner:

            connection.rollback()

            return {
                "success": False,
                "message": (
                    "That email address is already "
                    "being used by another account."
                ),
            }

        connection.execute(
            """
            UPDATE users

            SET
                name = ?,
                email = ?

            WHERE id = ?
              AND role = 'MENTOR'
            """,
            (
                name,
                email,
                user_id,
            ),
        )

        connection.execute(
            """
            UPDATE mentor_profiles

            SET
                domain = ?,
                skills = ?,
                expertise = ?,
                experience = ?,
                bio = ?,
                max_mentees = ?

            WHERE user_id = ?
            """,
            (
                domain.strip(),
                skills.strip(),
                expertise.strip(),
                int(experience),
                bio.strip(),
                int(max_mentees),
                user_id,
            ),
        )

        connection.commit()

        return {
            "success": True,
            "message": "Profile updated successfully.",
        }

    except sqlite3.IntegrityError:

        connection.rollback()

        return {
            "success": False,
            "message": "That email is already in use.",
        }

    except Exception as error:

        connection.rollback()

        return {
            "success": False,
            "message": f"Profile update failed: {error}",
        }

    finally:

        connection.close()


# ============================================================
# AVAILABILITY
# ============================================================

def is_mentor_available(
    mentor_user_id: int,
) -> bool:
    """
    Determine availability.

    EXACT RULE:

        current_mentees < max_mentees
    """

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT
                current_mentees,
                max_mentees

            FROM mentor_profiles

            WHERE user_id = ?

            LIMIT 1
            """,
            (mentor_user_id,),
        ).fetchone()

        if row is None:

            return False

        return (
            row["current_mentees"]
            < row["max_mentees"]
        )

    finally:

        connection.close()


# ============================================================
# ACTIVE REQUEST CHECK
# ============================================================

def has_existing_request(
    mentee_id: int,
    mentor_id: int,
) -> bool:
    """
    Check for PENDING or ACCEPTED request.
    """

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT id

            FROM mentorship_requests

            WHERE mentee_id = ?
              AND mentor_id = ?

              AND status IN (
                  'PENDING',
                  'ACCEPTED'
              )

            LIMIT 1
            """,
            (
                mentee_id,
                mentor_id,
            ),
        ).fetchone()

        return row is not None

    finally:

        connection.close()


# ============================================================
# CREATE REQUEST
# ============================================================

def create_request(
    mentee_id: int,
    mentor_id: int,
) -> dict:
    """
    Create a pending mentorship request.

    Capacity is checked inside a transaction.
    """

    connection = get_connection()

    try:

        connection.execute(
            "BEGIN IMMEDIATE"
        )

        mentee = connection.execute(
            """
            SELECT id
            FROM users

            WHERE id = ?
              AND role = 'MENTEE'

            LIMIT 1
            """,
            (mentee_id,),
        ).fetchone()

        if mentee is None:

            connection.rollback()

            return {
                "success": False,
                "message": "Mentee not found.",
            }

        mentor = connection.execute(
            """
            SELECT
                user_id,
                current_mentees,
                max_mentees

            FROM mentor_profiles

            WHERE user_id = ?

            LIMIT 1
            """,
            (mentor_id,),
        ).fetchone()

        if mentor is None:

            connection.rollback()

            return {
                "success": False,
                "message": "Mentor not found.",
            }

        if (
            mentor["current_mentees"]
            >= mentor["max_mentees"]
        ):

            connection.rollback()

            return {
                "success": False,
                "message": (
                    "This mentor is currently full."
                ),
            }

        existing = connection.execute(
            """
            SELECT id

            FROM mentorship_requests

            WHERE mentee_id = ?
              AND mentor_id = ?

              AND status IN (
                  'PENDING',
                  'ACCEPTED'
              )

            LIMIT 1
            """,
            (
                mentee_id,
                mentor_id,
            ),
        ).fetchone()

        if existing:

            connection.rollback()

            return {
                "success": False,
                "message": (
                    "You already have an active "
                    "request with this mentor."
                ),
            }

        connection.execute(
            """
            INSERT INTO mentorship_requests (
                mentee_id,
                mentor_id,
                status
            )
            VALUES (?, ?, 'PENDING')
            """,
            (
                mentee_id,
                mentor_id,
            ),
        )

        connection.commit()

        return {
            "success": True,
            "message": "Mentorship request sent.",
        }

    except sqlite3.IntegrityError:

        connection.rollback()

        return {
            "success": False,
            "message": (
                "An active request already exists."
            ),
        }

    except Exception as error:

        connection.rollback()

        return {
            "success": False,
            "message": (
                f"Could not create request: {error}"
            ),
        }

    finally:

        connection.close()


# ============================================================
# MENTEE REQUESTS
# ============================================================

def get_requests_for_mentee(
    mentee_id: int,
):
    """
    Get all requests created by a mentee.
    """

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT
                mr.id AS request_id,
                mr.status,
                mr.created_at,
                mr.updated_at,

                u.name AS mentor_name,
                u.email AS mentor_email,

                mp.domain,
                mp.skills,
                mp.expertise,
                mp.experience,
                mp.max_mentees,
                mp.current_mentees

            FROM mentorship_requests mr

            INNER JOIN users u
                ON mr.mentor_id = u.id

            INNER JOIN mentor_profiles mp
                ON u.id = mp.user_id

            WHERE mr.mentee_id = ?

            ORDER BY mr.created_at DESC
            """,
            (mentee_id,),
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        connection.close()


# ============================================================
# MENTOR PENDING REQUESTS
# ============================================================

def get_pending_requests_for_mentor(
    mentor_id: int,
):
    """
    Get pending requests for a mentor.
    """

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT
                mr.id AS request_id,
                mr.status,
                mr.created_at,

                u.id AS mentee_id,
                u.name AS mentee_name,
                u.email AS mentee_email,

                mp.current_domain,
                mp.current_skills,
                mp.skill_level,
                mp.learning_goals,
                mp.required_skills

            FROM mentorship_requests mr

            INNER JOIN users u
                ON mr.mentee_id = u.id

            INNER JOIN mentee_profiles mp
                ON u.id = mp.user_id

            WHERE mr.mentor_id = ?
              AND mr.status = 'PENDING'

            ORDER BY mr.created_at ASC
            """,
            (mentor_id,),
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        connection.close()


# ============================================================
# MENTOR REQUEST HISTORY
# ============================================================

def get_requests_for_mentor(
    mentor_id: int,
):
    """
    Get all requests received by a mentor.
    """

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT
                mr.id AS request_id,
                mr.status,
                mr.created_at,
                mr.updated_at,

                u.name AS mentee_name,
                u.email AS mentee_email,

                mp.current_domain,
                mp.current_skills,
                mp.skill_level,
                mp.learning_goals,
                mp.required_skills

            FROM mentorship_requests mr

            INNER JOIN users u
                ON mr.mentee_id = u.id

            INNER JOIN mentee_profiles mp
                ON u.id = mp.user_id

            WHERE mr.mentor_id = ?

            ORDER BY mr.created_at DESC
            """,
            (mentor_id,),
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        connection.close()


# ============================================================
# ACCEPT REQUEST
# ============================================================

def accept_request(
    request_id: int,
    mentor_id: int,
) -> dict:
    """
    Accept a mentorship request safely.

    Transaction:

        BEGIN IMMEDIATE

        Check request is PENDING.

        Check current capacity.

        Increment current_mentees.

        Change request to ACCEPTED.

        COMMIT.
    """

    connection = get_connection()

    try:

        connection.execute(
            "BEGIN IMMEDIATE"
        )

        request = connection.execute(
            """
            SELECT
                id,
                mentee_id,
                mentor_id,
                status

            FROM mentorship_requests

            WHERE id = ?
              AND mentor_id = ?

            LIMIT 1
            """,
            (
                request_id,
                mentor_id,
            ),
        ).fetchone()

        if request is None:

            connection.rollback()

            return {
                "success": False,
                "message": "Request not found.",
            }

        if request["status"] != "PENDING":

            connection.rollback()

            return {
                "success": False,
                "message": (
                    "This request has already been processed."
                ),
            }

        mentor = connection.execute(
            """
            SELECT
                current_mentees,
                max_mentees

            FROM mentor_profiles

            WHERE user_id = ?

            LIMIT 1
            """,
            (mentor_id,),
        ).fetchone()

        if mentor is None:

            connection.rollback()

            return {
                "success": False,
                "message": "Mentor profile not found.",
            }

        if (
            mentor["current_mentees"]
            >= mentor["max_mentees"]
        ):

            connection.rollback()

            return {
                "success": False,
                "message": (
                    "Cannot accept request because "
                    "mentor capacity is full."
                ),
            }

        update = connection.execute(
            """
            UPDATE mentor_profiles

            SET current_mentees =
                current_mentees + 1

            WHERE user_id = ?

              AND current_mentees < max_mentees
            """,
            (mentor_id,),
        )

        if update.rowcount != 1:

            connection.rollback()

            return {
                "success": False,
                "message": (
                    "Capacity changed before acceptance."
                ),
            }

        connection.execute(
            """
            UPDATE mentorship_requests

            SET
                status = 'ACCEPTED',
                updated_at = CURRENT_TIMESTAMP

            WHERE id = ?
              AND status = 'PENDING'
            """,
            (request_id,),
        )

        connection.commit()

        return {
            "success": True,
            "message": (
                "Mentorship request accepted."
            ),
        }

    except Exception as error:

        connection.rollback()

        return {
            "success": False,
            "message": (
                f"Could not accept request: {error}"
            ),
        }

    finally:

        connection.close()


# ============================================================
# REJECT REQUEST
# ============================================================

def reject_request(
    request_id: int,
    mentor_id: int,
) -> dict:
    """
    Reject a pending request.

    Capacity does not change.
    """

    connection = get_connection()

    try:

        result = connection.execute(
            """
            UPDATE mentorship_requests

            SET
                status = 'REJECTED',
                updated_at = CURRENT_TIMESTAMP

            WHERE id = ?
              AND mentor_id = ?
              AND status = 'PENDING'
            """,
            (
                request_id,
                mentor_id,
            ),
        )

        connection.commit()

        if result.rowcount == 0:

            return {
                "success": False,
                "message": (
                    "Request could not be rejected."
                ),
            }

        return {
            "success": True,
            "message": (
                "Mentorship request rejected."
            ),
        }

    except Exception as error:

        connection.rollback()

        return {
            "success": False,
            "message": (
                f"Could not reject request: {error}"
            ),
        }

    finally:

        connection.close()