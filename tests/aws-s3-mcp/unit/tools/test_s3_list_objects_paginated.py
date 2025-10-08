"""
Unit tests for s3_list_objects_paginated (V2 - Index-based pagination).

Tests the V2 implementation which uses numeric indices and continuation tokens
instead of requiring users to provide filenames.
"""

import base64
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from aws_s3_mcp.tools.s3_tools import s3_count_objects, s3_list_objects_paginated


class TestS3ListObjectsPaginatedV2:
    """Test suite for V2 index-based pagination."""

    @pytest.mark.asyncio
    async def test_first_batch_no_token(self):
        """Test fetching first batch (start_index=0, no continuation_token)."""
        mock_service = AsyncMock()
        mock_service.list_objects_paginated.return_value = {
            "objects": [
                {
                    "key": "doc_000.pdf",
                    "size": 1024,
                    "last_modified": datetime(
                        2024, 1, 1, tzinfo=timezone.utc
                    ).isoformat(),
                    "etag": "abc",
                },
                {
                    "key": "doc_001.pdf",
                    "size": 2048,
                    "last_modified": datetime(
                        2024, 1, 2, tzinfo=timezone.utc
                    ).isoformat(),
                    "etag": "def",
                },
            ],
            "keys": ["doc_000.pdf", "doc_001.pdf"],
            "count": 2,
            "start_index": 0,
            "next_start_index": 100,
            "has_more": True,
            "continuation_token": "eyJsYXN0X2tleSI6ICJkb2NfMDAxLnBkZiJ9",
        }

        with patch("aws_s3_mcp.tools.s3_tools.s3_service", mock_service):
            result = await s3_list_objects_paginated(
                bucket_name="test-bucket", start_index=0, batch_size=100
            )

        assert result["count"] == 2
        assert result["start_index"] == 0
        assert result["next_start_index"] == 100
        assert result["has_more"] is True
        assert result["continuation_token"] == "eyJsYXN0X2tleSI6ICJkb2NfMDAxLnBkZiJ9"
        assert "doc_000.pdf" in result["keys"]

        # Verify service was called with correct params
        mock_service.list_objects_paginated.assert_called_once_with(
            "test-bucket", "", 0, 100, ""
        )

    @pytest.mark.asyncio
    async def test_second_batch_with_token(self):
        """Test fetching second batch using continuation token."""
        # Create a continuation token
        token_data = {"last_key": "doc_099.pdf"}
        continuation_token = base64.b64encode(json.dumps(token_data).encode()).decode()

        mock_service = AsyncMock()
        mock_service.list_objects_paginated.return_value = {
            "objects": [
                {
                    "key": "doc_100.pdf",
                    "size": 3072,
                    "last_modified": datetime(
                        2024, 1, 3, tzinfo=timezone.utc
                    ).isoformat(),
                    "etag": "ghi",
                }
            ],
            "keys": ["doc_100.pdf"],
            "count": 1,
            "start_index": 100,
            "next_start_index": 200,
            "has_more": False,
            "continuation_token": "",
        }

        with patch("aws_s3_mcp.tools.s3_tools.s3_service", mock_service):
            result = await s3_list_objects_paginated(
                bucket_name="test-bucket",
                start_index=100,
                batch_size=100,
                continuation_token=continuation_token,
            )

        assert result["count"] == 1
        assert result["start_index"] == 100
        assert result["next_start_index"] == 200
        assert result["has_more"] is False
        assert result["continuation_token"] == ""
        assert result["keys"] == ["doc_100.pdf"]

    @pytest.mark.asyncio
    async def test_empty_bucket(self):
        """Test listing empty bucket."""
        mock_service = AsyncMock()
        mock_service.list_objects_paginated.return_value = {
            "objects": [],
            "keys": [],
            "count": 0,
            "start_index": 0,
            "next_start_index": 100,
            "has_more": False,
            "continuation_token": "",
        }

        with patch("aws_s3_mcp.tools.s3_tools.s3_service", mock_service):
            result = await s3_list_objects_paginated(bucket_name="empty-bucket")

        assert result["count"] == 0
        assert result["has_more"] is False
        assert result["keys"] == []

    @pytest.mark.asyncio
    async def test_custom_batch_size(self):
        """Test with custom batch_size parameter."""
        mock_service = AsyncMock()
        mock_service.list_objects_paginated.return_value = {
            "objects": [
                {
                    "key": f"file_{i}.pdf",
                    "size": 100,
                    "last_modified": "2024-01-01",
                    "etag": "x",
                }
                for i in range(50)
            ],
            "keys": [f"file_{i}.pdf" for i in range(50)],
            "count": 50,
            "start_index": 0,
            "next_start_index": 50,
            "has_more": True,
            "continuation_token": "token",
        }

        with patch("aws_s3_mcp.tools.s3_tools.s3_service", mock_service):
            result = await s3_list_objects_paginated(
                bucket_name="test-bucket", batch_size=50
            )

        assert result["count"] == 50
        assert result["next_start_index"] == 50

        # Verify batch_size was passed
        mock_service.list_objects_paginated.assert_called_once_with(
            "test-bucket", "", 0, 50, ""
        )

    @pytest.mark.asyncio
    async def test_with_prefix(self):
        """Test listing with prefix filter."""
        mock_service = AsyncMock()
        mock_service.list_objects_paginated.return_value = {
            "objects": [
                {
                    "key": "reports/report1.pdf",
                    "size": 1024,
                    "last_modified": "2024-01-01",
                    "etag": "abc",
                }
            ],
            "keys": ["reports/report1.pdf"],
            "count": 1,
            "start_index": 0,
            "next_start_index": 100,
            "has_more": False,
            "continuation_token": "",
        }

        with patch("aws_s3_mcp.tools.s3_tools.s3_service", mock_service):
            result = await s3_list_objects_paginated(
                bucket_name="test-bucket", prefix="reports/"
            )

        assert result["count"] == 1
        assert "reports/report1.pdf" in result["keys"]

        # Verify prefix was passed
        mock_service.list_objects_paginated.assert_called_once_with(
            "test-bucket", "reports/", 0, 100, ""
        )

    @pytest.mark.asyncio
    async def test_consistency_same_index(self):
        """Test that same index with same token returns same files."""
        token_data = {"last_key": "file_199.pdf"}
        continuation_token = base64.b64encode(json.dumps(token_data).encode()).decode()

        mock_service = AsyncMock()
        mock_service.list_objects_paginated.return_value = {
            "objects": [
                {
                    "key": "file_200.pdf",
                    "size": 100,
                    "last_modified": "2024-01-01",
                    "etag": "a",
                }
            ],
            "keys": ["file_200.pdf"],
            "count": 1,
            "start_index": 200,
            "next_start_index": 300,
            "has_more": True,
            "continuation_token": "new_token",
        }

        with patch("aws_s3_mcp.tools.s3_tools.s3_service", mock_service):
            # First call
            result1 = await s3_list_objects_paginated(
                bucket_name="test-bucket",
                start_index=200,
                continuation_token=continuation_token,
            )

            # Second call with same params
            result2 = await s3_list_objects_paginated(
                bucket_name="test-bucket",
                start_index=200,
                continuation_token=continuation_token,
            )

        # Results should be identical
        assert result1["keys"] == result2["keys"]
        assert result1["start_index"] == result2["start_index"]

    @pytest.mark.asyncio
    async def test_invalid_bucket_name(self):
        """Test validation of bucket_name parameter."""
        with pytest.raises(ValueError, match="bucket_name must be a non-empty string"):
            await s3_list_objects_paginated(bucket_name="")

        with pytest.raises(ValueError, match="bucket_name must be a non-empty string"):
            await s3_list_objects_paginated(bucket_name=None)

    @pytest.mark.asyncio
    async def test_invalid_start_index(self):
        """Test validation of start_index parameter."""
        with pytest.raises(
            ValueError, match="start_index must be a non-negative integer"
        ):
            await s3_list_objects_paginated(bucket_name="test-bucket", start_index=-1)

        with pytest.raises(
            ValueError, match="start_index must be a non-negative integer"
        ):
            await s3_list_objects_paginated(
                bucket_name="test-bucket", start_index="100"
            )

    @pytest.mark.asyncio
    async def test_invalid_batch_size(self):
        """Test validation of batch_size parameter."""
        with pytest.raises(ValueError, match="batch_size must be a positive integer"):
            await s3_list_objects_paginated(bucket_name="test-bucket", batch_size=0)

        with pytest.raises(ValueError, match="batch_size must be a positive integer"):
            await s3_list_objects_paginated(bucket_name="test-bucket", batch_size=-100)

    @pytest.mark.asyncio
    async def test_invalid_continuation_token(self):
        """Test validation of continuation_token parameter."""
        with pytest.raises(ValueError, match="continuation_token must be a string"):
            await s3_list_objects_paginated(
                bucket_name="test-bucket", continuation_token=123
            )

    @pytest.mark.asyncio
    async def test_service_error_handling(self):
        """Test handling of service layer errors."""
        mock_service = AsyncMock()
        mock_service.list_objects_paginated.return_value = {
            "error": True,
            "message": "Bucket does not exist",
        }

        with (
            patch("aws_s3_mcp.tools.s3_tools.s3_service", mock_service),
            pytest.raises(ValueError, match="Bucket does not exist"),
        ):
            await s3_list_objects_paginated(bucket_name="nonexistent-bucket")


class TestS3CountObjects:
    """Test suite for s3_count_objects tool."""

    @pytest.mark.asyncio
    async def test_count_all_objects(self):
        """Test counting all objects in bucket."""
        mock_service = AsyncMock()
        mock_service.count_objects.return_value = {
            "count": 542,
            "bucket_name": "test-bucket",
            "prefix": "",
        }

        with patch("aws_s3_mcp.tools.s3_tools.s3_service", mock_service):
            result = await s3_count_objects(bucket_name="test-bucket")

        assert result["count"] == 542
        assert result["bucket_name"] == "test-bucket"
        assert result["prefix"] == ""

        mock_service.count_objects.assert_called_once_with("test-bucket", "")

    @pytest.mark.asyncio
    async def test_count_with_prefix(self):
        """Test counting objects with prefix filter."""
        mock_service = AsyncMock()
        mock_service.count_objects.return_value = {
            "count": 87,
            "bucket_name": "test-bucket",
            "prefix": "reports/",
        }

        with patch("aws_s3_mcp.tools.s3_tools.s3_service", mock_service):
            result = await s3_count_objects(
                bucket_name="test-bucket", prefix="reports/"
            )

        assert result["count"] == 87
        assert result["prefix"] == "reports/"

        mock_service.count_objects.assert_called_once_with("test-bucket", "reports/")

    @pytest.mark.asyncio
    async def test_count_empty_bucket(self):
        """Test counting empty bucket."""
        mock_service = AsyncMock()
        mock_service.count_objects.return_value = {
            "count": 0,
            "bucket_name": "empty-bucket",
            "prefix": "",
        }

        with patch("aws_s3_mcp.tools.s3_tools.s3_service", mock_service):
            result = await s3_count_objects(bucket_name="empty-bucket")

        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_count_invalid_bucket_name(self):
        """Test validation of bucket_name parameter."""
        with pytest.raises(ValueError, match="bucket_name must be a non-empty string"):
            await s3_count_objects(bucket_name="")

    @pytest.mark.asyncio
    async def test_count_invalid_prefix(self):
        """Test validation of prefix parameter."""
        with pytest.raises(ValueError, match="prefix must be a string"):
            await s3_count_objects(bucket_name="test-bucket", prefix=123)

    @pytest.mark.asyncio
    async def test_count_service_error(self):
        """Test handling of service layer errors."""
        mock_service = AsyncMock()
        mock_service.count_objects.return_value = {
            "error": True,
            "message": "Access denied",
        }

        with (
            patch("aws_s3_mcp.tools.s3_tools.s3_service", mock_service),
            pytest.raises(ValueError, match="Access denied"),
        ):
            await s3_count_objects(bucket_name="test-bucket")
