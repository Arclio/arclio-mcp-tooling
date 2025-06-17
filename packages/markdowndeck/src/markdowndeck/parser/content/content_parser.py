import logging
import re
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
                normalized_content = self._normalize_content_for_parsing(child)

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

    def _normalize_content_for_parsing(self, content: str) -> str:
        """
        Normalize content to ensure consistent tokenization by markdown-it.

        This eliminates the inconsistent processing paths that cause tests to fail.
        The goal is to ensure similar input structures always produce similar tokens.
        """
        if not content.strip():
            return content

        logger.debug(f"Starting normalization of {len(content)} character content")

        # STEP 1: Protect all code constructs
        protected_content, protected_blocks = self._protect_all_code_constructs(content)
        logger.debug(f"Protected {len(protected_blocks)} code constructs")

        # STEP 2: Normalize indentation (prevents code_block tokenization)
        normalized_content = textwrap.dedent(protected_content).strip()
        logger.debug("Dedented content: removed common leading whitespace")

        # STEP 3: Ensure proper block separation for predictable parsing
        normalized_content = self._ensure_proper_block_separation(normalized_content)
        logger.debug("Applied block separation rules")

        # STEP 4: Restore protected code
        final_content = self._restore_all_code_constructs(
            normalized_content, protected_blocks
        )

        logger.debug(
            f"Content normalization complete: {len(content)} chars -> {len(final_content)} chars"
        )
        return final_content

    def _protect_all_code_constructs(self, content: str) -> tuple[str, dict[str, str]]:
        """Protect both fenced code blocks AND inline code spans."""
        protected_blocks = {}

        # Protect fenced code blocks first (higher priority)
        content, fenced_blocks = self._protect_fenced_code_blocks(content)
        protected_blocks.update(fenced_blocks)

        # Protect inline code spans
        content, inline_blocks = self._protect_inline_code_spans(content)
        protected_blocks.update(inline_blocks)

        return content, protected_blocks

    def _protect_fenced_code_blocks(self, content: str) -> tuple[str, dict[str, str]]:
        """Protect fenced code blocks from normalization."""
        protected_blocks = {}

        # Pattern for both ``` and ~~~ code blocks
        fenced_pattern = re.compile(
            r"^(```|~~~).*?\n(.*?)\n\1\s*$", re.MULTILINE | re.DOTALL
        )

        def replace_fenced_block(match):
            placeholder = f"__FENCED_BLOCK_{len(protected_blocks)}__"
            protected_blocks[placeholder] = match.group(0)
            logger.debug(f"Protected fenced code block: {placeholder}")
            return placeholder

        protected_content = fenced_pattern.sub(replace_fenced_block, content)
        return protected_content, protected_blocks

    def _protect_inline_code_spans(self, content: str) -> tuple[str, dict[str, str]]:
        """Protect inline code spans from normalization."""
        protected_blocks = {}

        # Robust pattern for inline code (single to triple backticks)
        inline_pattern = re.compile(r"(`{1,3})([^`]*?)\1")

        def replace_inline_code(match):
            placeholder = f"__INLINE_CODE_{len(protected_blocks)}__"
            original_span = match.group(0)
            protected_blocks[placeholder] = original_span

            # Debug logging for directive-like content in code spans
            if "[" in original_span and "]" in original_span:
                logger.debug(
                    f"Protected inline code with directive-like content: {original_span}"
                )

            return placeholder

        protected_content = inline_pattern.sub(replace_inline_code, content)
        return protected_content, protected_blocks

    def _ensure_proper_block_separation(self, content: str) -> str:
        """
        Ensure content has proper spacing for predictable markdown parsing.

        This addresses the inconsistent splitting behavior by ensuring headings
        are properly separated from following content.
        """
        lines = content.split("\n")
        normalized_lines = []

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Add current line
            normalized_lines.append(line)

            # Add spacing after headings if next line isn't empty
            if (
                stripped.startswith("#")
                and i + 1 < len(lines)
                and lines[i + 1].strip()
                and not lines[i + 1].strip().startswith("#")
                and lines[i + 1].strip()  # Combined condition to avoid nested if
            ):
                normalized_lines.append("")
                logger.debug(f"Added separator after heading: {stripped[:50]}...")

        return "\n".join(normalized_lines)

    def _restore_all_code_constructs(
        self, content: str, protected_blocks: dict[str, str]
    ) -> str:
        """Restore all protected code constructs."""
        restored_content = content

        for placeholder, original_block in protected_blocks.items():
            if placeholder in restored_content:
                restored_content = restored_content.replace(placeholder, original_block)
                logger.debug(f"Restored code construct: {placeholder}")
            else:
                logger.warning(
                    f"Code construct placeholder not found during restoration: {placeholder}"
                )

        return restored_content

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
