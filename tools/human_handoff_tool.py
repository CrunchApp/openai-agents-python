"""Tool to request human review by inserting entries into human_review_queue."""

import logging
from typing import Any, Dict
import json

from agents import function_tool
from core.db_manager import save_human_review_item
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Define strict Pydantic model for human handoff payload
class DraftedReplyData(BaseModel):
    draft_reply_text: str
    original_mention_id: str
    status: str

# Define Pydantic model for strategic direction request
class StrategicDirectionData(BaseModel):
    situation_analysis: str
    proposed_actions: list[str]
    uncertainty_reason: str

def _request_human_review_impl(
    task_type: str, data_for_review: DraftedReplyData, reason: str
) -> Dict[str, Any]:
    """Request human review by creating an entry in the human_review_queue.

    Args:
        task_type: The type of task requiring review.
        data_for_review: A DraftedReplyData model instance containing draft_reply_text, original_mention_id, and status.
        reason: The reason why human review is requested.

    Returns:
        A dict with the review status and review request ID.

    Raises:
        Exception: If saving the review request to the database fails.
    """
    logger.info("Requesting human review for task '%s': %s", task_type, reason)
    try:
        payload_json = data_for_review.model_dump_json()
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


@function_tool
def request_human_review(
    task_type: str, data_for_review: DraftedReplyData, reason: str
) -> Dict[str, Any]:
    """Request human review by creating an entry in the human_review_queue.

    Args:
        task_type: The type of task requiring review.
        data_for_review: A DraftedReplyData model instance containing draft_reply_text, original_mention_id, and status.
        reason: The reason why human review is requested.

    Returns:
        A dict with the review status and review request ID.

    Raises:
        Exception: If saving the review request to the database fails.
    """
    return _request_human_review_impl(task_type, data_for_review, reason)


def _request_strategic_direction_impl(
    situation_analysis: str, proposed_actions: list[str], uncertainty_reason: str
) -> Dict[str, Any]:
    """Request strategic direction from human by creating an entry in the human_review_queue.

    Args:
        situation_analysis: The agent's analysis of the current situation.
        proposed_actions: List of potential actions the agent is considering.
        uncertainty_reason: Why the agent is uncertain about which action to take.

    Returns:
        A dict with the review status and review request ID.

    Raises:
        Exception: If saving the strategic direction request to the database fails.
    """
    logger.info("Requesting strategic direction: %s", uncertainty_reason)
    try:
        strategic_data = StrategicDirectionData(
            situation_analysis=situation_analysis,
            proposed_actions=proposed_actions,
            uncertainty_reason=uncertainty_reason
        )
        payload_json = strategic_data.model_dump_json()
        review_id = save_human_review_item(
            task_type="strategic_direction",
            data_payload_json=payload_json,
            reason_for_review=uncertainty_reason,
            initial_status="pending_direction",
        )
        return {"status": "pending_strategic_direction", "review_request_id": review_id}
    except Exception as e:
        logger.error("Failed to request strategic direction: %s", e)
        raise


@function_tool
def request_strategic_direction(
    situation_analysis: str, proposed_actions: list[str], uncertainty_reason: str
) -> Dict[str, Any]:
    """Request strategic direction from human when agent is uncertain about next action.

    Args:
        situation_analysis: The agent's analysis of the current situation.
        proposed_actions: List of potential actions the agent is considering (2-3 options).
        uncertainty_reason: Why the agent is uncertain about which action to take.

    Returns:
        A dict with the review status and review request ID.

    Raises:
        Exception: If saving the strategic direction request to the database fails.
    """
    return _request_strategic_direction_impl(situation_analysis, proposed_actions, uncertainty_reason)
