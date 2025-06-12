"""Parser component for MarkdownDeck.

This module provides the main parser functionality that converts markdown
content into an intermediate representation suitable for generating slides.
"""

import logging

from markdowndeck.models import Deck, Slide, SlideLayout
from markdowndeck.parser.content import ContentParser
from markdowndeck.parser.directive import DirectiveParser
from markdowndeck.parser.section import SectionParser
from markdowndeck.parser.slide_extractor import SlideExtractor

logger = logging.getLogger(__name__)


class Parser:
    """Parse markdown into presentation slides with composable layouts."""

    def __init__(self):
        """Initialize the parser with its component parsers."""
        self.slide_extractor = SlideExtractor()
        self.section_parser = SectionParser()
        self.directive_parser = DirectiveParser()
        self.content_parser = ContentParser()

    def parse(self, markdown: str, title: str = None) -> Deck:
        """
        Parse markdown into a presentation deck.

        Args:
            markdown: Markdown content with slide formatting
            title: Optional presentation title (defaults to first slide title)

        Returns:
            Deck object representing the complete presentation
        """
        logger.info("Starting to parse markdown into presentation deck")
        slides_data = self.slide_extractor.extract_slides(markdown)
        logger.info(f"Extracted {len(slides_data)} slides from markdown")

        slides = []
        for slide_index, slide_data in enumerate(slides_data):
            try:
                # REFACTORED: Expect a single root section from the section parser
                # per PARSER_SPEC.md, Rule #4.1.
                root_section_model = self.section_parser.parse_sections(
                    slide_data["content"]
                )

                # REFACTORED: The content parser now operates on the children of the root section.
                # We pass the root section in a list to maintain a consistent interface for the content parser.
                elements = self.content_parser.parse_content(
                    slide_title_text=slide_data["title"],
                    subtitle_text=slide_data.get("subtitle"),
                    sections=[root_section_model] if root_section_model else [],
                    slide_footer_text=slide_data.get("footer"),
                    title_directives=slide_data.get("title_directives", {}),
                    subtitle_directives=slide_data.get("subtitle_directives", {}),
                )

                # Per spec, all slides are now BLANK layout
                layout = SlideLayout.BLANK

                # REFACTORED: Construct the Slide object with the new `root_section` model.
                # REMOVED: Obsolete attributes `sections` and `title_directives` are no longer set.
                slide = Slide(
                    elements=elements,
                    layout=layout,
                    notes=slide_data.get("notes"),
                    footer=slide_data.get("footer"),
                    background=slide_data.get("background"),
                    object_id=f"slide_{slide_index}",
                    root_section=root_section_model,
                )
                slides.append(slide)

            except Exception as e:
                logger.error(
                    f"Error processing slide {slide_index + 1}: {e}", exc_info=True
                )
                error_slide = self._create_error_slide(
                    slide_index, str(e), slide_data.get("title")
                )
                slides.append(error_slide)

        inferred_title = title or (
            slides_data[0].get("title") if slides_data else "Untitled"
        )
        deck = Deck(slides=slides, title=inferred_title)
        logger.info(
            f"Created deck with {len(slides)} slides and title: {inferred_title}"
        )
        return deck

    def _determine_layout(self, elements) -> SlideLayout:
        """All slides are BLANK layout per spec."""
        return SlideLayout.BLANK

    def _create_error_slide(
        self, slide_index: int, error_message: str, original_title: str | None = None
    ) -> Slide:
        """Creates a slide to display parsing errors."""
        from markdowndeck.models import ElementType, TextElement

        elements = [
            TextElement(
                element_type=ElementType.TITLE, text=f"Error in Slide {slide_index + 1}"
            ),
            TextElement(element_type=ElementType.TEXT, text=f"Error: {error_message}"),
        ]
        if original_title:
            elements.append(
                TextElement(
                    element_type=ElementType.SUBTITLE,
                    text=f"Original title: {original_title}",
                )
            )
        return Slide(
            elements=elements,
            layout=SlideLayout.BLANK,
            object_id=f"error_slide_{slide_index}",
        )
