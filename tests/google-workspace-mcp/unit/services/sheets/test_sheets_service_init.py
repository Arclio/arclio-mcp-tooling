"""
Unit tests for SheetsService initialization.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.services.sheets_service import SheetsService
from googleapiclient.errors import HttpError


class TestSheetsServiceInit:
    """Tests for SheetsService initialization and service property."""

    @patch("google_workspace_mcp.services.base.gauth.get_credentials")
    @patch("google_workspace_mcp.services.base.build")
    def test_init_success(self, mock_build, mock_get_credentials):
        """Test successful initialization of SheetsService."""
        # Setup mocks
        mock_credentials = MagicMock()
        mock_service = MagicMock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = mock_service

        # Create the service instance - lazy loading means no calls yet
        sheets_service = SheetsService()

        # Verify the service instance is created correctly but no API calls made yet
        assert sheets_service.service_name == "sheets"
        assert sheets_service.version == "v4"
        assert sheets_service._service is None

        # Access the service property triggers the actual initialization
        service_instance = sheets_service.service

        # Verify correct initialization
        mock_get_credentials.assert_called_once()
        mock_build.assert_called_once_with("sheets", "v4", credentials=mock_credentials)
        assert service_instance == mock_service

    @patch("google_workspace_mcp.services.base.gauth.get_credentials")
    @patch("google_workspace_mcp.services.base.build")
    def test_init_credential_error(self, mock_build, mock_get_credentials):
        """Test initialization failure due to credential error."""
        # Setup mocks
        mock_get_credentials.side_effect = ValueError("Invalid credentials")

        # Create the service instance
        sheets_service = SheetsService()

        # Verify the correct error is raised when accessing the service property
        with pytest.raises(ValueError, match="Invalid credentials"):
            _ = sheets_service.service

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
        sheets_service = SheetsService()

        # Verify the correct error is raised when accessing the service property
        with pytest.raises(HttpError):
            _ = sheets_service.service

        mock_get_credentials.assert_called_once()
        mock_build.assert_called_once()

    def test_service_name_and_version(self):
        """Test that the service uses correct name and version."""
        sheets_service = SheetsService()

        # Verify correct service name and version are set
        assert sheets_service.service_name == "sheets"
        assert sheets_service.version == "v4"
