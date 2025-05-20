import logging

import pytest

from project_agents.orchestrator_agent import OrchestratorAgent
from tools.human_handoff_tool import DraftedReplyData
from tools.x_api_tools import XApiError

pytestmark = pytest.mark.asyncio


async def test_no_new_mentions(mocker, caplog):
    # No mentions returned -> should not process or save state
    mocker.patch("agents.orchestrator_agent.get_agent_state", return_value="42")
    mocker.patch(
        "agents.orchestrator_agent.get_mentions",
        return_value={"data": [], "meta": {"newest_id": "42"}},
    )
    mock_agent = mocker.Mock()
    mocker.patch("agents.orchestrator_agent.ContentCreationAgent", return_value=mock_agent)
    mock_request = mocker.patch("agents.orchestrator_agent.request_human_review")
    mock_save = mocker.patch("agents.orchestrator_agent.save_agent_state")

    caplog.set_level(logging.INFO)
    orchestrator = OrchestratorAgent()
    await orchestrator.process_new_mentions_workflow()

    assert "No new mentions found" in caplog.text
    mock_agent.draft_reply.assert_not_called()
    mock_request.assert_not_called()
    mock_save.assert_not_called()


async def test_successful_processing(mocker):
    # Successful processing of multiple mentions
    mocker.patch("agents.orchestrator_agent.get_agent_state", return_value=None)
    mention1 = {"id": "1", "text": "hello", "author_id": "user1"}
    mention2 = {"id": "2", "text": "world", "author_id": "user2"}
    mock_response = {"data": [mention1, mention2], "meta": {"newest_id": "2"}}
    mocker.patch("agents.orchestrator_agent.get_mentions", return_value=mock_response)

    mock_agent = mocker.Mock()
    drafted1 = {"draft_reply_text": "reply1", "original_mention_id": "1", "status": "drafted"}
    drafted2 = {"draft_reply_text": "reply2", "original_mention_id": "2", "status": "drafted"}
    mock_agent.draft_reply.side_effect = [drafted1, drafted2]
    mocker.patch("agents.orchestrator_agent.ContentCreationAgent", return_value=mock_agent)

    mock_request = mocker.patch(
        "agents.orchestrator_agent.request_human_review",
        side_effect=[
            {"status": "ok", "review_request_id": 100},
            {"status": "ok", "review_request_id": 101},
        ],
    )
    mock_save = mocker.patch("agents.orchestrator_agent.save_agent_state")

    orchestrator = OrchestratorAgent()
    await orchestrator.process_new_mentions_workflow()

    # Verify draft_reply calls
    mock_agent.draft_reply.assert_has_calls(
        [
            mocker.call(
                original_tweet_text="hello", original_tweet_author="user1", mention_tweet_id="1"
            ),
            mocker.call(
                original_tweet_text="world", original_tweet_author="user2", mention_tweet_id="2"
            ),
        ],
        any_order=False,
    )
    # Verify human review calls receive DraftedReplyData instances
    expected_model1 = DraftedReplyData(**drafted1)
    expected_model2 = DraftedReplyData(**drafted2)
    mock_request.assert_has_calls(
        [
            mocker.call(
                task_type="reply_to_mention",
                data_for_review=expected_model1,
                reason="New mention reply drafted",
            ),
            mocker.call(
                task_type="reply_to_mention",
                data_for_review=expected_model2,
                reason="New mention reply drafted",
            ),
        ],
        any_order=False,
    )
    # Verify state is saved with newest_id
    mock_save.assert_called_once_with("last_processed_mention_id_default_user", "2")


async def test_error_fetching_mentions(mocker, caplog):
    # get_mentions raises XApiError -> should log and exit
    mocker.patch("agents.orchestrator_agent.get_agent_state", return_value="42")
    mocker.patch("agents.orchestrator_agent.get_mentions", side_effect=XApiError("fetch failed"))
    mock_agent = mocker.Mock()
    mocker.patch("agents.orchestrator_agent.ContentCreationAgent", return_value=mock_agent)
    mock_request = mocker.patch("agents.orchestrator_agent.request_human_review")
    mock_save = mocker.patch("agents.orchestrator_agent.save_agent_state")

    caplog.set_level(logging.ERROR)
    orchestrator = OrchestratorAgent()
    await orchestrator.process_new_mentions_workflow()

    assert "Failed to fetch new mentions" in caplog.text
    mock_agent.draft_reply.assert_not_called()
    mock_request.assert_not_called()
    mock_save.assert_not_called()


async def test_error_in_draft_reply_continues(mocker, caplog):
    # One mention causes draft_reply exception, others continue
    mocker.patch("agents.orchestrator_agent.get_agent_state", return_value=None)
    mention1 = {"id": "1", "text": "hello", "author_id": "user1"}
    mention2 = {"id": "2", "text": "world", "author_id": "user2"}
    mocker.patch(
        "agents.orchestrator_agent.get_mentions",
        return_value={"data": [mention1, mention2], "meta": {"newest_id": "2"}},
    )
    mock_agent = mocker.Mock()

    def draft_side_effect(original_tweet_text, original_tweet_author, mention_tweet_id):
        if mention_tweet_id == "1":
            return {"draft_reply_text": "reply1", "original_mention_id": "1", "status": "drafted"}
        raise Exception("draft error")

    mock_agent.draft_reply.side_effect = draft_side_effect
    mocker.patch("agents.orchestrator_agent.ContentCreationAgent", return_value=mock_agent)
    mock_request = mocker.patch(
        "agents.orchestrator_agent.request_human_review", return_value={"status": "ok"}
    )
    mock_save = mocker.patch("agents.orchestrator_agent.save_agent_state")

    caplog.set_level(logging.ERROR)
    orchestrator = OrchestratorAgent()
    await orchestrator.process_new_mentions_workflow()

    # draft_reply called twice
    assert mock_agent.draft_reply.call_count == 2
    # Verify human review only for successful draft with Pydantic model
    assert mock_request.call_count == 1
    call_kwargs = mock_request.call_args[1]
    # data_for_review should be a DraftedReplyData instance
    assert isinstance(call_kwargs["data_for_review"], DraftedReplyData)
    # Ensure model contains correct data
    assert call_kwargs["data_for_review"].model_dump() == {
        "draft_reply_text": "reply1",
        "original_mention_id": "1",
        "status": "drafted",
    }
    assert call_kwargs["task_type"] == "reply_to_mention"
    assert call_kwargs["reason"] == "New mention reply drafted"
    assert "Failed to process mention 2" in caplog.text
    # state still saved
    mock_save.assert_called_once_with("last_processed_mention_id_default_user", "2")


async def test_error_in_request_human_review_continues(mocker, caplog):
    # One mention causes request_human_review exception, others continue
    mocker.patch("agents.orchestrator_agent.get_agent_state", return_value=None)
    mention1 = {"id": "1", "text": "hello", "author_id": "user1"}
    mention2 = {"id": "2", "text": "world", "author_id": "user2"}
    mocker.patch(
        "agents.orchestrator_agent.get_mentions",
        return_value={"data": [mention1, mention2], "meta": {"newest_id": "2"}},
    )
    mock_agent = mocker.Mock()
    mock_agent.draft_reply.return_value = {
        "draft_reply_text": "reply",
        "original_mention_id": "id",
        "status": "drafted",
    }
    mocker.patch("agents.orchestrator_agent.ContentCreationAgent", return_value=mock_agent)
    mock_request = mocker.patch(
        "agents.orchestrator_agent.request_human_review",
        side_effect=[{"status": "ok"}, Exception("review error")],
    )
    mock_save = mocker.patch("agents.orchestrator_agent.save_agent_state")

    caplog.set_level(logging.ERROR)
    orchestrator = OrchestratorAgent()
    await orchestrator.process_new_mentions_workflow()

    # draft_reply called twice
    assert mock_agent.draft_reply.call_count == 2
    # request_human_review called at least once
    assert mock_request.call_count == 2
    assert "Failed to process mention 2" in caplog.text
    # state still saved
    mock_save.assert_called_once_with("last_processed_mention_id_default_user", "2")


async def test_newest_id_without_meta(mocker):
    # Determine newest_id from data if meta missing
    mocker.patch("agents.orchestrator_agent.get_agent_state", return_value=None)
    mention1 = {"id": "1", "text": "hello", "author_id": "user1"}
    mention2 = {"id": "3", "text": "world", "author_id": "user2"}
    mention3 = {"id": "2", "text": "!", "author_id": "user3"}
    mocker.patch(
        "agents.orchestrator_agent.get_mentions",
        return_value={"data": [mention1, mention2, mention3]},
    )
    mock_agent = mocker.Mock()
    mock_agent.draft_reply.return_value = {
        "draft_reply_text": "reply",
        "original_mention_id": "id",
        "status": "drafted",
    }
    mocker.patch("agents.orchestrator_agent.ContentCreationAgent", return_value=mock_agent)
    mocker.patch("agents.orchestrator_agent.request_human_review", return_value={"status": "ok"})
    mock_save = mocker.patch("agents.orchestrator_agent.save_agent_state")

    orchestrator = OrchestratorAgent()
    await orchestrator.process_new_mentions_workflow()

    # lexicographically max among '1','3','2' is '3'
    mock_save.assert_called_once_with("last_processed_mention_id_default_user", "3")


def test_process_new_mentions_tool_registered():
    """Ensure the process_new_mentions tool is registered on the OrchestratorAgent."""
    orchestrator = OrchestratorAgent()
    tool_names = [getattr(tool, "name", None) for tool in orchestrator.tools]
    assert "process_new_mentions" in tool_names


# Tests for process_approved_replies_workflow
async def test_no_approved_replies(mocker, caplog):
    """Should log and do nothing when there are no approved replies."""
    mocker.patch("agents.orchestrator_agent.get_approved_reply_tasks", return_value=[])
    mock_post = mocker.patch("agents.orchestrator_agent._post_text_tweet")
    mock_update = mocker.patch("agents.orchestrator_agent.update_human_review_status")
    orchestrator = OrchestratorAgent()
    caplog.set_level(logging.INFO)

    await orchestrator.process_approved_replies_workflow()

    assert "No approved replies to process." in caplog.text
    mock_post.assert_not_called()
    mock_update.assert_not_called()


async def test_successful_approved_replies(mocker):
    """Should post approved replies and update status successfully."""
    tasks = [
        {"review_id": 1, "data_for_review": '{"draft_reply_text":"r1","original_mention_id":"m1"}'},
        {"review_id": 2, "data_for_review": '{"draft_reply_text":"r2","original_mention_id":"m2"}'},
    ]
    mocker.patch("agents.orchestrator_agent.get_approved_reply_tasks", return_value=tasks)
    mock_post = mocker.patch("agents.orchestrator_agent._post_text_tweet", return_value={})
    mock_update = mocker.patch("agents.orchestrator_agent.update_human_review_status")
    orchestrator = OrchestratorAgent()

    await orchestrator.process_approved_replies_workflow()

    mock_post.assert_has_calls(
        [
            mocker.call(text="r1", in_reply_to_tweet_id="m1"),
            mocker.call(text="r2", in_reply_to_tweet_id="m2"),
        ],
        any_order=False,
    )
    mock_update.assert_has_calls(
        [
            mocker.call(1, "posted_successfully"),
            mocker.call(2, "posted_successfully"),
        ],
        any_order=False,
    )


async def test_failed_post_updates_status_failed_to_post(mocker, caplog):
    """Should update status to failed_to_post when posting fails."""
    tasks = [
        {
            "review_id": 10,
            "data_for_review": '{"draft_reply_text":"fail","original_mention_id":"m10"}',
        }
    ]
    mocker.patch("agents.orchestrator_agent.get_approved_reply_tasks", return_value=tasks)
    mocker.patch("agents.orchestrator_agent._post_text_tweet", side_effect=Exception("post error"))
    mock_update = mocker.patch("agents.orchestrator_agent.update_human_review_status")
    orchestrator = OrchestratorAgent()
    caplog.set_level(logging.ERROR)

    await orchestrator.process_approved_replies_workflow()

    mock_update.assert_called_once_with(10, "failed_to_post")
    assert "Failed to post reply for review_id 10: post error" in caplog.text


async def test_json_loads_error_updates_status(mocker, caplog):
    """Should update status to failed_to_post when JSON parsing fails."""
    tasks = [{"review_id": 20, "data_for_review": "invalid json"}]
    mocker.patch("agents.orchestrator_agent.get_approved_reply_tasks", return_value=tasks)
    mock_post = mocker.patch("agents.orchestrator_agent._post_text_tweet")
    mock_update = mocker.patch("agents.orchestrator_agent.update_human_review_status")
    orchestrator = OrchestratorAgent()
    caplog.set_level(logging.ERROR)

    await orchestrator.process_approved_replies_workflow()

    mock_post.assert_not_called()
    mock_update.assert_called_once_with(20, "failed_to_post")
    assert "Failed to post reply for review_id 20" in caplog.text


async def test_error_fetching_approved_replies(mocker, caplog):
    """Should log error and exit when fetching approved replies fails."""
    mocker.patch(
        "agents.orchestrator_agent.get_approved_reply_tasks", side_effect=Exception("db error")
    )
    mock_post = mocker.patch("agents.orchestrator_agent._post_text_tweet")
    mock_update = mocker.patch("agents.orchestrator_agent.update_human_review_status")
    orchestrator = OrchestratorAgent()
    caplog.set_level(logging.ERROR)

    await orchestrator.process_approved_replies_workflow()

    assert "Failed to fetch approved replies: db error" in caplog.text
    mock_post.assert_not_called()
    mock_update.assert_not_called()


# Test tool registration for approved replies
def test_process_approved_replies_tool_registered():
    """Ensure the process_approved_replies tool is registered on the OrchestratorAgent."""
    orchestrator = OrchestratorAgent()
    tool_names = [getattr(tool, "name", None) for tool in orchestrator.tools]
    assert "process_approved_replies" in tool_names
