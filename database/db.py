"""
Database initialization and mentor dataset seeding.

SQLite is the source of truth for:

- Mentor profiles
- Mentee profiles
- Authentication
- Mentorship requests
- Mentor capacity

The mentor CSV is imported into SQLite.

Mentee data is entered through the Streamlit application.
"""

from __future__ import annotations

import csv
import hashlib
import secrets
import sqlite3
from pathlib import Path
from typing import Any


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "mentor_matching.db"

DATA_DIR = BASE_DIR / "data"

MENTORS_CSV = DATA_DIR / "mentors_400.csv"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection() -> sqlite3.Connection:
    """
    Create a SQLite database connection.
    """

    connection = sqlite3.connect(
        DB_PATH,
        timeout=30,
        check_same_thread=False,
    )

    connection.row_factory = sqlite3.Row

    connection.execute(
        "PRAGMA foreign_keys = ON;"
    )

    connection.execute(
        "PRAGMA busy_timeout = 30000;"
    )

    return connection


# ============================================================
# PASSWORD HASHING
# ============================================================

def hash_password(password: str) -> str:
    """
    Hash a password using PBKDF2-HMAC-SHA256.

    Returns:
        salt$hash
    """

    if not password:
        raise ValueError(
            "Password cannot be empty."
        )

    salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    ).hex()

    return f"{salt}${password_hash}"


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db() -> None:
    """
    Create the application database and tables.
    """

    connection = get_connection()

    try:

        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                name TEXT NOT NULL,

                email TEXT NOT NULL UNIQUE COLLATE NOCASE,

                role TEXT NOT NULL
                    CHECK (
                        role IN ('MENTEE', 'MENTOR')
                    )
            );


            CREATE TABLE IF NOT EXISTS mentee_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER NOT NULL UNIQUE,

                current_domain TEXT NOT NULL DEFAULT '',

                current_skills TEXT NOT NULL DEFAULT '',

                skill_level TEXT NOT NULL DEFAULT 'Intermediate',

                learning_goals TEXT NOT NULL DEFAULT '',

                required_skills TEXT NOT NULL DEFAULT '',

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            );


            CREATE TABLE IF NOT EXISTS mentor_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER NOT NULL UNIQUE,

                domain TEXT NOT NULL DEFAULT '',

                skills TEXT NOT NULL DEFAULT '',

                expertise TEXT NOT NULL DEFAULT '',

                experience INTEGER NOT NULL DEFAULT 0,

                bio TEXT NOT NULL DEFAULT '',

                max_mentees INTEGER NOT NULL DEFAULT 1,

                current_mentees INTEGER NOT NULL DEFAULT 0,

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,

                CHECK (experience >= 0),

                CHECK (max_mentees > 0),

                CHECK (current_mentees >= 0),

                CHECK (
                    current_mentees <= max_mentees
                )
            );


            CREATE TABLE IF NOT EXISTS mentor_auth (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER NOT NULL UNIQUE,

                password_hash TEXT NOT NULL,

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            );


            CREATE TABLE IF NOT EXISTS mentorship_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                mentee_id INTEGER NOT NULL,

                mentor_id INTEGER NOT NULL,

                status TEXT NOT NULL DEFAULT 'PENDING'
                    CHECK (
                        status IN (
                            'PENDING',
                            'ACCEPTED',
                            'REJECTED'
                        )
                    ),

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                updated_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (mentee_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (mentor_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,

                CHECK (
                    mentee_id != mentor_id
                )
            );


            CREATE INDEX IF NOT EXISTS idx_users_role
            ON users(role);


            CREATE INDEX IF NOT EXISTS idx_mentee_user
            ON mentee_profiles(user_id);


            CREATE INDEX IF NOT EXISTS idx_mentor_user
            ON mentor_profiles(user_id);


            CREATE INDEX IF NOT EXISTS idx_request_mentee
            ON mentorship_requests(mentee_id);


            CREATE INDEX IF NOT EXISTS idx_request_mentor
            ON mentorship_requests(mentor_id);


            CREATE INDEX IF NOT EXISTS idx_request_status
            ON mentorship_requests(status);


            CREATE UNIQUE INDEX IF NOT EXISTS
            uq_active_mentorship_request

            ON mentorship_requests(
                mentee_id,
                mentor_id
            )

            WHERE status IN (
                'PENDING',
                'ACCEPTED'
            );
            """
        )

        connection.commit()

    finally:

        connection.close()


# ============================================================
# CSV HELPERS
# ============================================================

def _clean(value: Any) -> str:
    """
    Safely convert a value to a stripped string.
    """

    if value is None:
        return ""

    return str(value).strip()


def _to_int(
    value: Any,
    default: int = 0,
) -> int:
    """
    Safely convert a value to integer.
    """

    try:

        return int(
            float(
                str(value).strip()
            )
        )

    except (
        ValueError,
        TypeError,
    ):

        return default


def _read_mentor_csv() -> list[dict[str, str]]:
    """
    Read mentors_400.csv.
    """

    if not MENTORS_CSV.exists():

        raise FileNotFoundError(
            "Mentor dataset not found.\n\n"
            f"Expected file:\n{MENTORS_CSV}"
        )

    mentors = []

    with MENTORS_CSV.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        if not reader.fieldnames:

            raise ValueError(
                "Mentor CSV does not contain headers."
            )

        for row in reader:

            cleaned = {
                _clean(key): _clean(value)
                for key, value in row.items()
                if key is not None
            }

            if any(cleaned.values()):

                mentors.append(cleaned)

    return mentors


# ============================================================
# FIND USER
# ============================================================

def _find_user_by_email(
    connection: sqlite3.Connection,
    email: str,
):
    """
    Find user by case-insensitive email.
    """

    return connection.execute(
        """
        SELECT *
        FROM users
        WHERE LOWER(email) = LOWER(?)
        LIMIT 1
        """,
        (email.strip(),),
    ).fetchone()


# ============================================================
# CREATE USER
# ============================================================

def _create_user(
    connection: sqlite3.Connection,
    name: str,
    email: str,
    role: str,
) -> int:
    """
    Create a user and return user ID.
    """

    name = name.strip()
    email = email.strip().lower()
    role = role.strip().upper()

    if not name:
        raise ValueError(
            "Name cannot be empty."
        )

    if not email:
        raise ValueError(
            "Email cannot be empty."
        )

    if role not in {
        "MENTEE",
        "MENTOR",
    }:

        raise ValueError(
            "Invalid role."
        )

    cursor = connection.execute(
        """
        INSERT INTO users (
            name,
            email,
            role
        )
        VALUES (?, ?, ?)
        """,
        (
            name,
            email,
            role,
        ),
    )

    return int(cursor.lastrowid)


# ============================================================
# SEED MENTORS
# ============================================================

def seed_mentors_from_csv() -> int:
    """
    Import mentors from mentors_400.csv.

    Each mentor receives the demo password:

        Mentor@123

    Only the password hash is stored.

    Existing mentors are not duplicated.

    Returns:
        Number of newly inserted mentors.
    """

    mentors = _read_mentor_csv()

    connection = get_connection()

    inserted = 0

    try:

        for row in mentors:

            name = _clean(
                row.get("name")
            )

            email = _clean(
                row.get("email")
            ).lower()

            if not name or not email:
                continue

            existing = _find_user_by_email(
                connection,
                email,
            )

            if existing:

                # Never silently convert another
                # type of account into a mentor.
                continue

            user_id = _create_user(
                connection,
                name,
                email,
                "MENTOR",
            )

            experience = max(
                0,
                _to_int(
                    row.get("experience_years"),
                    0,
                ),
            )

            max_mentees = max(
                1,
                _to_int(
                    row.get("max_mentees"),
                    1,
                ),
            )

            current_mentees = max(
                0,
                _to_int(
                    row.get("current_mentees"),
                    0,
                ),
            )

            current_mentees = min(
                current_mentees,
                max_mentees,
            )

            connection.execute(
                """
                INSERT INTO mentor_profiles (
                    user_id,
                    domain,
                    skills,
                    expertise,
                    experience,
                    bio,
                    max_mentees,
                    current_mentees
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    _clean(
                        row.get("domain")
                    ),
                    _clean(
                        row.get("skills")
                    ),
                    _clean(
                        row.get("expertise")
                    ),
                    experience,
                    _clean(
                        row.get("bio")
                    ),
                    max_mentees,
                    current_mentees,
                ),
            )

            password_hash = hash_password(
                "Mentor@123"
            )

            connection.execute(
                """
                INSERT INTO mentor_auth (
                    user_id,
                    password_hash
                )
                VALUES (?, ?)
                """,
                (
                    user_id,
                    password_hash,
                ),
            )

            inserted += 1

        connection.commit()

    except Exception:

        connection.rollback()

        raise

    finally:

        connection.close()

    return inserted


# ============================================================
# SINGLE PUBLIC SEED FUNCTION
# ============================================================

def seed_from_csv() -> dict[str, int]:
    """
    Initialize the database and import mentor data.

    Mentees are intentionally NOT imported.
    """

    init_db()

    inserted = seed_mentors_from_csv()

    return {
        "mentors_inserted": inserted,
    }

def initialize_database():
    """
    Intialize the SQLite databse and load the CSV datasets,
    Safe to call when the app starts.
    """
    init_db()
    seed_from_csv()
    return True
# ============================================================
# DATABASE STATISTICS
# ============================================================

def get_database_stats() -> dict[str, int]:
    """
    Return database statistics.
    """

    connection = get_connection()

    try:

        users = connection.execute(
            """
            SELECT COUNT(*)
            FROM users
            """
        ).fetchone()[0]

        mentors = connection.execute(
            """
            SELECT COUNT(*)
            FROM mentor_profiles
            """
        ).fetchone()[0]

        mentees = connection.execute(
            """
            SELECT COUNT(*)
            FROM mentee_profiles
            """
        ).fetchone()[0]

        available = connection.execute(
            """
            SELECT COUNT(*)
            FROM mentor_profiles

            WHERE current_mentees < max_mentees
            """
        ).fetchone()[0]

        requests = connection.execute(
            """
            SELECT COUNT(*)
            FROM mentorship_requests
            WHERE status = 'PENDING'
            """
        ).fetchone()[0]

        enrolled = connection.execute(
            """
            SELECT COUNT(*)
            FROM mentorship_requests
            WHERE status = 'ACCEPTED'
            """
        ).fetchone()[0]

        return {
            "users": int(users),
            "mentors": int(mentors),
            "mentees": int(mentees),
            "available_mentors": int(available),
            "requests": int(requests),
            "enrolled": int(enrolled),
        }

    finally:

        connection.close()


# ============================================================
# COMMAND LINE
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("AI MENTOR-MENTEE MATCHING SYSTEM")
    print("DATABASE INITIALIZATION")
    print("=" * 60)

    init_db()

    print("\nDatabase initialized.")

    result = seed_from_csv()

    print(
        f"New mentors imported: "
        f"{result['mentors_inserted']}"
    )

    print("\nDatabase statistics:")

    stats = get_database_stats()

    for key, value in stats.items():

        print(
            f"{key}: {value}"
        )

    print("\nDatabase ready.")