"""
Unit tests for the DriveService initialization.
"""

from unittest.mock import MagicMock, patch

import pytest
from arclio_mcp_gsuite.services.drive import DriveService
from googleapiclient.errors import HttpError


class TestDriveServiceInit:
    """Tests for the DriveService.__init__ method."""

    @patch("arclio_mcp_gsuite.services.base.gauth.get_credentials")
    @patch("arclio_mcp_gsuite.services.base.build")
    def test_init_success(self, mock_build, mock_get_credentials):
        """Test successful initialization of DriveService."""
        # Setup mocks
        mock_credentials = MagicMock()
        mock_service = MagicMock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = mock_service

        # Create the service instance
        drive_service = DriveService()

        # Verify correct initialization
        mock_get_credentials.assert_called_once()
        mock_build.assert_called_once_with("drive", "v3", credentials=mock_credentials)
        assert drive_service.service == mock_service
        assert drive_service.service_name == "drive"

    @patch("arclio_mcp_gsuite.services.base.gauth.get_credentials")
    @patch("arclio_mcp_gsuite.services.base.build")
    def test_init_credential_error(self, mock_build, mock_get_credentials):
        """Test initialization failure due to credential error."""
        # Setup mocks
        mock_get_credentials.side_effect = ValueError("Invalid credentials")

        # Verify the correct error is raised
        with pytest.raises(RuntimeError) as excinfo:
            DriveService()

        # Check error message
        assert "Failed to initialize drive service due to credential error" in str(excinfo.value)
        assert "Invalid credentials" in str(excinfo.value)
        mock_get_credentials.assert_called_once()
        mock_build.assert_not_called()

    @patch("arclio_mcp_gsuite.services.base.gauth.get_credentials")
    @patch("arclio_mcp_gsuite.services.base.build")
    def test_init_http_error(self, mock_build, mock_get_credentials):
        """Test initialization failure due to HTTP error."""
        # Setup mocks
        mock_credentials = MagicMock()
        mock_get_credentials.return_value = mock_credentials

        # Create mock HTTP error
        mock_resp = MagicMock()
        mock_resp.status = 403
        mock_resp.reason = "API Quota Exceeded"
        mock_build.side_effect = HttpError(
            mock_resp, b'{"error": {"message": "API Quota Exceeded"}}'
        )

        # Verify the correct error is raised
        with pytest.raises(RuntimeError) as excinfo:
            DriveService()

        # Check error message
        assert "Failed to initialize drive service due to API error" in str(excinfo.value)
        mock_get_credentials.assert_called_once()
        mock_build.assert_called_once()
