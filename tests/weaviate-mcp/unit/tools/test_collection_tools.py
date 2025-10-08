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
    async def test_weaviate_create_collection_success(
        self, mock_service_class, sample_properties
    ):
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
    async def test_weaviate_create_collection_with_vectorizer(
        self, mock_service_class, sample_properties
    ):
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
    async def test_weaviate_create_collection_invalid_data_type(
        self, mock_service_class
    ):
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
    async def test_weaviate_create_collection_unsupported_vectorizer(
        self, mock_service_class, sample_properties
    ):
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
    async def test_weaviate_create_collection_service_error(
        self, mock_service_class, sample_properties
    ):
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
    async def test_weaviate_create_collection_exception(
        self, mock_service_class, sample_properties
    ):
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

    # --- Tests for index_searchable Bug Fix ---

    @pytest.mark.asyncio
    @patch("weaviate_mcp.tools.collection_tools.WeaviateService")
    async def test_index_searchable_defaults_for_text_type(self, mock_service_class):
        """Test that index_searchable defaults to True for text types when omitted."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.create_collection.return_value = {
            "success": True,
            "message": "Collection created successfully",
        }
        mock_service_class.return_value = mock_service

        properties = [
            {
                "name": "content",
                "data_type": "text",
                "description": "Text content",
                # index_searchable omitted - should default to True
            }
        ]

        # Act
        result = await weaviate_create_collection(
            name="TestCollection",
            description="Test collection",
            properties=properties,
        )

        # Assert
        assert result["success"] is True
        # Verify the Property was created with index_searchable=True
        call_args = mock_service.create_collection.call_args
        created_properties = call_args.kwargs["properties"]
        assert len(created_properties) == 1
        assert created_properties[0].indexSearchable is True

    @pytest.mark.asyncio
    @patch("weaviate_mcp.tools.collection_tools.WeaviateService")
    async def test_index_searchable_defaults_for_number_type(self, mock_service_class):
        """Test that index_searchable defaults to False for number types when omitted."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.create_collection.return_value = {
            "success": True,
            "message": "Collection created successfully",
        }
        mock_service_class.return_value = mock_service

        properties = [
            {
                "name": "price",
                "data_type": "number",
                "description": "Product price",
                # index_searchable omitted - should default to False
            }
        ]

        # Act
        result = await weaviate_create_collection(
            name="TestCollection",
            description="Test collection",
            properties=properties,
        )

        # Assert
        assert result["success"] is True
        # Verify the Property was created with index_searchable=False
        call_args = mock_service.create_collection.call_args
        created_properties = call_args.kwargs["properties"]
        assert len(created_properties) == 1
        assert created_properties[0].indexSearchable is False

    @pytest.mark.asyncio
    @patch("weaviate_mcp.tools.collection_tools.WeaviateService")
    async def test_index_searchable_defaults_for_int_type(self, mock_service_class):
        """Test that index_searchable defaults to False for int types when omitted."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.create_collection.return_value = {
            "success": True,
            "message": "Collection created successfully",
        }
        mock_service_class.return_value = mock_service

        properties = [
            {
                "name": "chunk_index",
                "data_type": "int",
                "description": "Chunk index",
                # index_searchable omitted - should default to False
            }
        ]

        # Act
        result = await weaviate_create_collection(
            name="TestCollection",
            description="Test collection",
            properties=properties,
        )

        # Assert
        assert result["success"] is True
        # Verify the Property was created with index_searchable=False
        call_args = mock_service.create_collection.call_args
        created_properties = call_args.kwargs["properties"]
        assert len(created_properties) == 1
        assert created_properties[0].indexSearchable is False

    @pytest.mark.asyncio
    @patch("weaviate_mcp.tools.collection_tools.WeaviateService")
    async def test_index_searchable_error_for_number_with_true(
        self, mock_service_class
    ):
        """Test that setting index_searchable=True on number type returns error."""
        # Arrange
        mock_service_class.return_value = AsyncMock()

        properties = [
            {
                "name": "price",
                "data_type": "number",
                "description": "Product price",
                "index_searchable": True,  # Invalid for number type
            }
        ]

        # Act
        result = await weaviate_create_collection(
            name="TestCollection",
            description="Test collection",
            properties=properties,
        )

        # Assert
        assert result["error"] is True
        assert "index_searchable" in result["message"].lower()
        assert "price" in result["message"]
        assert "number" in result["message"]

    @pytest.mark.asyncio
    @patch("weaviate_mcp.tools.collection_tools.WeaviateService")
    async def test_index_searchable_error_for_int_with_true(self, mock_service_class):
        """Test that setting index_searchable=True on int type returns error."""
        # Arrange
        mock_service_class.return_value = AsyncMock()

        properties = [
            {
                "name": "chunk_index",
                "data_type": "int",
                "description": "Chunk index",
                "index_searchable": True,  # Invalid for int type
            }
        ]

        # Act
        result = await weaviate_create_collection(
            name="TestCollection",
            description="Test collection",
            properties=properties,
        )

        # Assert
        assert result["error"] is True
        assert "index_searchable" in result["message"].lower()
        assert "chunk_index" in result["message"]
        assert "int" in result["message"]

    @pytest.mark.asyncio
    @patch("weaviate_mcp.tools.collection_tools.WeaviateService")
    async def test_index_searchable_error_for_boolean_with_true(
        self, mock_service_class
    ):
        """Test that setting index_searchable=True on boolean type returns error."""
        # Arrange
        mock_service_class.return_value = AsyncMock()

        properties = [
            {
                "name": "is_active",
                "data_type": "boolean",
                "description": "Active status",
                "index_searchable": True,  # Invalid for boolean type
            }
        ]

        # Act
        result = await weaviate_create_collection(
            name="TestCollection",
            description="Test collection",
            properties=properties,
        )

        # Assert
        assert result["error"] is True
        assert "index_searchable" in result["message"].lower()
        assert "is_active" in result["message"]
        assert "boolean" in result["message"]

    @pytest.mark.asyncio
    @patch("weaviate_mcp.tools.collection_tools.WeaviateService")
    async def test_index_searchable_defaults_for_text_array(self, mock_service_class):
        """Test that index_searchable defaults to True for text_array types when omitted."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.create_collection.return_value = {
            "success": True,
            "message": "Collection created successfully",
        }
        mock_service_class.return_value = mock_service

        properties = [
            {
                "name": "tags",
                "data_type": "text_array",
                "description": "Tags",
                # index_searchable omitted - should default to True for text_array
            }
        ]

        # Act
        result = await weaviate_create_collection(
            name="TestCollection",
            description="Test collection",
            properties=properties,
        )

        # Assert
        assert result["success"] is True
        # Verify the Property was created with index_searchable=True
        call_args = mock_service.create_collection.call_args
        created_properties = call_args.kwargs["properties"]
        assert len(created_properties) == 1
        assert created_properties[0].indexSearchable is True

    @pytest.mark.asyncio
    @patch("weaviate_mcp.tools.collection_tools.WeaviateService")
    async def test_mixed_properties_with_correct_index_searchable(
        self, mock_service_class
    ):
        """Test a realistic collection with mixed data types and proper index_searchable settings."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.create_collection.return_value = {
            "success": True,
            "message": "Collection created successfully",
        }
        mock_service_class.return_value = mock_service

        # This is the pattern from the optimal workflow
        properties = [
            {
                "name": "content",
                "data_type": "text",
                "description": "Text content",
                # index_searchable defaults to True
            },
            {
                "name": "source_pdf",
                "data_type": "text",
                "description": "Source PDF path",
                "index_searchable": False,  # Explicitly disabled
            },
            {
                "name": "chunk_index",
                "data_type": "int",
                "description": "Chunk index",
                # index_searchable defaults to False
            },
            {
                "name": "title",
                "data_type": "text",
                "description": "Document title",
                # index_searchable defaults to True
            },
        ]

        # Act
        result = await weaviate_create_collection(
            name="ResearchPapers",
            description="Research papers collection",
            properties=properties,
        )

        # Assert
        assert result["success"] is True
        call_args = mock_service.create_collection.call_args
        created_properties = call_args.kwargs["properties"]
        assert len(created_properties) == 4

        # Verify each property's index_searchable setting
        assert created_properties[0].name == "content"
        assert created_properties[0].indexSearchable is True  # text default

        assert created_properties[1].name == "source_pdf"
        assert created_properties[1].indexSearchable is False  # explicitly disabled

        assert created_properties[2].name == "chunk_index"
        assert created_properties[2].indexSearchable is False  # int default

        assert created_properties[3].name == "title"
        assert created_properties[3].indexSearchable is True  # text default
