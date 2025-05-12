"""Authentication utilities for Google Slides API."""

import json
import logging
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger(__name__)

# OAuth scopes needed for Google Slides
SCOPES = ["https://www.googleapis.com/auth/presentations"]


def get_credentials_from_env() -> Credentials | None:
    """
    Get Google OAuth credentials from environment variables.

    Returns:
        Credentials or None if not available
    """
    # Check for service account credentials
    service_account_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if service_account_file and os.path.exists(service_account_file):
        try:
            logger.info(f"Using service account credentials from {service_account_file}")
            return service_account.Credentials.from_service_account_file(
                service_account_file, scopes=SCOPES
            )
        except Exception as e:
            logger.warning(f"Failed to use service account: {e}")

    # Check for user credentials in environment
    client_id = os.environ.get("SLIDES_CLIENT_ID")
    client_secret = os.environ.get("SLIDES_CLIENT_SECRET")
    refresh_token = os.environ.get("SLIDES_REFRESH_TOKEN")

    if client_id and client_secret and refresh_token:
        logger.info("Using credentials from environment variables")
        return Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES,
        )

    logger.debug("No credentials found in environment variables")
    return None


def get_credentials_from_token_file(token_path: Path = None) -> Credentials | None:
    """
    Get credentials from token file.

    Args:
        token_path: Path to token file (default: ~/.markdowndeck/token.json)

    Returns:
        Credentials or None if not available
    """
    if token_path is None:
        token_path = Path.home() / ".markdowndeck" / "token.json"

    # Check if token exists
    if not token_path.exists():
        logger.debug(f"Token file not found: {token_path}")
        return None

    try:
        # Load token data
        token_data = json.loads(token_path.read_text())
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)

        # Check if credentials are valid
        if creds and creds.valid:
            logger.info(f"Using credentials from token file: {token_path}")
            return creds

        # Refresh if expired
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired credentials")
            creds.refresh(Request())

            # Save refreshed token
            token_path.write_text(creds.to_json())
            logger.info(f"Saved refreshed token to {token_path}")
            return creds

    except Exception as e:
        logger.warning(f"Error loading credentials from token file: {e}")

    return None


def run_oauth_flow(client_secrets_path: Path = None) -> Credentials | None:
    """
    Run OAuth flow to get credentials.

    Args:
        client_secrets_path: Path to client secrets file

    Returns:
        Credentials or None if flow failed
    """
    if client_secrets_path is None:
        client_secrets_path = Path.home() / ".markdowndeck" / "credentials.json"

    # Check if client secrets exist
    if not client_secrets_path.exists():
        logger.error(f"Client secrets file not found: {client_secrets_path}")
        return None

    try:
        # Run OAuth flow
        logger.info(f"Running OAuth flow with client secrets from: {client_secrets_path}")
        flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, SCOPES)
        creds = flow.run_local_server(port=0)

        # Save token for future use
        token_path = Path.home() / ".markdowndeck" / "token.json"
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json())
        logger.info(f"Saved new credentials to {token_path}")

        return creds

    except Exception as e:
        logger.error(f"OAuth flow failed: {e}")

    return None


def get_credentials() -> Credentials | None:
    """
    Get credentials using all available methods.

    Returns:
        Credentials or None if all methods failed
    """
    # Try environment first
    creds = get_credentials_from_env()
    if creds:
        return creds

    # Try token file
    creds = get_credentials_from_token_file()
    if creds:
        return creds

    # Try OAuth flow as last resort
    return run_oauth_flow()
