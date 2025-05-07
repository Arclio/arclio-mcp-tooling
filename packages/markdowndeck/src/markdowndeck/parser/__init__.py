"""Parser component for MarkdownDeck.

This module provides the main parser functionality that converts markdown
content into an intermediate representation suitable for generating slides.
"""

import logging

from ..models import Deck, Slide, SlideLayout
from .content_parser import ContentParser
from .directive_parser import DirectiveParser
from .layout_processor import LayoutProcessor
from .section_parser import SectionParser
from .slide_extractor import SlideExtractor

logger = logging.getLogger(__name__)


class Parser:
    """Parse markdown into presentation slides with composable layouts."""

    def __init__(self):
        """Initialize the parser with its component parsers."""
        self.slide_extractor = SlideExtractor()
        self.section_parser = SectionParser()
        self.directive_parser = DirectiveParser()
        self.content_parser = ContentParser()
        self.layout_processor = LayoutProcessor()

    def parse(self, markdown: str, title: str = None, theme_id: str | None = None) -> Deck:
        """
        Parse markdown into a presentation deck.

        Args:
            markdown: Markdown content with slide formatting
            title: Optional presentation title (defaults to first slide title)
            theme_id: Optional theme ID for the presentation

        Returns:
            Deck object representing the complete presentation
        """
        # Log start of parsing
        logger.info("Starting to parse markdown into presentation deck")

        # Step 1: Split markdown into individual slides
        slides_data = self.slide_extractor.extract_slides(markdown)
        logger.info(f"Extracted {len(slides_data)} slides from markdown")

        # Process each slide
        slides = []
        for slide_index, slide_data in enumerate(slides_data):
            try:
                # Log current slide
                logger.debug(f"Processing slide {slide_index + 1}")

                # Step 2: Parse slide sections
                sections = self.section_parser.parse_sections(slide_data["content"])
                logger.debug(f"Parsed {len(sections)} sections for slide {slide_index + 1}")

                # Step 3: Parse directives for each section
                for section in sections:
                    self.directive_parser.parse_directives(section)

                    # If this is a row section, parse directives for subsections too
                    if section["type"] == "row" and "subsections" in section:
                        for subsection in section["subsections"]:
                            self.directive_parser.parse_directives(subsection)

                # Step 4: Calculate implicit sizing for sections
                self.layout_processor.calculate_implicit_dimensions(sections)

                # Step 5: Parse content in each section to create elements
                elements = self.content_parser.parse_content(
                    slide_data["title"], sections, slide_data.get("footer")
                )
                logger.debug(f"Created {len(elements)} elements for slide {slide_index + 1}")

                # Step 6: Create slide
                slide = Slide(
                    elements=elements,
                    layout=self.layout_processor.determine_layout(elements),
                    notes=slide_data.get("notes"),
                    footer=slide_data.get("footer"),
                    background=slide_data.get("background"),
                    object_id=f"slide_{slide_index}",
                    sections=sections,
                )

                slides.append(slide)
                logger.debug(f"Added slide {slide_index + 1} to deck")

            except Exception as e:
                # Log error but continue with other slides
                logger.error(f"Error processing slide {slide_index + 1}: {e}", exc_info=True)

                # Create an error slide
                error_slide = self._create_error_slide(slide_index, str(e), slide_data.get("title"))
                slides.append(error_slide)

        # Create and return deck
        inferred_title = title or (slides_data[0].get("title") if slides_data else "Untitled")

        deck = Deck(slides=slides, title=inferred_title, theme_id=theme_id)
        logger.info(f"Created deck with {len(slides)} slides and title: {inferred_title}")

        return deck

    def _create_error_slide(
        self, slide_index: int, error_message: str, original_title: str | None = None
    ) -> Slide:
        """
        Create an error slide for when processing fails.

        Args:
            slide_index: Index of the problematic slide
            error_message: Error message to display
            original_title: Original slide title if available

        Returns:
            Slide with error message
        """
        from ..models import ElementType, TextElement

        # Create title and error message elements
        elements = [
            TextElement(
                element_type=ElementType.TITLE,
                text=f"Error in Slide {slide_index + 1}",
            ),
            TextElement(
                element_type=ElementType.TEXT,
                text=f"There was an error processing this slide: {error_message}",
            ),
        ]

        # Add original title as subtitle if available
        if original_title:
            elements.append(
                TextElement(
                    element_type=ElementType.SUBTITLE,
                    text=f"Original title: {original_title}",
                )
            )

        return Slide(
            elements=elements,
            layout=SlideLayout.TITLE_AND_BODY,
            object_id=f"error_slide_{slide_index}",
        )
