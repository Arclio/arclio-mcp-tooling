"""
MarkdownDeck - Convert Markdown to Google Slides presentations.

This module provides functionality to convert specially formatted markdown
content into Google Slides presentations with precise layout control.
"""

import json
import logging

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource

from markdowndeck.api.api_client import ApiClient
from markdowndeck.layout import LayoutManager
from markdowndeck.models.deck import Deck
from markdowndeck.overflow import OverflowManager
from markdowndeck.parser import Parser

__version__ = "0.1.0"

logger = logging.getLogger(__name__)
# Dedicated logger for debug data
debug_data_logger = logging.getLogger("markdowndeck.debugdata")

# Set up default logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def _process_markdown_to_deck(markdown: str, title: str, theme_id: str | None) -> Deck:
    """
    Private helper function to parse markdown and calculate layout.

    Args:
        markdown: Markdown content for the presentation
        title: Title of the presentation
        theme_id: Google Slides theme ID (optional)

    Returns:
        Processed Deck object with calculated layouts
    """
    # Step 1: Parse the markdown using the enhanced parser
    parser = Parser()
    deck = parser.parse(markdown, title, theme_id)
    logger.info(f"Parsed {len(deck.slides)} slides from markdown")

    # Step 2: Calculate element positions and handle overflow
    layout_manager = LayoutManager()
    overflow_manager = OverflowManager()  # Instantiate the manager
    processed_slides = []

    for i, slide in enumerate(deck.slides):
        logger.info(f"Calculating layout for slide {i + 1}")
        # First, calculate positions for the slide
        positioned_slide = layout_manager.calculate_positions(slide)

        # Then, process the positioned slide for overflow
        logger.info(f"Handling overflow for positioned slide {i + 1}")
        final_slides = overflow_manager.process_slide(positioned_slide)

        # Log if overflow occurred
        if len(final_slides) > 1:
            logger.info(
                f"Slide {i + 1} was split into {len(final_slides)} slides due to overflow."
            )

        # Add the resulting slide(s) to our list
        processed_slides.extend(final_slides)

    # Per OVERFLOW_SPEC.md Rule #3: OverflowManager now orchestrates continuation slide positioning
    # No additional positioning needed here - all slides are properly positioned and finalized
    deck.slides = processed_slides
    logger.info(
        f"Layout and overflow processing completed for {len(deck.slides)} final slides"
    )

    return deck


def create_presentation(
    markdown: str,
    title: str = "Markdown Presentation",
    credentials: Credentials | None = None,
    service: Resource | None = None,
    theme_id: str | None = None,
) -> dict:
    """
    Create a Google Slides presentation from Markdown content.

    Args:
        markdown: Markdown content for the presentation
        title: Title of the presentation
        credentials: Google OAuth credentials (optional if service is provided)
        service: Existing Google API service (optional if credentials are provided)
        theme_id: Google Slides theme ID (optional)

    Returns:
        Dictionary with presentation details including ID and URL
    """
    # --- START TEMPORARY DEBUG LOGGING ---
    # WARNING: This logging is for temporary debugging purposes only and should be disabled in production
    log_entry = {"markdown": markdown, "title": title, "theme_id": theme_id}

    if credentials:
        creds_info = {
            "type": type(credentials).__name__,
            "has_token": hasattr(credentials, "token")
            and credentials.token is not None,
            "has_refresh_token": hasattr(credentials, "refresh_token")
            and credentials.refresh_token is not None,
            "token_uri": getattr(credentials, "token_uri", None),
            "client_id": getattr(credentials, "client_id", None),
            # Include actual token values for testing - REMOVE IN PRODUCTION
            "refresh_token": getattr(credentials, "refresh_token", None),
            "client_secret": getattr(credentials, "client_secret", None),
            "token": getattr(credentials, "token", None),
            # End of added values
            "client_secret_present": hasattr(credentials, "client_secret")
            and credentials.client_secret is not None,
            "scopes": getattr(credentials, "scopes", None),
            "service_account_email": getattr(
                credentials, "_service_account_email", None
            ),  # For ServiceAccountCredentials
        }
        # Add specific attributes if it's a service account credential
        if hasattr(credentials, "signer") and hasattr(
            credentials.signer, "email"
        ):  # Heuristic for service account
            creds_info["service_account_signer_email"] = getattr(
                credentials.signer, "email", None
            )

        log_entry["credentials_summary"] = creds_info
    else:
        log_entry["credentials_summary"] = "None provided"

    # Log service object info if provided
    if service:
        service_info = {
            "type": type(service).__name__,
            "service_name": getattr(service, "_servicePath", None),
            "base_url": getattr(service, "_baseUrl", None),
        }
        log_entry["service_summary"] = service_info
    else:
        log_entry["service_summary"] = "None provided"

    # Log as a JSON string for easier parsing
    try:
        debug_data_logger.info(f"MARKDOWNDECK_INPUT_DATA: {json.dumps(log_entry)}")
    except TypeError:  # Handle non-serializable parts gracefully if any slip through
        debug_data_logger.info(
            f"MARKDOWNDECK_INPUT_DATA (serialization fallback): {str(log_entry)}"
        )
    # --- END TEMPORARY DEBUG LOGGING ---

    try:
        logger.info(f"Creating presentation: {title}")

        # Process markdown to deck using shared helper
        deck = _process_markdown_to_deck(markdown, title, theme_id)

        # Step 3: Create the presentation via the API
        api_client = ApiClient(credentials, service)
        result = api_client.create_presentation_from_deck(deck)
        logger.info(f"Created presentation with ID: {result.get('presentationId')}")

        return result
    except Exception as e:
        logger.error(f"Failed to create presentation: {e}", exc_info=True)
        raise


def get_themes(
    credentials: Credentials | None = None,
    service: Resource | None = None,
) -> list[dict]:
    """
    Get a list of available presentation themes.

    Args:
        credentials: Google OAuth credentials (optional if service is provided)
        service: Existing Google API service (optional if credentials are provided)

    Returns:
        List of theme dictionaries with id and name
    """
    try:
        logger.info("Getting available themes")
        api_client = ApiClient(credentials, service)
        themes = api_client.get_available_themes()
        logger.info(f"Found {len(themes)} themes")
        return themes
    except Exception as e:
        logger.error(f"Failed to get themes: {e}", exc_info=True)
        raise


def markdown_to_requests(
    markdown: str,
    title: str = "Markdown Presentation",
    theme_id: str | None = None,
) -> dict:
    """
    Convert markdown to Google Slides API requests without executing them.

    This function is useful for integrations that need to generate requests
    but want to manage the API calls themselves.

    Args:
        markdown: Markdown content for the presentation
        title: Title of the presentation
        theme_id: Google Slides theme ID (optional)

    Returns:
        Dictionary with title and slide_batches list for API requests
    """
    try:
        logger.info(f"Converting markdown to API requests: {title}")

        # Process markdown to deck using shared helper
        deck = _process_markdown_to_deck(markdown, title, theme_id)

        # Step 3: Generate API requests
        from markdowndeck.api.api_generator import ApiRequestGenerator

        generator = ApiRequestGenerator()

        # Use a placeholder presentation ID that will be replaced by the consumer
        placeholder_id = "PLACEHOLDER_PRESENTATION_ID"
        batches = generator.generate_batch_requests(deck, placeholder_id)
        logger.info(f"Generated {len(batches)} batches of API requests")

        return {
            "title": deck.title,
            "slide_batches": batches,
        }
    except Exception as e:
        logger.error(f"Failed to convert markdown to requests: {e}", exc_info=True)
        raise
