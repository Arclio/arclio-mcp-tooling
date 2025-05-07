"""
Base service implementation for Google Workspace services.
"""

import logging
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from arclio_mcp_gsuite.auth import gauth

logger = logging.getLogger(__name__)


class BaseGoogleService:
    """
    Base class for all Google Workspace service implementations.

    Provides common functionality for service initialization, error handling,
    and API interactions.
    """

    def __init__(self, service_name: str, api_version: str):
        """
        Initialize a Google Workspace service.

        Args:
            service_name: The name of the Google API service (e.g., 'drive', 'gmail')
            api_version: The API version to use (e.g., 'v3', 'v1')

        Raises:
            RuntimeError: If service initialization fails
        """
        self.service_name = service_name
        self.api_version = api_version

        try:
            credentials = gauth.get_credentials()
            self.service = build(service_name, api_version, credentials=credentials)
            logger.info(f"Initialized {service_name} service (v{api_version})")
        except ValueError as e:
            logger.error(f"Credential error during {service_name} service initialization: {e}")
            raise RuntimeError(
                f"Failed to initialize {service_name} service due to credential error: {e}"
            ) from e
        except HttpError as e:
            logger.error(f"HTTP error during {service_name} service initialization: {e}")
            raise RuntimeError(
                f"Failed to initialize {service_name} service due to API error: {e}"
            ) from e
        except Exception as e:
            logger.exception(f"Unexpected error during {service_name} service initialization")
            raise RuntimeError(f"Unexpected error initializing {service_name} service: {e}") from e

    def handle_api_error(self, operation: str, error: Exception) -> dict[str, Any] | None:
        """
        Handle API errors uniformly across services.

        Args:
            operation: The operation being performed (for logging)
            error: The exception that was raised

        Returns:
            Optional error information dictionary or None
        """
        if isinstance(error, HttpError):
            status_code = error.resp.status
            reason = error.reason
            logger.error(
                f"HTTP error during {self.service_name}.{operation}: {status_code} {reason}"
            )
            return {
                "error": True,
                "error_type": "http_error",
                "status_code": status_code,
                "message": f"{reason}",
                "operation": operation,
            }
        logger.exception(f"Error during {self.service_name}.{operation}")
        return {
            "error": True,
            "error_type": "service_error",
            "message": str(error),
            "operation": operation,
        }
