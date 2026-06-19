"""
Base classes and utilities for Google API service implementations.
"""

import json
import logging
import random
import time
from typing import Any

import google.auth.transport.requests
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from google_workspace_mcp.auth import gauth

logger = logging.getLogger(__name__)

# HTTP statuses that are safe to retry with backoff.
_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
_MAX_RETRIES = 3
_BASE_DELAY_SECONDS = 0.5

# Normalized, agent-facing error codes. Agents can branch on these instead of
# parsing raw HTTP status codes.
ERROR_CODE_BY_STATUS = {
    400: "INVALID_ARGUMENT",
    401: "AUTH_EXPIRED",
    403: "PERMISSION_DENIED",
    404: "NOT_FOUND",
    409: "CONFLICT",
    429: "RATE_LIMITED",
    500: "TRANSIENT",
    502: "TRANSIENT",
    503: "TRANSIENT",
    504: "TRANSIENT",
}


def _parse_google_error(error: HttpError) -> dict[str, Any]:
    """Pull the human-readable message and reason out of HttpError.content.

    googleapiclient.errors.HttpError does NOT expose error_details; the useful
    JSON (e.g. "Requested range is out of grid") lives in error.content. This
    parses it defensively, returning {} when the body isn't the expected shape.
    """
    raw = getattr(error, "content", None)
    if not raw:
        return {}
    try:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        payload = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    err = payload.get("error", payload)
    parsed: dict[str, Any] = {}
    if isinstance(err, dict):
        if err.get("message"):
            parsed["api_message"] = err["message"]
        if err.get("status"):
            parsed["api_status"] = err["status"]
        if err.get("errors"):
            parsed["api_errors"] = err["errors"]
    return parsed


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

    def execute_with_retry(self, request: Any, operation: str = "execute") -> Any:
        """Execute a googleapiclient request with backoff and a 401 refresh-retry.

        Wrap a request object (the thing you would call ``.execute()`` on) so the
        call survives transient failures instead of dead-ending:

        - 429 / 5xx → exponential backoff with jitter, honoring ``Retry-After``,
          up to ``_MAX_RETRIES`` attempts.
        - 401 → refresh the credentials once and retry, since google-auth's
          in-transport refresh can still leave a stale token on the built client.

        Returns the request's result on success. Re-raises the final HttpError on
        exhaustion so callers keep routing it through ``handle_api_error``.
        """
        attempt = 0
        refreshed = False
        while True:
            try:
                return request.execute()
            except HttpError as error:
                status = error.resp.status if error.resp else None

                # One-shot credential refresh on 401.
                if status == 401 and not refreshed:
                    refreshed = True
                    if self._try_refresh_credentials():
                        logger.info(
                            f"Refreshed credentials after 401 in {operation}; retrying."
                        )
                        continue

                # Backoff on transient statuses.
                if status in _RETRYABLE_STATUSES and attempt < _MAX_RETRIES:
                    delay = self._backoff_delay(attempt, error)
                    logger.warning(
                        f"{operation} got {status}; retry {attempt + 1}/{_MAX_RETRIES} "
                        f"in {delay:.2f}s."
                    )
                    time.sleep(delay)
                    attempt += 1
                    continue

                raise

    def _try_refresh_credentials(self) -> bool:
        """Force a credential refresh and rebuild the client. Returns success."""
        try:
            credentials = gauth.get_credentials()
            credentials.refresh(google.auth.transport.requests.Request())
            # Rebuild the client so it picks up the new token.
            self._service = build(
                self.service_name, self.version, credentials=credentials
            )
            return True
        except Exception:
            logger.exception("Credential refresh failed")
            return False

    @staticmethod
    def _backoff_delay(attempt: int, error: HttpError) -> float:
        """Exponential backoff with jitter, honoring a Retry-After header."""
        retry_after = None
        if error.resp:
            # httplib2 lowercases all response header keys, so look up the
            # lowercase form only.
            header = error.resp.get("retry-after")
            if header:
                try:
                    retry_after = float(header)
                except (ValueError, TypeError):
                    retry_after = None
        if retry_after is not None:
            return retry_after
        return _BASE_DELAY_SECONDS * (2**attempt) + random.uniform(0, 0.25)

    def handle_api_error(self, operation: str, error: Exception) -> dict[str, Any]:
        """
        Standardized error handling for Google API operations.

        Args:
            operation (str): The operation being performed.
            error (Exception): The exception that occurred.

        Returns:
            Dict[str, Any]: Structured error information with a normalized
            ``error_code`` and Google's real error message when available.
        """
        if isinstance(error, HttpError):
            status = error.resp.status if error.resp else None
            error_details: dict[str, Any] = {
                "error": True,
                "operation": operation,
                "status_code": status,
                "reason": error.resp.reason if error.resp else None,
                "message": str(error),
                "error_code": ERROR_CODE_BY_STATUS.get(status, "API_ERROR"),
            }

            # Surface Google's real error body (message/status/sub-errors).
            parsed = _parse_google_error(error)
            if parsed:
                error_details.update(parsed)
                # Prefer the API's human message as the headline when present.
                if parsed.get("api_message"):
                    error_details["message"] = parsed["api_message"]

            if status == 429:
                delay = self._backoff_delay(0, error)
                error_details["retry_after"] = round(delay, 2)

            logger.error(
                f"Google API error in {operation}: {status} "
                f"{error_details.get('reason')} - {error_details['message']}"
            )

        else:
            # Handle non-HTTP errors
            error_details = {
                "error": True,
                "operation": operation,
                "message": str(error),
                "error_code": "INTERNAL_ERROR",
                "type": type(error).__name__,
            }
            logger.error(f"Unexpected error in {operation}: {type(error).__name__} - {error}")

        return error_details
