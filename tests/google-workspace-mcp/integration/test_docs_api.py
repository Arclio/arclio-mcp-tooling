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
