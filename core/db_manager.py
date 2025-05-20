"""
Core database interaction module.

This module manages SQLite connections, initializes the database schema, and provides CRUD
operations for OAuth tokens and core tables.
"""
import sqlite3
import logging
from typing import Optional, Any

from core.config import settings

# Initialize logger for this module
logger = logging.getLogger(__name__)


def get_db_connection() -> sqlite3.Connection:
    """Get a SQLite database connection with row factory configured.

    Returns:
        sqlite3.Connection: SQLite connection object.

    Raises:
        sqlite3.Error: If connection to the database fails.
    """
    try:
        conn = sqlite3.connect(
            settings.sqlite_db_path, detect_types=sqlite3.PARSE_DECLTYPES
        )
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logger.error(
            "Failed to connect to SQLite database at %s: %s",
            settings.sqlite_db_path,
            e,
        )
        raise


def initialize_database(conn: sqlite3.Connection) -> None:
    """Create necessary tables if they do not already exist.

    Args:
        conn: SQLite database connection.

    Raises:
        sqlite3.Error: If schema creation fails.
    """
    try:
        cursor = conn.cursor()
        # OAuth tokens table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS x_oauth_tokens (
                user_x_id TEXT PRIMARY KEY,
                access_token TEXT NOT NULL,
                refresh_token TEXT,
                expires_at TEXT NOT NULL,
                scopes TEXT
            )
            """
        )
        # Task queue table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS task_queue (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT NOT NULL,
                payload TEXT,
                status TEXT NOT NULL DEFAULT 'pending'
            )
            """
        )
        # Agent state table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_state (
                state_key TEXT PRIMARY KEY,
                state_value TEXT,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Human review queue table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS human_review_queue (
                review_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_queue_id INTEGER,
                task_type TEXT NOT NULL,
                reason_for_review TEXT,
                data_for_review TEXT,
                status TEXT NOT NULL DEFAULT 'pending_review',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TEXT
            )
            """
        )
        conn.commit()
    except sqlite3.Error as e:
        logger.error("Failed to initialize database schema: %s", e)
        raise


def save_oauth_tokens(
    user_x_id: str,
    access_token: str,
    refresh_token: Optional[str],
    expires_at: str,
    scopes: str,
) -> None:
    """Insert or update OAuth tokens for a user in the database.

    Args:
        user_x_id: X user identifier.
        access_token: Encrypted access token.
        refresh_token: Encrypted refresh token.
        expires_at: Expiration timestamp in ISO format.
        scopes: Space-separated scopes string.

    Raises:
        sqlite3.Error: If the database operation fails.
    """
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO x_oauth_tokens
                (user_x_id, access_token, refresh_token, expires_at, scopes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_x_id, access_token, refresh_token, expires_at, scopes),
            )
    except sqlite3.Error as e:
        logger.error(
            "Failed to save OAuth tokens for user %s: %s", user_x_id, e
        )
        raise
    finally:
        conn.close()


def get_oauth_tokens(user_x_id: str) -> Optional[sqlite3.Row]:
    """Retrieve OAuth tokens for a user from the database.

    Args:
        user_x_id: X user identifier.

    Returns:
        sqlite3.Row or None: Row with token data or None if not found.

    Raises:
        sqlite3.Error: If the database operation fails.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT user_x_id, access_token, refresh_token, expires_at, scopes
            FROM x_oauth_tokens
            WHERE user_x_id = ?
            """,
            (user_x_id,),
        )
        return cursor.fetchone()
    except sqlite3.Error as e:
        logger.error(
            "Failed to get OAuth tokens for user %s: %s", user_x_id, e
        )
        raise
    finally:
        conn.close()


def save_agent_state(state_key: str, state_value: str) -> None:
    """Insert or update an agent state key-value pair in the database.

    Args:
        state_key: The key for the state entry.
        state_value: The value to store.

    Raises:
        sqlite3.Error: If the database operation fails.
    """
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO agent_state (state_key, state_value, last_updated)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                """,
                (state_key, state_value),
            )
    except sqlite3.Error as e:
        logger.error("Failed to save agent state for key %s: %s", state_key, e)
        raise
    finally:
        conn.close()


def get_agent_state(state_key: str) -> Optional[str]:
    """Retrieve the value for the given agent state key from the database.

    Args:
        state_key: The key of the state entry.

    Returns:
        The state value if found, otherwise None.

    Raises:
        sqlite3.Error: If the database operation fails.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT state_value FROM agent_state WHERE state_key = ?
            """,
            (state_key,),
        )
        row = cursor.fetchone()
        return row["state_value"] if row else None
    except sqlite3.Error as e:
        logger.error("Failed to retrieve agent state for key %s: %s", state_key, e)
        raise
    finally:
        conn.close()


def save_human_review_item(
    task_type: str,
    data_payload_json: str,
    reason_for_review: str,
    initial_status: str = "pending_review",
) -> int:
    """Insert a new item into the human_review_queue for human review.

    Args:
        task_type: The type of task requiring review.
        data_payload_json: JSON-serialized payload for review.
        reason_for_review: A text explanation for why review is needed.
        initial_status: Review request status, defaults to 'pending_review'.

    Returns:
        The review_id of the newly created review request.

    Raises:
        sqlite3.Error: If the database operation fails.
    """
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO human_review_queue (
                    task_queue_id,
                    task_type,
                    reason_for_review,
                    data_for_review,
                    status
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (None, task_type, reason_for_review, data_payload_json, initial_status),
            )
            return cursor.lastrowid
    except sqlite3.Error as e:
        logger.error("Failed to save human review item: %s", e)
        raise
    finally:
        conn.close()


# -------------------------------------------------------------------------
# Functions for processing approved replies from human_review_queue
# -------------------------------------------------------------------------
def get_approved_reply_tasks() -> list[dict[str, Any]]:
    """Get tasks from human_review_queue with status 'approved' for reply_to_mention."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT review_id, data_for_review
            FROM human_review_queue
            WHERE status = 'approved' AND task_type = 'reply_to_mention'
            """
        )
        rows = cursor.fetchall()
        tasks: list[dict[str, Any]] = []
        for row in rows:
            tasks.append({
                "review_id": row["review_id"],
                "data_for_review": row["data_for_review"]
            })
        return tasks
    except sqlite3.Error as e:
        logger.error("Failed to fetch approved reply tasks: %s", e)
        raise
    finally:
        conn.close()

def update_human_review_status(review_id: int, new_status: str) -> None:
    """Update the status of a human review task and set reviewed_at timestamp."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                """
                UPDATE human_review_queue
                SET status = ?, reviewed_at = CURRENT_TIMESTAMP
                WHERE review_id = ?
                """,
                (new_status, review_id),
            )
    except sqlite3.Error as e:
        logger.error("Failed to update human review status for review_id %s: %s", review_id, e)
        raise
    finally:
        conn.close()