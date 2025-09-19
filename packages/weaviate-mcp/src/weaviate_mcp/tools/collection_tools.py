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
    description="Create a new collection in Weaviate with specified properties and configuration.",
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
            - model: Model name (e.g., "text-embedding-3-small")
            - type: Vectorizer type (e.g., "text2vec_openai")

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
            if vectorizer_config.get("type") == "text2vec_openai":
                model = vectorizer_config.get("model", "text-embedding-3-small")
                vectorizer = Configure.Vectorizer.text2vec_openai(model=model)
            else:
                return {
                    "error": True,
                    "message": f"Unsupported vectorizer type: {vectorizer_config.get('type')}",
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
