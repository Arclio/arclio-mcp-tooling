"""
Integration tests for Google Drive API.

These tests require actual Google API credentials and make real API calls.
They are disabled by default and must be explicitly enabled by setting
the RUN_INTEGRATION_TESTS environment variable.
"""

import contextlib
import os
import uuid

import pytest
from google_workspace_mcp.services.drive import DriveService

# Skip these tests unless integration testing is explicitly enabled
pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_INTEGRATION_TESTS"), reason="Integration tests not enabled"
)


class TestDriveIntegration:
    """Integration tests for Google Drive API."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up the DriveService for each test."""
        # Check if credentials are available
        for var in [
            "GOOGLE_WORKSPACE_CLIENT_ID",
            "GOOGLE_WORKSPACE_CLIENT_SECRET",
            "GOOGLE_WORKSPACE_REFRESH_TOKEN",
        ]:
            if not os.environ.get(var):
                pytest.skip(f"Environment variable {var} not set")

        self.service = DriveService()

        # Generate a unique identifier for test files
        self.test_id = f"test-{uuid.uuid4().hex[:8]}"

        # Store created file IDs for cleanup
        self.files_to_delete = []

    def teardown_method(self):
        """Clean up any created files."""
        if hasattr(self, "files_to_delete"):
            for file_id in self.files_to_delete:
                with contextlib.suppress(Exception):
                    self.service.delete_file(file_id)

    def test_search_files_integration(self):
        """Test searching for files with the actual API."""
        # Use a safe, generic search query for text files
        files = self.service.search_files("mimeType = 'text/plain'", page_size=5)

        # Verify the response structure
        assert isinstance(files, list)
        if files:
            # Check structure of first file
            file = files[0]
            assert "id" in file
            assert "name" in file
            assert "mimeType" in file

    def test_file_lifecycle_integration(self, tmp_path):
        """
        Test the complete lifecycle of a file: create, upload, read, delete.

        This test is safer than others because it:
        1. Creates a temporary test file
        2. Uploads it to Drive
        3. Reads it back
        4. Deletes it afterward
        """
        # Create a temp file with known content and unique ID
        file_name = f"test_file_{self.test_id}.txt"
        temp_file = tmp_path / file_name
        test_content = f"This is test content created by Google Workspace MCP integration tests.\nUnique ID: {self.test_id}"
        temp_file.write_text(test_content)

        try:
            # 1. Upload to Drive
            file_metadata = self.service.upload_file(str(temp_file))

            # Verify upload was successful
            assert isinstance(file_metadata, dict)
            assert "id" in file_metadata, "File upload did not return an ID"
            assert not file_metadata.get("error", False), "Upload returned an error"

            file_id = file_metadata["id"]
            self.files_to_delete.append(file_id)

            # 2. Read the file back
            result = self.service.read_file(file_id)

            # Verify content
            assert isinstance(result, dict)
            assert "mimeType" in result
            assert result["mimeType"] == "text/plain"
            assert "content" in result
            assert (
                self.test_id in result["content"]
            ), "Retrieved content doesn't match what was uploaded"

            # 3. Search for the file by name
            search_query = f"name contains '{self.test_id}'"
            search_results = self.service.search_files(search_query)

            # Verify search works
            assert len(search_results) >= 1, "Uploaded file not found in search results"
            found = False
            for file in search_results:
                if file["id"] == file_id:
                    found = True
                    break
            assert found, "Uploaded file not found in search results"

        finally:
            # 4. Clean up - delete the created file
            if hasattr(self, "files_to_delete") and self.files_to_delete:
                for file_id in self.files_to_delete:
                    delete_result = self.service.delete_file(file_id)
                    assert isinstance(delete_result, dict)
                    assert delete_result.get(
                        "success", False
                    ), f"Failed to delete file {file_id}"

    def test_error_handling_integration(self):
        """Test error handling with invalid file IDs."""
        # Try to read a file with an invalid ID
        invalid_id = f"nonexistent_{self.test_id}"
        result = self.service.read_file(invalid_id)

        # Verify error response structure
        assert isinstance(result, dict)
        assert result.get("error") is True, "Error not indicated in response"
        assert "message" in result
        assert "error_type" in result
