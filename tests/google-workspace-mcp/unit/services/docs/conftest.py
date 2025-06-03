"""
Fixtures for Google Docs service tests.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.services.docs_service import DocsService


@pytest.fixture
def mock_docs_service():
    """Create a DocsService with mocked service attribute."""
    with (
        patch("google_workspace_mcp.auth.gauth.get_credentials"),
        patch("googleapiclient.discovery.build"),
    ):
        docs_service = DocsService()
        # Replace the private service attribute with a mock
        docs_service._service = MagicMock()
        return docs_service
