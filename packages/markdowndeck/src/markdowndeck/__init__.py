"""
MarkdownDeck - Convert Markdown to Google Slides presentations.
"""

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
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def _process_markdown_to_deck(markdown: str, title: str) -> Deck:
    """
    Private helper function to parse markdown and calculate layout.
    """
    parser = Parser()
    deck = parser.parse(markdown, title)
    logger.info(f"Parsed {len(deck.slides)} slides from markdown")

    layout_manager = LayoutManager()
    overflow_manager = OverflowManager()

    # FIXED: Corrected processing loop to prevent infinite overflow bug.
    final_slides_for_deck = []
    initial_slides = list(deck.slides)  # Iterate over a copy.

    for i, slide in enumerate(initial_slides):
        logger.info(f"Calculating layout for slide {i + 1}")
        positioned_slide = layout_manager.calculate_positions(slide)
        final_slides = overflow_manager.process_slide(positioned_slide)
        final_slides_for_deck.extend(final_slides)

    deck.slides = final_slides_for_deck
    logger.info(
        f"Layout and overflow processing completed for {len(deck.slides)} final slides"
    )
    return deck


def create_presentation(
    markdown: str,
    title: str = "Markdown Presentation",
    credentials: Credentials | None = None,
    service: Resource | None = None,
) -> dict:
    """
    Create a Google Slides presentation from Markdown content.
    """
    try:
        logger.info(f"Creating presentation: {title}")
        deck = _process_markdown_to_deck(markdown, title)
        api_client = ApiClient(credentials, service)
        result = api_client.create_presentation_from_deck(deck)
        logger.info(f"Created presentation with ID: {result.get('presentationId')}")
        return result
    except Exception as e:
        logger.error(f"Failed to create presentation: {e}", exc_info=True)
        raise


def markdown_to_requests(
    markdown: str,
    title: str = "Markdown Presentation",
) -> dict:
    """
    Convert markdown to Google Slides API requests without executing them.
    """
    try:
        logger.info(f"Converting markdown to API requests: {title}")
        deck = _process_markdown_to_deck(markdown, title)
        from markdowndeck.api.api_generator import ApiRequestGenerator

        generator = ApiRequestGenerator()
        placeholder_id = "PLACEHOLDER_PRESENTATION_ID"
        batches = generator.generate_batch_requests(deck, placeholder_id)
        logger.info(f"Generated {len(batches)} batches of API requests")
        return {"title": deck.title, "slide_batches": batches}
    except Exception as e:
        logger.error(f"Failed to convert markdown to requests: {e}", exc_info=True)
        raise
