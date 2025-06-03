"""
Base classes and utilities for Google API service implementations.
"""

import logging
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from google_workspace_mcp.auth import gauth

logger = logging.getLogger(__name__)


class BaseGoogleService:
    """
    Base class for Google service implementations providing common
    authentication and error handling patterns.
    """

    def __init__(self, service_name: str, version: str):
        """Initialize the service with credentials."""
        self.service_name = service_name
        self.version = version
        self._service = None

    @property
    def service(self):
        """Lazy-load the Google API service client."""
        if self._service is None:
            credentials = gauth.get_credentials()
            self._service = build(self.service_name, self.version, credentials=credentials)
        return self._service

    def handle_api_error(self, operation: str, error: Exception) -> dict[str, Any]:
        """
        Standardized error handling for Google API operations.

        Args:
            operation (str): The operation being performed.
            error (Exception): The exception that occurred.

        Returns:
            Dict[str, Any]: Structured error information.
        """
        if isinstance(error, HttpError):
            # Extract meaningful error information from Google API errors
            error_details = {
                "error": True,
                "operation": operation,
                "status_code": error.resp.status,
                "reason": error.resp.reason,
                "message": str(error),
            }

            # Try to extract additional error details from the response
            if hasattr(error, "error_details"):
                error_details["details"] = error.error_details

            logger.error(f"Google API error in {operation}: {error.resp.status} {error.resp.reason} - {error}")

        else:
            # Handle non-HTTP errors
            error_details = {
                "error": True,
                "operation": operation,
                "message": str(error),
                "type": type(error).__name__,
            }
            logger.error(f"Unexpected error in {operation}: {type(error).__name__} - {error}")

        return error_details
