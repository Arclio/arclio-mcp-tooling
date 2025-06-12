"""
Command line interface for MarkdownDeck.
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

from markdowndeck import create_presentation

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/presentations"]


def get_credentials() -> Credentials | None:
    """Get credentials from environment or user OAuth flow."""
    # Service account credentials
    service_account_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if service_account_file and os.path.exists(service_account_file):
        try:
            return service_account.Credentials.from_service_account_file(
                service_account_file, scopes=SCOPES
            )
        except Exception as e:
            logger.warning(f"Failed to use service account: {e}")

    # User credentials in environment
    client_id = os.environ.get("SLIDES_CLIENT_ID")
    client_secret = os.environ.get("SLIDES_CLIENT_SECRET")
    refresh_token = os.environ.get("SLIDES_REFRESH_TOKEN")
    if client_id and client_secret and refresh_token:
        return Credentials(
            None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES,
        )

    # User credentials from token file
    token_path = Path.home() / ".markdowndeck" / "token.json"
    if token_path.exists():
        creds = Credentials.from_authorized_user_info(
            json.loads(token_path.read_text()), SCOPES
        )
        if creds and creds.valid:
            return creds
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_path.write_text(creds.to_json())
            return creds

    # Run OAuth flow
    client_secrets_path = Path.home() / ".markdowndeck" / "credentials.json"
    if not client_secrets_path.exists():
        logger.error(
            "No credentials available. Set environment variables or provide a credentials file."
        )
        return None
    flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, SCOPES)
    creds = flow.run_local_server(port=0)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json())
    return creds


def create_presentation_command(args: argparse.Namespace) -> None:
    """Create a presentation from markdown."""
    if args.input == "-":
        markdown = sys.stdin.read()
    else:
        input_path = Path(args.input)
        if not input_path.exists():
            logger.error(f"Input file not found: {args.input}")
            sys.exit(1)
        markdown = input_path.read_text()

    try:
        credentials = get_credentials()
        if not credentials:
            logger.error("Authentication failed")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        sys.exit(1)

    try:
        # REFACTORED: Removed theme_id argument.
        result = create_presentation(
            markdown=markdown, title=args.title, credentials=credentials
        )
        print(
            f"Created presentation:\n  - ID: {result['presentationId']}\n  - URL: {result['presentationUrl']}"
        )
        if args.output:
            with open(args.output, "w") as f:
                json.dump(result, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to create presentation: {e}")
        sys.exit(1)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Convert Markdown to Google Slides presentation"
    )
    subparsers = parser.add_subparsers(
        dest="command", help="Command to execute", required=True
    )

    create_parser = subparsers.add_parser("create", help="Create a presentation")
    create_parser.add_argument("input", help="Markdown file path or - for stdin")
    create_parser.add_argument(
        "-t", "--title", default="Markdown Presentation", help="Presentation title"
    )
    create_parser.add_argument(
        "-o", "--output", help="Save presentation ID to specified file"
    )
    create_parser.set_defaults(func=create_presentation_command)

    # REFACTORED: Removed 'themes' command.
    # JUSTIFICATION: Obsolete under the "Blank Canvas First" principle.

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    args.func(args)


if __name__ == "__main__":
    main()
