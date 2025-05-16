from datetime import datetime, timedelta, timezone

import pytest
from cryptography.fernet import Fernet

import core.oauth_manager as oauth_manager
from core.oauth_manager import OAuthError


def test_encrypt_decrypt_token_success(mocker):
    """Test that a token encrypted can be decrypted back to original."""
    # Generate a valid Fernet key and patch settings
    key = Fernet.generate_key().decode()
    mocker.patch.object(oauth_manager.settings, 'token_encryption_key', key)
    token = 'my_secret_token'
    encrypted = oauth_manager._encrypt_token(token)
    assert isinstance(encrypted, str)
    decrypted = oauth_manager._decrypt_token(encrypted)
    assert decrypted == token


def test_get_fernet_invalid_key(mocker):
    """Test that invalid token_encryption_key raises OAuthError."""
    mocker.patch.object(oauth_manager.settings, 'token_encryption_key', 'invalid')
    with pytest.raises(OAuthError) as exc:
        oauth_manager._get_fernet()
    assert 'Invalid token encryption key' in str(exc.value)


def test_decrypt_invalid_token(mocker):
    """Test that decrypting an invalid token raises OAuthError."""
    key = Fernet.generate_key().decode()
    mocker.patch.object(oauth_manager.settings, 'token_encryption_key', key)
    with pytest.raises(OAuthError) as exc:
        oauth_manager._decrypt_token('not_a_valid_token')
    assert 'Invalid encrypted token' in str(exc.value)


def test_encrypt_token_invalid_input(mocker):
    """Test that _encrypt_token invalid input raises OAuthError."""
    key = Fernet.generate_key().decode()
    mocker.patch.object(oauth_manager.settings, 'token_encryption_key', key)
    with pytest.raises(OAuthError) as exc:
        oauth_manager._encrypt_token(None)  # type: ignore
    assert 'Token encryption failed' in str(exc.value)


def test_save_tokens_calls_db_save(mocker):
    """Test that save_tokens encrypts and calls db save with correct args."""
    # Patch encryption to return a predictable value
    mocker.patch.object(oauth_manager, '_encrypt_token',
                        side_effect=lambda x: f'enc_{x}')
    save_mock = mocker.patch.object(oauth_manager, 'save_oauth_tokens')
    expires = datetime(2020, 1, 1, tzinfo=timezone.utc)
    oauth_manager.save_tokens('user1', 'access', 'refresh', expires, ['s1', 's2'])
    save_mock.assert_called_once_with(
        user_x_id='user1',
        access_token='enc_access',
        refresh_token='enc_refresh',
        expires_at=expires.isoformat(),
        scopes='s1 s2'
    )


def test_save_tokens_without_refresh(mocker):
    """Test that save_tokens handles None refresh_token and empty scopes."""
    mocker.patch.object(oauth_manager, '_encrypt_token', return_value='enc')
    save_mock = mocker.patch.object(oauth_manager, 'save_oauth_tokens')
    expires = datetime(2020, 1, 1, tzinfo=timezone.utc)
    oauth_manager.save_tokens('user', 'access', None, expires, [])
    save_mock.assert_called_once_with(
        user_x_id='user',
        access_token='enc',
        refresh_token=None,
        expires_at=expires.isoformat(),
        scopes=''
    )


def test_save_tokens_db_error(mocker):
    """Test that save_tokens raises OAuthError when db save fails."""
    mocker.patch.object(oauth_manager, '_encrypt_token', return_value='enc')
    mocker.patch.object(oauth_manager, 'save_oauth_tokens',
                        side_effect=Exception('db error'))
    expires = datetime(2020, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(OAuthError) as exc:
        oauth_manager.save_tokens('u', 'a', None, expires, [])
    assert 'Failed to save tokens' in str(exc.value)


def test_get_tokens_success(mocker):
    """Test get_tokens decrypts and parses data correctly."""
    # Generate key and patch settings
    key = Fernet.generate_key().decode()
    mocker.patch.object(oauth_manager.settings, 'token_encryption_key', key)
    # Prepare encrypted tokens
    raw_access = 'tokA'
    raw_refresh = 'tokR'
    encrypted_access = oauth_manager._encrypt_token(raw_access)
    encrypted_refresh = oauth_manager._encrypt_token(raw_refresh)
    expires = datetime(2020, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    row = {
        'access_token': encrypted_access,
        'refresh_token': encrypted_refresh,
        'expires_at': expires.isoformat(),
        'scopes': 'one two'
    }
    mocker.patch.object(oauth_manager, 'get_oauth_tokens', return_value=row)
    access, refresh, exp, scopes = oauth_manager.get_tokens('userX')
    assert access == raw_access
    assert refresh == raw_refresh
    assert exp == expires
    assert scopes == ['one', 'two']


def test_get_tokens_no_row(mocker):
    """Test get_tokens raises OAuthError when no row is returned."""
    mocker.patch.object(oauth_manager, 'get_oauth_tokens', return_value=None)
    with pytest.raises(OAuthError) as exc:
        oauth_manager.get_tokens('userX')
    assert 'No tokens found' in str(exc.value)


def test_get_tokens_no_refresh_no_scopes(mocker):
    """Test get_tokens handles None refresh and empty scopes."""
    key = Fernet.generate_key().decode()
    mocker.patch.object(oauth_manager.settings, 'token_encryption_key', key)
    raw_access = 'tokA'
    encrypted_access = oauth_manager._encrypt_token(raw_access)
    expires = datetime(2020, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    row = {
        'access_token': encrypted_access,
        'refresh_token': None,
        'expires_at': expires.isoformat(),
        'scopes': ''
    }
    mocker.patch.object(oauth_manager, 'get_oauth_tokens', return_value=row)
    access, refresh, exp, scopes = oauth_manager.get_tokens()
    assert access == raw_access
    assert refresh is None
    assert exp == expires
    assert scopes == []


def test_refresh_access_token_no_refresh(mocker):
    """Test refresh_access_token raises if no refresh_token available."""
    now = datetime.now(timezone.utc)
    mocker.patch.object(oauth_manager, 'get_tokens',
                        return_value=('A', None, now, []))
    with pytest.raises(OAuthError) as exc:
        oauth_manager.refresh_access_token('u1')
    assert 'No refresh token available' in str(exc.value)


def test_refresh_access_token_http_error(mocker):
    """Test refresh_access_token raises on HTTP error response."""
    now = datetime.now(timezone.utc)
    mocker.patch.object(oauth_manager, 'get_tokens',
                        return_value=('A', 'R', now, []))
    mocker.patch.object(oauth_manager.settings, 'x_api_key', 'key')
    class Resp:
        status_code = 400
        text = 'error'
    mocker.patch.object(oauth_manager.requests, 'post', return_value=Resp())
    with pytest.raises(OAuthError) as exc:
        oauth_manager.refresh_access_token('u2')
    assert 'Token refresh failed: 400' in str(exc.value)


def test_refresh_access_token_success(mocker):
    """Test successful token refresh flow."""
    now = datetime.now(timezone.utc)
    scopes = ['x', 'y']
    mocker.patch.object(oauth_manager, 'get_tokens',
                        return_value=('A', 'R', now, scopes))
    mocker.patch.object(oauth_manager.settings, 'x_api_key', 'key')
    class FakeResp:
        status_code = 200
        def json(self):
            return {
                'access_token': 'NEW',
                'refresh_token': 'NEW_R',
                'expires_in': 3600,
                'scope': 'a b'
            }
    mocker.patch.object(oauth_manager.requests, 'post', return_value=FakeResp())
    save_patch = mocker.patch.object(oauth_manager, 'save_tokens')
    new_access = oauth_manager.refresh_access_token('usr')
    assert new_access == 'NEW'
    save_patch.assert_called_once()
    args = save_patch.call_args[0]
    assert args[0] == 'usr'
    assert args[1] == 'NEW'
    assert args[2] == 'NEW_R'
    assert isinstance(args[3], datetime)
    assert args[4] == ['a', 'b']


def test_get_valid_x_token_not_expired(mocker):
    """Test get_valid_x_token returns existing token if not expiring soon."""
    now = datetime.now(timezone.utc)
    future = now + timedelta(minutes=10)
    mocker.patch.object(oauth_manager, 'get_tokens',
                        return_value=('OLD', None, future, []))
    refresh_patch = mocker.patch.object(oauth_manager, 'refresh_access_token')
    token = oauth_manager.get_valid_x_token('usr2')
    assert token == 'OLD'
    refresh_patch.assert_not_called()


def test_get_valid_x_token_expired(mocker):
    """Test get_valid_x_token refreshes token if expiring soon."""
    now = datetime.now(timezone.utc)
    soon = now + timedelta(minutes=4)
    mocker.patch.object(oauth_manager, 'get_tokens',
                        return_value=('OLD', None, soon, []))
    refresh_patch = mocker.patch.object(oauth_manager, 'refresh_access_token',
                                        return_value='REF')
    token = oauth_manager.get_valid_x_token('usr3')
    assert token == 'REF'
    refresh_patch.assert_called_once_with('usr3') 