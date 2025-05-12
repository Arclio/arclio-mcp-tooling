import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from google.oauth2.credentials import (
    Credentials as OAuthCredentials,
)  # Alias to avoid conflict
from google_auth_oauthlib.flow import InstalledAppFlow

# Functions to test
from markdowndeck.api.auth import (
    SCOPES,
    get_credentials,  # The main orchestrator
    get_credentials_from_env,
    get_credentials_from_token_file,
    run_oauth_flow,
)


@pytest.fixture
def mock_google_creds() -> MagicMock:
    """Returns a MagicMock for google.oauth2.credentials.Credentials."""
    creds_mock = MagicMock(spec=OAuthCredentials)
    creds_mock.valid = True
    creds_mock.expired = False
    creds_mock.refresh_token = "fake_refresh_token"
    creds_mock.token = "fake_token"
    creds_mock.client_id = "fake_client_id"
    creds_mock.client_secret = "fake_client_secret"
    creds_mock.scopes = SCOPES
    creds_mock.to_json.return_value = json.dumps(
        {
            "token": "fake_token",
            "refresh_token": "fake_refresh_token",
            "client_id": "fake_client_id",
            "client_secret": "fake_client_secret",
            "scopes": SCOPES,
        }
    )
    return creds_mock


class TestAuthGetCredentialsFromEnv:
    """Tests for get_credentials_from_env."""

    @patch("os.path.exists", return_value=True)
    @patch(
        "markdowndeck.api.auth.service_account.Credentials.from_service_account_file"
    )
    def test_service_account_creds_valid(
        self,
        mock_from_sac: MagicMock,
        mock_exists: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        mock_google_creds: MagicMock,
    ):
        sac_file = "/fake/path/to/sac.json"
        monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", sac_file)
        mock_from_sac.return_value = mock_google_creds

        creds = get_credentials_from_env()
        assert creds == mock_google_creds
        mock_from_sac.assert_called_once_with(sac_file, scopes=SCOPES)

    def test_service_account_creds_load_error_falls_through_improved(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test service account credentials failure with fallback to user credentials."""
        # Setup environment variables
        monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/fake/path/to/sac.json")
        monkeypatch.setenv("SLIDES_CLIENT_ID", "user_client_id")
        monkeypatch.setenv("SLIDES_CLIENT_SECRET", "user_client_secret")
        monkeypatch.setenv("SLIDES_REFRESH_TOKEN", "user_refresh_token")

        # Create a mock credential result
        mock_creds = MagicMock()

        # Mock both service account failure and successful user credentials creation
        with (
            patch("os.path.exists", return_value=True),
            patch(
                "markdowndeck.api.auth.service_account.Credentials.from_service_account_file",
                side_effect=Exception("SAC load error"),
            ),
            patch("markdowndeck.api.auth.Credentials", return_value=mock_creds),
        ):

            result = get_credentials_from_env()

            # Verify the mock credential was returned
            assert result is mock_creds

    def test_user_env_vars_creds_valid_improved(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test user environment variables for credentials."""
        # Setup environment variables
        monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
        monkeypatch.setenv("SLIDES_CLIENT_ID", "client_id_env")
        monkeypatch.setenv("SLIDES_CLIENT_SECRET", "client_secret_env")
        monkeypatch.setenv("SLIDES_REFRESH_TOKEN", "refresh_token_env")

        # Create a mock credentials object
        mock_creds = MagicMock()

        # Mock successful credentials creation
        with patch("markdowndeck.api.auth.Credentials", return_value=mock_creds):
            result = get_credentials_from_env()

            # Verify the mock credential was returned
            assert result is mock_creds

    def test_partial_user_env_vars(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
        monkeypatch.setenv("SLIDES_CLIENT_ID", "client_id_env")
        monkeypatch.delenv("SLIDES_CLIENT_SECRET", raising=False)  # Missing secret
        monkeypatch.setenv("SLIDES_REFRESH_TOKEN", "refresh_token_env")
        assert get_credentials_from_env() is None

    def test_no_env_vars(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
        monkeypatch.delenv("SLIDES_CLIENT_ID", raising=False)
        monkeypatch.delenv("SLIDES_CLIENT_SECRET", raising=False)
        monkeypatch.delenv("SLIDES_REFRESH_TOKEN", raising=False)
        assert get_credentials_from_env() is None


class TestAuthGetCredentialsFromTokenFile:
    """Tests for get_credentials_from_token_file."""

    @patch("markdowndeck.api.auth.Path.exists", return_value=False)
    def test_token_file_not_exists(self, mock_exists: MagicMock):
        assert get_credentials_from_token_file(Path("/fake/token.json")) is None

    @patch("markdowndeck.api.auth.Path.exists", return_value=True)
    @patch("markdowndeck.api.auth.Path.read_text")
    @patch("google.oauth2.credentials.Credentials.from_authorized_user_info")
    def test_token_file_valid_non_expired(
        self,
        mock_from_auth_user: MagicMock,
        mock_read_text: MagicMock,
        mock_exists: MagicMock,
        mock_google_creds: MagicMock,
    ):
        mock_google_creds.valid = True
        mock_google_creds.expired = False
        mock_from_auth_user.return_value = mock_google_creds
        mock_read_text.return_value = json.dumps({"token": "valid"})

        creds = get_credentials_from_token_file(Path("/fake/token.json"))
        assert creds == mock_google_creds
        mock_from_auth_user.assert_called_once_with({"token": "valid"}, SCOPES)

    @patch("markdowndeck.api.auth.Path.exists", return_value=True)
    @patch("markdowndeck.api.auth.Path.read_text")
    @patch("markdowndeck.api.auth.Path.write_text")
    @patch("google.oauth2.credentials.Credentials.from_authorized_user_info")
    @patch("markdowndeck.api.auth.Request")
    def test_token_file_expired_refreshable(
        self,
        mock_request_cls: MagicMock,
        mock_from_auth_user: MagicMock,
        mock_write_text: MagicMock,
        mock_read_text: MagicMock,
        mock_exists: MagicMock,
        mock_google_creds: MagicMock,
    ):
        mock_google_creds.valid = False  # Will become true after refresh
        mock_google_creds.expired = True
        mock_google_creds.refresh_token = "can_refresh"

        def refresh_side_effect(request):
            mock_google_creds.valid = True

        mock_google_creds.refresh.side_effect = refresh_side_effect
        mock_from_auth_user.return_value = mock_google_creds
        mock_read_text.return_value = (
            '{"token": "expired", "refresh_token": "can_refresh"}'
        )

        fake_token_path = Path("/fake/token.json")
        creds = get_credentials_from_token_file(fake_token_path)

        assert creds == mock_google_creds
        assert creds.valid is True
        mock_google_creds.refresh.assert_called_once_with(mock_request_cls.return_value)
        mock_write_text.assert_called_once_with(mock_google_creds.to_json())

    @patch("markdowndeck.api.auth.Path.exists", return_value=True)
    @patch("markdowndeck.api.auth.Path.read_text")
    @patch("google.oauth2.credentials.Credentials.from_authorized_user_info")
    def test_token_file_expired_not_refreshable(
        self,
        mock_from_auth_user: MagicMock,
        mock_read_text: MagicMock,
        mock_exists: MagicMock,
        mock_google_creds: MagicMock,
    ):
        mock_google_creds.valid = False
        mock_google_creds.expired = True
        mock_google_creds.refresh_token = None  # Cannot refresh
        mock_from_auth_user.return_value = mock_google_creds
        mock_read_text.return_value = '{"token": "expired"}'

        assert get_credentials_from_token_file(Path("/fake/token.json")) is None
        mock_google_creds.refresh.assert_not_called()

    @patch("markdowndeck.api.auth.Path.exists", return_value=True)
    @patch(
        "markdowndeck.api.auth.Path.read_text",
        side_effect=json.JSONDecodeError("err", "doc", 0),
    )
    def test_token_file_malformed_json(
        self, mock_read_text: MagicMock, mock_exists: MagicMock
    ):
        assert get_credentials_from_token_file(Path("/fake/token.json")) is None


class TestAuthRunOauthFlow:
    """Tests for run_oauth_flow."""

    @patch("markdowndeck.api.auth.Path.exists", return_value=False)
    def test_client_secrets_not_exists(self, mock_exists: MagicMock):
        assert run_oauth_flow(Path("/fake/secrets.json")) is None

    @patch("markdowndeck.api.auth.Path.exists", return_value=True)
    @patch("markdowndeck.api.auth.InstalledAppFlow.from_client_secrets_file")
    @patch("markdowndeck.api.auth.Path.write_text")
    @patch("markdowndeck.api.auth.Path.mkdir")
    def test_oauth_flow_success(
        self,
        mock_mkdir: MagicMock,
        mock_write_text: MagicMock,
        mock_from_secrets: MagicMock,
        mock_exists: MagicMock,
        mock_google_creds: MagicMock,
    ):
        mock_flow_instance = MagicMock(spec=InstalledAppFlow)
        mock_flow_instance.run_local_server.return_value = mock_google_creds
        mock_from_secrets.return_value = mock_flow_instance

        secrets_path = Path("/fake/secrets.json")
        with patch(
            "pathlib.Path.home", return_value=Path("/fakehome")
        ):  # Mock home for token path
            creds = run_oauth_flow(secrets_path)

        assert creds == mock_google_creds
        mock_from_secrets.assert_called_once_with(secrets_path, SCOPES)
        mock_flow_instance.run_local_server.assert_called_once_with(port=0)
        mock_write_text.assert_called_once_with(mock_google_creds.to_json())
        # Check that parent directory for token was created
        # mock_mkdir call is on the parent of write_text's path
        assert (
            mock_write_text.call_args[0][0] == mock_google_creds.to_json()
        )  # Verify what's written
        # Path object for write_text is tricky to get here, check mkdir call args
        assert mock_mkdir.call_args[1]["parents"] is True
        assert mock_mkdir.call_args[1]["exist_ok"] is True

    @patch("markdowndeck.api.auth.Path.exists", return_value=True)
    @patch("markdowndeck.api.auth.InstalledAppFlow.from_client_secrets_file")
    def test_oauth_flow_failure(
        self, mock_from_secrets: MagicMock, mock_exists: MagicMock
    ):
        mock_flow_instance = MagicMock(spec=InstalledAppFlow)
        mock_flow_instance.run_local_server.side_effect = Exception(
            "OAuth server error"
        )
        mock_from_secrets.return_value = mock_flow_instance

        assert run_oauth_flow(Path("/fake/secrets.json")) is None


class TestAuthGetCredentialsOrchestration:
    """Tests for the main get_credentials orchestrator."""

    @patch("markdowndeck.api.auth.get_credentials_from_env")
    def test_priority_env_creds(
        self, mock_get_env: MagicMock, mock_google_creds: MagicMock
    ):
        mock_get_env.return_value = mock_google_creds
        assert get_credentials() == mock_google_creds
        mock_get_env.assert_called_once()

    @patch("markdowndeck.api.auth.get_credentials_from_env", return_value=None)
    @patch("markdowndeck.api.auth.get_credentials_from_token_file")
    def test_priority_token_file_after_env(
        self,
        mock_get_token: MagicMock,
        mock_get_env: MagicMock,
        mock_google_creds: MagicMock,
    ):
        mock_get_token.return_value = mock_google_creds
        assert get_credentials() == mock_google_creds
        mock_get_env.assert_called_once()
        mock_get_token.assert_called_once()

    @patch("markdowndeck.api.auth.get_credentials_from_env", return_value=None)
    @patch("markdowndeck.api.auth.get_credentials_from_token_file", return_value=None)
    @patch("markdowndeck.api.auth.run_oauth_flow")
    def test_priority_oauth_flow_last(
        self,
        mock_run_oauth: MagicMock,
        mock_get_token: MagicMock,
        mock_get_env: MagicMock,
        mock_google_creds: MagicMock,
    ):
        mock_run_oauth.return_value = mock_google_creds
        assert get_credentials() == mock_google_creds
        mock_get_env.assert_called_once()
        mock_get_token.assert_called_once()
        mock_run_oauth.assert_called_once()

    @patch("markdowndeck.api.auth.get_credentials_from_env", return_value=None)
    @patch("markdowndeck.api.auth.get_credentials_from_token_file", return_value=None)
    @patch("markdowndeck.api.auth.run_oauth_flow", return_value=None)
    def test_all_methods_fail(
        self,
        mock_run_oauth: MagicMock,
        mock_get_token: MagicMock,
        mock_get_env: MagicMock,
    ):
        assert get_credentials() is None
        mock_get_env.assert_called_once()
        mock_get_token.assert_called_once()
        mock_run_oauth.assert_called_once()
