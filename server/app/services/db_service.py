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
            airport_code TEXT NOT NULL,
            operator_code TEXT NOT NULL,
            speech_text TEXT,
            curated_text TEXT,
            default_parameters TEXT NOT NULL,
            extracted_parameters TEXT NOT NULL,
            generated_html TEXT NOT NULL,
            weather_data TEXT
        )
    """)
    conn.commit()
    conn.close()
    logger.info("SNOWTAM history database initialized at %s", DB_PATH)


def save_generation(
    airport_code: str,
    operator_code: str,
    speech_text: str,
    curated_text: str,
    default_parameters: dict,
    extracted_parameters: dict,
    generated_html: str,
    weather_data: list | None = None,
) -> int:
    """Save a generation record and return its id."""
    conn = _get_connection()
    cursor = conn.execute(
        """
        INSERT INTO generations
            (created_at, airport_code, operator_code, speech_text, curated_text,
             default_parameters, extracted_parameters, generated_html, weather_data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now(timezone.utc).isoformat(),
            airport_code,
            operator_code,
            speech_text,
            curated_text,
            json.dumps(default_parameters, ensure_ascii=False),
            json.dumps(extracted_parameters, ensure_ascii=False),
            generated_html,
            json.dumps(weather_data, ensure_ascii=False) if weather_data else None,
        ),
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    logger.info("Saved SNOWTAM generation #%d", row_id)
    return row_id


def get_all_generations(
    airport_code: str | None = None,
    operator_code: str | None = None,
) -> list[dict]:
    """Return all generations ordered by most recent first, optionally filtered."""
    query = (
        "SELECT id, created_at, airport_code, operator_code, speech_text, curated_text "
        "FROM generations"
    )
    conditions = []
    params = []
    if airport_code:
        conditions.append("airport_code = ?")
        params.append(airport_code)
    if operator_code:
        conditions.append("operator_code = ?")
        params.append(operator_code)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY id DESC"
    conn = _get_connection()
    rows = conn.execute(query, params).fetchall()
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
    if result.get("weather_data"):
        result["weather_data"] = json.loads(result["weather_data"])
    return result
