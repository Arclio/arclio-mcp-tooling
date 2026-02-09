#!/usr/bin/env python3
"""
OAuth2 refresh token generator for Google Workspace MCP server.

Runs a local OAuth flow to obtain a refresh token with all scopes required
by google-workspace-mcp. The token can then be set as the
GOOGLE_WORKSPACE_REFRESH_TOKEN environment variable.

Usage:
    # With uv (no install needed):
    uv run scripts/get_refresh_token.py path/to/client_secret.json

    # Or with pip:
    pip install google-auth-oauthlib
    python scripts/get_refresh_token.py path/to/client_secret.json

    # Optional: select only the scopes you need
    uv run scripts/get_refresh_token.py client_secret.json --scopes gmail drive

Download your client_secret.json from:
    Google Cloud Console -> APIs & Services -> Credentials -> OAuth 2.0 Client ID -> Download JSON
"""

# /// script
# dependencies = ["google-auth-oauthlib"]
# ///

import argparse
import json
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

# All scopes supported by Google Workspace MCP, grouped by service
SCOPES_BY_SERVICE = {
    "gmail": [
        "https://mail.google.com/",
        "https://www.googleapis.com/auth/gmail.settings.basic",
    ],
    "drive": [
        "https://www.googleapis.com/auth/drive",
    ],
    "docs": [
        "https://www.googleapis.com/auth/docs",
    ],
    "sheets": [
        "https://www.googleapis.com/auth/spreadsheets",
    ],
    "calendar": [
        "https://www.googleapis.com/auth/calendar",
    ],
    "slides": [
        "https://www.googleapis.com/auth/presentations",
    ],
}

ALL_SERVICES = list(SCOPES_BY_SERVICE.keys())


def get_scopes(services: list[str]) -> list[str]:
    """Collect OAuth scopes for the requested services."""
    scopes = []
    for service in services:
        service = service.lower()
        if service not in SCOPES_BY_SERVICE:
            print(f"Warning: Unknown service '{service}', skipping. Valid: {', '.join(ALL_SERVICES)}")
            continue
        scopes.extend(SCOPES_BY_SERVICE[service])
    return scopes


def main():
    parser = argparse.ArgumentParser(
        description="Generate an OAuth2 refresh token for Google Workspace MCP.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # All scopes (recommended):
  uv run scripts/get_refresh_token.py client_secret.json

  # Gmail and Drive only:
  uv run scripts/get_refresh_token.py client_secret.json --scopes gmail drive

  # Custom port for the OAuth callback:
  uv run scripts/get_refresh_token.py client_secret.json --port 8080
""",
    )
    parser.add_argument(
        "client_secret_file",
        help="Path to the OAuth client secret JSON file downloaded from Google Cloud Console.",
    )
    parser.add_argument(
        "--scopes",
        nargs="+",
        choices=ALL_SERVICES,
        default=ALL_SERVICES,
        help=f"Services to request scopes for (default: all). Choices: {', '.join(ALL_SERVICES)}",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=0,
        help="Port for the local OAuth callback server (default: auto-select).",
    )
    args = parser.parse_args()

    # Validate client secret file
    try:
        with open(args.client_secret_file) as f:
            client_config = json.load(f)
            # Extract client_id for display
            if "installed" in client_config:
                client_id = client_config["installed"].get("client_id", "unknown")
            elif "web" in client_config:
                client_id = client_config["web"].get("client_id", "unknown")
            else:
                print("Error: Unrecognized client secret file format.", file=sys.stderr)
                sys.exit(1)
    except FileNotFoundError:
        print(f"Error: File not found: {args.client_secret_file}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {args.client_secret_file}", file=sys.stderr)
        sys.exit(1)

    scopes = get_scopes(args.scopes)
    if not scopes:
        print("Error: No valid scopes selected.", file=sys.stderr)
        sys.exit(1)

    print(f"Client ID: {client_id}")
    print(f"Services:  {', '.join(args.scopes)}")
    print(f"Scopes:    {len(scopes)} scope(s)")
    for scope in scopes:
        print(f"  - {scope}")
    print()
    print("Opening browser for authorization...")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(args.client_secret_file, scopes)
    creds = flow.run_local_server(port=args.port)

    print()
    print("=" * 70)
    print("  SUCCESS - OAuth authorization complete")
    print("=" * 70)
    print()
    print("Refresh Token:")
    print(creds.refresh_token)
    print()
    print("Set this as your GOOGLE_WORKSPACE_REFRESH_TOKEN environment variable.")
    print()
    print("For Claude Code, add it to your MCP server config, e.g.:")
    print()
    print('  "env": {')
    print(f'    "GOOGLE_WORKSPACE_CLIENT_ID": "{client_id}",')
    print('    "GOOGLE_WORKSPACE_CLIENT_SECRET": "<your-client-secret>",')
    print(f'    "GOOGLE_WORKSPACE_REFRESH_TOKEN": "{creds.refresh_token}"')
    print("  }")
    print()


if __name__ == "__main__":
    main()
