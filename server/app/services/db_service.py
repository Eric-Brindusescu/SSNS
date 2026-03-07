"""
SQLite database service for persisting SNOWTAM generation history.
"""
import json
import logging
import os
import sqlite3
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "snowtam_history.db")


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the generations table if it doesn't exist."""
    conn = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS generations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            speech_text TEXT,
            curated_text TEXT,
            default_parameters TEXT NOT NULL,
            extracted_parameters TEXT NOT NULL,
            generated_html TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    logger.info("SNOWTAM history database initialized at %s", DB_PATH)


def save_generation(
    speech_text: str,
    curated_text: str,
    default_parameters: dict,
    extracted_parameters: dict,
    generated_html: str,
) -> int:
    """Save a generation record and return its id."""
    conn = _get_connection()
    cursor = conn.execute(
        """
        INSERT INTO generations
            (created_at, speech_text, curated_text, default_parameters, extracted_parameters, generated_html)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now(timezone.utc).isoformat(),
            speech_text,
            curated_text,
            json.dumps(default_parameters, ensure_ascii=False),
            json.dumps(extracted_parameters, ensure_ascii=False),
            generated_html,
        ),
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    logger.info("Saved SNOWTAM generation #%d", row_id)
    return row_id


def get_all_generations() -> list[dict]:
    """Return all generations ordered by most recent first."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT id, created_at, speech_text, curated_text FROM generations ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_generation(generation_id: int) -> dict | None:
    """Return a single generation by id, or None if not found."""
    conn = _get_connection()
    row = conn.execute(
        "SELECT * FROM generations WHERE id = ?", (generation_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    result = dict(row)
    result["default_parameters"] = json.loads(result["default_parameters"])
    result["extracted_parameters"] = json.loads(result["extracted_parameters"])
    return result
