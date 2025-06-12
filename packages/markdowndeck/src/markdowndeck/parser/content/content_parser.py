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
    ListFormatter,
    TableFormatter,
    TextFormatter,
)
from markdowndeck.parser.directive import DirectiveParser

logger = logging.getLogger(__name__)


class ContentParser:
    """
    Parse markdown content into slide elements with improved directive handling.
    """

    def __init__(self):
        """Initialize the content parser and its formatters."""
        opts = {"html": False, "typographer": True, "linkify": True, "breaks": True}
        self.md = MarkdownIt("commonmark", opts)
        self.md.enable("table")
        self.md.enable("strikethrough")
        self.element_factory = ElementFactory()
        self.directive_parser = DirectiveParser()
        self.formatters: list[BaseFormatter] = [
            # ImageFormatter is now simpler and only handles `image` tokens.
            # TextFormatter handles complex paragraphs with images.
            ListFormatter(self.element_factory),
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
        Parse content into slide elements and populate section.children.
        """
        logger.debug("Parsing content with improved directive handling")
        all_elements: list[Element] = []

        if slide_title_text:
            cleaned_title, line_directives = (
                self.directive_parser.parse_and_strip_from_text(slide_title_text)
            )
            final_title_directives = {**(title_directives or {}), **line_directives}
            formatting = self.element_factory.extract_formatting_from_text(
                cleaned_title, self.md
            )
            title_element = self.element_factory.create_title_element(
                cleaned_title, formatting, final_title_directives
            )
            all_elements.append(title_element)

        if subtitle_text:
            cleaned_subtitle, line_directives = (
                self.directive_parser.parse_and_strip_from_text(subtitle_text)
            )
            final_subtitle_directives = {
                **(subtitle_directives or {}),
                **line_directives,
            }
            subtitle_formatting = self.element_factory.extract_formatting_from_text(
                cleaned_subtitle, self.md
            )
            subtitle_alignment = AlignmentType(
                final_subtitle_directives.get("align", "center")
            )
            subtitle_element = self.element_factory.create_subtitle_element(
                text=cleaned_subtitle,
                formatting=subtitle_formatting,
                alignment=subtitle_alignment,
                directives=final_subtitle_directives,
            )
            all_elements.append(subtitle_element)

        for section in sections:
            self._process_section_recursively(section, all_elements)

        if slide_footer_text:
            cleaned_footer, line_directives = (
                self.directive_parser.parse_and_strip_from_text(slide_footer_text)
            )
            formatting = self.element_factory.extract_formatting_from_text(
                cleaned_footer, self.md
            )
            footer_element = self.element_factory.create_footer_element(
                cleaned_footer, formatting
            )
            # Apply directives to footer if any were found
            if line_directives:
                footer_element.directives = line_directives
            all_elements.append(footer_element)

        logger.info(f"Created {len(all_elements)} total elements from content")
        return all_elements

    def _process_section_recursively(
        self, section: Section, all_elements: list[Element]
    ):
        """
        Process a section and its children recursively, populating elements.
        """
        if section.content:
            tokens = self.md.parse(section.content)
            parsed_elements = self._process_tokens_with_directive_detection(
                tokens, section.directives
            )
            section.children.extend(parsed_elements)
            all_elements.extend(parsed_elements)
            section.content = ""

        child_sections = [
            child for child in section.children if isinstance(child, Section)
        ]
        for child_section in child_sections:
            self._process_section_recursively(child_section, all_elements)

    def _process_tokens_with_directive_detection(
        self, tokens: list[Token], section_directives: dict[str, Any]
    ) -> list[Element]:
        """Process tokens, detecting and applying directives correctly."""
        elements: list[Element] = []
        current_index = 0
        heading_info = self._analyze_headings(tokens)

        while current_index < len(tokens):
            element_directives, consumed_tokens = self._extract_preceding_directives(
                tokens, current_index
            )
            current_index += consumed_tokens

            if current_index >= len(tokens):
                break

            created_elements, new_index = self._dispatch_to_formatter(
                tokens,
                current_index,
                section_directives,
                element_directives,
                heading_info,
            )

            if created_elements:
                elements.extend(created_elements)

            current_index = max(new_index + 1, current_index + 1)

        return elements

    def _extract_preceding_directives(
        self, tokens: list[Token], current_index: int
    ) -> tuple[dict[str, Any], int]:
        """Extracts directives from a directive-only paragraph preceding another element."""
        if (
            current_index >= len(tokens)
            or tokens[current_index].type != "paragraph_open"
        ):
            return {}, 0

        inline_index = current_index + 1
        if inline_index >= len(tokens) or tokens[inline_index].type != "inline":
            return {}, 0

        inline_token = tokens[inline_index]
        content = inline_token.content.strip()
        if not content:
            return {}, 0

        directives, remaining_text = self.directive_parser.parse_inline_directives(
            content
        )

        if directives and not remaining_text:
            logger.debug(f"Found element-specific directives: {directives}")
            close_index = self.find_closing_token(
                tokens, current_index, "paragraph_close"
            )
            return directives, close_index - current_index + 1

        return {}, 0

    def find_closing_token(
        self, tokens: list[Token], open_token_index: int, close_tag_type: str
    ) -> int:
        """Finds the index of the matching closing token."""
        open_token = tokens[open_token_index]
        depth = 1
        for i in range(open_token_index + 1, len(tokens)):
            token = tokens[i]
            if token.level == open_token.level:
                if token.type == open_token.type:
                    depth += 1
                elif token.type == close_tag_type:
                    depth -= 1
                    if depth == 0:
                        return i
        return len(tokens) - 1

    def _analyze_headings(self, tokens: list[Token]) -> dict[int, dict]:
        """Analyzes heading tokens to classify them."""
        heading_info = {}
        first_h1_index = -1
        for i, token in enumerate(tokens):
            if token.type == "heading_open":
                level = int(token.tag[1])
                if level == 1 and first_h1_index == -1:
                    first_h1_index = i
                    heading_info[i] = {"type": "title", "level": level}
                elif level == 2 and i == first_h1_index + 3:
                    heading_info[i] = {"type": "subtitle", "level": level}
                else:
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
        """Dispatches token processing to the appropriate formatter."""
        if current_index >= len(tokens):
            return [], current_index

        token = tokens[current_index]

        # A paragraph can contain anything, so TextFormatter is the general handler.
        if token.type == "paragraph_open":
            formatter = self.formatters[-1]  # TextFormatter
            return formatter.process(
                tokens, current_index, section_directives, element_directives
            )

        for formatter in self.formatters:
            if formatter.can_handle(token, tokens[current_index:]):
                try:
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
                    if elements:
                        return elements, end_index
                except Exception as e:
                    logger.error(
                        f"Error in {formatter.__class__.__name__}: {e}", exc_info=True
                    )

        return [], current_index
