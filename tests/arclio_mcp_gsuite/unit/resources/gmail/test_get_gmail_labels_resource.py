"""
Unit tests for Gmail get_gmail_labels resource.
"""

from unittest.mock import MagicMock, patch

import pytest
from arclio_mcp_gsuite.resources.gmail import get_gmail_labels

pytestmark = pytest.mark.anyio


class TestGetGmailLabelsResource:
    """Tests for the get_gmail_labels resource function."""

    @pytest.fixture
    def mock_gmail_service(self):
        """Patch GmailService for resource tests."""
        with patch(
            "arclio_mcp_gsuite.resources.gmail.GmailService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_get_labels_success(self, mock_gmail_service):
        """Test get_gmail_labels successful case."""
        mock_service_response = [
            {"id": "INBOX", "name": "Inbox", "type": "system"},
            {"id": "SENT", "name": "Sent", "type": "system"},
            {"id": "IMPORTANT", "name": "Important", "type": "system"},
        ]
        mock_gmail_service.get_labels.return_value = mock_service_response

        result = await get_gmail_labels()

        mock_gmail_service.get_labels.assert_called_once_with()
        assert result == {"count": 3, "labels": mock_service_response}

    async def test_get_labels_no_results(self, mock_gmail_service):
        """Test get_gmail_labels when no labels are found."""
        mock_gmail_service.get_labels.return_value = []

        result = await get_gmail_labels()

        mock_gmail_service.get_labels.assert_called_once_with()
        assert result == {"count": 0, "labels": []}

    async def test_get_labels_service_error(self, mock_gmail_service):
        """Test get_gmail_labels when the service call fails."""
        mock_gmail_service.get_labels.return_value = {
            "error": True,
            "message": "API Error: Failed to retrieve labels",
        }

        with pytest.raises(ValueError, match="API Error: Failed to retrieve labels"):
            await get_gmail_labels()
