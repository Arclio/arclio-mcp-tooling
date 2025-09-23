"""
Unit tests for collection management tools.
"""

from unittest.mock import AsyncMock, patch

import pytest
from weaviate_mcp.tools.collection_tools import (
    weaviate_create_collection,
    weaviate_delete_collection,
    weaviate_get_schema,
)


class TestCollectionTools:
    """Test cases for collection management tools."""

    @pytest.mark.asyncio
    @patch("weaviate_mcp.tools.collection_tools.WeaviateService")
    async def test_weaviate_create_collection_success(self, mock_service_class, sample_properties):
        """Test successful collection creation."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.create_collection.return_value = {
            "success": True,
            "message": "Collection 'TestCollection' created successfully",
        }
        mock_service_class.return_value = mock_service

        # Act
        result = await weaviate_create_collection(
            name="TestCollection",
            description="Test collection",
            properties=sample_properties,
        )

        # Assert
        assert result["success"] is True
        assert "TestCollection" in result["message"]
        mock_service.create_collection.assert_called_once()

    @pytest.mark.asyncio
    @patch("weaviate_mcp.tools.collection_tools.WeaviateService")
    async def test_weaviate_create_collection_with_vectorizer(self, mock_service_class, sample_properties):
        """Test collection creation with vectorizer configuration."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.create_collection.return_value = {
            "success": True,
            "message": "Collection 'TestCollection' created successfully",
        }
        mock_service_class.return_value = mock_service

        vectorizer_config = {
            "type": "text2vec_openai",
            "model": "text-embedding-3-small",
        }

        # Act
        result = await weaviate_create_collection(
            name="TestCollection",
            description="Test collection",
            properties=sample_properties,
            vectorizer_config=vectorizer_config,
        )

        # Assert
        assert result["success"] is True
        mock_service.create_collection.assert_called_once()

        # Check that vectorizer was configured
        call_args = mock_service.create_collection.call_args
        assert call_args.kwargs["vectorizer_config"] is not None
        assert call_args.kwargs["generative_config"] is not None

    @pytest.mark.asyncio
    @patch("weaviate_mcp.tools.collection_tools.WeaviateService")
    async def test_weaviate_create_collection_invalid_data_type(self, mock_service_class):
        """Test collection creation with invalid data type."""
        # Arrange
        mock_service_class.return_value = AsyncMock()

        invalid_properties = [
            {
                "name": "test_field",
                "data_type": "invalid_type",
                "description": "Test field",
            }
        ]

        # Act
        result = await weaviate_create_collection(
            name="TestCollection",
            description="Test collection",
            properties=invalid_properties,
        )

        # Assert
        assert result["error"] is True
        assert "Unsupported data type" in result["message"]
        assert "invalid_type" in result["message"]

    @pytest.mark.asyncio
    @patch("weaviate_mcp.tools.collection_tools.WeaviateService")
    async def test_weaviate_create_collection_unsupported_vectorizer(self, mock_service_class, sample_properties):
        """Test collection creation with unsupported vectorizer."""
        # Arrange
        mock_service_class.return_value = AsyncMock()

        vectorizer_config = {"type": "unsupported_vectorizer", "model": "some-model"}

        # Act
        result = await weaviate_create_collection(
            name="TestCollection",
            description="Test collection",
            properties=sample_properties,
            vectorizer_config=vectorizer_config,
        )

        # Assert
        assert result["error"] is True
        assert "Unsupported vectorizer type" in result["message"]

    @pytest.mark.asyncio
    @patch("weaviate_mcp.tools.collection_tools.WeaviateService")
    async def test_weaviate_create_collection_service_error(self, mock_service_class, sample_properties):
        """Test collection creation when service returns error."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.create_collection.return_value = {
            "error": True,
            "message": "Failed to create collection",
        }
        mock_service_class.return_value = mock_service

        # Act
        result = await weaviate_create_collection(
            name="TestCollection",
            description="Test collection",
            properties=sample_properties,
        )

        # Assert
        assert result["error"] is True
        assert "Failed to create collection" in result["message"]

    @pytest.mark.asyncio
    @patch("weaviate_mcp.tools.collection_tools.WeaviateService")
    async def test_weaviate_create_collection_exception(self, mock_service_class, sample_properties):
        """Test collection creation with exception."""
        # Arrange
        mock_service_class.side_effect = Exception("Connection error")

        # Act
        result = await weaviate_create_collection(
            name="TestCollection",
            description="Test collection",
            properties=sample_properties,
        )

        # Assert
        assert result["error"] is True
        assert "Connection error" in result["message"]

    @pytest.mark.asyncio
    @patch("weaviate_mcp.tools.collection_tools.WeaviateService")
    async def test_weaviate_delete_collection_success(self, mock_service_class):
        """Test successful collection deletion."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.delete_collection.return_value = {
            "success": True,
            "message": "Collection 'TestCollection' deleted successfully",
        }
        mock_service_class.return_value = mock_service

        # Act
        result = await weaviate_delete_collection("TestCollection")

        # Assert
        assert result["success"] is True
        assert "TestCollection" in result["message"]
        mock_service.delete_collection.assert_called_once_with("TestCollection")

    @pytest.mark.asyncio
    @patch("weaviate_mcp.tools.collection_tools.WeaviateService")
    async def test_weaviate_delete_collection_error(self, mock_service_class):
        """Test collection deletion with error."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.delete_collection.return_value = {
            "error": True,
            "message": "Collection not found",
        }
        mock_service_class.return_value = mock_service

        # Act
        result = await weaviate_delete_collection("NonexistentCollection")

        # Assert
        assert result["error"] is True
        assert "Collection not found" in result["message"]

    @pytest.mark.asyncio
    @patch("weaviate_mcp.tools.collection_tools.WeaviateService")
    async def test_weaviate_get_schema_success(self, mock_service_class):
        """Test successful schema retrieval."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.get_schema.return_value = {
            "Collection1": {"properties": []},
            "Collection2": {"properties": []},
        }
        mock_service_class.return_value = mock_service

        # Act
        result = await weaviate_get_schema()

        # Assert
        assert "Collection1" in result
        assert "Collection2" in result
        mock_service.get_schema.assert_called_once()

    @pytest.mark.asyncio
    @patch("weaviate_mcp.tools.collection_tools.WeaviateService")
    async def test_weaviate_get_schema_error(self, mock_service_class):
        """Test schema retrieval with error."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.get_schema.return_value = {
            "error": True,
            "message": "Failed to retrieve schema",
        }
        mock_service_class.return_value = mock_service

        # Act
        result = await weaviate_get_schema()

        # Assert
        assert result["error"] is True
        assert "Failed to retrieve schema" in result["message"]

    @pytest.mark.asyncio
    @patch("weaviate_mcp.tools.collection_tools.WeaviateService")
    async def test_weaviate_get_schema_exception(self, mock_service_class):
        """Test schema retrieval with exception."""
        # Arrange
        mock_service_class.side_effect = Exception("Connection error")

        # Act
        result = await weaviate_get_schema()

        # Assert
        assert result["error"] is True
        assert "Connection error" in result["message"]
