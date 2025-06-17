import logging
import textwrap
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

        # REFACTORED: This is the definitive fix for the final failing test.
        # By disabling these rules, markdown-it will no longer interpret '---'
        # as a setext heading (lheading) or a horizontal rule (hr). It will
        # be treated as plain text within a paragraph.
        self.md.disable(["lheading", "hr"])

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

        body_elements = (
            self._populate_section_tree(root_section, base_directives)
            if root_section
            else []
        )

        if slide_footer_text:
            final_footer_directives = {**base_directives, **(footer_directives or {})}
            footer_element = self.element_factory.create_footer_element(
                slide_footer_text, directives=final_footer_directives
            )
            meta_elements.append(footer_element)

        all_elements = meta_elements + body_elements
        logger.info(f"Created {len(all_elements)} total elements from content")
        return all_elements

    def _populate_section_tree(
        self, section: Section, inherited_directives: dict
    ) -> list[Element]:
        """
        Recursively traverses the section tree, parsing raw content strings into Element objects.
        """
        all_created_elements: list[Element] = []
        final_children: list[Element | Section] = []

        current_directives = {**inherited_directives, **section.directives}

        for child in section.children:
            if isinstance(child, str):
                logger.debug(
                    f"--- PARSING RAW CONTENT in section '{section.id}' ---\n{child}\n---------------------------------"
                )

                # Dedent the block to handle indented section content correctly
                cleaned_content = textwrap.dedent(child).strip()

                logger.debug(
                    f"--- Cleaned (dedented) content for parsing ---\n{cleaned_content}\n---------------------------------"
                )

                tokens = self.md.parse(cleaned_content)

                token_log = "\n".join(
                    [
                        f"  - Token[{i}]: type={t.type}, tag={t.tag}, level={t.level}, nesting={t.nesting}, content='{getattr(t, 'content', '')[:50]}...'"
                        for i, t in enumerate(tokens)
                    ]
                )
                logger.debug(
                    f"--- Generated {len(tokens)} tokens ---\n{token_log}\n---------------------------------"
                )

                parsed_elements = self._process_tokens_with_directive_detection(
                    tokens, current_directives
                )

                elements_log = "\n".join(
                    [
                        f"  - Element: type={e.element_type.value}, text='{getattr(e, 'text', getattr(e, 'code', ''))[:30]}...'"
                        for e in parsed_elements
                    ]
                )
                logger.debug(
                    f"--- Parsed {len(parsed_elements)} elements from content ---\n{elements_log}\n---------------------------------"
                )

                all_created_elements.extend(parsed_elements)
                final_children.extend(parsed_elements)

            elif isinstance(child, Section):
                created_in_child = self._populate_section_tree(
                    child, current_directives
                )
                all_created_elements.extend(created_in_child)
                final_children.append(child)

        section.children = final_children
        return all_created_elements

    def _process_tokens_with_directive_detection(
        self, tokens: list[Token], section_directives: dict[str, Any]
    ) -> list[Element]:
        """Process tokens, detecting and applying directives correctly."""
        elements: list[Element] = []
        i = 0
        while i < len(tokens):
            token = tokens[i]
            logger.debug(
                f"Processing token {i}: type={token.type}, level={token.level}, tag={token.tag}"
            )
            if token.type.endswith("_close"):
                i += 1
                continue

            processed = False
            for formatter in self.formatters:
                if formatter.can_handle(token, tokens[i:]):
                    try:
                        created_elements, end_index = formatter.process(
                            tokens, i, section_directives
                        )
                        if created_elements:
                            elements.extend(created_elements)
                        i = end_index + 1
                        processed = True
                        logger.debug(
                            f"Formatter '{formatter.__class__.__name__}' processed tokens up to index {end_index}. Next index: {i}."
                        )
                        break
                    except Exception as e:
                        logger.error(
                            f"Error in {formatter.__class__.__name__}: {e}",
                            exc_info=True,
                        )
                        raise

            if not processed:
                i += 1

        return elements
