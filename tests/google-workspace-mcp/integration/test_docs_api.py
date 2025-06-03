"""
Integration tests for Google Docs API.

These tests require valid Google API credentials and will make actual API calls.
They should be run cautiously to avoid unwanted side effects on real accounts.
"""

import os
import uuid

import pytest
from google_workspace_mcp.services.docs_service import DocsService

# Skip integration tests if environment flag is not set
pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION_TESTS", "0") != "1",
    reason="Integration tests are disabled. Set RUN_INTEGRATION_TESTS=1 to enable.",
)


class TestDocsIntegration:
    """Integration tests for Google Docs API."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up the DocsService for each test."""
        # Check if credentials are available
        for var in [
            "GOOGLE_WORKSPACE_CLIENT_ID",
            "GOOGLE_WORKSPACE_CLIENT_SECRET",
            "GOOGLE_WORKSPACE_REFRESH_TOKEN",
        ]:
            if not os.environ.get(var):
                pytest.skip(f"Environment variable {var} not set")

        self.service = DocsService()

        # Generate a unique identifier for test documents
        self.test_id = f"test-{uuid.uuid4().hex[:8]}"

    def test_create_document_integration(self):
        """Test creating a document with the actual API."""
        # Generate unique document title
        document_title = f"Integration Test Document {self.test_id}"

        # Create the document
        result = self.service.create_document(title=document_title)

        # Verify response structure
        assert isinstance(result, dict)
        assert "document_id" in result
        assert "title" in result
        assert "document_link" in result

        # Verify the document was created with correct title
        assert result["title"] == document_title
        assert result["document_id"] is not None
        assert "docs.google.com" in result["document_link"]

        # Store document ID for potential cleanup (though we can't delete via Docs API)
        document_id = result["document_id"]
        print(f"Created test document: {result['document_link']}")

        # Note: Google Docs API doesn't provide a delete method, so created documents
        # will remain in the account. In a production test suite, you might want to
        # move them to trash via Drive API or use a dedicated test account.

        return document_id

    def test_get_document_metadata_integration(self):
        """Test retrieving document metadata with the actual API."""
        # First create a document to retrieve metadata for
        document_title = f"Metadata Test Document {self.test_id}"
        create_result = self.service.create_document(title=document_title)

        assert isinstance(create_result, dict)
        assert "document_id" in create_result
        document_id = create_result["document_id"]

        # Now retrieve the metadata
        metadata_result = self.service.get_document_metadata(document_id=document_id)

        # Verify response structure
        assert isinstance(metadata_result, dict)
        assert "document_id" in metadata_result
        assert "title" in metadata_result
        assert "document_link" in metadata_result

        # Verify the metadata matches what we created
        assert metadata_result["document_id"] == document_id
        assert metadata_result["title"] == document_title
        assert "docs.google.com" in metadata_result["document_link"]

    def test_get_nonexistent_document_metadata_integration(self):
        """Test retrieving metadata for a nonexistent document."""
        # Use a clearly fake document ID
        fake_document_id = "nonexistent_doc_12345"

        # Attempt to retrieve metadata
        result = self.service.get_document_metadata(document_id=fake_document_id)

        # Should return an error dictionary
        assert isinstance(result, dict)
        assert result.get("error") is True
        assert "operation" in result
        assert result["operation"] == "get_document_metadata"

    def test_get_document_content_as_markdown_integration(self):
        """Test retrieving document content as markdown with the actual API."""
        # First create a document with some content
        document_title = f"Content Test Document {self.test_id}"
        create_result = self.service.create_document(title=document_title)

        assert isinstance(create_result, dict)
        assert "document_id" in create_result
        document_id = create_result["document_id"]

        # Add some content to the document first
        append_result = self.service.append_text(
            document_id=document_id,
            text="# Test Heading\n\nThis is test content for markdown export.",
            ensure_newline=False,
        )
        assert append_result.get("success") is True

        # Now retrieve the content as markdown
        content_result = self.service.get_document_content_as_markdown(document_id=document_id)

        # Verify response structure
        assert isinstance(content_result, dict)
        assert "document_id" in content_result
        assert "markdown_content" in content_result

        # Verify the content was retrieved
        assert content_result["document_id"] == document_id
        assert isinstance(content_result["markdown_content"], str)
        assert len(content_result["markdown_content"]) > 0
        print(f"Retrieved markdown content: {content_result['markdown_content'][:100]}...")

    def test_append_text_integration(self):
        """Test appending text to a document with the actual API."""
        # First create a document
        document_title = f"Append Test Document {self.test_id}"
        create_result = self.service.create_document(title=document_title)

        assert isinstance(create_result, dict)
        assert "document_id" in create_result
        document_id = create_result["document_id"]

        # Append text to the document
        text_to_append = "This is appended text from integration test."
        append_result = self.service.append_text(document_id=document_id, text=text_to_append, ensure_newline=True)

        # Verify response structure
        assert isinstance(append_result, dict)
        assert "document_id" in append_result
        assert "success" in append_result
        assert "operation" in append_result

        # Verify the operation was successful
        assert append_result["document_id"] == document_id
        assert append_result["success"] is True
        assert append_result["operation"] == "append_text"

        print(f"Successfully appended text to document: {create_result['document_link']}")

    def test_prepend_text_integration(self):
        """Test prepending text to a document with the actual API."""
        # First create a document
        document_title = f"Prepend Test Document {self.test_id}"
        create_result = self.service.create_document(title=document_title)

        assert isinstance(create_result, dict)
        assert "document_id" in create_result
        document_id = create_result["document_id"]

        # Add some existing content first
        append_result = self.service.append_text(
            document_id=document_id,
            text="This is existing content.",
            ensure_newline=False,
        )
        assert append_result.get("success") is True

        # Prepend text to the document
        text_to_prepend = "This is prepended text from integration test."
        prepend_result = self.service.prepend_text(document_id=document_id, text=text_to_prepend, ensure_newline=True)

        # Verify response structure
        assert isinstance(prepend_result, dict)
        assert "document_id" in prepend_result
        assert "success" in prepend_result
        assert "operation" in prepend_result

        # Verify the operation was successful
        assert prepend_result["document_id"] == document_id
        assert prepend_result["success"] is True
        assert prepend_result["operation"] == "prepend_text"

        print(f"Successfully prepended text to document: {create_result['document_link']}")

    def test_text_operations_workflow_integration(self):
        """Test a complete workflow of text operations with the actual API."""
        # Create a document
        document_title = f"Workflow Test Document {self.test_id}"
        create_result = self.service.create_document(title=document_title)
        document_id = create_result["document_id"]

        # 1. Prepend some introductory text
        prepend_result = self.service.prepend_text(
            document_id=document_id,
            text="Introduction: This document was created via integration test.",
            ensure_newline=True,
        )
        assert prepend_result.get("success") is True

        # 2. Append some content
        append_result = self.service.append_text(
            document_id=document_id,
            text="Body: This is the main content of the document.",
            ensure_newline=True,
        )
        assert append_result.get("success") is True

        # 3. Append more content
        append_result2 = self.service.append_text(
            document_id=document_id,
            text="Conclusion: This document demonstrates text operations.",
            ensure_newline=True,
        )
        assert append_result2.get("success") is True

        # 4. Retrieve the final content as markdown
        content_result = self.service.get_document_content_as_markdown(document_id=document_id)
        assert "markdown_content" in content_result

        markdown_content = content_result["markdown_content"]

        # Verify the content contains all our added text
        assert "Introduction:" in markdown_content
        assert "Body:" in markdown_content
        assert "Conclusion:" in markdown_content

        print(f"Workflow completed successfully. Final content length: {len(markdown_content)} characters")
        print(f"Document link: {create_result['document_link']}")

    def test_get_content_nonexistent_document_integration(self):
        """Test retrieving content for a nonexistent document."""
        # Use a clearly fake document ID
        fake_document_id = "nonexistent_doc_12345"

        # Attempt to retrieve content
        result = self.service.get_document_content_as_markdown(document_id=fake_document_id)

        # Should return an error dictionary
        assert isinstance(result, dict)
        assert result.get("error") is True
        assert "operation" in result

    def test_insert_text_integration(self):
        """Test inserting text at a specific location with the actual API."""
        # First create a document with some initial content
        document_title = f"Insert Test Document {self.test_id}"
        create_result = self.service.create_document(title=document_title)
        document_id = create_result["document_id"]

        # Add some initial content
        initial_text = "Start. End."
        append_result = self.service.append_text(document_id=document_id, text=initial_text, ensure_newline=False)
        assert append_result.get("success") is True

        # Insert text in the middle (after "Start. ")
        # Note: In practice, calculating precise indices requires knowledge of document structure
        # For this integration test, we'll insert at a reasonable position
        text_to_insert = "Middle. "
        insert_result = self.service.insert_text(
            document_id=document_id,
            text=text_to_insert,
            index=7,  # After "Start. "
        )

        # Verify response structure
        assert isinstance(insert_result, dict)
        assert "document_id" in insert_result
        assert "success" in insert_result
        assert "operation" in insert_result

        # Verify the operation was successful
        assert insert_result["document_id"] == document_id
        assert insert_result["success"] is True
        assert insert_result["operation"] == "insert_text"

        print(f"Successfully inserted text into document: {create_result['document_link']}")

    def test_batch_update_integration(self):
        """Test batch update with multiple operations using the actual API."""
        # Create a document
        document_title = f"Batch Update Test Document {self.test_id}"
        create_result = self.service.create_document(title=document_title)
        document_id = create_result["document_id"]

        # Define batch requests - insert multiple text pieces
        requests = [
            {"insertText": {"location": {"index": 1}, "text": "First line.\n"}},
            {
                "insertText": {
                    "location": {"index": 13},  # After "First line.\n"
                    "text": "Second line.\n",
                }
            },
            {
                "insertText": {
                    "location": {"index": 27},  # After both previous lines
                    "text": "Third line.",
                }
            },
        ]

        # Execute batch update
        batch_result = self.service.batch_update(document_id=document_id, requests=requests)

        # Verify response structure
        assert isinstance(batch_result, dict)
        assert "document_id" in batch_result
        assert "replies" in batch_result

        # Verify the operation was successful
        assert batch_result["document_id"] == document_id
        assert isinstance(batch_result["replies"], list)
        assert len(batch_result["replies"]) == len(requests)  # One reply per request

        print(f"Successfully executed batch update on document: {create_result['document_link']}")

    def test_batch_update_empty_requests_integration(self):
        """Test batch update with empty requests list."""
        # Create a document
        document_title = f"Empty Batch Test Document {self.test_id}"
        create_result = self.service.create_document(title=document_title)
        document_id = create_result["document_id"]

        # Execute batch update with empty requests
        batch_result = self.service.batch_update(document_id=document_id, requests=[])

        # Verify response structure for empty requests
        assert isinstance(batch_result, dict)
        assert "document_id" in batch_result
        assert "replies" in batch_result
        assert "message" in batch_result

        # Verify the response
        assert batch_result["document_id"] == document_id
        assert batch_result["replies"] == []
        assert "No requests provided" in batch_result["message"]
