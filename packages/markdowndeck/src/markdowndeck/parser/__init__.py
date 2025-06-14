import logging

from markdowndeck.models import Deck, Slide, SlideLayout
from markdowndeck.parser.content import ContentParser
from markdowndeck.parser.section import SectionParser
from markdowndeck.parser.slide_extractor import SlideExtractor

logger = logging.getLogger(__name__)


class Parser:
    """Parse markdown into presentation slides with composable layouts."""

    def __init__(self):
        """Initialize the parser with its component parsers."""
        self.slide_extractor = SlideExtractor()
        self.section_parser = SectionParser()
        self.content_parser = ContentParser()

    def parse(self, markdown: str, title: str = None) -> Deck:
        """
        Parse markdown into a presentation deck.
        """
        logger.info("Starting to parse markdown into presentation deck")
        slides_data = self.slide_extractor.extract_slides(markdown)
        logger.info(f"Extracted {len(slides_data)} slides from markdown")

        slides = []
        for slide_index, slide_data in enumerate(slides_data):
            try:
                root_section_model = self.section_parser.parse_sections(
                    slide_data["content"]
                )

                elements = self.content_parser.parse_content(
                    slide_title_text=slide_data.get("title"),
                    subtitle_text=slide_data.get("subtitle"),
                    root_section=root_section_model,
                    slide_footer_text=slide_data.get("footer"),
                    title_directives=slide_data.get("title_directives"),
                    subtitle_directives=slide_data.get("subtitle_directives"),
                    footer_directives=slide_data.get("footer_directives"),
                    base_directives=slide_data.get("base_directives", {}),
                )

                slide = Slide(
                    elements=elements,
                    layout=SlideLayout.BLANK,
                    notes=slide_data.get("notes"),
                    background=slide_data.get("background"),
                    object_id=f"slide_{slide_index}",
                    root_section=root_section_model,
                    base_directives=slide_data.get("base_directives", {}),
                    title_directives=slide_data.get("title_directives", {}),
                    subtitle_directives=slide_data.get("subtitle_directives", {}),
                    footer_directives=slide_data.get("footer_directives", {}),
                )
                slides.append(slide)

            except ValueError as e:
                logger.error(
                    f"Failed to parse slide {slide_index + 1}: {e}", exc_info=False
                )
                error_slide = self._create_error_slide(
                    slide_index, str(e), slide_data.get("title")
                )
                slides.append(error_slide)
            except Exception as e:
                logger.error(
                    f"An unexpected error occurred while processing slide {slide_index + 1}: {e}",
                    exc_info=True,
                )
                error_slide = self._create_error_slide(
                    slide_index, f"Unexpected error: {e}", slide_data.get("title")
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

    def _create_error_slide(
        self, slide_index: int, error_message: str, original_title: str | None = None
    ) -> Slide:
        """Creates a slide to display parsing errors."""
        # REFACTORED: Creates a fully valid Slide object with well-formed elements to fix test failures.
        # MAINTAINS: The core behavior of displaying an error on a slide.
        # JUSTIFICATION: The previous implementation, while seemingly correct, resulted in an invalid
        # object that could not be inspected by tests, causing an AttributeError. This version ensures
        # a valid object is always created.
        from markdowndeck.models import ElementType, TextElement

        error_title = TextElement(
            object_id=f"error_title_{slide_index}",
            element_type=ElementType.TITLE,
            text=f"Error in Slide {slide_index + 1}",
        )
        error_text = TextElement(
            object_id=f"error_text_{slide_index}",
            element_type=ElementType.TEXT,
            text=f"Error: {error_message}",
        )

        elements = [error_title, error_text]
        if original_title:
            elements.append(
                TextElement(
                    object_id=f"error_subtitle_{slide_index}",
                    element_type=ElementType.SUBTITLE,
                    text=f"Original title: '{original_title}'",
                )
            )

        # Create a valid slide object with elements populated.
        # This slide will be processed by the LayoutManager later.
        return Slide(
            elements=elements,
            renderable_elements=[],
            root_section=None,
            layout=SlideLayout.BLANK,
            object_id=f"error_slide_{slide_index}",
        )
