"""Tool to request human review by inserting entries into human_review_queue."""

import logging
import json
from typing import Dict, Any

from core.db_manager import save_human_review_item

logger = logging.getLogger(__name__)


def request_human_review(
    task_type: str, data_for_review: Dict[str, Any], reason: str
) -> Dict[str, Any]:
    """Request human review by creating an entry in the human_review_queue.

    Args:
        task_type: The type of task requiring review.
        data_for_review: The data payload that needs human review.
        reason: The reason why human review is requested.

    Returns:
        A dict with the review status and review request ID.

    Raises:
        Exception: If saving the review request to the database fails.
    """
    logger.info("Requesting human review for task '%s': %s", task_type, reason)
    try:
        payload_json = json.dumps(data_for_review)
        review_id = save_human_review_item(
            task_type=task_type,
            data_payload_json=payload_json,
            reason_for_review=reason,
            initial_status="pending_review",
        )
        return {"status": "pending_human_review", "review_request_id": review_id}
    except Exception as e:
        logger.error("Failed to request human review: %s", e)
        raise 