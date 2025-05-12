"""
Command line interface for MarkdownDeck.

This module provides a CLI for converting markdown files to Google Slides presentations.
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from markdowndeck import create_presentation, get_themes

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# OAuth scopes needed
SCOPES = ["https://www.googleapis.com/auth/presentations"]


def get_credentials() -> Credentials | None:
    """
    Get credentials from environment or user OAuth flow.

    Returns:
        Credentials object or None if authentication fails
    """
    creds = None

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

    # If no environment credentials, try to load from token file
    token_path = Path.home() / ".markdowndeck" / "token.json"
    if token_path.exists():
        logger.info(f"Loading credentials from {token_path}")
        creds = Credentials.from_authorized_user_info(json.loads(token_path.read_text()), SCOPES)

    # If no valid credentials, run the OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired credentials")
            creds.refresh(Request())
        else:
            # Look for client secrets file
            client_secrets_path = Path.home() / ".markdowndeck" / "credentials.json"
            if not client_secrets_path.exists():
                logger.error(
                    "No credentials available. Please set environment variables "
                    "or provide a credentials file at ~/.markdowndeck/credentials.json"
                )
                return None

            logger.info(f"Running OAuth flow with credentials from {client_secrets_path}")
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, SCOPES)
            creds = flow.run_local_server(port=0)

            # Save credentials for next time
            token_path.parent.mkdir(parents=True, exist_ok=True)
            token_path.write_text(creds.to_json())
            logger.info(f"Saved new credentials to {token_path}")

    return creds


def list_themes_command(args: argparse.Namespace) -> None:
    """
    List available presentation themes.

    Args:
        args: Command line arguments
    """
    try:
        # Get credentials
        credentials = get_credentials()
        if not credentials:
            logger.error("Authentication failed")
            sys.exit(1)

        # Get themes
        themes = get_themes(credentials=credentials)

        # Display themes
        print("Available themes:")
        for theme in themes:
            print(f"  - {theme['name']} (ID: {theme['id']})")

    except Exception as e:
        logger.error(f"Failed to list themes: {e}")
        sys.exit(1)


def create_presentation_command(args: argparse.Namespace) -> None:
    """
    Create a presentation from markdown.

    Args:
        args: Command line arguments
    """
    # Read markdown content
    if args.input == "-":
        logger.info("Reading markdown from stdin")
        markdown = sys.stdin.read()
    else:
        input_path = Path(args.input)
        if not input_path.exists():
            logger.error(f"Input file not found: {args.input}")
            sys.exit(1)
        logger.info(f"Reading markdown from file: {args.input}")
        markdown = input_path.read_text()

    # Get credentials
    try:
        credentials = get_credentials()
        if not credentials:
            logger.error("Authentication failed")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        sys.exit(1)

    # Create presentation
    try:
        result = create_presentation(
            markdown=markdown,
            title=args.title,
            credentials=credentials,
            theme_id=args.theme,
        )

        # Display result
        print("Created presentation:")
        print(f"  - ID: {result['presentationId']}")
        print(f"  - URL: {result['presentationUrl']}")
        print(f"  - Title: {result['title']}")
        print(f"  - Slides: {result.get('slideCount', 'unknown')}")

        # Save output if requested
        if args.output:
            logger.info(f"Saving presentation details to {args.output}")
            with open(args.output, "w") as f:
                json.dump(result, f, indent=2)

    except Exception as e:
        logger.error(f"Failed to create presentation: {e}")
        sys.exit(1)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Convert Markdown to Google Slides presentation",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Create subparsers
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Create presentation command
    create_parser = subparsers.add_parser("create", help="Create a presentation")
    create_parser.add_argument("input", help="Markdown file path or - for stdin")
    create_parser.add_argument(
        "-t", "--title", default="Markdown Presentation", help="Presentation title"
    )
    create_parser.add_argument("--theme", help="Google Slides theme ID")
    create_parser.add_argument("-o", "--output", help="Save presentation ID to specified file")
    create_parser.set_defaults(func=create_presentation_command)

    # List themes command
    themes_parser = subparsers.add_parser("themes", help="List available themes")
    themes_parser.set_defaults(func=list_themes_command)

    # Verbose flag for all commands
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")

    # Parse arguments
    args = parser.parse_args()

    # Set logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Handle default command (create)
    if not args.command:
        if hasattr(args, "input"):
            args.command = "create"
            args.func = create_presentation_command
        else:
            parser.print_help()
            sys.exit(0)

    # Execute the command
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
