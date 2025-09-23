"""
Collection management tools for Weaviate operations.
"""

import logging
from typing import Any

from weaviate.classes.config import Configure, DataType, Property

from ..app import mcp  # Import from central app module
from ..services.weaviate_service import WeaviateService

logger = logging.getLogger(__name__)


# --- Collection Management Tool Functions --- #


@mcp.tool(
    name="weaviate_create_collection",
    description="Create a new Weaviate collection with custom properties and optional vectorizer for semantic search. Use weaviate_create_collection_with_vectorizer for document ingestion.",
)
async def weaviate_create_collection(
    name: str,
    description: str,
    properties: list[dict[str, Any]],
    vectorizer_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create a new collection in Weaviate.

    Args:
        name: Name of the collection to create
        description: Description of the collection
        properties: List of property definitions, each containing:
            - name: Property name
            - data_type: Data type (text, number, int, boolean, text_array, etc.)
            - description: Property description
            - index_filterable: Whether the property can be filtered (default: True)
            - index_searchable: Whether the property can be searched (default: True)
        vectorizer_config: Optional vectorizer configuration dict with:
            - type: Vectorizer type ("text2vec_openai", "text2vec_transformers", "text2vec_cohere", "text2vec_huggingface", "none")
            - model: Model name (e.g., "text-embedding-3-small" for OpenAI, "sentence-transformers/all-MiniLM-L6-v2" for transformers)
            - pooling_strategy: For transformers only ("masked_mean", "cls", "mean")

    Returns:
        Dictionary with success status and message or error details.

    Example:
        ```python
        await weaviate_create_collection(
            name="Product",
            description="Product catalog",
            properties=[
                {
                    "name": "title",
                    "data_type": "text",
                    "description": "Product title",
                    "index_filterable": True,
                    "index_searchable": True
                },
                {
                    "name": "price",
                    "data_type": "number",
                    "description": "Product price",
                    "index_filterable": True,
                    "index_searchable": False
                }
            ],
            vectorizer_config={
                "type": "text2vec_openai",
                "model": "text-embedding-3-small"
            }
        )
        ```
    """
    try:
        service = WeaviateService()

        # Convert property dictionaries to Property objects
        weaviate_properties = []
        for prop in properties:
            # Validate required fields
            if "name" not in prop:
                return {
                    "error": True,
                    "message": "Property missing required 'name' field. Each property must have: name, data_type, description",
                }
            if "data_type" not in prop:
                return {
                    "error": True,
                    "message": f"Property '{prop.get('name', 'unknown')}' missing required 'data_type' field. "
                    f"Supported types: text, number, int, boolean, text_array, int_array, number_array, boolean_array",
                }

            # Map string data types to Weaviate DataType enum
            data_type_map = {
                "text": DataType.TEXT,
                "string": DataType.TEXT,
                "number": DataType.NUMBER,
                "int": DataType.INT,
                "boolean": DataType.BOOL,
                "text_array": DataType.TEXT_ARRAY,
                "string_array": DataType.TEXT_ARRAY,
                "int_array": DataType.INT_ARRAY,
                "number_array": DataType.NUMBER_ARRAY,
                "boolean_array": DataType.BOOL_ARRAY,
            }

            data_type = data_type_map.get(prop["data_type"].lower())
            if not data_type:
                return {
                    "error": True,
                    "message": f"Unsupported data type: '{prop['data_type']}' for property '{prop['name']}'. "
                    f"Supported types: {list(data_type_map.keys())}",
                }

            weaviate_property = Property(
                name=prop["name"],
                data_type=data_type,
                description=prop.get("description", ""),
                index_filterable=prop.get("index_filterable", True),
                index_searchable=prop.get("index_searchable", True),
            )
            weaviate_properties.append(weaviate_property)

        # Configure vectorizer if provided
        vectorizer = None
        if vectorizer_config:
            vectorizer_type = vectorizer_config.get("type", "").lower()

            if vectorizer_type == "text2vec_openai":
                model = vectorizer_config.get("model", "text-embedding-3-small")
                vectorizer = Configure.Vectorizer.text2vec_openai(model=model)
            elif vectorizer_type == "text2vec_transformers":
                # Support for local transformers vectorizer
                model = vectorizer_config.get(
                    "model", "sentence-transformers/all-MiniLM-L6-v2"
                )
                vectorizer = Configure.Vectorizer.text2vec_transformers(
                    model_name=model,
                    pooling_strategy=vectorizer_config.get(
                        "pooling_strategy", "masked_mean"
                    ),
                )
            elif vectorizer_type == "text2vec_cohere":
                model = vectorizer_config.get("model", "embed-multilingual-v2.0")
                vectorizer = Configure.Vectorizer.text2vec_cohere(model=model)
            elif vectorizer_type == "text2vec_huggingface":
                model = vectorizer_config.get(
                    "model", "sentence-transformers/all-MiniLM-L6-v2"
                )
                vectorizer = Configure.Vectorizer.text2vec_huggingface(model=model)
            elif vectorizer_type in ["none", "disabled", ""]:
                # Explicitly no vectorizer
                vectorizer = None
            else:
                return {
                    "error": True,
                    "message": f"Unsupported vectorizer type: '{vectorizer_config.get('type')}'. "
                    f"Supported types: text2vec_openai, text2vec_transformers, text2vec_cohere, text2vec_huggingface, none",
                }

        # Create the collection
        result = await service.create_collection(
            name=name,
            description=description,
            properties=weaviate_properties,
            vectorizer_config=vectorizer,
            generative_config=Configure.Generative.openai() if vectorizer else None,
        )

        logger.info(f"Collection creation result: {result}")
        return result

    except Exception as e:
        logger.error(f"Error in weaviate_create_collection: {e}")
        return {"error": True, "message": str(e)}


@mcp.tool(
    name="weaviate_delete_collection",
    description="Delete a collection from Weaviate.",
)
async def weaviate_delete_collection(name: str) -> dict[str, Any]:
    """
    Delete a collection from Weaviate.

    Args:
        name: Name of the collection to delete

    Returns:
        Dictionary with success status and message or error details.

    Example:
        ```python
        await weaviate_delete_collection(name="Product")
        ```
    """
    try:
        service = WeaviateService()
        result = await service.delete_collection(name)

        logger.info(f"Collection deletion result: {result}")
        return result

    except Exception as e:
        logger.error(f"Error in weaviate_delete_collection: {e}")
        return {"error": True, "message": str(e)}


@mcp.tool(
    name="weaviate_get_schema",
    description="Get the current schema from Weaviate, showing all collections and their properties.",
)
async def weaviate_get_schema() -> dict[str, Any]:
    """
    Get the current schema from Weaviate.

    Returns:
        Dictionary containing the schema information or error details.
        On success, returns the schema with collection names and their properties.

    Example:
        ```python
        schema = await weaviate_get_schema()
        if not schema.get("error"):
            # Schema info available in return value
            pass
        ```
    """
    try:
        service = WeaviateService()
        result = await service.get_schema()

        logger.info(
            f"Schema retrieval result: {type(result)} with keys: {result.keys() if isinstance(result, dict) else 'N/A'}"
        )
        return result

    except Exception as e:
        logger.error(f"Error in weaviate_get_schema: {e}")
        return {"error": True, "message": str(e)}


@mcp.tool(
    name="weaviate_create_collection_with_vectorizer",
    description="Create a new collection with optimal vectorizer settings for document ingestion and semantic search.",
)
async def weaviate_create_collection_with_vectorizer(
    name: str,
    description: str,
    use_openai_vectorizer: bool = True,
    openai_model: str = "text-embedding-3-small",
) -> dict[str, Any]:
    """
    Create a new collection with optimal settings for document ingestion.

    This is a convenience tool that creates a collection with standard properties
    for document ingestion (content, title, source_url, chunk_index) and
    configures an optimal vectorizer for semantic search.

    Args:
        name: Name of the collection to create
        description: Description of the collection
        use_openai_vectorizer: Whether to use OpenAI vectorizer (default: True)
        openai_model: OpenAI model to use (default: "text-embedding-3-small")

    Returns:
        Dictionary with success status and message or error details.

    Example:
        ```python
        await weaviate_create_collection_with_vectorizer(
            name="Documents",
            description="Collection for document chunks with semantic search",
            use_openai_vectorizer=True,
            openai_model="text-embedding-3-small"
        )
        ```
    """
    try:
        # Define standard properties for document ingestion
        properties = [
            {
                "name": "content",
                "data_type": "text",
                "description": "Text content of the document chunk",
                "index_filterable": True,
                "index_searchable": True,
            },
            {
                "name": "title",
                "data_type": "text",
                "description": "Title of the source document",
                "index_filterable": True,
                "index_searchable": True,
            },
            {
                "name": "source_url",
                "data_type": "text",
                "description": "Source URL or identifier",
                "index_filterable": True,
                "index_searchable": False,
            },
            {
                "name": "chunk_index",
                "data_type": "int",
                "description": "Sequential chunk number for ordering",
                "index_filterable": True,
                "index_searchable": False,
            },
            {
                "name": "total_chunks",
                "data_type": "int",
                "description": "Total number of chunks in the document",
                "index_filterable": True,
                "index_searchable": False,
            },
            {
                "name": "content_type",
                "data_type": "text",
                "description": "MIME type of the original content",
                "index_filterable": True,
                "index_searchable": False,
            },
        ]

        # Configure vectorizer
        vectorizer_config = None
        if use_openai_vectorizer:
            vectorizer_config = {
                "type": "text2vec_openai",
                "model": openai_model,
            }

        # Create the collection using the main creation tool
        result = await weaviate_create_collection(
            name=name,
            description=description,
            properties=properties,
            vectorizer_config=vectorizer_config,
        )

        if result.get("success"):
            logger.info(
                f"Created optimized collection '{name}' with vectorizer: {use_openai_vectorizer}"
            )
            result["message"] = (
                f"Collection '{name}' created successfully with optimal settings for document ingestion. "
                f"Vectorizer: {'OpenAI ' + openai_model if use_openai_vectorizer else 'None'}"
            )

        return result

    except Exception as e:
        logger.error(f"Error in weaviate_create_collection_with_vectorizer: {e}")
        return {"error": True, "message": str(e)}
