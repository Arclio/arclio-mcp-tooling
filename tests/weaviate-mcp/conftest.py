"""
Pytest configuration and fixtures for weaviate-mcp tests.
"""

import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from weaviate import WeaviateAsyncClient
from weaviate.classes.config import DataType, Property


@pytest.fixture
def mock_weaviate_config():
    """Mock Weaviate configuration."""
    return {
        "url": "localhost",
        "http_port": 8080,
        "grpc_port": 50051,
    }


@pytest.fixture
def mock_openai_api_key():
    """Mock OpenAI API key."""
    return "test-openai-key"


@pytest.fixture
def mock_env_vars(mock_weaviate_config, mock_openai_api_key):
    """Set up mock environment variables."""
    env_vars = {
        "WEAVIATE_URL": mock_weaviate_config["url"],
        "WEAVIATE_HTTP_PORT": str(mock_weaviate_config["http_port"]),
        "WEAVIATE_GRPC_PORT": str(mock_weaviate_config["grpc_port"]),
        "WEAVIATE_OPENAI_API_KEY": mock_openai_api_key,
    }

    # Store original values
    original_values = {}
    for key, value in env_vars.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = value

    yield env_vars

    # Restore original values
    for key, original_value in original_values.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.fixture
def mock_weaviate_client():
    """Mock WeaviateAsyncClient."""
    client = AsyncMock(spec=WeaviateAsyncClient)

    # Mock collections
    client.collections = MagicMock()
    client.collections.create = AsyncMock()
    client.collections.delete = AsyncMock()
    client.collections.list_all = AsyncMock(return_value={})

    # Mock collection instance
    mock_collection = MagicMock()
    mock_collection.data = MagicMock()
    mock_collection.data.insert = AsyncMock(return_value="test-uuid-123")
    mock_collection.data.update = AsyncMock()
    mock_collection.data.delete_by_id = AsyncMock()

    mock_collection.query = MagicMock()
    mock_collection.query.fetch_object_by_id = AsyncMock()
    mock_collection.query.fetch_objects = AsyncMock()
    mock_collection.query.near_text = AsyncMock()
    mock_collection.query.hybrid = AsyncMock()

    mock_collection.aggregate = MagicMock()
    mock_collection.aggregate.over_all = AsyncMock()

    # Make sure get returns the mock collection directly, not a coroutine
    client.collections.get = MagicMock(return_value=mock_collection)

    return client


@pytest.fixture
def sample_properties():
    """Sample properties for testing."""
    return [
        {
            "name": "title",
            "data_type": "text",
            "description": "Product title",
            "index_filterable": True,
            "index_searchable": True,
        },
        {
            "name": "price",
            "data_type": "number",
            "description": "Product price",
            "index_filterable": True,
            "index_searchable": False,
        },
        {
            "name": "tags",
            "data_type": "text_array",
            "description": "Product tags",
            "index_filterable": False,
            "index_searchable": True,
        },
    ]


@pytest.fixture
def sample_weaviate_properties():
    """Sample Weaviate Property objects for testing."""
    return [
        Property(
            name="title",
            data_type=DataType.TEXT,
            description="Product title",
            index_filterable=True,
            index_searchable=True,
        ),
        Property(
            name="price",
            data_type=DataType.NUMBER,
            description="Product price",
            index_filterable=True,
            index_searchable=False,
        ),
        Property(
            name="tags",
            data_type=DataType.TEXT_ARRAY,
            description="Product tags",
            index_filterable=False,
            index_searchable=True,
        ),
    ]


@pytest.fixture
def sample_object_data():
    """Sample object data for testing."""
    return {
        "title": "Wireless Headphones",
        "price": 99.99,
        "tags": ["electronics", "audio", "wireless"],
    }


@pytest.fixture
def sample_objects_response():
    """Sample objects response for testing."""
    mock_obj1 = MagicMock()
    mock_obj1.properties = {"title": "Product 1", "price": 10.99}
    mock_obj1.uuid = "uuid-1"

    mock_obj2 = MagicMock()
    mock_obj2.properties = {"title": "Product 2", "price": 20.99}
    mock_obj2.uuid = "uuid-2"

    mock_response = MagicMock()
    mock_response.objects = [mock_obj1, mock_obj2]

    return mock_response


@pytest.fixture
def sample_search_response():
    """Sample search response with metadata for testing."""
    mock_obj = MagicMock()
    mock_obj.properties = {"title": "Wireless Headphones", "price": 99.99}
    mock_obj.uuid = "test-uuid"
    mock_obj.metadata = MagicMock()
    mock_obj.metadata.distance = 0.15
    mock_obj.metadata.certainty = 0.85

    mock_response = MagicMock()
    mock_response.objects = [mock_obj]

    return mock_response


# Remove custom event_loop fixture to avoid deprecation warning
# pytest-asyncio will handle event loop creation automatically
