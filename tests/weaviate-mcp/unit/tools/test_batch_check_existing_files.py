"""Unit tests for weaviate_batch_check_existing_files tool."""

import pytest
from weaviate_mcp.tools.data_tools import weaviate_batch_check_existing_files


class TestBatchCheckExistingFiles:
    """Test cases for batch file existence checking."""

    @pytest.mark.asyncio
    async def test_batch_check_all_new_files(self, weaviate_test_collection):
        """Test batch checking when all files are new (don't exist)."""
        collection_name = weaviate_test_collection

        # Check for files that don't exist
        file_keys = [
            "brand_new_file_1.pdf",
            "brand_new_file_2.pdf",
            "brand_new_file_3.pdf",
        ]

        result = await weaviate_batch_check_existing_files(
            collection_name=collection_name,
            file_keys=file_keys,
            source_field="source_pdf",
        )

        # Verify results
        assert not result.get("error"), f"Unexpected error: {result.get('message')}"
        assert result["new_count"] == 3
        assert result["existing_count"] == 0
        assert result["total_checked"] == 3
        assert set(result["new_files"]) == set(file_keys)
        assert result["existing_files"] == []

    @pytest.mark.asyncio
    async def test_batch_check_all_existing_files(
        self, weaviate_test_collection, sample_documents
    ):
        """Test batch checking when all files already exist."""
        collection_name = weaviate_test_collection

        # Insert some test documents
        from weaviate_mcp.tools.data_tools import weaviate_batch_insert_objects

        objects = [
            {
                "content": f"Content from {doc}",
                "source_pdf": doc,
                "chunk_index": 0,
                "title": f"Document {i}",
            }
            for i, doc in enumerate(sample_documents)
        ]

        insert_result = await weaviate_batch_insert_objects(
            collection_name=collection_name,
            objects=objects,
        )
        assert insert_result.get("success"), "Failed to insert test documents"

        # Check for files that now exist
        result = await weaviate_batch_check_existing_files(
            collection_name=collection_name,
            file_keys=sample_documents,
            source_field="source_pdf",
        )

        # Verify results
        assert not result.get("error"), f"Unexpected error: {result.get('message')}"
        assert result["new_count"] == 0
        assert result["existing_count"] == len(sample_documents)
        assert result["total_checked"] == len(sample_documents)
        assert result["new_files"] == []
        assert set(result["existing_files"]) == set(sample_documents)

    @pytest.mark.asyncio
    async def test_batch_check_mixed_files(
        self, weaviate_test_collection, sample_documents
    ):
        """Test batch checking with mix of existing and new files."""
        collection_name = weaviate_test_collection

        # Insert only first two documents
        from weaviate_mcp.tools.data_tools import weaviate_batch_insert_objects

        existing_docs = sample_documents[:2]
        objects = [
            {
                "content": f"Content from {doc}",
                "source_pdf": doc,
                "chunk_index": 0,
                "title": f"Document {i}",
            }
            for i, doc in enumerate(existing_docs)
        ]

        insert_result = await weaviate_batch_insert_objects(
            collection_name=collection_name,
            objects=objects,
        )
        assert insert_result.get("success"), "Failed to insert test documents"

        # Check for mix of existing and new files
        all_files = sample_documents + ["new_file_1.pdf", "new_file_2.pdf"]

        result = await weaviate_batch_check_existing_files(
            collection_name=collection_name,
            file_keys=all_files,
            source_field="source_pdf",
        )

        # Verify results
        assert not result.get("error"), f"Unexpected error: {result.get('message')}"
        assert result["new_count"] == 3  # 1 from sample_documents + 2 new
        assert result["existing_count"] == 2  # First 2 from sample_documents
        assert result["total_checked"] == len(all_files)
        assert set(result["existing_files"]) == set(existing_docs)
        assert len(result["new_files"]) == 3

    @pytest.mark.asyncio
    async def test_batch_check_empty_file_list(self, weaviate_test_collection):
        """Test batch checking with empty file list."""
        collection_name = weaviate_test_collection

        result = await weaviate_batch_check_existing_files(
            collection_name=collection_name,
            file_keys=[],
            source_field="source_pdf",
        )

        # Verify results for empty input
        assert not result.get("error"), f"Unexpected error: {result.get('message')}"
        assert result["new_count"] == 0
        assert result["existing_count"] == 0
        assert result["total_checked"] == 0
        assert result["new_files"] == []
        assert result["existing_files"] == []

    @pytest.mark.asyncio
    async def test_batch_check_single_file(self, weaviate_test_collection):
        """Test batch checking with a single file."""
        collection_name = weaviate_test_collection

        result = await weaviate_batch_check_existing_files(
            collection_name=collection_name,
            file_keys=["single_file.pdf"],
            source_field="source_pdf",
        )

        # Verify results
        assert not result.get("error"), f"Unexpected error: {result.get('message')}"
        assert result["new_count"] == 1
        assert result["existing_count"] == 0
        assert result["total_checked"] == 1
        assert result["new_files"] == ["single_file.pdf"]
        assert result["existing_files"] == []

    @pytest.mark.asyncio
    async def test_batch_check_large_file_list(
        self, weaviate_test_collection, large_file_list
    ):
        """Test batch checking with large file list (100+ files)."""
        collection_name = weaviate_test_collection

        # Insert half of the files
        from weaviate_mcp.tools.data_tools import weaviate_batch_insert_objects

        existing_files = large_file_list[: len(large_file_list) // 2]
        objects = [
            {
                "content": f"Content from {doc}",
                "source_pdf": doc,
                "chunk_index": 0,
                "title": doc,
            }
            for doc in existing_files
        ]

        insert_result = await weaviate_batch_insert_objects(
            collection_name=collection_name,
            objects=objects,
        )
        assert insert_result.get("success"), "Failed to insert test documents"

        # Check all files
        result = await weaviate_batch_check_existing_files(
            collection_name=collection_name,
            file_keys=large_file_list,
            source_field="source_pdf",
        )

        # Verify results
        assert not result.get("error"), f"Unexpected error: {result.get('message')}"
        assert result["new_count"] == len(large_file_list) // 2
        assert result["existing_count"] == len(existing_files)
        assert result["total_checked"] == len(large_file_list)
        assert set(result["existing_files"]) == set(existing_files)

    @pytest.mark.asyncio
    async def test_batch_check_custom_source_field(self, weaviate_service):
        """Test batch checking with custom source field name."""
        # Create collection with custom source field
        from weaviate.classes.config import DataType, Property

        collection_name = "CustomSourceTest"
        properties = [
            Property(name="content", data_type=DataType.TEXT),
            Property(name="file_key", data_type=DataType.TEXT),  # Custom field
        ]

        # Create collection
        await weaviate_service.create_collection(
            name=collection_name,
            description="Test collection with custom source field",
            properties=properties,
        )

        try:
            # Insert documents with custom field
            from weaviate_mcp.tools.data_tools import weaviate_batch_insert_objects

            objects = [
                {"content": "Content 1", "file_key": "custom_file_1.pdf"},
                {"content": "Content 2", "file_key": "custom_file_2.pdf"},
            ]

            await weaviate_batch_insert_objects(
                collection_name=collection_name,
                objects=objects,
            )

            # Check using custom field
            result = await weaviate_batch_check_existing_files(
                collection_name=collection_name,
                file_keys=["custom_file_1.pdf", "custom_file_2.pdf", "new_file.pdf"],
                source_field="file_key",  # Custom field name
            )

            # Verify results
            assert not result.get("error"), f"Unexpected error: {result.get('message')}"
            assert result["new_count"] == 1
            assert result["existing_count"] == 2
            assert result["new_files"] == ["new_file.pdf"]
            assert set(result["existing_files"]) == {
                "custom_file_1.pdf",
                "custom_file_2.pdf",
            }

        finally:
            # Clean up
            await weaviate_service.delete_collection(collection_name)

    @pytest.mark.asyncio
    async def test_batch_check_nonexistent_collection(self):
        """Test batch checking with non-existent collection."""
        result = await weaviate_batch_check_existing_files(
            collection_name="NonExistentCollection",
            file_keys=["file1.pdf", "file2.pdf"],
            source_field="source_pdf",
        )

        # Verify error handling
        assert result.get("error") is True
        assert "message" in result

    @pytest.mark.asyncio
    async def test_batch_check_duplicate_file_keys(
        self, weaviate_test_collection, sample_documents
    ):
        """Test batch checking with duplicate file keys in input."""
        collection_name = weaviate_test_collection

        # Insert one document
        from weaviate_mcp.tools.data_tools import weaviate_insert_object

        await weaviate_insert_object(
            collection_name=collection_name,
            data={
                "content": "Test content",
                "source_pdf": sample_documents[0],
                "chunk_index": 0,
                "title": "Test",
            },
        )

        # Check with duplicates in file_keys
        file_keys_with_dupes = [
            sample_documents[0],
            sample_documents[0],  # Duplicate
            sample_documents[1],
        ]

        result = await weaviate_batch_check_existing_files(
            collection_name=collection_name,
            file_keys=file_keys_with_dupes,
            source_field="source_pdf",
        )

        # Verify results - duplicates should be handled
        assert not result.get("error"), f"Unexpected error: {result.get('message')}"
        assert result["existing_count"] == 1  # Only one unique existing file
        assert result["new_count"] == 1  # Only one unique new file

    @pytest.mark.asyncio
    async def test_batch_check_results_are_sorted(
        self, weaviate_test_collection, sample_documents
    ):
        """Test that results are sorted for consistency."""
        collection_name = weaviate_test_collection

        # Insert documents
        from weaviate_mcp.tools.data_tools import weaviate_batch_insert_objects

        objects = [
            {
                "content": f"Content {i}",
                "source_pdf": doc,
                "chunk_index": 0,
                "title": doc,
            }
            for i, doc in enumerate(sample_documents)
        ]

        await weaviate_batch_insert_objects(
            collection_name=collection_name,
            objects=objects,
        )

        # Check with unsorted input
        unsorted_files = ["zebra.pdf", "apple.pdf", "banana.pdf"] + sample_documents

        result = await weaviate_batch_check_existing_files(
            collection_name=collection_name,
            file_keys=unsorted_files,
            source_field="source_pdf",
        )

        # Verify results are sorted
        assert not result.get("error"), f"Unexpected error: {result.get('message')}"
        assert result["new_files"] == sorted(result["new_files"])
        assert result["existing_files"] == sorted(result["existing_files"])
