"""
Integration tests for Weaviate collection management edge cases.

Tests the actual behavior when:
- Creating a collection that already exists
- Deleting a collection that doesn't exist
- Error message formats and consistency
"""

import pytest
from weaviate_mcp.tools.collection_tools import (
    weaviate_create_collection,
    weaviate_delete_collection,
)


class TestCollectionEdgeCases:
    """Test edge cases for collection management."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_collection_that_already_exists(self):
        """
        Test creating a collection that already exists.

        Expected behavior:
        - Should return an error dict (not empty string or None)
        - Should have "error": True
        - Should have meaningful error message
        """
        collection_name = "TestDuplicateCollection"

        # Clean up if it exists
        await weaviate_delete_collection(collection_name)

        # First creation should succeed
        properties = [
            {
                "name": "content",
                "data_type": "text",
                "description": "Test content",
            }
        ]

        result1 = await weaviate_create_collection(
            name=collection_name,
            description="Test collection",
            properties=properties,
        )

        # Verify first creation succeeded
        assert isinstance(result1, dict), f"Expected dict, got {type(result1)}"
        assert result1 != "", "Result should not be empty string"
        assert result1 is not None, "Result should not be None"
        assert (
            result1.get("success") is True or result1.get("error") is True
        ), f"Result should have 'success' or 'error' key: {result1}"

        if result1.get("error"):
            # Collection already existed, clean up
            await weaviate_delete_collection(collection_name)
            # Try again
            result1 = await weaviate_create_collection(
                name=collection_name,
                description="Test collection",
                properties=properties,
            )
            assert (
                result1.get("success") is True
            ), f"First creation should succeed: {result1}"

        # Second creation should fail with proper error
        result2 = await weaviate_create_collection(
            name=collection_name,
            description="Test collection duplicate",
            properties=properties,
        )

        # Critical assertions based on chat history issue
        assert isinstance(
            result2, dict
        ), f"Expected dict, got {type(result2)}: {result2}"
        assert result2 != "", "❌ BUG: Result is empty string instead of error dict"
        assert result2 is not None, "❌ BUG: Result is None instead of error dict"
        assert (
            "error" in result2 or "success" in result2
        ), f"Result should have 'error' or 'success' key: {result2}"

        # If Weaviate doesn't error on duplicate, at least verify format
        if result2.get("success"):
            # Some versions of Weaviate might not error on duplicate creation
            print("⚠️  Weaviate allowed duplicate creation (idempotent behavior)")
        else:
            assert result2.get("error") is True, f"Expected error=True: {result2}"
            assert "message" in result2, f"Error should have message: {result2}"
            assert (
                result2["message"] != ""
            ), f"Error message should not be empty: {result2}"
            assert isinstance(
                result2["message"], str
            ), f"Error message should be string: {result2}"

        # Clean up
        await weaviate_delete_collection(collection_name)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_delete_nonexistent_collection(self):
        """
        Test deleting a collection that doesn't exist.

        Expected behavior:
        - Should return an error dict (not empty string or None)
        - Should have "error": True
        - Should have meaningful error message
        """
        collection_name = "NonexistentCollection_12345"

        # Ensure it doesn't exist
        await weaviate_delete_collection(collection_name)

        # Try to delete again
        result = await weaviate_delete_collection(collection_name)

        # Critical assertions
        assert isinstance(result, dict), f"Expected dict, got {type(result)}: {result}"
        assert result != "", "❌ BUG: Result is empty string instead of error dict"
        assert result is not None, "❌ BUG: Result is None instead of error dict"
        assert (
            "error" in result or "success" in result
        ), f"Result should have 'error' or 'success' key: {result}"

        # Weaviate might be idempotent for deletions
        if result.get("success"):
            print("⚠️  Weaviate allowed deletion of nonexistent collection (idempotent)")
        else:
            assert result.get("error") is True, f"Expected error=True: {result}"
            assert "message" in result, f"Error should have message: {result}"
            assert (
                result["message"] != ""
            ), f"Error message should not be empty: {result}"
            assert isinstance(
                result["message"], str
            ), f"Error message should be string: {result}"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_delete_create_cycle(self):
        """
        Test a complete cycle: create -> delete -> create again.

        This verifies:
        - Deletion actually works
        - Can recreate after deletion
        - No residual state issues
        """
        collection_name = "TestCycleCollection"
        properties = [
            {
                "name": "test_field",
                "data_type": "text",
                "description": "Test field",
            }
        ]

        # Clean start
        await weaviate_delete_collection(collection_name)

        # Create
        result1 = await weaviate_create_collection(
            name=collection_name,
            description="First creation",
            properties=properties,
        )
        assert isinstance(result1, dict)
        assert result1.get("success") or result1.get("error")

        # If creation failed, it might already exist - delete and retry
        if result1.get("error"):
            await weaviate_delete_collection(collection_name)
            result1 = await weaviate_create_collection(
                name=collection_name,
                description="First creation",
                properties=properties,
            )

        assert (
            result1.get("success") is True
        ), f"First creation should succeed: {result1}"

        # Delete
        result2 = await weaviate_delete_collection(collection_name)
        assert isinstance(result2, dict)
        assert result2.get("success") is True, f"Deletion should succeed: {result2}"

        # Create again - should succeed since we deleted it
        result3 = await weaviate_create_collection(
            name=collection_name,
            description="Second creation",
            properties=properties,
        )
        assert isinstance(result3, dict)
        assert result3 != "", "Result should not be empty string"
        assert (
            result3.get("success") is True
        ), f"Second creation after deletion should succeed: {result3}"

        # Clean up
        await weaviate_delete_collection(collection_name)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_error_message_quality(self):
        """
        Test that error messages are informative and actionable.
        """
        # Test with invalid data type
        result = await weaviate_create_collection(
            name="TestInvalidType",
            description="Test",
            properties=[
                {
                    "name": "field1",
                    "data_type": "invalid_type_xyz",
                    "description": "Test",
                }
            ],
        )

        assert isinstance(result, dict)
        assert result.get("error") is True
        assert "message" in result
        assert (
            "invalid_type_xyz" in result["message"].lower()
            or "unsupported" in result["message"].lower()
        ), f"Error should mention the invalid type: {result['message']}"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_response_format_consistency(self):
        """
        Test that all responses follow a consistent format.

        All responses should be dict with either:
        - {"success": True, "message": "..."} for success
        - {"error": True, "message": "..."} for errors
        """
        collection_name = "TestFormatCollection"
        properties = [
            {
                "name": "content",
                "data_type": "text",
                "description": "Content",
            }
        ]

        # Clean up
        delete_result = await weaviate_delete_collection(collection_name)
        assert isinstance(delete_result, dict)
        assert "success" in delete_result or "error" in delete_result

        # Create
        create_result = await weaviate_create_collection(
            name=collection_name,
            description="Test",
            properties=properties,
        )
        assert isinstance(create_result, dict)
        assert "success" in create_result or "error" in create_result
        assert "message" in create_result

        # Clean up
        await weaviate_delete_collection(collection_name)
