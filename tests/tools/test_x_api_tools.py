import pytest
import requests

from tools.x_api_tools import post_text_tweet, XApiError
from core.oauth_manager import OAuthError


def test_successful_tweet_post(mocker):
    """Successful tweet post returns API data and calls requests with correct args."""
    mocker.patch('tools.x_api_tools.get_valid_x_token', return_value='FAKE_TOKEN')
    class FakeResponse:
        status_code = 201
        def __init__(self):
            self.text = '{"data":{"id":"123","text":"Test tweet"}}'
        def json(self):
            return {"data": {"id": "123", "text": "Test tweet"}}
    mock_post = mocker.patch('tools.x_api_tools.requests.post', return_value=FakeResponse())
    result = post_text_tweet("Hello world")
    assert result == {"data": {"id": "123", "text": "Test tweet"}}
    mock_post.assert_called_once_with(
        "https://api.twitter.com/2/tweets",
        headers={
            "Authorization": "Bearer FAKE_TOKEN",
            "Content-Type": "application/json"
        },
        json={"text": "Hello world"}
    )


def test_get_valid_x_token_failure(mocker):
    """OAuthError from get_valid_x_token is propagated."""
    mocker.patch('tools.x_api_tools.get_valid_x_token', side_effect=OAuthError("token fail"))
    with pytest.raises(OAuthError):
        post_text_tweet("Hello")


def test_requests_post_network_error(mocker):
    """Network errors during requests.post raise XApiError."""
    mocker.patch('tools.x_api_tools.get_valid_x_token', return_value='FAKE_TOKEN')
    mocker.patch('tools.x_api_tools.requests.post', side_effect=requests.exceptions.ConnectionError("conn err"))
    with pytest.raises(XApiError) as exc:
        post_text_tweet("Test")
    assert "Failed to send tweet request" in str(exc.value)


def test_x_api_response_error_code(mocker):
    """Non-201 responses raise XApiError with status code."""
    mocker.patch('tools.x_api_tools.get_valid_x_token', return_value='FAKE_TOKEN')
    class FakeResp:
        status_code = 403
        text = '{"title":"Forbidden","detail":"No permission"}'
        def json(self):
            return {"title": "Forbidden", "detail": "No permission"}
    mocker.patch('tools.x_api_tools.requests.post', return_value=FakeResp())
    with pytest.raises(XApiError) as exc:
        post_text_tweet("Hello")
    assert "Tweet creation failed with status code 403" in str(exc.value)


def test_invalid_json_response_after_success(mocker):
    """Invalid JSON in 201 response raises XApiError."""
    mocker.patch('tools.x_api_tools.get_valid_x_token', return_value='FAKE_TOKEN')
    class BadJsonResp:
        status_code = 201
        text = "invalid"
        def json(self):
            raise ValueError("no json")
    mocker.patch('tools.x_api_tools.requests.post', return_value=BadJsonResp())
    with pytest.raises(XApiError) as exc:
        post_text_tweet("Hello")
    assert "Failed to parse tweet response JSON" in str(exc.value) 