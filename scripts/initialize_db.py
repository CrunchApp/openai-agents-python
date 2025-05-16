"""Temporary script to initialize the SQLite database schema.

This script creates all necessary tables in the database for initial setup.
"""

import sys

from core.db_manager import get_db_connection, initialize_database


def main() -> None:
    """Initialize the database schema by creating required tables."""
    try:
        conn = get_db_connection()
        initialize_database(conn)
        conn.close()
        print("Database schema initialized successfully.")
    except Exception as e:
        print(f"Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 