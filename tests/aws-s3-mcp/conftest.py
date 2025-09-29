"""
Shared test fixtures for AWS S3 MCP server tests.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_s3_client():
    """Mock aioboto3 S3 client for testing."""
    client = AsyncMock()

    # Mock list_objects_v2 response
    client.list_objects_v2.return_value = {
        "Contents": [
            {
                "Key": "test-file.txt",
                "LastModified": datetime(2024, 1, 1, 12, 0, 0),
                "Size": 1024,
                "ETag": '"abc123"',
            },
            {
                "Key": "folder/document.pdf",
                "LastModified": datetime(2024, 1, 2, 12, 0, 0),
                "Size": 2048,
                "ETag": '"def456"',
            },
        ]
    }

    # Mock get_object response
    mock_body = AsyncMock()
    mock_body.read.return_value = b"Test file content"

    client.get_object.return_value = {
        "Body": mock_body,
        "ContentType": "text/plain",
        "ContentLength": 17,
    }

    return client


@pytest.fixture
def mock_session(mock_s3_client):
    """Mock aioboto3 session."""
    session = MagicMock()
    session.client.return_value.__aenter__.return_value = mock_s3_client
    session.client.return_value.__aexit__.return_value = None
    return session


@pytest.fixture
def sample_bucket_name():
    """Sample bucket name for testing."""
    return "test-bucket"


@pytest.fixture
def sample_object_key():
    """Sample object key for testing."""
    return "test-folder/test-file.txt"


@pytest.fixture
def sample_text_content():
    """Sample text content for testing."""
    return "This is a test file with some content."


@pytest.fixture
def sample_binary_content():
    """Sample binary content for testing."""
    return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
