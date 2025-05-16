import logging
import pytest

from agents.content_creation_agent import ContentCreationAgent


def test_draft_reply_structure_and_logging(caplog):
    """Test that draft_reply returns correct structure and logs appropriately."""
    caplog.set_level(logging.INFO)
    agent = ContentCreationAgent()
    original_text = (
        "This is a sample tweet that mentions the agent for help!"
    )
    author = "testuser"
    tweet_id = "12345"
    result = agent.draft_reply(original_text, author, tweet_id)

    # Check that an info log was created with the correct message
    assert any(
        record.levelname == "INFO" and
        f"Drafting reply to tweet ID {tweet_id} from author @{author}" in record.getMessage()
        for record in caplog.records
    )

    # Verify the result is a dict with expected keys
    assert isinstance(result, dict)
    assert set(result.keys()) == {
        "draft_reply_text",
        "original_mention_id",
        "status",
    }

    # Verify the values in the result
    assert result["original_mention_id"] == tweet_id
    assert result["status"] == "drafted_for_review"
    # Placeholder text should include author mention and part of the original text
    draft_text = result["draft_reply_text"]
    assert draft_text.startswith(f"Thank you @{author}")
    # Ensure the first 30 characters of the original text appear in the draft
    assert original_text[:30] in draft_text 