"""
Unit tests for the GmailService initialization.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.services.gmail import GmailService
from googleapiclient.errors import HttpError


class TestGmailServiceInit:
    """Tests for the GmailService initialization and service property."""

    @patch("google_workspace_mcp.services.base.gauth.get_credentials")
    @patch("google_workspace_mcp.services.base.build")
    def test_init_success(self, mock_build, mock_get_credentials):
        """Test successful initialization of GmailService."""
        # Setup mocks
        mock_credentials = MagicMock()
        mock_service = MagicMock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = mock_service

        # Create the service instance - lazy loading means no calls yet
        gmail_service = GmailService()

        # Verify the service instance is created correctly but no API calls made yet
        assert gmail_service.service_name == "gmail"
        assert gmail_service.version == "v1"
        assert gmail_service._service is None

        # Access the service property triggers the actual initialization
        service_instance = gmail_service.service

        # Verify correct initialization
        mock_get_credentials.assert_called_once()
        mock_build.assert_called_once_with("gmail", "v1", credentials=mock_credentials)
        assert service_instance == mock_service

    @patch("google_workspace_mcp.services.base.gauth.get_credentials")
    @patch("google_workspace_mcp.services.base.build")
    def test_init_credential_error(self, mock_build, mock_get_credentials):
        """Test initialization failure due to credential error."""
        # Setup mocks
        mock_get_credentials.side_effect = ValueError("Invalid credentials")

        # Create the service instance
        gmail_service = GmailService()

        # Verify the correct error is raised when accessing the service property
        with pytest.raises(ValueError, match="Invalid credentials"):
            _ = gmail_service.service

        mock_get_credentials.assert_called_once()
        mock_build.assert_not_called()

    @patch("google_workspace_mcp.services.base.gauth.get_credentials")
    @patch("google_workspace_mcp.services.base.build")
    def test_init_http_error(self, mock_build, mock_get_credentials):
        """Test initialization failure due to HTTP error."""
        # Setup mocks
        mock_credentials = MagicMock()
        mock_get_credentials.return_value = mock_credentials

        # Create mock HTTP error
        mock_resp = MagicMock()
        mock_resp.status = 403
        mock_resp.reason = "API Quota Exceeded"
        mock_build.side_effect = HttpError(mock_resp, b'{"error": {"message": "API Quota Exceeded"}}')

        # Create the service instance
        gmail_service = GmailService()

        # Verify the correct error is raised when accessing the service property
        with pytest.raises(HttpError):
            _ = gmail_service.service

        mock_get_credentials.assert_called_once()
        mock_build.assert_called_once()
