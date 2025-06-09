"""Parse markdown content into slide elements with improved directive handling."""

import logging
from typing import Any

from markdown_it import MarkdownIt
from markdown_it.token import Token

from markdowndeck.models import AlignmentType, Element
from markdowndeck.models.slide import Section
from markdowndeck.parser.content.element_factory import ElementFactory
from markdowndeck.parser.content.formatters import (
    BaseFormatter,
    CodeFormatter,
    ImageFormatter,
    ListFormatter,
    TableFormatter,
    TextFormatter,
)
from markdowndeck.parser.directive import DirectiveParser

logger = logging.getLogger(__name__)


class ContentParser:
    """
    Parse markdown content into slide elements with improved directive handling.

    Key improvements:
    - Robust element-specific directive detection and association
    - Proper directive consumption to prevent spurious text elements
    - Enhanced block element directive support
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
        # ARCHITECTURAL IMPROVEMENT: Create single DirectiveParser instance
        self.directive_parser = DirectiveParser()

        # Initialize formatters with dependency injection
        self.formatters: list[BaseFormatter] = [
            ImageFormatter(
                self.element_factory
            ),  # TASK 1.3: ImageFormatter now handles post-image directives
            ListFormatter(
                self.element_factory
            ),  # ListFormatter now has its own DirectiveParser
            CodeFormatter(self.element_factory),
            TableFormatter(self.element_factory),
            TextFormatter(self.element_factory, self.directive_parser),
        ]

    def parse_content(
        self,
        slide_title_text: str,
        subtitle_text: str | None,
        sections: list[Section],
        slide_footer_text: str | None,
        title_directives: dict[str, Any] | None = None,
        subtitle_directives: dict[str, Any] | None = None,
    ) -> list[Element]:
        """
        Parse content into slide elements and populate section.elements.

        Args:
            slide_title_text: The slide title text
            subtitle_text: Optional subtitle text
            sections: The list of Section models for the slide
            slide_footer_text: Optional footer text
            title_directives: Optional title-level directives (from same-line parsing)
            subtitle_directives: Optional subtitle-level directives (from same-line parsing)

        Returns:
            List of all elements for the slide
        """
        logger.debug("Parsing content with improved directive handling")
        all_elements: list[Element] = []

        # Process the title (H1) with directives
        if slide_title_text:
            formatting = self.element_factory.extract_formatting_from_text(
                slide_title_text, self.md
            )

            # Per Unified Hierarchical Directive Scoping: only use title-level directives
            # (from same-line parsing), NOT section directives
            title_element = self.element_factory.create_title_element(
                slide_title_text, formatting, title_directives or {}
            )

            all_elements.append(title_element)
            logger.debug(f"Added title element: {slide_title_text[:30]}")

        # After the `if slide_title_text:` block, add this:
        if subtitle_text:
            # Subtitle formatting is simple, no need to parse complex markdown
            subtitle_formatting = self.element_factory.extract_formatting_from_text(
                subtitle_text, self.md
            )

            # FIX: Use subtitle directives from same-line parsing, not section directives
            # Per DIRECTIVES.md Rule 1: same-line directives take precedence
            if subtitle_directives:
                # Use subtitle directives from same-line parsing
                directives_to_use = subtitle_directives.copy()
                subtitle_alignment = AlignmentType(
                    subtitle_directives.get("align", "center")
                )
            else:
                # Fallback to section directives if no same-line directives
                section_for_subtitle = sections[0] if sections else Section()
                section_directives = section_for_subtitle.directives or {}
                directives_to_use = section_directives.copy()
                subtitle_alignment = AlignmentType(
                    section_directives.get("align", "center")
                )

            subtitle_element = self.element_factory.create_subtitle_element(
                text=subtitle_text,
                formatting=subtitle_formatting,
                alignment=subtitle_alignment,
                directives=directives_to_use,
            )
            all_elements.append(subtitle_element)
            logger.debug(f"Added subtitle element: {subtitle_text[:30]}")

        # Process all sections recursively
        for section in sections:
            self._process_section_recursively(section, all_elements)

        # Process the footer
        if slide_footer_text:
            formatting = self.element_factory.extract_formatting_from_text(
                slide_footer_text, self.md
            )
            footer_element = self.element_factory.create_footer_element(
                slide_footer_text, formatting
            )
            all_elements.append(footer_element)
            logger.debug(f"Added footer element: {slide_footer_text[:30]}")

        logger.info(f"Created {len(all_elements)} total elements from content")
        return all_elements

    def _process_section_recursively(
        self, section: Section, all_elements: list[Element]
    ):
        """Process a section and its subsections recursively."""
        if section.type == "row" and section.children:
            # Process child sections in row
            for child in section.children:
                if isinstance(child, Section):
                    self._process_section_recursively(child, all_elements)
        elif section.type == "section" and section.content:
            tokens = self.md.parse(section.content)
            logger.debug(f"Processing section {section.id} with {len(tokens)} tokens")

            # CRITICAL FIX P1: Enhanced token processing with directive detection
            parsed_elements = self._process_tokens_with_directive_detection(
                tokens, section.directives
            )

            # Add elements to the unified children list
            section.children.extend(parsed_elements)
            all_elements.extend(parsed_elements)
            logger.debug(
                f"Added {len(parsed_elements)} elements to section {section.id}"
            )

            # Clear stale raw content after parsing to prevent data inconsistency
            section.content = ""

    def _process_tokens_with_directive_detection(
        self, tokens: list[Token], section_directives: dict[str, Any]
    ) -> list[Element]:
        """
        Process tokens with enhanced directive detection for block elements.

        CRITICAL FIX P1: This method implements proper element-specific directive
        detection and association for block elements (lists, tables, code blocks).
        """
        elements: list[Element] = []
        current_index = 0

        # First pass: identify heading types for proper classification
        heading_info = self._analyze_headings(tokens)

        while current_index < len(tokens):
            if current_index >= len(tokens):
                break

            tokens[current_index]

            # TASK 1.1 FIX: Detect and consume directive-only paragraphs for THIS element only
            element_directives, consumed_tokens = self._extract_preceding_directives(
                tokens, current_index
            )

            if consumed_tokens > 0:
                # We consumed directive tokens, advance index
                current_index += consumed_tokens
                if current_index >= len(tokens):
                    break
                tokens[current_index]

            # TASK 1.1 FIX: Pass section and element directives separately
            # Don't merge them here - let the formatter handle the merging
            # This prevents element directives from being treated as section directives

            # Dispatch to appropriate formatter
            created_elements, new_index = self._dispatch_to_formatter(
                tokens,
                current_index,
                section_directives,
                element_directives,
                heading_info,
            )

            if created_elements:
                elements.extend(created_elements)
                for element in created_elements:
                    logger.debug(f"Added element: {element.element_type}")

            # TASK 1.1 FIX: Clear element_directives after processing to prevent bleeding
            # Directives should only apply to the immediately following element
            element_directives = {}

            # Advance to next token
            current_index = max(new_index + 1, current_index + 1)

        return elements

    def _extract_preceding_directives(
        self, tokens: list[Token], current_index: int
    ) -> tuple[dict[str, Any], int]:
        """
        Extract directives from directive-only paragraphs that precede block elements.

        CRITICAL FIX P1: This implements the missing functionality to detect
        directive lines like '[cell-align=center][border=1pt solid #DEE2E6]'
        that should apply to subsequent block elements.

        Returns:
            Tuple of (extracted_directives, number_of_tokens_consumed)
        """
        if current_index >= len(tokens):
            return {}, 0

        token = tokens[current_index]

        # Only check paragraph tokens for directive content
        if token.type != "paragraph_open":
            return {}, 0

        # Look for inline token
        if (
            current_index + 1 >= len(tokens)
            or tokens[current_index + 1].type != "inline"
        ):
            return {}, 0

        inline_token = tokens[current_index + 1]
        if not hasattr(inline_token, "content"):
            return {}, 0

        # Check if this paragraph contains only directives
        content = inline_token.content.strip()
        if not content:
            return {}, 0

        # Use DirectiveParser to check if this is a directive-only line
        directives, remaining_text = self.directive_parser.parse_inline_directives(
            content
        )

        if directives and not remaining_text.strip():
            # This is a directive-only paragraph, consume it
            logger.debug(f"Found element-specific directives: {directives}")

            # Find the closing paragraph token
            close_index = current_index + 2
            while (
                close_index < len(tokens)
                and tokens[close_index].type != "paragraph_close"
            ):
                close_index += 1

            tokens_consumed = close_index - current_index + 1
            return directives, tokens_consumed

        return {}, 0

    def _analyze_headings(self, tokens: list[Token]) -> dict[int, dict]:
        """
        Analyze heading tokens to determine their types (title, subtitle, section).

        ARCHITECTURAL IMPROVEMENT: Centralized heading analysis for consistent
        classification across the parser.
        """
        heading_info = {}
        first_h1_index = -1

        for i, token in enumerate(tokens):
            if token.type == "heading_open":
                level = int(token.tag[1])

                if level == 1 and first_h1_index == -1:
                    first_h1_index = i
                    heading_info[i] = {"type": "title", "level": level}
                elif level == 2 and first_h1_index != -1 and i == first_h1_index + 3:
                    # H2 immediately following first H1 is subtitle
                    heading_info[i] = {"type": "subtitle", "level": level}
                else:
                    # All other headings are section headings
                    heading_info[i] = {"type": "section", "level": level}

        return heading_info

    def _dispatch_to_formatter(
        self,
        tokens: list[Token],
        current_index: int,
        section_directives: dict[str, Any],
        element_directives: dict[str, Any],
        heading_info: dict,
    ) -> tuple[list[Element], int]:
        """
        Dispatch token processing to the appropriate formatter.

        TASK 3.1: Updated to handle list[Element] return from formatters.
        Enhanced dispatcher that tries multiple formatters until one
        successfully creates elements, enabling mixed-content parsing.
        """
        if current_index >= len(tokens):
            return [], current_index

        token = tokens[current_index]

        for formatter in self.formatters:
            if formatter.can_handle(token, tokens[current_index:]):
                try:
                    # Pass additional context for heading classification
                    kwargs = {}
                    if (
                        isinstance(formatter, TextFormatter)
                        and token.type == "heading_open"
                    ):
                        heading_data = heading_info.get(current_index, {})
                        kwargs["is_section_heading"] = (
                            heading_data.get("type") == "section"
                        )
                        kwargs["is_subtitle"] = heading_data.get("type") == "subtitle"

                    elements, end_index = formatter.process(
                        tokens,
                        current_index,
                        section_directives,
                        element_directives,
                        **kwargs,
                    )

                    # TASK 3.1: Return if the formatter created any elements
                    # If elements list is empty, continue trying other formatters
                    if elements:
                        logger.debug(
                            f"{formatter.__class__.__name__} successfully handled {token.type}, created {len(elements)} elements"
                        )
                        return elements, end_index
                    logger.debug(
                        f"{formatter.__class__.__name__} could not handle {token.type}, trying next formatter"
                    )

                except Exception as e:
                    logger.error(
                        f"Error in {formatter.__class__.__name__} processing token {token.type} at index {current_index}: {e}",
                        exc_info=True,
                    )
                    # Continue to next formatter instead of returning immediately

        # No formatter successfully handled the token
        if token.type not in ["softbreak", "hardbreak"]:
            logger.debug(
                f"No formatter successfully handled token: {token.type} at index {current_index}"
            )

        return [], current_index

    def _merge_directives(
        self, section_directives: dict[str, Any], element_directives: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Merge section and element-specific directives.

        Element-specific directives take precedence over section directives.
        """
        merged = section_directives.copy()
        if element_directives:
            merged.update(element_directives)
            logger.debug(f"Merged directives: {merged}")
        return merged
