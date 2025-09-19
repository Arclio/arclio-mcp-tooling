"""
Schema management and validation tools for Weaviate operations.
"""

import logging
from typing import Any

from ..app import mcp  # Import from central app module
from ..services.weaviate_service import WeaviateService

logger = logging.getLogger(__name__)


# --- Schema Management Tool Functions --- #


@mcp.tool(
    name="weaviate_get_schema_info",
    description="Get detailed schema information including collection counts and property details.",
)
async def weaviate_get_schema_info() -> dict[str, Any]:
    """
    Get detailed schema information with collection counts and property details.

    Returns:
        Dictionary containing detailed schema information or error details.
        Includes collection names, object counts, properties, and vectorizer info.

    Example:
        ```python
        info = await weaviate_get_schema_info()
        if not info.get("error"):
            pass  # Schema info available in return value
        ```
    """
    try:
        service = WeaviateService()
        schema_result = await service.get_schema()

        if schema_result.get("error"):
            return schema_result

        # Build detailed schema information
        schema_info = []
        schema_info.append("Weaviate Schema Information:")
        schema_info.append("")

        if not schema_result:
            schema_info.append("No collections found in the schema.")
            return {"schema_info": "\n".join(schema_info)}

        for collection_name, collection_info in schema_result.items():
            # Get object count for this collection
            count_result = await service.aggregate(collection_name)
            count = 0
            if count_result.get("success") and count_result.get("results"):
                count = count_result["results"].get("total_count", 0)

            schema_info.extend(
                [
                    f"Collection: {collection_name}",
                    f"  Object Count: {count}",
                    "  Properties:",
                ]
            )

            # Add property information if available
            if hasattr(collection_info, "properties") and collection_info.properties:
                for prop in collection_info.properties:
                    prop_info = f"    - {prop.name}"
                    if hasattr(prop, "data_type"):
                        prop_info += f" (Type: {prop.data_type})"
                    if hasattr(prop, "description") and prop.description:
                        prop_info += f" - {prop.description}"
                    schema_info.append(prop_info)
            else:
                schema_info.append("    - No property details available")

            # Add vectorizer information if available
            if hasattr(collection_info, "vectorizer"):
                schema_info.append(f"  Vectorizer: {collection_info.vectorizer}")

            schema_info.append("")

        logger.info("Schema info generated successfully")
        return {"schema_info": "\n".join(schema_info)}

    except Exception as e:
        logger.error(f"Error in weaviate_get_schema_info: {e}")
        return {"error": True, "message": str(e)}


@mcp.tool(
    name="weaviate_validate_collection_exists",
    description="Validate that a specific collection exists in the Weaviate schema.",
)
async def weaviate_validate_collection_exists(collection_name: str) -> dict[str, Any]:
    """
    Validate that a specific collection exists in the Weaviate schema.

    Args:
        collection_name: Name of the collection to validate

    Returns:
        Dictionary with validation result and collection details or error.

    Example:
        ```python
        result = await weaviate_validate_collection_exists("Product")
        if result["exists"]:
            pass  # Collection info available in return value
        ```
    """
    try:
        service = WeaviateService()
        schema_result = await service.get_schema()

        if schema_result.get("error"):
            return schema_result

        exists = collection_name in schema_result

        if exists:
            collection_info = schema_result[collection_name]
            property_count = 0

            if hasattr(collection_info, "properties") and collection_info.properties:
                property_count = len(collection_info.properties)

            # Get object count
            count_result = await service.aggregate(collection_name)
            object_count = 0
            if count_result.get("success") and count_result.get("results"):
                object_count = count_result["results"].get("total_count", 0)

            return {
                "exists": True,
                "collection_name": collection_name,
                "property_count": property_count,
                "object_count": object_count,
                "message": f"Collection '{collection_name}' exists with {property_count} properties and {object_count} objects",
            }
        return {
            "exists": False,
            "collection_name": collection_name,
            "message": f"Collection '{collection_name}' does not exist",
            "available_collections": list(schema_result.keys()),
        }

    except Exception as e:
        logger.error(f"Error in weaviate_validate_collection_exists: {e}")
        return {"error": True, "message": str(e)}


@mcp.tool(
    name="weaviate_get_collection_properties",
    description="Get detailed property information for a specific collection.",
)
async def weaviate_get_collection_properties(collection_name: str) -> dict[str, Any]:
    """
    Get detailed property information for a specific collection.

    Args:
        collection_name: Name of the collection

    Returns:
        Dictionary containing property details or error information.

    Example:
        ```python
        props = await weaviate_get_collection_properties("Product")
        if not props.get("error"):
            # Properties info available in return value
            pass
        ```
    """
    try:
        service = WeaviateService()
        schema_result = await service.get_schema()

        if schema_result.get("error"):
            return schema_result

        if collection_name not in schema_result:
            return {
                "error": True,
                "message": f"Collection '{collection_name}' does not exist",
                "available_collections": list(schema_result.keys()),
            }

        collection_info = schema_result[collection_name]
        properties = {}

        if hasattr(collection_info, "properties") and collection_info.properties:
            for prop in collection_info.properties:
                prop_details = {
                    "name": prop.name,
                    "description": getattr(prop, "description", ""),
                }

                # Add data type information
                if hasattr(prop, "data_type"):
                    prop_details["data_type"] = str(prop.data_type)

                # Add indexing information
                if hasattr(prop, "index_filterable"):
                    prop_details["filterable"] = prop.index_filterable
                if hasattr(prop, "index_searchable"):
                    prop_details["searchable"] = prop.index_searchable

                properties[prop.name] = prop_details

        return {
            "collection_name": collection_name,
            "properties": properties,
            "property_count": len(properties),
            "message": f"Retrieved {len(properties)} properties for collection '{collection_name}'",
        }

    except Exception as e:
        logger.error(f"Error in weaviate_get_collection_properties: {e}")
        return {"error": True, "message": str(e)}


@mcp.tool(
    name="weaviate_compare_collections",
    description="Compare properties between two collections to identify differences.",
)
async def weaviate_compare_collections(
    collection1_name: str,
    collection2_name: str,
) -> dict[str, Any]:
    """
    Compare properties between two collections to identify differences.

    Args:
        collection1_name: Name of the first collection
        collection2_name: Name of the second collection

    Returns:
        Dictionary containing comparison results or error information.

    Example:
        ```python
        comparison = await weaviate_compare_collections("Product", "ProductV2")
        if not comparison.get("error"):
            # Comparison info available in return value
            pass
        ```
    """
    try:
        service = WeaviateService()
        schema_result = await service.get_schema()

        if schema_result.get("error"):
            return schema_result

        # Validate both collections exist
        missing_collections = []
        if collection1_name not in schema_result:
            missing_collections.append(collection1_name)
        if collection2_name not in schema_result:
            missing_collections.append(collection2_name)

        if missing_collections:
            return {
                "error": True,
                "message": f"Collections not found: {missing_collections}",
                "available_collections": list(schema_result.keys()),
            }

        # Get properties for both collections
        coll1_props = {}
        coll2_props = {}

        for collection_name, props_dict in [
            (collection1_name, coll1_props),
            (collection2_name, coll2_props),
        ]:
            collection_info = schema_result[collection_name]
            if hasattr(collection_info, "properties") and collection_info.properties:
                for prop in collection_info.properties:
                    props_dict[prop.name] = {
                        "data_type": str(getattr(prop, "data_type", "unknown")),
                        "description": getattr(prop, "description", ""),
                        "filterable": getattr(prop, "index_filterable", None),
                        "searchable": getattr(prop, "index_searchable", None),
                    }

        # Compare properties
        coll1_prop_names = set(coll1_props.keys())
        coll2_prop_names = set(coll2_props.keys())

        common_properties = coll1_prop_names & coll2_prop_names
        only_in_coll1 = coll1_prop_names - coll2_prop_names
        only_in_coll2 = coll2_prop_names - coll1_prop_names

        # Check for differences in common properties
        property_differences = {}
        for prop_name in common_properties:
            prop1 = coll1_props[prop_name]
            prop2 = coll2_props[prop_name]

            differences = {}
            for key in prop1:
                if prop1[key] != prop2[key]:
                    differences[key] = {
                        collection1_name: prop1[key],
                        collection2_name: prop2[key],
                    }

            if differences:
                property_differences[prop_name] = differences

        return {
            "collection1": collection1_name,
            "collection2": collection2_name,
            "common_properties": list(common_properties),
            "only_in_collection1": list(only_in_coll1),
            "only_in_collection2": list(only_in_coll2),
            "property_differences": property_differences,
            "summary": {
                "total_common": len(common_properties),
                "unique_to_coll1": len(only_in_coll1),
                "unique_to_coll2": len(only_in_coll2),
                "properties_with_differences": len(property_differences),
            },
        }

    except Exception as e:
        logger.error(f"Error in weaviate_compare_collections: {e}")
        return {"error": True, "message": str(e)}


@mcp.tool(
    name="weaviate_get_database_stats",
    description="Get overall database statistics including total collections and objects.",
)
async def weaviate_get_database_stats() -> dict[str, Any]:
    """
    Get overall database statistics including total collections and objects.

    Returns:
        Dictionary containing database statistics or error information.

    Example:
        ```python
        stats = await weaviate_get_database_stats()
        if not stats.get("error"):
            # Database stats available in return value
            pass
        ```
    """
    try:
        service = WeaviateService()
        schema_result = await service.get_schema()

        if schema_result.get("error"):
            return schema_result

        total_collections = len(schema_result)
        total_objects = 0
        collection_stats = {}

        # Get object count for each collection
        for collection_name in schema_result:
            count_result = await service.aggregate(collection_name)
            count = 0
            if count_result.get("success") and count_result.get("results"):
                count = count_result["results"].get("total_count", 0)

            collection_stats[collection_name] = count
            total_objects += count

        return {
            "total_collections": total_collections,
            "total_objects": total_objects,
            "collection_stats": collection_stats,
            "collections": list(schema_result.keys()),
            "message": f"Database contains {total_collections} collections with {total_objects} total objects",
        }

    except Exception as e:
        logger.error(f"Error in weaviate_get_database_stats: {e}")
        return {"error": True, "message": str(e)}
