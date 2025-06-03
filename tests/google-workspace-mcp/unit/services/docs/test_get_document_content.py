"""
Unit tests for DocsService get_document_content_as_markdown method.
"""

from unittest.mock import MagicMock, patch

from googleapiclient.errors import HttpError


class TestDocsGetDocumentContentAsMarkdown:
    """Tests for DocsService get_document_content_as_markdown method."""

    def test_get_content_as_markdown_success(self, mock_docs_service):
        """Test successful document content retrieval as markdown."""
        # Test data
        document_id = "test_doc_123"
        mock_markdown_content = "# Test Document\n\nThis is test content."

        # Mock the gauth.get_credentials call
        mock_credentials = MagicMock()
        with patch("google_workspace_mcp.services.docs_service.gauth.get_credentials") as mock_get_creds:
            mock_get_creds.return_value = mock_credentials

            # Mock the Drive service build and export
            with patch("google_workspace_mcp.services.docs_service.build") as mock_build:
                mock_drive_service = MagicMock()
                mock_build.return_value = mock_drive_service

                # Mock the export_media and downloader
                mock_request = MagicMock()
                mock_drive_service.files.return_value.export_media.return_value = mock_request

                # Mock MediaIoBaseDownload
                with patch("google_workspace_mcp.services.docs_service.MediaIoBaseDownload") as mock_downloader_class:
                    mock_downloader = MagicMock()
                    mock_downloader_class.return_value = mock_downloader

                    # Mock downloader behavior
                    mock_status = MagicMock()
                    mock_status.progress.return_value = 1.0
                    mock_downloader.next_chunk.return_value = (mock_status, True)

                    # Mock BytesIO to return our test content
                    mock_fh = MagicMock()
                    mock_fh.getvalue.return_value = mock_markdown_content.encode("utf-8")

                    with patch("google_workspace_mcp.services.docs_service.io.BytesIO") as mock_bytesio:
                        mock_bytesio.return_value = mock_fh

                        # Call the method
                        result = mock_docs_service.get_document_content_as_markdown(document_id)

                        # Verify API calls
                        mock_get_creds.assert_called_once()
                        mock_build.assert_called_once_with("drive", "v3", credentials=mock_credentials)
                        mock_drive_service.files.return_value.export_media.assert_called_once_with(
                            fileId=document_id, mimeType="text/markdown"
                        )

                        # Verify result
                        expected_result = {
                            "document_id": "test_doc_123",
                            "markdown_content": mock_markdown_content,
                        }
                        assert result == expected_result

    def test_get_content_as_markdown_no_credentials(self, mock_docs_service):
        """Test document content retrieval when credentials fail."""
        # Test data
        document_id = "test_doc_123"

        # Mock failed credentials
        with patch("google_workspace_mcp.services.docs_service.gauth.get_credentials") as mock_get_creds:
            mock_get_creds.return_value = None

            # Call the method
            result = mock_docs_service.get_document_content_as_markdown(document_id)

            # Verify error result
            assert isinstance(result, dict)
            assert result["error"] is True
            assert result["error_type"] == "authentication_error"
            assert result["operation"] == "get_document_content_as_markdown"
            assert "Failed to obtain credentials" in result["message"]

    def test_get_content_as_markdown_http_error(self, mock_docs_service):
        """Test document content retrieval with HTTP error."""
        # Test data
        document_id = "restricted_doc"

        # Mock credentials
        mock_credentials = MagicMock()
        with patch("google_workspace_mcp.services.docs_service.gauth.get_credentials") as mock_get_creds:
            mock_get_creds.return_value = mock_credentials

            # Mock the Drive service build
            with patch("google_workspace_mcp.services.docs_service.build") as mock_build:
                mock_drive_service = MagicMock()
                mock_build.return_value = mock_drive_service

                # Create a mock HttpError
                mock_resp = MagicMock()
                mock_resp.status = 403
                mock_resp.reason = "Forbidden"
                http_error = HttpError(mock_resp, b'{"error": {"message": "Permission denied"}}')

                # Setup the mock to raise the error
                mock_drive_service.files.return_value.export_media.side_effect = http_error

                # Mock error handling
                expected_error = {
                    "error": True,
                    "error_type": "http_error",
                    "status_code": 403,
                    "message": "Permission denied",
                    "operation": "get_document_content_as_markdown_drive_export",
                }
                mock_docs_service.handle_api_error = MagicMock(return_value=expected_error)

                # Call the method
                result = mock_docs_service.get_document_content_as_markdown(document_id)

                # Verify error handling
                mock_docs_service.handle_api_error.assert_called_once_with(
                    "get_document_content_as_markdown_drive_export", http_error
                )
                assert result == expected_error

    def test_get_content_as_markdown_download_failure(self, mock_docs_service):
        """Test document content retrieval when download fails."""
        # Test data
        document_id = "test_doc_123"

        # Mock credentials
        mock_credentials = MagicMock()
        with patch("google_workspace_mcp.services.docs_service.gauth.get_credentials") as mock_get_creds:
            mock_get_creds.return_value = mock_credentials

            # Mock the Drive service build
            with patch("google_workspace_mcp.services.docs_service.build") as mock_build:
                mock_drive_service = MagicMock()
                mock_build.return_value = mock_drive_service

                # Mock the export_media
                mock_request = MagicMock()
                mock_drive_service.files.return_value.export_media.return_value = mock_request

                # Mock MediaIoBaseDownload with download failure
                with patch("google_workspace_mcp.services.docs_service.MediaIoBaseDownload") as mock_downloader_class:
                    mock_downloader = MagicMock()
                    mock_downloader_class.return_value = mock_downloader

                    # Mock downloader behavior - fail
                    mock_status = MagicMock()
                    mock_status.progress.return_value = 1.0
                    mock_downloader.next_chunk.return_value = (mock_status, True)

                    # Mock BytesIO to return None (failure case)
                    mock_fh = MagicMock()
                    mock_fh.getvalue.return_value = None

                    with patch("google_workspace_mcp.services.docs_service.io.BytesIO") as mock_bytesio:
                        mock_bytesio.return_value = mock_fh

                        # Call the method
                        result = mock_docs_service.get_document_content_as_markdown(document_id)

                        # Verify error result
                        assert isinstance(result, dict)
                        assert result["error"] is True
                        assert result["error_type"] == "export_error"
                        assert result["operation"] == "get_document_content_as_markdown"
                        assert "Failed to download exported content" in result["message"]

    def test_get_content_as_markdown_unexpected_error(self, mock_docs_service):
        """Test document content retrieval with unexpected error."""
        # Test data
        document_id = "error_doc"

        # Mock credentials
        mock_credentials = MagicMock()
        with patch("google_workspace_mcp.services.docs_service.gauth.get_credentials") as mock_get_creds:
            mock_get_creds.return_value = mock_credentials

            # Mock unexpected error during build
            with patch("google_workspace_mcp.services.docs_service.build") as mock_build:
                mock_build.side_effect = Exception("Network timeout")

                # Call the method
                result = mock_docs_service.get_document_content_as_markdown(document_id)

                # Verify result contains error
                assert isinstance(result, dict)
                assert result["error"] is True
                assert result["error_type"] == "export_error"
                assert result["message"] == "Network timeout"
                assert result["operation"] == "get_document_content_as_markdown"
