import pytest

from tools.human_handoff_tool import DraftedReplyData, request_human_review


def test_request_human_review_success(mocker):
    """Test that request_human_review calls save_human_review_item and returns correct response."""
    task = "taskA"
    # Use Pydantic model for data payload
    data_dict = {"draft_reply_text": "foo text", "original_mention_id": "123", "status": "pending"}
    data_model = DraftedReplyData(**data_dict)
    reason = "Needs human attention"
    mock_review_id = 42

    # Patch save_human_review_item in the human_handoff_tool module
    mock_save = mocker.patch(
        "tools.human_handoff_tool.save_human_review_item",
        return_value=mock_review_id,
    )

    result = request_human_review(task, data_model, reason)

    # Verify model_dump_json() was applied
    expected_payload = data_model.model_dump_json()
    mock_save.assert_called_once_with(
        task_type=task,
        data_payload_json=expected_payload,
        reason_for_review=reason,
        initial_status="pending_review",
    )

    # Verify the returned dictionary
    assert result == {
        "status": "pending_human_review",
        "review_request_id": mock_review_id,
    }


def test_request_human_review_failure(mocker):
    """Test that request_human_review propagates exceptions from save_human_review_item."""
    task = "taskB"
    # Use Pydantic model for data payload
    data_dict = {
        "draft_reply_text": "error text",
        "original_mention_id": "456",
        "status": "pending",
    }
    data_model = DraftedReplyData(**data_dict)
    reason = "Error scenario"

    # Patch save_human_review_item to raise an exception
    mocker.patch(
        "tools.human_handoff_tool.save_human_review_item",
        side_effect=Exception("db fail"),
    )

    with pytest.raises(Exception) as excinfo:
        request_human_review(task, data_model, reason)
    assert "db fail" in str(excinfo.value)
