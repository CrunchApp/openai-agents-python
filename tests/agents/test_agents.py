import pytest

from agents.x_interaction_agent import XInteractionAgent
from agents.orchestrator_agent import OrchestratorAgent
from core.oauth_manager import OAuthError
from tweepy import TweepyException
from tools.x_api_tools import XApiError


def test_post_tweet_success(mocker):
    """Test that XInteractionAgent.post_tweet calls post_text_tweet and returns its result."""
    mock_result = {"id": "123", "text": "hello"}
    # Patch the imported function in XInteractionAgent
    mocker.patch(
        "agents.x_interaction_agent.post_text_tweet",
        return_value=mock_result,
    )
    agent = XInteractionAgent()
    result = agent.post_tweet("hello")
    assert result == mock_result


def test_post_tweet_oauth_error(mocker):
    """Test that XInteractionAgent.post_tweet propagates OAuthError."""
    mocker.patch(
        "agents.x_interaction_agent.post_text_tweet",
        side_effect=OAuthError("auth failed"),
    )
    agent = XInteractionAgent()
    with pytest.raises(OAuthError):
        agent.post_tweet("hello")


def test_post_tweet_x_api_error(mocker):
    """Test that XInteractionAgent.post_tweet propagates XApiError."""
    mocker.patch(
        "agents.x_interaction_agent.post_text_tweet",
        side_effect=XApiError("api call failed"),
    )
    agent = XInteractionAgent()
    with pytest.raises(XApiError):
        agent.post_tweet("hello")


def test_post_tweet_unexpected_error(mocker):
    """Test that XInteractionAgent.post_tweet propagates generic Exception."""
    mocker.patch(
        "agents.x_interaction_agent.post_text_tweet",
        side_effect=Exception("unexpected"),
    )
    agent = XInteractionAgent()
    with pytest.raises(Exception):
        agent.post_tweet("hello")


def test_run_simple_post_workflow_success(mocker):
    """Test that OrchestratorAgent.run_simple_post_workflow instantiates XInteractionAgent and calls post_tweet."""
    # Create a mock XInteractionAgent instance
    mock_x_agent = mocker.Mock()
    mock_x_agent.post_tweet.return_value = {"id": "456"}
    # Patch the XInteractionAgent constructor in the orchestrator module
    mocker.patch(
        "agents.orchestrator_agent.XInteractionAgent",
        return_value=mock_x_agent,
    )
    orchestrator = OrchestratorAgent()
    # The method does not return, but should call post_tweet
    orchestrator.run_simple_post_workflow("test content")
    mock_x_agent.post_tweet.assert_called_once_with(text_to_post="test content")


def test_run_simple_post_workflow_exception(mocker):
    """Test that OrchestratorAgent.run_simple_post_workflow propagates exceptions from XInteractionAgent."""
    mock_x_agent = mocker.Mock()
    mock_x_agent.post_tweet.side_effect = Exception("workflow failed")
    mocker.patch(
        "agents.orchestrator_agent.XInteractionAgent",
        return_value=mock_x_agent,
    )
    orchestrator = OrchestratorAgent()
    with pytest.raises(Exception):
        orchestrator.run_simple_post_workflow("error content")
    mock_x_agent.post_tweet.assert_called_once_with(text_to_post="error content") 