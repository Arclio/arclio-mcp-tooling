"""
Unit tests for S3Service class.

Tests the core S3 service functionality including async operations,
error handling, and content type detection.
"""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aws_s3_mcp.services.s3_service import S3Service
from botocore.exceptions import ClientError


class TestS3Service:
    """Test cases for S3Service class."""

    @patch("aws_s3_mcp.services.s3_service.aioboto3.Session")
    def test_init_validates_credentials(self, mock_session_class):
        """Test that S3Service validates credentials on initialization."""
        # Mock session that returns valid credentials
        mock_session = MagicMock()
        mock_session.get_credentials.return_value = MagicMock()
        mock_session_class.return_value = mock_session

        # Should not raise an exception
        service = S3Service()
        assert service is not None

    @patch("aws_s3_mcp.services.s3_service.aioboto3.Session")
    def test_init_raises_on_no_credentials(self, mock_session_class):
        """Test that S3Service raises ValueError when no credentials found."""
        # Mock session that returns no credentials
        mock_session = MagicMock()
        mock_session.get_credentials.return_value = None
        mock_session_class.return_value = mock_session

        with pytest.raises(ValueError, match="AWS credentials not found"):
            S3Service()

    @patch("aws_s3_mcp.services.s3_service.aioboto3.Session")
    @patch("aws_s3_mcp.services.s3_service.config")
    async def test_list_objects_success(
        self, mock_config, mock_session_class, mock_s3_client
    ):
        """Test successful object listing."""
        # Setup mocks
        mock_config.s3_buckets = None
        mock_config.aws_region = "us-east-1"
        mock_config.s3_object_max_keys = 1000

        mock_session = MagicMock()
        mock_session.client.return_value.__aenter__.return_value = mock_s3_client
        mock_session.client.return_value.__aexit__.return_value = None
        mock_session.get_credentials.return_value = MagicMock()
        mock_session_class.return_value = mock_session

        service = S3Service()
        result = await service.list_objects("test-bucket", "prefix/", 100)

        # Verify result structure
        assert "count" in result
        assert "objects" in result
        assert result["count"] == 2
        assert len(result["objects"]) == 2

        # Verify object structure
        obj = result["objects"][0]
        assert "key" in obj
        assert "last_modified" in obj
        assert "size" in obj
        assert "etag" in obj
        assert obj["etag"] == "abc123"  # ETag quotes should be stripped

    @patch("aws_s3_mcp.services.s3_service.aioboto3.Session")
    @patch("aws_s3_mcp.services.s3_service.config")
    async def test_list_objects_bucket_not_configured(
        self, mock_config, mock_session_class
    ):
        """Test that listing fails when bucket is not in configured list."""
        mock_config.s3_buckets = ["allowed-bucket"]
        mock_session = MagicMock()
        mock_session.get_credentials.return_value = MagicMock()
        mock_session_class.return_value = mock_session

        service = S3Service()
        result = await service.list_objects("forbidden-bucket")

        assert result["error"] is True
        assert "not in configured bucket list" in result["message"]

    @patch("aws_s3_mcp.services.s3_service.aioboto3.Session")
    @patch("aws_s3_mcp.services.s3_service.config")
    async def test_list_objects_client_error(self, mock_config, mock_session_class):
        """Test handling of S3 client errors during listing."""
        mock_config.s3_buckets = None
        mock_config.aws_region = "us-east-1"

        # Mock client that raises ClientError
        mock_client = AsyncMock()
        error_response = {
            "Error": {
                "Code": "NoSuchBucket",
                "Message": "The specified bucket does not exist",
            }
        }
        mock_client.list_objects_v2.side_effect = ClientError(
            error_response, "ListObjectsV2"
        )

        mock_session = MagicMock()
        mock_session.client.return_value.__aenter__.return_value = mock_client
        mock_session.client.return_value.__aexit__.return_value = None
        mock_session.get_credentials.return_value = MagicMock()
        mock_session_class.return_value = mock_session

        service = S3Service()
        result = await service.list_objects("nonexistent-bucket")

        assert result["error"] is True
        assert "NoSuchBucket" in result["details"]["error_code"]
        assert "does not exist" in result["message"]

    @patch("aws_s3_mcp.services.s3_service.aioboto3.Session")
    @patch("aws_s3_mcp.services.s3_service.config")
    async def test_get_object_content_text_file(
        self, mock_config, mock_session_class, sample_text_content
    ):
        """Test getting content of a text file."""
        mock_config.s3_buckets = None
        mock_config.aws_region = "us-east-1"

        # Mock client for text file
        mock_client = AsyncMock()
        mock_body = AsyncMock()
        mock_body.read.return_value = sample_text_content.encode("utf-8")

        mock_client.get_object.return_value = {
            "Body": mock_body,
            "ContentType": "text/plain",
        }

        mock_session = MagicMock()
        mock_session.client.return_value.__aenter__.return_value = mock_client
        mock_session.client.return_value.__aexit__.return_value = None
        mock_session.get_credentials.return_value = MagicMock()
        mock_session_class.return_value = mock_session

        service = S3Service()
        result = await service.get_object_content("test-bucket", "test.txt")

        assert result["content"] == sample_text_content
        assert result["mime_type"] == "text/plain"
        assert result["encoding"] == "utf-8"
        assert result["size"] == len(sample_text_content.encode("utf-8"))

    @patch("aws_s3_mcp.services.s3_service.aioboto3.Session")
    @patch("aws_s3_mcp.services.s3_service.config")
    async def test_get_object_content_binary_file(
        self, mock_config, mock_session_class, sample_binary_content
    ):
        """Test getting content of a binary file."""
        mock_config.s3_buckets = None
        mock_config.aws_region = "us-east-1"

        # Mock client for binary file
        mock_client = AsyncMock()
        mock_body = AsyncMock()
        mock_body.read.return_value = sample_binary_content

        mock_client.get_object.return_value = {
            "Body": mock_body,
            "ContentType": "image/png",
        }

        mock_session = MagicMock()
        mock_session.client.return_value.__aenter__.return_value = mock_client
        mock_session.client.return_value.__aexit__.return_value = None
        mock_session.get_credentials.return_value = MagicMock()
        mock_session_class.return_value = mock_session

        service = S3Service()
        result = await service.get_object_content("test-bucket", "test.png")

        expected_content = base64.b64encode(sample_binary_content).decode("ascii")
        assert result["content"] == expected_content
        assert result["mime_type"] == "image/png"
        assert result["encoding"] == "base64"
        assert result["size"] == len(sample_binary_content)

    @patch("aws_s3_mcp.services.s3_service.aioboto3.Session")
    @patch("aws_s3_mcp.services.s3_service.config")
    async def test_get_object_content_no_such_key(
        self, mock_config, mock_session_class
    ):
        """Test handling of missing object key."""
        mock_config.s3_buckets = None
        mock_config.aws_region = "us-east-1"

        # Mock client that raises NoSuchKey error
        mock_client = AsyncMock()
        error_response = {
            "Error": {
                "Code": "NoSuchKey",
                "Message": "The specified key does not exist",
            }
        }
        mock_client.get_object.side_effect = ClientError(error_response, "GetObject")

        mock_session = MagicMock()
        mock_session.client.return_value.__aenter__.return_value = mock_client
        mock_session.client.return_value.__aexit__.return_value = None
        mock_session.get_credentials.return_value = MagicMock()
        mock_session_class.return_value = mock_session

        service = S3Service()
        result = await service.get_object_content("test-bucket", "nonexistent.txt")

        assert result["error"] is True
        assert "NoSuchKey" in result["details"]["error_code"]
        assert "does not exist" in result["message"]

    def test_is_text_content_mime_types(self):
        """Test text content detection based on MIME types."""
        # Mock service for testing private method
        with (
            patch("aws_s3_mcp.services.s3_service.aioboto3.Session"),
            patch("aws_s3_mcp.services.s3_service.S3Service._validate_credentials"),
        ):
            service = S3Service()

        # Test text MIME types
        assert service._is_text_content("text/plain", b"test") is True
        assert service._is_text_content("text/markdown", b"test") is True
        assert service._is_text_content("application/json", b"test") is True

        # Test binary MIME types
        assert service._is_text_content("image/png", b"test") is False
        assert service._is_text_content("application/pdf", b"test") is False

        # Test heuristic for unknown MIME type with text content
        assert (
            service._is_text_content("application/octet-stream", b"Hello World") is True
        )

        # Test heuristic for unknown MIME type with binary content (null bytes)
        assert (
            service._is_text_content("application/octet-stream", b"Hello\x00World")
            is False
        )

    @pytest.mark.asyncio
    @patch("aws_s3_mcp.services.s3_service.aioboto3.Session")
    @patch("aws_s3_mcp.services.s3_service.config")
    async def test_get_text_content_success_text_file(
        self, mock_config, mock_session_class
    ):
        """Test successful text content retrieval for a text file."""
        mock_config.s3_buckets = None
        mock_config.aws_region = "us-east-1"

        # Mock S3 response with text content
        text_content = "# Sample Markdown\n\nThis is a test document."
        mock_response = {
            "Body": AsyncMock(),
            "ContentType": "text/markdown",
        }
        mock_response["Body"].read = AsyncMock(
            return_value=text_content.encode("utf-8")
        )

        mock_client = AsyncMock()
        mock_client.get_object = AsyncMock(return_value=mock_response)

        mock_session = MagicMock()
        mock_session.client.return_value.__aenter__.return_value = mock_client
        mock_session.client.return_value.__aexit__.return_value = None
        mock_session.get_credentials.return_value = MagicMock()
        mock_session_class.return_value = mock_session

        service = S3Service()
        result = await service.get_text_content("test-bucket", "docs/sample.md")

        assert "error" not in result or result.get("error") is False
        assert result["content"] == text_content
        assert result["mime_type"] == "text/markdown"
        assert result["size"] == len(text_content.encode("utf-8"))

    @pytest.mark.asyncio
    @patch("aws_s3_mcp.services.s3_service.aioboto3.Session")
    @patch("aws_s3_mcp.services.s3_service.config")
    async def test_get_text_content_fails_for_binary_file(
        self, mock_config, mock_session_class
    ):
        """Test that get_text_content fails for binary files (e.g., PDF)."""
        mock_config.s3_buckets = None
        mock_config.aws_region = "us-east-1"

        # Mock S3 response with PDF content
        pdf_content = b"%PDF-1.4\n%binary content here"
        mock_response = {
            "Body": AsyncMock(),
            "ContentType": "application/pdf",
        }
        mock_response["Body"].read = AsyncMock(return_value=pdf_content)

        mock_client = AsyncMock()
        mock_client.get_object = AsyncMock(return_value=mock_response)

        mock_session = MagicMock()
        mock_session.client.return_value.__aenter__.return_value = mock_client
        mock_session.client.return_value.__aexit__.return_value = None
        mock_session.get_credentials.return_value = MagicMock()
        mock_session_class.return_value = mock_session

        service = S3Service()
        result = await service.get_text_content("test-bucket", "docs/report.pdf")

        assert result["error"] is True
        assert "not a text file" in result["message"]
        assert result["details"]["mime_type"] == "application/pdf"
        assert "s3_get_object_content" in result["details"]["suggestion"]

    @pytest.mark.asyncio
    @patch("aws_s3_mcp.services.s3_service.aioboto3.Session")
    @patch("aws_s3_mcp.services.s3_service.config")
    async def test_get_text_content_fails_for_invalid_utf8(
        self, mock_config, mock_session_class
    ):
        """Test that get_text_content fails for files that can't be decoded as UTF-8."""
        mock_config.s3_buckets = None
        mock_config.aws_region = "us-east-1"

        # Mock S3 response with content that looks like text but isn't valid UTF-8
        invalid_utf8_content = b"Hello\x80\x81World"
        mock_response = {
            "Body": AsyncMock(),
            "ContentType": "text/plain",
        }
        mock_response["Body"].read = AsyncMock(return_value=invalid_utf8_content)

        mock_client = AsyncMock()
        mock_client.get_object = AsyncMock(return_value=mock_response)

        mock_session = MagicMock()
        mock_session.client.return_value.__aenter__.return_value = mock_client
        mock_session.client.return_value.__aexit__.return_value = None
        mock_session.get_credentials.return_value = MagicMock()
        mock_session_class.return_value = mock_session

        service = S3Service()
        result = await service.get_text_content("test-bucket", "docs/invalid.txt")

        assert result["error"] is True
        assert "could not be decoded as UTF-8" in result["message"]
        assert "decode_error" in result["details"]

    @pytest.mark.asyncio
    @patch("aws_s3_mcp.services.s3_service.aioboto3.Session")
    @patch("aws_s3_mcp.services.s3_service.config")
    async def test_get_text_content_json_file(self, mock_config, mock_session_class):
        """Test successful text content retrieval for JSON file."""
        mock_config.s3_buckets = None
        mock_config.aws_region = "us-east-1"

        json_content = '{"name": "test", "value": 123}'
        mock_response = {
            "Body": AsyncMock(),
            "ContentType": "application/json",
        }
        mock_response["Body"].read = AsyncMock(
            return_value=json_content.encode("utf-8")
        )

        mock_client = AsyncMock()
        mock_client.get_object = AsyncMock(return_value=mock_response)

        mock_session = MagicMock()
        mock_session.client.return_value.__aenter__.return_value = mock_client
        mock_session.client.return_value.__aexit__.return_value = None
        mock_session.get_credentials.return_value = MagicMock()
        mock_session_class.return_value = mock_session

        service = S3Service()
        result = await service.get_text_content("test-bucket", "config/settings.json")

        assert "error" not in result or result.get("error") is False
        assert result["content"] == json_content
        assert result["mime_type"] == "application/json"

    @pytest.mark.asyncio
    @patch("aws_s3_mcp.services.s3_service.aioboto3.Session")
    @patch("aws_s3_mcp.services.s3_service.config")
    async def test_get_text_content_bucket_not_configured(
        self, mock_config, mock_session_class
    ):
        """Test that get_text_content fails when bucket is not in configured list."""
        mock_config.s3_buckets = ["allowed-bucket"]

        mock_session = MagicMock()
        mock_session.get_credentials.return_value = MagicMock()
        mock_session_class.return_value = mock_session

        service = S3Service()
        result = await service.get_text_content("forbidden-bucket", "test.txt")

        assert result["error"] is True
        assert "not in configured bucket list" in result["message"]
