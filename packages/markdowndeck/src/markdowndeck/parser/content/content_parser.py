import logging
from typing import Any

from markdown_it import MarkdownIt
from markdown_it.token import Token

from markdowndeck.models import Element
from markdowndeck.models.slide import Section
from markdowndeck.parser.content.content_normalizer import ContentNormalizer
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
    Parse markdown content into slide elements with unified processing pipeline.

    REFACTORED Version 7.1:
    - Unified content normalization for consistent tokenization
    - Enhanced code span protection throughout the pipeline
    - Predictable content splitting rules
    - Single processing path for all content types
    """

    def __init__(self):
        """Initialize the content parser and its formatters."""
        opts = {"html": False, "typographer": True, "linkify": True, "breaks": True}
        self.md = MarkdownIt("commonmark", opts)
        self.md.enable("table")
        self.md.enable("strikethrough")

        # PRESERVED: Disable rules that interfere with separator handling
        self.md.disable(["lheading", "hr"])

        self.element_factory = ElementFactory()
        self.directive_parser = DirectiveParser()
        self.normalizer = ContentNormalizer()
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
        REFACTORED: Unified content processing with normalization pipeline.

        FIXES:
        - test_bug_consecutive_headings_in_section_are_merged_6
        - test_bug_content_after_heading_in_same_block_is_lost
        - test_bug_directives_are_parsed_from_code_blocks
        """
        all_created_elements: list[Element] = []
        final_children: list[Element | Section] = []

        current_directives = {**inherited_directives, **section.directives}

        for child in section.children:
            if isinstance(child, str):
                logger.debug(
                    f"--- PROCESSING RAW CONTENT (UNIFIED PIPELINE) in section '{section.id}' ---\n{child}\n---------------------------------"
                )

                # PHASE 1: Normalize content for consistent processing
                normalized_content = self.normalizer.normalize(child)

                logger.debug(
                    f"--- NORMALIZED CONTENT ---\n{normalized_content}\n---------------------------------"
                )

                # PHASE 2: Tokenize normalized content
                tokens = self.md.parse(normalized_content)

                token_log = "\n".join(
                    [
                        f"  - Token[{i}]: type={t.type}, tag={t.tag}, level={t.level}, nesting={t.nesting}, content='{getattr(t, 'content', '')[:50]}...'"
                        for i, t in enumerate(tokens)
                    ]
                )
                logger.debug(
                    f"--- UNIFIED TOKENIZATION RESULT ({len(tokens)} tokens) ---\n{token_log}\n---------------------------------"
                )

                # PHASE 3: Process with unified logic (NO special cases)
                parsed_elements = self._process_tokens(tokens, current_directives)

                elements_log = "\n".join(
                    [
                        f"  - Element: type={e.element_type.value}, text='{getattr(e, 'text', getattr(e, 'code', ''))[:30]}...'"
                        for e in parsed_elements
                    ]
                )
                logger.debug(
                    f"--- UNIFIED PROCESSING RESULT ({len(parsed_elements)} elements) ---\n{elements_log}\n---------------------------------"
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

    def _process_tokens(
        self, tokens: list[Token], section_directives: dict[str, Any]
    ) -> list[Element]:
        """
        Clean token processing using formatter delegation.

        Iterates through markdown-it tokens and delegates to formatters based on token type,
        eliminating complex, heuristic-based splitting logic.
        """
        elements: list[Element] = []
        i = 0

        while i < len(tokens):
            token = tokens[i]
            logger.debug(
                f"Processing token {i}: type={token.type}, level={token.level}, tag={token.tag}"
            )

            # Try each formatter to see if it can handle this token
            handled = False
            for formatter in self.formatters:
                if formatter.can_handle(token, tokens[i:]):
                    try:
                        created_elements, end_index = formatter.process(
                            tokens, i, section_directives
                        )
                        if created_elements:
                            elements.extend(created_elements)
                            logger.debug(
                                f"Formatter '{formatter.__class__.__name__}' created {len(created_elements)} elements"
                            )

                        # Update loop index to continue after the processed tokens
                        i = end_index + 1
                        handled = True
                        logger.debug(
                            f"Formatter '{formatter.__class__.__name__}' processed tokens {i-1}-{end_index}"
                        )
                        break
                    except Exception as e:
                        logger.error(
                            f"Error in {formatter.__class__.__name__}: {e}",
                            exc_info=True,
                        )
                        raise

            # If no formatter can handle the token, log warning and skip
            if not handled:
                logger.warning(
                    f"No formatter could handle token {i}: type={token.type}, skipping"
                )
                i += 1

        logger.debug(f"Token processing created {len(elements)} total elements")
        return elements

    def _extract_clean_text_and_formatting(self, cleaned_text: str) -> tuple[str, list]:
        """Extract clean text and formatting from cleaned markdown text."""
        if not cleaned_text.strip():
            return "", []

        tokens = self.md.parse(cleaned_text.strip())
        for token in tokens:
            if token.type == "inline":
                plain_text = self._get_plain_text_from_inline_token(token)
                formatting = self.element_factory._extract_formatting_from_inline_token(
                    token
                )
                return plain_text, formatting

        return cleaned_text.strip(), []

    def _get_plain_text_from_inline_token(self, inline_token: Token) -> str:
        """Extract plain text content from an inline token."""
        if not hasattr(inline_token, "children") or inline_token.children is None:
            return getattr(inline_token, "content", "")

        plain_text = ""
        for child in inline_token.children:
            if child.type == "text" or child.type == "code_inline":
                plain_text += child.content
            elif child.type == "softbreak" or child.type == "hardbreak":
                plain_text += "\n"
            elif child.type == "image":
                plain_text += (
                    child.attrs.get("alt", "") if hasattr(child, "attrs") else ""
                )
            # Skip formatting markers

        return plain_text
