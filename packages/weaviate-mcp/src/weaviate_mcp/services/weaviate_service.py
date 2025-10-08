"""Weaviate service implementation for MCP server."""

import logging
from typing import Any

from weaviate import WeaviateAsyncClient
from weaviate.classes.config import Configure, Property
from weaviate.classes.init import AdditionalConfig, Timeout
from weaviate.classes.query import Filter, MetadataQuery, Sort
from weaviate.connect import ConnectionParams

from ..auth import get_openai_api_key
from ..config import get_weaviate_config

logger = logging.getLogger(__name__)


class WeaviateService:
    """Weaviate service for MCP server with fail-safe error handling."""

    def __init__(self):
        """Initialize the Weaviate service."""
        self._client = None
        self._connected = False

    async def _ensure_connected(self) -> bool:
        """Ensure the client is connected."""
        if self._client and self._connected:
            return True

        try:
            # Get configuration from environment
            config = get_weaviate_config()
            openai_api_key = get_openai_api_key()

            # Create the Weaviate client
            self._client = WeaviateAsyncClient(
                connection_params=ConnectionParams.from_params(
                    http_host=config["url"],
                    http_port=config["http_port"],
                    http_secure=False,  # Default to False for local development
                    grpc_host=config["url"],
                    grpc_port=config["grpc_port"],
                    grpc_secure=False,  # Default to False for local development
                ),
                additional_headers={"X-OpenAI-Api-Key": openai_api_key},
                additional_config=AdditionalConfig(
                    timeout=Timeout(
                        init=30,
                        query=60,
                        insert=120,
                    ),
                ),
                skip_init_checks=False,
            )

            # Connect the client
            await self._client.connect()
            self._connected = True
            logger.info("WeaviateService connected successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to connect WeaviateService: {e}")
            self._client = None
            self._connected = False
            return False

    async def close(self):
        """Close the Weaviate connection."""
        if self._client and self._connected:
            try:
                await self._client.close()
                logger.info("WeaviateService connection closed")
            except Exception as e:
                logger.error(f"Error closing WeaviateService: {e}")
            finally:
                self._client = None
                self._connected = False

    # Collection management methods
    async def get_schema(self) -> dict[str, Any]:
        """Get current schema."""
        try:
            if not await self._ensure_connected():
                return {"error": True, "message": "Failed to connect to Weaviate"}

            return await self._client.collections.list_all()
        except Exception as e:
            logger.error(f"Error getting schema: {e}")
            return {"error": True, "message": str(e)}

    async def create_collection(
        self,
        name: str,
        description: str,
        properties: list[Property],
        vectorizer_config: Configure.Vectorizer | None = None,
        generative_config: Configure.Generative | None = None,
    ) -> dict[str, Any]:
        """Create a new collection."""
        try:
            if not await self._ensure_connected():
                return {"error": True, "message": "Failed to connect to Weaviate"}

            await self._client.collections.create(
                name=name,
                description=description,
                properties=properties,
                vectorizer_config=vectorizer_config,
                generative_config=generative_config,
            )
            return {
                "success": True,
                "message": f"Collection '{name}' created successfully",
            }
        except Exception as e:
            error_message = str(e)

            # Provide more specific error messages for common cases
            if "already exists" in error_message.lower():
                error_message = f"Collection '{name}' already exists. Delete it first or use a different name."
            elif (
                "invalid" in error_message.lower()
                and "property" in error_message.lower()
            ):
                error_message = f"Invalid property configuration for collection '{name}': {error_message}"
            elif "unexpected status code: 422" in error_message:
                error_message = f"Collection '{name}' may not have been created properly. Weaviate validation error: {error_message}"

            logger.error(f"Error creating collection {name}: {error_message}")
            return {"error": True, "message": error_message}

    async def delete_collection(self, name: str) -> dict[str, Any]:
        """Delete a collection."""
        try:
            if not await self._ensure_connected():
                return {"error": True, "message": "Failed to connect to Weaviate"}

            await self._client.collections.delete(name)
            return {
                "success": True,
                "message": f"Collection '{name}' deleted successfully",
            }
        except Exception as e:
            error_message = str(e)

            # Provide more specific error messages for common cases
            if (
                "not found" in error_message.lower()
                or "does not exist" in error_message.lower()
            ):
                # Some Weaviate versions might error on non-existent collections
                logger.warning(f"Attempted to delete non-existent collection '{name}'")
                # Treat as success (idempotent) since the desired state is achieved
                return {
                    "success": True,
                    "message": f"Collection '{name}' did not exist (already deleted or never created)",
                }

            logger.error(f"Error deleting collection {name}: {error_message}")
            return {"error": True, "message": error_message}

    # Object operations
    async def insert_object(
        self,
        collection_name: str,
        data: dict[str, Any],
        unique_properties: list[str] | None = None,
    ) -> dict[str, Any]:
        """Insert a new object."""
        try:
            if not await self._ensure_connected():
                return {"error": True, "message": "Failed to connect to Weaviate"}

            collection = self._client.collections.get(collection_name)

            if unique_properties:
                # Build list of filters for unique properties
                filter_conditions = [
                    Filter.by_property(prop).equal(data.get(prop))
                    for prop in unique_properties
                    if prop in data and data.get(prop) is not None
                ]

                if filter_conditions:
                    # Use Filter.all_of() with a list of conditions
                    filters = Filter.all_of(filter_conditions)
                    existing_result = await self.get_objects(
                        collection_name, filters=filters, limit=1
                    )
                else:
                    # No valid filter conditions, skip duplicate check
                    existing_result = {"objects": []}
                if existing_result.get("objects"):
                    logger.warning(
                        f"Object with properties {unique_properties} already exists"
                    )
                    return {
                        "success": True,
                        "object_id": existing_result["objects"][0]["id"],
                    }

            object_id = await collection.data.insert(data)
            return {"success": True, "object_id": str(object_id)}
        except Exception as e:
            logger.error(f"Error inserting object into {collection_name}: {e}")
            return {"error": True, "message": str(e)}

    async def get_object(
        self,
        collection_name: str,
        uuid: str,
        include_vector: bool = False,
        return_properties: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get object by ID."""
        try:
            if not await self._ensure_connected():
                return {"error": True, "message": "Failed to connect to Weaviate"}

            collection = self._client.collections.get(collection_name)
            result = await collection.query.fetch_object_by_id(
                uuid,
                include_vector=include_vector,
                return_properties=return_properties,
            )

            if result:
                properties = result.properties
                properties["id"] = str(result.uuid)
                return properties
            return {"error": True, "message": f"Object {uuid} not found"}
        except Exception as e:
            logger.error(f"Error getting object {uuid} from {collection_name}: {e}")
            return {"error": True, "message": str(e)}

    async def get_objects(
        self,
        collection_name: str,
        filters: Filter | None = None,
        limit: int = 20,
        offset: int = 0,
        sort: Sort | None = None,
        return_properties: list[str] | None = None,
        include_vector: bool = False,
    ) -> dict[str, Any]:
        """Get objects from a collection."""
        try:
            if not await self._ensure_connected():
                return {"error": True, "message": "Failed to connect to Weaviate"}

            collection = self._client.collections.get(collection_name)
            results = await collection.query.fetch_objects(
                filters=filters,
                limit=limit,
                offset=offset,
                sort=sort,
                return_properties=return_properties,
                include_vector=include_vector,
            )

            objects = []
            for obj in results.objects:
                properties = obj.properties
                properties["id"] = str(obj.uuid)
                objects.append(properties)

            return {"objects": objects, "count": len(objects)}
        except Exception as e:
            logger.error(
                f"Error retrieving objects from collection {collection_name}: {e}"
            )
            return {"error": True, "message": str(e)}

    # Search operations
    async def search(
        self,
        collection_name: str,
        query_text: str,
        filters: Filter | None = None,
        limit: int = 10,
        offset: int = 0,
        include_vector: bool = False,
        return_properties: list[str] | None = None,
    ) -> dict[str, Any]:
        """Perform semantic search."""
        try:
            if not await self._ensure_connected():
                return {"error": True, "message": "Failed to connect to Weaviate"}

            collection = self._client.collections.get(collection_name)
            results = await collection.query.near_text(
                query=query_text,
                filters=filters,
                limit=limit,
                offset=offset,
                include_vector=include_vector,
                return_properties=return_properties,
                return_metadata=MetadataQuery(distance=True, certainty=True),
            )

            objects = []
            for obj in results.objects:
                properties = obj.properties
                properties["id"] = str(obj.uuid)
                properties["distance"] = obj.metadata.distance
                properties["certainty"] = obj.metadata.certainty
                objects.append(properties)

            return {"objects": objects, "count": len(objects)}
        except Exception as e:
            logger.error(f"Error searching in {collection_name}: {e}")
            return {"error": True, "message": str(e)}

    async def hybrid_search(
        self,
        collection_name: str,
        query_text: str,
        filters: Filter | None = None,
        limit: int = 10,
        alpha: float = 0.5,
        include_vector: bool = False,
        return_properties: list[str] | None = None,
    ) -> dict[str, Any]:
        """Perform hybrid search (semantic + keyword)."""
        try:
            if not await self._ensure_connected():
                return {"error": True, "message": "Failed to connect to Weaviate"}

            collection = self._client.collections.get(collection_name)
            results = await collection.query.hybrid(
                query=query_text,
                alpha=alpha,
                filters=filters,
                limit=limit,
                include_vector=include_vector,
                return_properties=return_properties,
                return_metadata=MetadataQuery(distance=True, certainty=True),
            )

            objects = []
            for obj in results.objects:
                properties = obj.properties
                properties["id"] = str(obj.uuid)
                properties["distance"] = obj.metadata.distance
                properties["certainty"] = obj.metadata.certainty
                objects.append(properties)

            return {"objects": objects, "count": len(objects)}
        except Exception as e:
            logger.error(f"Error performing hybrid search in {collection_name}: {e}")
            return {"error": True, "message": str(e)}

    # Additional object operations
    async def update_object(
        self,
        collection_name: str,
        uuid: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Update an existing object."""
        try:
            if not await self._ensure_connected():
                return {"error": True, "message": "Failed to connect to Weaviate"}

            collection = self._client.collections.get(collection_name)
            await collection.data.update(uuid, data)
            return {"success": True, "message": f"Object {uuid} updated successfully"}
        except Exception as e:
            logger.error(f"Error updating object {uuid} in {collection_name}: {e}")
            return {"error": True, "message": str(e)}

    async def delete_object(
        self,
        collection_name: str,
        uuid: str,
    ) -> dict[str, Any]:
        """Delete an object."""
        try:
            if not await self._ensure_connected():
                return {"error": True, "message": "Failed to connect to Weaviate"}

            collection = self._client.collections.get(collection_name)
            await collection.data.delete_by_id(uuid)
            return {"success": True, "message": f"Object {uuid} deleted successfully"}
        except Exception as e:
            logger.error(f"Error deleting object {uuid} from {collection_name}: {e}")
            return {"error": True, "message": str(e)}

    async def batch_insert_objects(
        self,
        collection_name: str,
        objects: list[dict[str, Any]],
        unique_properties: list[str] | None = None,
        batch_size: int = 100,
    ) -> dict[str, Any]:
        """Batch insert objects."""
        try:
            if not await self._ensure_connected():
                return {"error": True, "message": "Failed to connect to Weaviate"}

            inserted_ids: list[str] = []
            for start_idx in range(0, len(objects), batch_size):
                chunk = objects[start_idx : start_idx + batch_size]

                # Process each object in the chunk
                chunk_results = []
                for obj in chunk:
                    if unique_properties:
                        # Check for existing objects with unique properties
                        filter_conditions = [
                            Filter.by_property(prop).equal(obj.get(prop))
                            for prop in unique_properties
                            if prop in obj and obj.get(prop) is not None
                        ]

                        if filter_conditions:
                            # Use Filter.all_of() with a list of conditions
                            filters = Filter.all_of(filter_conditions)
                            existing_result = await self.get_objects(
                                collection_name, filters=filters, limit=1
                            )
                        else:
                            # No valid filter conditions, skip duplicate check
                            existing_result = {"objects": []}
                        if existing_result.get("objects"):
                            logger.warning(
                                f"Object with properties {unique_properties} already exists"
                            )
                            chunk_results.append(existing_result["objects"][0]["id"])
                            continue

                    # Insert new object
                    insert_result = await self.insert_object(collection_name, obj)
                    if insert_result.get("success"):
                        chunk_results.append(insert_result["object_id"])
                    else:
                        return insert_result  # Return error if any insertion fails

                inserted_ids.extend(chunk_results)

            return {
                "success": True,
                "inserted_ids": inserted_ids,
                "count": len(inserted_ids),
            }
        except Exception as e:
            logger.error(f"Error batch inserting objects into {collection_name}: {e}")
            return {"error": True, "message": str(e)}

    async def aggregate(
        self,
        collection_name: str,
        group_by: list[str] | None = None,
        properties: list[str] | None = None,
    ) -> dict[str, Any]:
        """Perform aggregation on a collection."""
        try:
            if not await self._ensure_connected():
                return {"error": True, "message": "Failed to connect to Weaviate"}

            collection = self._client.collections.get(collection_name)
            query = collection.aggregate

            if group_by:
                query = query.group_by(group_by)
            if properties:
                for prop in properties:
                    query = query.with_fields(prop)

            results = await query.over_all(total_count=True)

            # Convert AggregateReturn to dictionary
            result_dict = {}
            if hasattr(results, "total_count"):
                result_dict["total_count"] = results.total_count
            if hasattr(results, "groups") and results.groups:
                result_dict["groups"] = []
                for group in results.groups:
                    group_dict = {}
                    if hasattr(group, "grouped_by"):
                        group_dict["grouped_by"] = group.grouped_by
                    if hasattr(group, "total_count"):
                        group_dict["total_count"] = group.total_count
                    result_dict["groups"].append(group_dict)

            logger.info(
                f"Aggregation results for collection {collection_name}: {result_dict}"
            )
            return {"success": True, "results": result_dict}
        except Exception as e:
            logger.error(
                f"Error performing aggregation in collection {collection_name}: {e}"
            )
            return {"error": True, "message": str(e)}

    async def batch_check_existing_files(
        self,
        collection_name: str,
        file_keys: list[str],
        source_field: str = "source_pdf",
    ) -> dict[str, Any]:
        """Check which files from a list already exist in Weaviate.

        This method efficiently checks multiple files in a single query,
        filtering them into 'new' and 'existing' categories based on
        whether they already exist in the specified collection.

        Args:
            collection_name: Name of the Weaviate collection to check
            file_keys: List of file identifiers to check (e.g., S3 keys, file paths)
            source_field: Name of the field containing the source identifier
                         (default: "source_pdf")

        Returns:
            Dictionary containing:
                - new_files: Array of file keys that do NOT exist in Weaviate
                - existing_files: Array of file keys that already exist
                - new_count: Count of new files
                - existing_count: Count of existing files
                - total_checked: Total number of files checked

        Note:
            This method requires the collection schema to have a field
            (specified by source_field) that stores file identifiers.
        """
        try:
            if not await self._ensure_connected():
                return {"error": True, "message": "Failed to connect to Weaviate"}

            # Handle empty input
            if not file_keys:
                return {
                    "new_files": [],
                    "existing_files": [],
                    "new_count": 0,
                    "existing_count": 0,
                    "total_checked": 0,
                }

            collection = self._client.collections.get(collection_name)

            # Build OR filter for all file keys
            # Use containsAny filter which is more efficient for this use case
            filter_conditions = [
                Filter.by_property(source_field).equal(file_key)
                for file_key in file_keys
            ]

            # Combine with OR operator if we have multiple conditions
            if len(filter_conditions) > 1:
                filters = Filter.any_of(filter_conditions)
            elif len(filter_conditions) == 1:
                filters = filter_conditions[0]
            else:
                filters = None

            # Query for objects with matching source field
            # Use a high limit since each file may have multiple chunks
            # We only need unique source_field values, but must fetch enough objects
            results = await collection.query.fetch_objects(
                filters=filters,
                limit=10000,  # High limit to capture all unique files even with many chunks each
                return_properties=[source_field],
                include_vector=False,
            )

            # Extract unique existing file keys from results
            existing_keys = set()
            for obj in results.objects:
                if source_field in obj.properties:
                    existing_keys.add(obj.properties[source_field])

            # Determine which files are new
            file_keys_set = set(file_keys)
            new_keys = file_keys_set - existing_keys

            # Return sorted lists for consistency
            return {
                "new_files": sorted(new_keys),
                "existing_files": sorted(existing_keys),
                "new_count": len(new_keys),
                "existing_count": len(existing_keys),
                "total_checked": len(file_keys),
            }

        except Exception as e:
            logger.error(
                f"Error batch checking files in collection {collection_name}: {e}"
            )
            return {"error": True, "message": str(e)}
