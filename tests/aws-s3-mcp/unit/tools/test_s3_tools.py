"""
Unit tests for S3 MCP tools.

Tests the MCP tool implementations including input validation,
error handling, and proper service integration.
"""

from unittest.mock import AsyncMock, patch

import pytest
from aws_s3_mcp.tools.s3_tools import s3_get_object_content, s3_list_objects


class TestS3ListObjectsTool:
    """Test cases for s3_list_objects MCP tool."""

    @pytest.mark.asyncio
    @patch("aws_s3_mcp.tools.s3_tools.s3_service")
    async def test_list_objects_success(self, mock_service):
        """Test successful object listing through MCP tool."""
        # Mock service response
        mock_service.list_objects = AsyncMock(
            return_value={
                "count": 2,
                "objects": [
                    {
                        "key": "file1.txt",
                        "last_modified": "2024-01-01T12:00:00Z",
                        "size": 1024,
                        "etag": "abc123",
                    },
                    {
                        "key": "file2.pdf",
                        "last_modified": "2024-01-02T12:00:00Z",
                        "size": 2048,
                        "etag": "def456",
                    },
                ],
            }
        )

        result = await s3_list_objects("test-bucket", "prefix/", 100)

        assert result["count"] == 2
        assert len(result["objects"]) == 2
        assert result["objects"][0]["key"] == "file1.txt"

        # Verify service was called with correct parameters
        mock_service.list_objects.assert_called_once_with("test-bucket", "prefix/", 100)

    @pytest.mark.asyncio
    @patch("aws_s3_mcp.tools.s3_tools.s3_service")
    async def test_list_objects_default_parameters(self, mock_service):
        """Test tool with default parameters."""
        mock_service.list_objects = AsyncMock(return_value={"count": 0, "objects": []})

        result = await s3_list_objects("test-bucket")

        # Verify defaults were applied
        mock_service.list_objects.assert_called_once_with("test-bucket", "", 1000)
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_list_objects_invalid_bucket_name(self):
        """Test tool validation for invalid bucket name."""
        with pytest.raises(ValueError, match="bucket_name must be a non-empty string"):
            await s3_list_objects("")

        with pytest.raises(ValueError, match="bucket_name must be a non-empty string"):
            await s3_list_objects(None)

        with pytest.raises(ValueError, match="bucket_name must be a non-empty string"):
            await s3_list_objects(123)

    @pytest.mark.asyncio
    async def test_list_objects_invalid_prefix(self):
        """Test tool validation for invalid prefix."""
        with pytest.raises(ValueError, match="prefix must be a string"):
            await s3_list_objects("test-bucket", 123)

    @pytest.mark.asyncio
    async def test_list_objects_invalid_max_keys(self):
        """Test tool validation for invalid max_keys."""
        with pytest.raises(ValueError, match="max_keys must be a positive integer"):
            await s3_list_objects("test-bucket", "", 0)

        with pytest.raises(ValueError, match="max_keys must be a positive integer"):
            await s3_list_objects("test-bucket", "", -1)

        with pytest.raises(ValueError, match="max_keys must be a positive integer"):
            await s3_list_objects("test-bucket", "", "invalid")

    @pytest.mark.asyncio
    @patch("aws_s3_mcp.tools.s3_tools.s3_service")
    async def test_list_objects_service_error(self, mock_service):
        """Test tool handling of service errors."""
        # Mock service error response
        mock_service.list_objects = AsyncMock(
            return_value={
                "error": True,
                "message": "Bucket not found",
                "details": {"error_code": "NoSuchBucket"},
            }
        )

        with pytest.raises(ValueError, match="Bucket not found"):
            await s3_list_objects("nonexistent-bucket")


class TestS3GetObjectContentTool:
    """Test cases for s3_get_object_content MCP tool."""

    @pytest.mark.asyncio
    @patch("aws_s3_mcp.tools.s3_tools.s3_service")
    async def test_get_object_content_text_success(self, mock_service):
        """Test successful text content retrieval through MCP tool."""
        # Mock service response for text file
        mock_service.get_object_content = AsyncMock(
            return_value={
                "content": "This is test content",
                "mime_type": "text/plain",
                "encoding": "utf-8",
                "size": 20,
            }
        )

        result = await s3_get_object_content("test-bucket", "test.txt")

        assert result["content"] == "This is test content"
        assert result["mime_type"] == "text/plain"
        assert result["encoding"] == "utf-8"
        assert result["size"] == 20

        # Verify service was called with correct parameters
        mock_service.get_object_content.assert_called_once_with(
            "test-bucket", "test.txt"
        )

    @pytest.mark.asyncio
    @patch("aws_s3_mcp.tools.s3_tools.s3_service")
    async def test_get_object_content_binary_success(self, mock_service):
        """Test successful binary content retrieval through MCP tool."""
        # Mock service response for binary file
        mock_service.get_object_content = AsyncMock(
            return_value={
                "content": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
                "mime_type": "image/png",
                "encoding": "base64",
                "size": 67,
            }
        )

        result = await s3_get_object_content("test-bucket", "image.png")

        assert result["encoding"] == "base64"
        assert result["mime_type"] == "image/png"
        assert len(result["content"]) > 0

        # Verify service was called with correct parameters
        mock_service.get_object_content.assert_called_once_with(
            "test-bucket", "image.png"
        )

    @pytest.mark.asyncio
    async def test_get_object_content_invalid_bucket_name(self):
        """Test tool validation for invalid bucket name."""
        with pytest.raises(ValueError, match="bucket_name must be a non-empty string"):
            await s3_get_object_content("", "test.txt")

        with pytest.raises(ValueError, match="bucket_name must be a non-empty string"):
            await s3_get_object_content(None, "test.txt")

        with pytest.raises(ValueError, match="bucket_name must be a non-empty string"):
            await s3_get_object_content(123, "test.txt")

    @pytest.mark.asyncio
    async def test_get_object_content_invalid_key(self):
        """Test tool validation for invalid object key."""
        with pytest.raises(ValueError, match="key must be a non-empty string"):
            await s3_get_object_content("test-bucket", "")

        with pytest.raises(ValueError, match="key must be a non-empty string"):
            await s3_get_object_content("test-bucket", None)

        with pytest.raises(ValueError, match="key must be a non-empty string"):
            await s3_get_object_content("test-bucket", 123)

    @pytest.mark.asyncio
    @patch("aws_s3_mcp.tools.s3_tools.s3_service")
    async def test_get_object_content_service_error(self, mock_service):
        """Test tool handling of service errors."""
        # Mock service error response
        mock_service.get_object_content = AsyncMock(
            return_value={
                "error": True,
                "message": "Object not found",
                "details": {"error_code": "NoSuchKey"},
            }
        )

        with pytest.raises(ValueError, match="Object not found"):
            await s3_get_object_content("test-bucket", "nonexistent.txt")
