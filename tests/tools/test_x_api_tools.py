import pytest
import requests

from core.oauth_manager import OAuthError
from tools.x_api_tools import XApiError, get_mentions, post_text_tweet


def test_successful_tweet_post(mocker):
    """Successful tweet post returns API data and calls requests with correct args."""
    mocker.patch("tools.x_api_tools.get_valid_x_token", return_value="FAKE_TOKEN")

    class FakeResponse:
        status_code = 201

        def __init__(self):
            self.text = '{"data":{"id":"123","text":"Test tweet"}}'

        def json(self):
            return {"data": {"id": "123", "text": "Test tweet"}}

    mock_post = mocker.patch("tools.x_api_tools.requests.post", return_value=FakeResponse())
    result = post_text_tweet("Hello world")
    assert result == {"data": {"id": "123", "text": "Test tweet"}}
    mock_post.assert_called_once_with(
        "https://api.twitter.com/2/tweets",
        headers={"Authorization": "Bearer FAKE_TOKEN", "Content-Type": "application/json"},
        json={"text": "Hello world"},
    )


def test_get_valid_x_token_failure(mocker):
    """OAuthError from get_valid_x_token is propagated."""
    mocker.patch("tools.x_api_tools.get_valid_x_token", side_effect=OAuthError("token fail"))
    with pytest.raises(OAuthError):
        post_text_tweet("Hello")


def test_requests_post_network_error(mocker):
    """Network errors during requests.post raise XApiError."""
    mocker.patch("tools.x_api_tools.get_valid_x_token", return_value="FAKE_TOKEN")
    mocker.patch(
        "tools.x_api_tools.requests.post",
        side_effect=requests.exceptions.ConnectionError("conn err"),
    )
    with pytest.raises(XApiError) as exc:
        post_text_tweet("Test")
    assert "Failed to send tweet request" in str(exc.value)


def test_x_api_response_error_code(mocker):
    """Non-201 responses raise XApiError with status code."""
    mocker.patch("tools.x_api_tools.get_valid_x_token", return_value="FAKE_TOKEN")

    class FakeResp:
        status_code = 403
        text = '{"title":"Forbidden","detail":"No permission"}'

        def json(self):
            return {"title": "Forbidden", "detail": "No permission"}

    mocker.patch("tools.x_api_tools.requests.post", return_value=FakeResp())
    with pytest.raises(XApiError) as exc:
        post_text_tweet("Hello")
    assert "Tweet creation failed with status code 403" in str(exc.value)


def test_invalid_json_response_after_success(mocker):
    """Invalid JSON in 201 response raises XApiError."""
    mocker.patch("tools.x_api_tools.get_valid_x_token", return_value="FAKE_TOKEN")

    class BadJsonResp:
        status_code = 201
        text = "invalid"

        def json(self):
            raise ValueError("no json")

    mocker.patch("tools.x_api_tools.requests.post", return_value=BadJsonResp())
    with pytest.raises(XApiError) as exc:
        post_text_tweet("Hello")
    assert "Failed to parse tweet response JSON" in str(exc.value)


# Tests for get_mentions tool


def test_get_mentions_success_with_since(mocker):
    mocker.patch("tools.x_api_tools.get_valid_x_token", return_value="FAKE_TOKEN")

    class FakeUserRes:
        status_code = 200

        def json(self):
            return {"data": {"id": "user123"}}

    class FakeMentionsRes:
        status_code = 200

        def json(self):
            return {
                "data": [{"id": "m1"}],
                "includes": {"users": [{"id": "u1", "username": "user", "name": "User"}]},
            }

    calls = []

    def fake_get(url, headers=None, params=None):
        calls.append((url, headers, params))
        if url.endswith("/2/users/me"):
            return FakeUserRes()
        elif url.endswith("/mentions"):
            return FakeMentionsRes()
        raise ValueError(f"Unexpected URL: {url}")

    mocker.patch("tools.x_api_tools.requests.get", side_effect=fake_get)

    result = get_mentions(since_id="since123")
    assert result == {
        "data": [{"id": "m1"}],
        "includes": {"users": [{"id": "u1", "username": "user", "name": "User"}]},
    }
    # Verify user info call
    assert calls[0][0].endswith("/2/users/me")
    assert calls[0][1] == {"Authorization": "Bearer FAKE_TOKEN"}
    assert calls[0][2] is None
    # Verify mentions call
    assert calls[1][0].endswith("/mentions")
    assert calls[1][2]["since_id"] == "since123"
    assert "tweet.fields" in calls[1][2]


def test_get_mentions_success_without_since(mocker):
    mocker.patch("tools.x_api_tools.get_valid_x_token", return_value="FAKE_TOKEN")

    class FakeUserRes:
        status_code = 200

        def json(self):
            return {"data": {"id": "user123"}}

    class FakeMentionsRes:
        status_code = 200

        def json(self):
            return {"status": "ok"}

    calls = []

    def fake_get(url, headers=None, params=None):
        calls.append((url, headers, params))
        if url.endswith("/2/users/me"):
            return FakeUserRes()
        elif url.endswith("/mentions"):
            return FakeMentionsRes()
        raise ValueError(f"Unexpected URL: {url}")

    mocker.patch("tools.x_api_tools.requests.get", side_effect=fake_get)

    result = get_mentions()
    assert result == {"status": "ok"}
    # since_id should not be in params
    assert calls[1][2] is not None
    assert "since_id" not in calls[1][2]


def test_get_mentions_user_info_error(mocker):
    mocker.patch("tools.x_api_tools.get_valid_x_token", return_value="FAKE_TOKEN")

    class ErrRes:
        status_code = 403
        text = "Forbidden"

        def json(self):
            return {"title": "Forbidden"}

    mocker.patch("tools.x_api_tools.requests.get", return_value=ErrRes())
    with pytest.raises(XApiError):
        get_mentions()


def test_get_mentions_user_info_json_error(mocker):
    mocker.patch("tools.x_api_tools.get_valid_x_token", return_value="FAKE_TOKEN")

    class BadJsonRes:
        status_code = 200
        text = "bad"

        def json(self):
            raise ValueError("bad json")

    mocker.patch("tools.x_api_tools.requests.get", return_value=BadJsonRes())
    with pytest.raises(XApiError):
        get_mentions()


def test_get_mentions_mentions_call_error(mocker):
    mocker.patch("tools.x_api_tools.get_valid_x_token", return_value="FAKE_TOKEN")

    class FakeUserRes:
        status_code = 200

        def json(self):
            return {"data": {"id": "user123"}}

    class ErrMentionsRes:
        status_code = 500
        text = "Server error"

        def json(self):
            return {}

    def side_effect(url, headers=None, params=None):
        if url.endswith("/2/users/me"):
            return FakeUserRes()
        elif url.endswith("/mentions"):
            return ErrMentionsRes()
        raise ValueError("Unexpected URL")

    mocker.patch("tools.x_api_tools.requests.get", side_effect=side_effect)
    with pytest.raises(XApiError):
        get_mentions()


def test_get_mentions_mentions_json_error(mocker):
    mocker.patch("tools.x_api_tools.get_valid_x_token", return_value="FAKE_TOKEN")

    class FakeUserRes:
        status_code = 200

        def json(self):
            return {"data": {"id": "user123"}}

    class BadJsonMentionsRes:
        status_code = 200
        text = "bad"

        def json(self):
            raise ValueError("bad json")

    def side_effect(url, headers=None, params=None):
        if url.endswith("/2/users/me"):
            return FakeUserRes()
        elif url.endswith("/mentions"):
            return BadJsonMentionsRes()
        raise ValueError("Unexpected URL")

    mocker.patch("tools.x_api_tools.requests.get", side_effect=side_effect)
    with pytest.raises(XApiError):
        get_mentions()


def test_get_mentions_oauth_error(mocker):
    mocker.patch("tools.x_api_tools.get_valid_x_token", side_effect=OAuthError("auth failed"))
    with pytest.raises(OAuthError):
        get_mentions()


# Add new test for in-reply-to support
def test_successful_tweet_post_with_reply(mocker):
    """Successful tweet post with in_reply_to_tweet_id includes reply field in JSON."""
    mocker.patch("tools.x_api_tools.get_valid_x_token", return_value="FAKE_TOKEN")

    class FakeResponse:
        status_code = 201

        def __init__(self):
            self.text = '{"data":{"id":"456","text":"Reply tweet"}}'

        def json(self):
            return {"data": {"id": "456", "text": "Reply tweet"}}

    mock_post = mocker.patch("tools.x_api_tools.requests.post", return_value=FakeResponse())
    result = post_text_tweet("Reply content", in_reply_to_tweet_id="789")
    assert result == {"data": {"id": "456", "text": "Reply tweet"}}
    mock_post.assert_called_once_with(
        "https://api.twitter.com/2/tweets",
        headers={"Authorization": "Bearer FAKE_TOKEN", "Content-Type": "application/json"},
        json={"text": "Reply content", "reply": {"in_reply_to_tweet_id": "789"}},
    )
