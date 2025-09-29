"""
Integration tests for AWS S3 MCP tools.

Tests the complete integration of tools with the FastMCP framework
and proper error propagation through the MCP layer.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aws_s3_mcp.app import mcp


class TestMCPToolsIntegration:
    """Integration tests for MCP tools with FastMCP framework."""

    @pytest.mark.asyncio
    @patch("aws_s3_mcp.services.s3_service.aioboto3.Session")
    @patch("aws_s3_mcp.services.s3_service.config")
    async def test_s3_list_objects_mcp_integration(
        self, mock_config, mock_session_class
    ):
        """Test s3_list_objects tool through MCP framework."""
        # Setup configuration
        mock_config.s3_buckets = None
        mock_config.aws_region = "us-east-1"
        mock_config.s3_object_max_keys = 1000

        # Setup mock S3 client
        mock_client = AsyncMock()
        mock_client.list_objects_v2.return_value = {
            "Contents": [
                {
                    "Key": "integration-test.txt",
                    "LastModified": "2024-01-01T12:00:00Z",
                    "Size": 512,
                    "ETag": '"integration123"',
                }
            ]
        }

        mock_session = MagicMock()
        mock_session.client.return_value.__aenter__.return_value = mock_client
        mock_session.client.return_value.__aexit__.return_value = None
        mock_session.get_credentials.return_value = MagicMock()
        mock_session_class.return_value = mock_session

        # Test tool through MCP framework
        from aws_s3_mcp.tools.s3_tools import s3_list_objects

        result = await s3_list_objects("integration-bucket", "test/", 50)

        assert result["count"] == 1
        assert result["objects"][0]["key"] == "integration-test.txt"
        assert result["objects"][0]["etag"] == "integration123"

    @pytest.mark.asyncio
    @patch("aws_s3_mcp.services.s3_service.aioboto3.Session")
    @patch("aws_s3_mcp.services.s3_service.config")
    async def test_s3_get_object_content_mcp_integration(
        self, mock_config, mock_session_class
    ):
        """Test s3_get_object_content tool through MCP framework."""
        # Setup configuration
        mock_config.s3_buckets = None
        mock_config.aws_region = "us-east-1"

        # Setup mock S3 client
        mock_client = AsyncMock()
        mock_body = AsyncMock()
        mock_body.read.return_value = b"Integration test content"

        mock_client.get_object.return_value = {
            "Body": mock_body,
            "ContentType": "text/plain",
        }

        mock_session = MagicMock()
        mock_session.client.return_value.__aenter__.return_value = mock_client
        mock_session.client.return_value.__aexit__.return_value = None
        mock_session.get_credentials.return_value = MagicMock()
        mock_session_class.return_value = mock_session

        # Test tool through MCP framework
        from aws_s3_mcp.tools.s3_tools import s3_get_object_content

        result = await s3_get_object_content("integration-bucket", "test-file.txt")

        assert result["content"] == "Integration test content"
        assert result["mime_type"] == "text/plain"
        assert result["encoding"] == "utf-8"
        assert result["size"] == 23

    def test_mcp_app_initialization(self):
        """Test that MCP app is properly initialized."""
        # Verify that the MCP app exists and has the correct name
        assert mcp.name == "aws-s3-mcp"
