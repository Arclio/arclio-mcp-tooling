"""
Unit tests for WeaviateService.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from weaviate_mcp.services.weaviate_service import WeaviateService


class TestWeaviateService:
    """Test cases for WeaviateService."""

    def test_init_success(self):
        """Test successful initialization of WeaviateService."""
        # Act
        service = WeaviateService()

        # Assert - client is None until _ensure_connected is called
        assert service._client is None
        assert service._connected is False

    @patch("weaviate_mcp.services.weaviate_service.get_weaviate_config")
    @patch("weaviate_mcp.services.weaviate_service.get_openai_api_key")
    def test_init_failure(self, mock_get_api_key, mock_get_config):
        """Test initialization failure handling."""
        # Arrange
        mock_get_config.side_effect = Exception("Config error")

        # Act
        service = WeaviateService()

        # Assert
        assert service._client is None

    @pytest.mark.asyncio
    async def test_get_schema_success(self, mock_env_vars):
        """Test successful schema retrieval."""
        # Arrange
        with patch(
            "weaviate_mcp.services.weaviate_service.WeaviateAsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.collections.list_all.return_value = {
                "Collection1": {},
                "Collection2": {},
            }
            mock_client_class.return_value = mock_client

            service = WeaviateService()

            # Act
            result = await service.get_schema()

            # Assert
            assert result == {"Collection1": {}, "Collection2": {}}
            mock_client.collections.list_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_schema_client_not_initialized(self):
        """Test schema retrieval when client is not initialized."""
        # Arrange
        service = WeaviateService()
        service._client = None

        # Act
        result = await service.get_schema()

        # Assert
        assert result["error"] is True
        assert "Failed to connect to Weaviate" in result["message"]

    @pytest.mark.asyncio
    async def test_get_schema_exception(self, mock_env_vars):
        """Test schema retrieval with exception."""
        # Arrange
        with patch(
            "weaviate_mcp.services.weaviate_service.WeaviateAsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.collections.list_all.side_effect = Exception("Connection error")
            mock_client_class.return_value = mock_client

            service = WeaviateService()

            # Act
            result = await service.get_schema()

            # Assert
            assert result["error"] is True
            assert "Connection error" in result["message"]

    @pytest.mark.asyncio
    async def test_create_collection_success(
        self, mock_env_vars, sample_weaviate_properties
    ):
        """Test successful collection creation."""
        # Arrange
        with patch(
            "weaviate_mcp.services.weaviate_service.WeaviateAsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.collections.create = AsyncMock()
            mock_client_class.return_value = mock_client

            service = WeaviateService()

            # Act
            result = await service.create_collection(
                name="TestCollection",
                description="Test collection",
                properties=sample_weaviate_properties,
            )

            # Assert
            assert result["success"] is True
            assert "TestCollection" in result["message"]
            mock_client.collections.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_collection_success(self, mock_env_vars):
        """Test successful collection deletion."""
        # Arrange
        with patch(
            "weaviate_mcp.services.weaviate_service.WeaviateAsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.collections.delete = AsyncMock()
            mock_client_class.return_value = mock_client

            service = WeaviateService()

            # Act
            result = await service.delete_collection("TestCollection")

            # Assert
            assert result["success"] is True
            assert "TestCollection" in result["message"]
            mock_client.collections.delete.assert_called_once_with("TestCollection")

    @pytest.mark.asyncio
    async def test_insert_object_success(self, mock_env_vars, sample_object_data):
        """Test successful object insertion."""
        # Arrange
        with patch(
            "weaviate_mcp.services.weaviate_service.WeaviateAsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_collection = MagicMock()
            mock_collection.data.insert = AsyncMock(return_value="test-uuid-123")
            # Fix: collections.get() is synchronous, not async
            mock_client.collections.get = MagicMock(return_value=mock_collection)
            mock_client_class.return_value = mock_client

            service = WeaviateService()

            # Act
            result = await service.insert_object("TestCollection", sample_object_data)

            # Assert
            assert result["success"] is True
            assert result["object_id"] == "test-uuid-123"
            mock_collection.data.insert.assert_called_once_with(sample_object_data)

    @pytest.mark.asyncio
    async def test_insert_object_with_unique_properties_existing(
        self, mock_env_vars, sample_object_data
    ):
        """Test object insertion with unique properties when object already exists."""
        # Arrange
        with (
            patch(
                "weaviate_mcp.services.weaviate_service.WeaviateAsyncClient"
            ) as mock_client_class,
            patch("weaviate_mcp.services.weaviate_service.Filter") as mock_filter_class,
        ):
            mock_client = AsyncMock()
            mock_collection = MagicMock()
            mock_client.collections.get = MagicMock(return_value=mock_collection)
            mock_client_class.return_value = mock_client

            # Mock the Filter class to avoid complex filter construction
            mock_filter = MagicMock()
            mock_filter_class.all_of.return_value = mock_filter
            mock_filter_class.by_property.return_value.equal.return_value = mock_filter

            service = WeaviateService()

            # Mock get_objects to return existing object
            service.get_objects = AsyncMock(
                return_value={
                    "objects": [{"id": "existing-uuid", "title": "Wireless Headphones"}]
                }
            )

            # Act
            result = await service.insert_object(
                "TestCollection", sample_object_data, unique_properties=["title"]
            )

            # Assert
            assert result["success"] is True
            assert result["object_id"] == "existing-uuid"

    @pytest.mark.asyncio
    async def test_get_object_success(self, mock_env_vars):
        """Test successful object retrieval."""
        # Arrange
        with patch(
            "weaviate_mcp.services.weaviate_service.WeaviateAsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_collection = MagicMock()

            mock_result = MagicMock()
            mock_result.properties = {"title": "Test Product", "price": 99.99}
            mock_result.uuid = "test-uuid"

            mock_collection.query.fetch_object_by_id = AsyncMock(
                return_value=mock_result
            )
            mock_client.collections.get = MagicMock(return_value=mock_collection)
            mock_client_class.return_value = mock_client

            service = WeaviateService()

            # Act
            result = await service.get_object("TestCollection", "test-uuid")

            # Assert
            assert result["title"] == "Test Product"
            assert result["price"] == 99.99
            assert result["id"] == "test-uuid"

    @pytest.mark.asyncio
    async def test_get_object_not_found(self, mock_env_vars):
        """Test object retrieval when object not found."""
        # Arrange
        with patch(
            "weaviate_mcp.services.weaviate_service.WeaviateAsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_collection = MagicMock()
            mock_collection.query.fetch_object_by_id = AsyncMock(return_value=None)
            mock_client.collections.get = MagicMock(return_value=mock_collection)
            mock_client_class.return_value = mock_client

            service = WeaviateService()

            # Act
            result = await service.get_object("TestCollection", "nonexistent-uuid")

            # Assert
            assert result["error"] is True
            assert "not found" in result["message"]

    @pytest.mark.asyncio
    async def test_search_success(self, mock_env_vars, sample_search_response):
        """Test successful vector search."""
        # Arrange
        with patch(
            "weaviate_mcp.services.weaviate_service.WeaviateAsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_collection = MagicMock()
            mock_collection.query.near_text = AsyncMock(
                return_value=sample_search_response
            )
            mock_client.collections.get = MagicMock(return_value=mock_collection)
            mock_client_class.return_value = mock_client

            service = WeaviateService()

            # Act
            result = await service.search("TestCollection", "wireless headphones")

            # Assert
            assert result["objects"][0]["title"] == "Wireless Headphones"
            assert result["objects"][0]["distance"] == 0.15
            assert result["objects"][0]["certainty"] == 0.85
            assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_update_object_success(self, mock_env_vars):
        """Test successful object update."""
        # Arrange
        with patch(
            "weaviate_mcp.services.weaviate_service.WeaviateAsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_collection = MagicMock()
            mock_collection.data.update = AsyncMock()
            mock_client.collections.get = MagicMock(return_value=mock_collection)
            mock_client_class.return_value = mock_client

            service = WeaviateService()

            # Act
            result = await service.update_object(
                "TestCollection", "test-uuid", {"price": 89.99}
            )

            # Assert
            assert result["success"] is True
            assert "updated successfully" in result["message"]
            mock_collection.data.update.assert_called_once_with(
                "test-uuid", {"price": 89.99}
            )

    @pytest.mark.asyncio
    async def test_delete_object_success(self, mock_env_vars):
        """Test successful object deletion."""
        # Arrange
        with patch(
            "weaviate_mcp.services.weaviate_service.WeaviateAsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_collection = MagicMock()
            mock_collection.data.delete_by_id = AsyncMock()
            mock_client.collections.get = MagicMock(return_value=mock_collection)
            mock_client_class.return_value = mock_client

            service = WeaviateService()

            # Act
            result = await service.delete_object("TestCollection", "test-uuid")

            # Assert
            assert result["success"] is True
            assert "deleted successfully" in result["message"]
            mock_collection.data.delete_by_id.assert_called_once_with("test-uuid")

    @pytest.mark.asyncio
    async def test_aggregate_success(self, mock_env_vars):
        """Test successful aggregation."""
        # Arrange
        with patch(
            "weaviate_mcp.services.weaviate_service.WeaviateAsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_collection = MagicMock()
            mock_query = MagicMock()

            # Create a mock result object with the expected attributes
            mock_result = MagicMock()
            mock_result.total_count = 100
            mock_query.over_all = AsyncMock(return_value=mock_result)

            mock_collection.aggregate = mock_query
            mock_client.collections.get = MagicMock(return_value=mock_collection)
            mock_client_class.return_value = mock_client

            service = WeaviateService()

            # Act
            result = await service.aggregate("TestCollection")

            # Assert
            assert result["success"] is True
            assert result["results"]["total_count"] == 100
            mock_query.over_all.assert_called_once_with(total_count=True)
