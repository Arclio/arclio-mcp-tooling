import logging
from typing import Any

from markdown_it import MarkdownIt
from markdown_it.token import Token

from markdowndeck.models import Element
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
            ListFormatter(self.element_factory),
            CodeFormatter(self.element_factory),
            TableFormatter(self.element_factory),
            TextFormatter(self.element_factory, self.directive_parser),
        ]

    def parse_content(
        self,
        slide_title_text: str,
        subtitle_text: str | None,
        root_section: Section,
        slide_footer_text: str | None,
        title_directives: dict[str, Any] | None = None,
        subtitle_directives: dict[str, Any] | None = None,
        footer_directives: dict[str, Any] | None = None,
        base_directives: dict[str, Any] | None = None,
    ) -> list[Element]:
        """
        Parse content into slide elements, populating the section hierarchy.
        Returns a flat list of all created elements for the slide inventory.
        """
        base_directives = base_directives or {}
        meta_elements: list[Element] = []

        if slide_title_text:
            # Meta elements also inherit base directives
            final_title_directives = {**base_directives, **(title_directives or {})}
            title_element = self.element_factory.create_title_element(
                slide_title_text, directives=final_title_directives
            )
            meta_elements.append(title_element)

        if subtitle_text:
            final_subtitle_directives = {
                **base_directives,
                **(subtitle_directives or {}),
            }
            subtitle_element = self.element_factory.create_subtitle_element(
                subtitle_text, directives=final_subtitle_directives
            )
            meta_elements.append(subtitle_element)

        if root_section:
            self._process_section_recursively(root_section, base_directives)

        body_elements: list[Element] = []

        def extract_elements(sec: Section):
            for child in sec.children:
                if isinstance(child, Section):
                    extract_elements(child)
                elif isinstance(child, Element):
                    body_elements.append(child)

        if root_section:
            extract_elements(root_section)

        if slide_footer_text:
            final_footer_directives = {**base_directives, **(footer_directives or {})}
            footer_element = self.element_factory.create_footer_element(
                slide_footer_text, directives=final_footer_directives
            )
            meta_elements.append(footer_element)

        all_elements = meta_elements + body_elements
        logger.info(f"Created {len(all_elements)} total elements from content")
        return all_elements

    def _process_section_recursively(
        self, section: Section, inherited_directives: dict
    ):
        """
        Process a section's raw content into elements and recurse through child sections.
        """
        current_directives = {**inherited_directives, **section.directives}

        parsed_elements = []
        content_str = getattr(section, "content", None)
        if content_str:
            tokens = self.md.parse(content_str)
            parsed_elements = self._process_tokens_with_directive_detection(
                tokens, current_directives
            )
            if hasattr(section, "content"):
                delattr(section, "content")

        child_sections = [
            child for child in section.children if isinstance(child, Section)
        ]

        for child_section in child_sections:
            self._process_section_recursively(child_section, current_directives)

        section.children = parsed_elements + child_sections

    def _process_tokens_with_directive_detection(
        self, tokens: list[Token], section_directives: dict[str, Any]
    ) -> list[Element]:
        """Process tokens, detecting and applying directives correctly."""
        elements: list[Element] = []
        current_index = 0

        while current_index < len(tokens):
            created_elements, new_index = self._dispatch_to_formatter(
                tokens, current_index, section_directives
            )

            if created_elements:
                elements.extend(created_elements)

            current_index = max(new_index, current_index + 1)

        return elements

    def find_closing_token(
        self, tokens: list[Token], open_token_index: int, close_tag_type: str
    ) -> int:
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

    def _dispatch_to_formatter(
        self,
        tokens: list[Token],
        current_index: int,
        section_directives: dict[str, Any],
    ) -> tuple[list[Element], int]:
        if current_index >= len(tokens):
            return [], current_index
        token = tokens[current_index]

        for formatter in self.formatters:
            if formatter.can_handle(token, tokens[current_index:]):
                try:
                    elements, end_index = formatter.process(
                        tokens, current_index, section_directives
                    )
                    if elements is not None:
                        return elements, end_index
                except Exception as e:
                    # REFACTORED: Re-raise exceptions to be caught by the main Parser.
                    # MAINTAINS: Error logging for debuggability.
                    # JUSTIFICATION: Swallowing exceptions here prevents the main parser from knowing a slide
                    # failed, which in turn prevents the creation of a proper error slide. This fix
                    # ensures failures are propagated correctly.
                    logger.error(
                        f"Error in {formatter.__class__.__name__}: {e}", exc_info=True
                    )
                    raise

        return [], current_index
