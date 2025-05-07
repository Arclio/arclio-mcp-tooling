"""
Google authentication utilities for MCP-GSuite.

Handles OAuth 2.0 authentication using environment variables.
"""

import logging
import os
from functools import lru_cache

import google.auth.exceptions
import google.auth.transport.requests
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)


@lru_cache(maxsize=32)
def get_credentials():
    """
    Retrieves Google OAuth credentials from environment variables.

    The credentials are cached to avoid redundant processing, but will
    be automatically refreshed when expired.

    Returns:
        google.oauth2.credentials.Credentials: Initialized credentials object.

    Raises:
        ValueError: If any of the required environment variables are missing.
        CredentialsError: If credentials are invalid or revoked.
    """
    client_id = os.environ.get("GSUITE_CLIENT_ID")
    client_secret = os.environ.get("GSUITE_CLIENT_SECRET")
    refresh_token = os.environ.get("GSUITE_REFRESH_TOKEN")

    if not client_id:
        raise ValueError("Environment variable 'GSUITE_CLIENT_ID' is required but not set.")
    if not client_secret:
        raise ValueError("Environment variable 'GSUITE_CLIENT_SECRET' is required but not set.")
    if not refresh_token:
        raise ValueError("Environment variable 'GSUITE_REFRESH_TOKEN' is required but not set.")

    logger.info("Successfully retrieved G Suite credentials from environment variables.")

    try:
        return Credentials(
            token=None,  # Will be fetched automatically on first use
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
        )
        # The google-auth library automatically handles token refreshing
        # when needed during API requests using the provided refresh token.

    except google.auth.exceptions.RefreshError as e:
        logger.exception("Credentials refresh failed - token may be revoked or expired")
        raise ValueError(f"Invalid or revoked credentials: {e}") from e
    except Exception as e:
        logger.exception("Failed to create Credentials object")
        raise ValueError(f"Failed to initialize credentials: {e}") from e
