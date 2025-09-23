"""
Integration tests for MCP tools.
These tests verify that tools work together correctly and handle realistic scenarios.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from weaviate_mcp.tools.collection_tools import (
    weaviate_create_collection,
    weaviate_delete_collection,
)
from weaviate_mcp.tools.data_tools import (
    weaviate_get_object,
    weaviate_insert_object,
    weaviate_vector_search,
)
from weaviate_mcp.tools.schema_tools import (
    weaviate_get_schema_info,
    weaviate_validate_collection_exists,
)


class TestMCPToolsIntegration:
    """Integration tests for MCP tools working together."""

    @pytest.mark.asyncio
    @patch("weaviate_mcp.services.weaviate_service.WeaviateAsyncClient")
    @patch("weaviate_mcp.services.weaviate_service.get_weaviate_config")
    @patch("weaviate_mcp.services.weaviate_service.get_openai_api_key")
    async def test_complete_collection_workflow(
        self,
        mock_get_api_key,
        mock_get_config,
        mock_client_class,
        sample_properties,
        sample_object_data,
    ):
        """Test a complete workflow: create collection, insert data, search, delete."""
        # Arrange
        mock_get_config.return_value = {
            "url": "localhost",
            "http_port": 8080,
            "grpc_port": 50051,
        }
        mock_get_api_key.return_value = "test-key"

        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock collection operations
        mock_client.collections.create = AsyncMock()
        mock_client.collections.delete = AsyncMock()
        mock_client.collections.list_all = AsyncMock()

        # Mock collection instance
        mock_collection = MagicMock()
        mock_collection.data.insert = AsyncMock(return_value="test-uuid-123")

        # Mock search results
        mock_search_obj = MagicMock()
        mock_search_obj.properties = sample_object_data
        mock_search_obj.uuid = "test-uuid-123"
        mock_search_obj.metadata = MagicMock()
        mock_search_obj.metadata.distance = 0.1
        mock_search_obj.metadata.certainty = 0.9

        mock_search_response = MagicMock()
        mock_search_response.objects = [mock_search_obj]

        mock_collection.query.near_text = AsyncMock(return_value=mock_search_response)
        mock_client.collections.get = MagicMock(return_value=mock_collection)

        # Step 1: Create collection
        create_result = await weaviate_create_collection(
            name="TestProduct",
            description="Test product collection",
            properties=sample_properties,
            vectorizer_config={
                "type": "text2vec_openai",
                "model": "text-embedding-3-small",
            },
        )

        assert create_result["success"] is True
        mock_client.collections.create.assert_called_once()

        # Step 2: Verify collection exists
        mock_client.collections.list_all.return_value = {"TestProduct": MagicMock()}

        validate_result = await weaviate_validate_collection_exists("TestProduct")
        assert validate_result["exists"] is True
        assert validate_result["collection_name"] == "TestProduct"

        # Step 3: Insert object
        insert_result = await weaviate_insert_object(collection_name="TestProduct", data=sample_object_data)

        assert insert_result["success"] is True
        assert insert_result["object_id"] == "test-uuid-123"
        mock_collection.data.insert.assert_called_once_with(sample_object_data)

        # Step 4: Search for the object
        search_result = await weaviate_vector_search(collection_name="TestProduct", query_text="wireless headphones")

        assert search_result["objects"][0]["title"] == sample_object_data["title"]
        assert search_result["objects"][0]["distance"] == 0.1
        mock_collection.query.near_text.assert_called_once()

        # Step 5: Delete collection
        delete_result = await weaviate_delete_collection("TestProduct")
        assert delete_result["success"] is True
        mock_client.collections.delete.assert_called_once_with("TestProduct")

    @pytest.mark.asyncio
    @patch("weaviate_mcp.services.weaviate_service.WeaviateAsyncClient")
    @patch("weaviate_mcp.services.weaviate_service.get_weaviate_config")
    @patch("weaviate_mcp.services.weaviate_service.get_openai_api_key")
    async def test_schema_validation_workflow(self, mock_get_api_key, mock_get_config, mock_client_class):
        """Test schema validation and information retrieval workflow."""
        # Arrange
        mock_get_config.return_value = {
            "url": "localhost",
            "http_port": 8080,
            "grpc_port": 50051,
        }
        mock_get_api_key.return_value = "test-key"

        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock schema with multiple collections
        mock_collection1 = MagicMock()
        mock_collection1.properties = [
            MagicMock(name="title", data_type="TEXT", description="Product title"),
            MagicMock(name="price", data_type="NUMBER", description="Product price"),
        ]

        mock_collection2 = MagicMock()
        mock_collection2.properties = [
            MagicMock(name="name", data_type="TEXT", description="Category name"),
        ]

        mock_schema = {"Product": mock_collection1, "Category": mock_collection2}

        mock_client.collections.list_all.return_value = mock_schema

        # Mock aggregation results
        mock_collection_instance = MagicMock()
        mock_aggregate_query = MagicMock()

        # Create mock result object with attributes instead of dictionary
        mock_aggregate_result = MagicMock()
        mock_aggregate_result.total_count = 50
        mock_aggregate_query.over_all = AsyncMock(return_value=mock_aggregate_result)

        mock_collection_instance.aggregate = mock_aggregate_query
        mock_client.collections.get = MagicMock(return_value=mock_collection_instance)

        # Step 1: Get overall schema info
        schema_info_result = await weaviate_get_schema_info()

        assert "schema_info" in schema_info_result
        assert "Product" in schema_info_result["schema_info"]
        assert "Category" in schema_info_result["schema_info"]
        assert "Object Count: 50" in schema_info_result["schema_info"]

        # Step 2: Validate specific collection exists
        validate_result = await weaviate_validate_collection_exists("Product")

        assert validate_result["exists"] is True
        assert validate_result["collection_name"] == "Product"
        assert validate_result["property_count"] == 2
        assert validate_result["object_count"] == 50

        # Step 3: Validate non-existent collection
        validate_missing_result = await weaviate_validate_collection_exists("NonExistent")

        assert validate_missing_result["exists"] is False
        assert "NonExistent" in validate_missing_result["message"]
        assert "Product" in validate_missing_result["available_collections"]
        assert "Category" in validate_missing_result["available_collections"]

    @pytest.mark.asyncio
    @patch("weaviate_mcp.services.weaviate_service.WeaviateAsyncClient")
    @patch("weaviate_mcp.services.weaviate_service.get_weaviate_config")
    @patch("weaviate_mcp.services.weaviate_service.get_openai_api_key")
    async def test_error_handling_workflow(self, mock_get_api_key, mock_get_config, mock_client_class):
        """Test error handling across different tools."""
        # Arrange
        mock_get_config.return_value = {
            "url": "localhost",
            "http_port": 8080,
            "grpc_port": 50051,
        }
        mock_get_api_key.return_value = "test-key"

        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock schema to return empty (no collections)
        mock_client.collections.list_all.return_value = {}

        # Step 1: Try to insert into non-existent collection
        insert_result = await weaviate_insert_object(collection_name="NonExistentCollection", data={"title": "Test Product"})

        # Should handle the error gracefully
        assert insert_result.get("error") is True or insert_result.get("success") is False

        # Step 2: Try to search in non-existent collection
        search_result = await weaviate_vector_search(collection_name="NonExistentCollection", query_text="test query")

        # Should handle the error gracefully
        assert search_result.get("error") is True or search_result.get("objects") == []

        # Step 3: Validate that schema info handles empty schema
        schema_info_result = await weaviate_get_schema_info()

        assert "schema_info" in schema_info_result
        assert "No collections found" in schema_info_result["schema_info"]

    @pytest.mark.asyncio
    @patch("weaviate_mcp.services.weaviate_service.WeaviateAsyncClient")
    @patch("weaviate_mcp.services.weaviate_service.get_weaviate_config")
    @patch("weaviate_mcp.services.weaviate_service.get_openai_api_key")
    async def test_data_consistency_workflow(self, mock_get_api_key, mock_get_config, mock_client_class, sample_object_data):
        """Test data consistency across insert, retrieve, and search operations."""
        # Arrange
        mock_get_config.return_value = {
            "url": "localhost",
            "http_port": 8080,
            "grpc_port": 50051,
        }
        mock_get_api_key.return_value = "test-key"

        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock collection
        mock_collection = MagicMock()
        mock_collection.data.insert = AsyncMock(return_value="consistent-uuid-123")

        # Mock get object result
        mock_get_result = MagicMock()
        mock_get_result.properties = sample_object_data.copy()
        mock_get_result.uuid = "consistent-uuid-123"
        mock_collection.query.fetch_object_by_id = AsyncMock(return_value=mock_get_result)

        # Mock search result with same data
        mock_search_obj = MagicMock()
        mock_search_obj.properties = sample_object_data.copy()
        mock_search_obj.uuid = "consistent-uuid-123"
        mock_search_obj.metadata = MagicMock()
        mock_search_obj.metadata.distance = 0.0
        mock_search_obj.metadata.certainty = 1.0

        mock_search_response = MagicMock()
        mock_search_response.objects = [mock_search_obj]
        mock_collection.query.near_text = AsyncMock(return_value=mock_search_response)

        mock_client.collections.get = MagicMock(return_value=mock_collection)

        # Step 1: Insert object
        insert_result = await weaviate_insert_object(collection_name="TestCollection", data=sample_object_data)

        assert insert_result["success"] is True
        inserted_uuid = insert_result["object_id"]

        # Step 2: Retrieve the same object by UUID
        get_result = await weaviate_get_object(collection_name="TestCollection", uuid=inserted_uuid)

        assert get_result["title"] == sample_object_data["title"]
        assert get_result["price"] == sample_object_data["price"]
        assert get_result["id"] == inserted_uuid

        # Step 3: Search should find the same object
        search_result = await weaviate_vector_search(collection_name="TestCollection", query_text=sample_object_data["title"])

        assert len(search_result["objects"]) == 1
        found_object = search_result["objects"][0]
        assert found_object["title"] == sample_object_data["title"]
        assert found_object["price"] == sample_object_data["price"]
        assert found_object["id"] == inserted_uuid
