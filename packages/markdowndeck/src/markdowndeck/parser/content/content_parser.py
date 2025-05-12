"""Parse markdown content into slide elements with improved handling using formatters."""

import logging
from typing import Any

from markdown_it import MarkdownIt
from markdown_it.token import Token

from markdowndeck.models import (
    Element,
)
from markdowndeck.models.slide import Section
from markdowndeck.parser.content.element_factory import ElementFactory
from markdowndeck.parser.content.formatters import (
    BaseFormatter,
    CodeFormatter,
    ImageFormatter,  # Added
    ListFormatter,
    TableFormatter,
    TextFormatter,
)

logger = logging.getLogger(__name__)


class ContentParser:
    """
    Parse markdown content into slide elements by dispatching to specialized formatters.
    """

    def __init__(self):
        """Initialize the content parser and its formatters."""
        opts = {
            "html": False,
            "typographer": True,
            "linkify": True,
            "breaks": True,
        }
        self.md = MarkdownIt("commonmark", opts)
        self.md.enable("table")
        self.md.enable("strikethrough")

        self.element_factory = ElementFactory()

        # Initialize formatters, injecting the element factory
        # Order matters: ImageFormatter should attempt to handle image-only paragraphs
        # before TextFormatter handles general paragraphs.
        self.formatters: list[BaseFormatter] = [
            ImageFormatter(self.element_factory),
            ListFormatter(self.element_factory),
            CodeFormatter(self.element_factory),
            TableFormatter(self.element_factory),
            TextFormatter(self.element_factory),  # Handles headings, paragraphs, quotes
        ]

    def parse_content(
        self,
        slide_title_text: str,
        sections: list[Section],
        slide_footer_text: str | None,
    ) -> list[Element]:
        """
        Parse content into slide elements and populate section.elements.
        Also returns a flat list of all elements for the slide's main elements list.

        Args:
            slide_title_text: The slide title text
            sections: The list of Section models for the slide
            slide_footer_text: Optional footer text

        Returns:
            List of all elements for the slide (for the slide.elements list)
        """
        logger.debug(
            "Parsing content into slide elements and populating section.elements"
        )
        all_elements: list[Element] = []

        if slide_title_text:
            formatting = self.element_factory.extract_formatting_from_text(
                slide_title_text, self.md
            )
            title_element = self.element_factory.create_title_element(
                slide_title_text, formatting
            )
            all_elements.append(title_element)
            logger.debug(f"Added title element: {slide_title_text[:30]}")

        # Helper function to process a single section and its subsections
        def _process_section_recursively(current_section: Section):
            if current_section.type == "row" and current_section.subsections:
                for subsection in current_section.subsections:
                    _process_section_recursively(subsection)
            elif current_section.type == "section" and current_section.content:
                tokens = self.md.parse(current_section.content)
                logger.debug(
                    f"Tokens for section {current_section.id}: {[t.type for t in tokens if t.type != 'softbreak']}"
                )
                # Process tokens and populate section.elements
                parsed_elements = self._process_tokens(
                    tokens, current_section.directives
                )
                current_section.elements.extend(parsed_elements)
                all_elements.extend(parsed_elements)
                logger.debug(
                    f"Added {len(parsed_elements)} elements to section {current_section.id}"
                )

        # Process all sections and populate their elements
        for section in sections:
            _process_section_recursively(section)

        if slide_footer_text:
            formatting = self.element_factory.extract_formatting_from_text(
                slide_footer_text, self.md
            )
            footer_element = self.element_factory.create_footer_element(
                slide_footer_text, formatting
            )
            all_elements.append(footer_element)
            logger.debug(f"Added footer element: {slide_footer_text[:30]}")

        logger.info(
            f"Created {len(all_elements)} total elements from content using formatters."
        )
        return all_elements

    def _process_tokens(
        self, tokens: list[Token], directives: dict[str, Any]
    ) -> list[Element]:
        elements: list[Element] = []
        current_index = 0

        # First pass: identify which headings are section headers within content
        # Instead of modifying tokens, track their indices
        section_heading_indices = set()
        first_h1_seen = False
        first_h2_seen = False

        for i, token in enumerate(tokens):
            if token.type == "heading_open":
                level = int(token.tag[1])
                if level == 1 and not first_h1_seen:
                    first_h1_seen = True
                elif level == 2 and not first_h2_seen:
                    first_h2_seen = True
                else:
                    # Mark all other headings as section headings by storing their index
                    section_heading_indices.add(i)

        # Second pass: process all tokens
        while current_index < len(tokens):
            token = tokens[current_index]
            dispatched = False

            for formatter in self.formatters:
                if formatter.can_handle(token, tokens[current_index:]):
                    try:
                        # Pass section_heading_indices to formatters that need it
                        if (
                            isinstance(formatter, TextFormatter)
                            and token.type == "heading_open"
                        ):
                            # Add is_section_heading parameter to process
                            element, new_index_offset = formatter.process(
                                tokens,
                                current_index,
                                directives,
                                is_section_heading=(
                                    current_index in section_heading_indices
                                ),
                            )
                        else:
                            element, new_index_offset = formatter.process(
                                tokens, current_index, directives
                            )

                        if element:
                            elements.append(element)

                        current_index = new_index_offset + 1
                        dispatched = True
                        break
                    except Exception as e:
                        logger.error(
                            f"Error processing token type {token.type} at index {current_index} "
                            f"with formatter {formatter.__class__.__name__}: {e}",
                            exc_info=True,
                        )
                        # Graceful skip logic (unchanged)
                        original_token_for_skip = tokens[current_index]
                        if original_token_for_skip.type.endswith("_open"):
                            try:
                                if hasattr(formatter, "find_closing_token"):
                                    current_index = (
                                        formatter.find_closing_token(
                                            tokens,
                                            current_index,
                                            original_token_for_skip.type.replace(
                                                "_open", "_close"
                                            ),
                                        )
                                        + 1
                                    )
                                else:
                                    temp_bf = BaseFormatter(self.element_factory)
                                    current_index = (
                                        temp_bf.find_closing_token(
                                            tokens,
                                            current_index,
                                            original_token_for_skip.type.replace(
                                                "_open", "_close"
                                            ),
                                        )
                                        + 1
                                    )
                            except Exception:
                                current_index += 1
                        else:
                            current_index += 1
                        dispatched = True
                        break

            if not dispatched:
                if token.type not in ["softbreak", "hardbreak"] and token.type:
                    logger.debug(
                        f"No formatter handled token: {token.type} at index {current_index}. Content: '{token.content[:50]}...' Skipping."
                    )
                current_index += 1

        return [e for e in elements if e is not None]
