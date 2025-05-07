"""
MarkdownDeck - Convert Markdown to Google Slides presentations.

This module provides functionality to convert specially formatted markdown
content into Google Slides presentations with precise layout control.
"""

import logging

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource

from .api_client import ApiClient
from .layout import LayoutManager
from .parser import Parser

__version__ = "0.1.0"

logger = logging.getLogger(__name__)

# Set up default logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


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
    try:
        logger.info(f"Creating presentation: {title}")

        # Step 1: Parse the markdown using the enhanced parser
        parser = Parser()
        deck = parser.parse(markdown, title, theme_id)
        logger.info(f"Parsed {len(deck.slides)} slides from markdown")

        # Step 2: Calculate element positions and handle overflow
        layout_manager = LayoutManager()
        processed_slides = []

        for i, slide in enumerate(deck.slides):
            logger.info(f"Calculating layout for slide {i + 1}")
            result = layout_manager.calculate_positions(slide)

            # Handle both single slide and list of slides results
            if isinstance(result, list):
                logger.info(f"Slide {i + 1} overflow created {len(result)} slides")
                processed_slides.extend(result)
            else:
                processed_slides.append(result)

        deck.slides = processed_slides
        logger.info(f"Layout calculation completed for {len(deck.slides)} slides")

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

        # Step 1: Parse the markdown using the enhanced parser
        parser = Parser()
        deck = parser.parse(markdown, title, theme_id)
        logger.info(f"Parsed {len(deck.slides)} slides from markdown")

        # Step 2: Calculate element positions and handle overflow
        layout_manager = LayoutManager()
        processed_slides = []

        for i, slide in enumerate(deck.slides):
            logger.info(f"Calculating layout for slide {i + 1}")
            processed_slide = layout_manager.calculate_positions(slide)

            # Handle case where overflow creates multiple slides
            if isinstance(processed_slide, list):
                logger.info(f"Slide {i + 1} overflow created {len(processed_slide)} slides")
                processed_slides.extend(processed_slide)
            else:
                processed_slides.append(processed_slide)

        deck.slides = processed_slides
        logger.info(f"Layout calculation completed for {len(deck.slides)} slides")

        # Step 3: Generate API requests
        from .api_generator import ApiRequestGenerator

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
