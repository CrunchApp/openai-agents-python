import sys
import os

# Add the project root directory to the Python path
# This assumes the script is in 'project_root/scripts/'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


import argparse
import logging

from core.config import settings
from core.db_manager import get_db_connection, update_human_review_status

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


def manual_approve(review_id: int) -> None:
    """Manually approves a human review task by updating its status to 'approved'."""
    logger.info(f"Attempting to approve review task with ID: {review_id}")
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Optional: Check if the task exists first
        cursor.execute("SELECT 1 FROM human_review_queue WHERE review_id = ?", (review_id,))
        if cursor.fetchone() is None:
            logger.warning(f"Review task with ID {review_id} not found.")
            print(f"Error: Review task with ID {review_id} not found.")
            return

        update_human_review_status(review_id, "approved")
        logger.info(f"Successfully approved review task with ID: {review_id}")
        print(f"Review task with ID {review_id} successfully approved.")
    except Exception as e:
        logger.error(f"Failed to approve review task with ID {review_id}: {e}")
        print(f"Error approving review task with ID {review_id}: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Manually approve a human review task by updating its status in the database."
    )
    parser.add_argument("review_id", type=int, help="The ID of the human review task to approve.")

    args = parser.parse_args()

    # Ensure the database path is configured
    if not settings.sqlite_db_path:
        logger.error("Database path not configured. Ensure SQLITE_DB_PATH is set in .env")
        print("Error: Database path not configured. Ensure SQLITE_DB_PATH is set in .env")
    else:
        manual_approve(args.review_id)
