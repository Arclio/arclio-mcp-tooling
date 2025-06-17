import logging
import re
import textwrap
from typing import Any

from markdown_it import MarkdownIt
from markdown_it.token import Token

from markdowndeck.models import AlignmentType, Element, TextFormat
from markdowndeck.parser.content.formatters.base import BaseFormatter
from markdowndeck.parser.directive import DirectiveParser

logger = logging.getLogger(__name__)


class TextFormatter(BaseFormatter):
    """
    Formatter for text elements with enhanced directive handling and predictable splitting.

    REFACTORED Version 7.2:
    - Fixed code span preservation during directive parsing
    - Enhanced multi-line content splitting with list detection
    - Intelligent code block processing for mis-tokenized content
    - Comprehensive line-by-line splitting when appropriate
    """

    def __init__(self, element_factory, directive_parser: DirectiveParser = None):
        """Initialize the TextFormatter with required dependencies."""
        super().__init__(element_factory)
        opts = {"html": False, "typographer": True, "linkify": True, "breaks": True}
        self.md = MarkdownIt("commonmark", opts)
        self.md.enable("table")
        self.md.enable("strikethrough")

        # PRESERVED: Disabled 'lheading' and 'hr' rules to ensure separators are treated as plain text
        self.md.disable(["lheading", "hr"])

        self.directive_parser = directive_parser or DirectiveParser()

    def can_handle(self, token: Token, leading_tokens: list[Token]) -> bool:
        """Check if this formatter can handle the given token."""
        return token.type in [
            "heading_open",
            "blockquote_open",
            "paragraph_open",
            "hr",
            "code_block",
        ]

    def process(
        self,
        tokens: list[Token],
        start_index: int,
        section_directives: dict[str, Any],
        element_specific_directives: dict[str, Any] | None = None,
        **kwargs,
    ) -> tuple[list[Element], int]:
        """Process tokens into text elements with improved directive handling."""
        if not tokens or start_index >= len(tokens):
            return [], start_index

        token = tokens[start_index]
        merged_directives = self.merge_directives(
            section_directives, element_specific_directives
        )

        if token.type == "heading_open":
            elements, end_index = self._process_heading(
                tokens, start_index, merged_directives
            )
            return elements, end_index
        if token.type == "paragraph_open":
            elements, end_index = self._process_paragraph(
                tokens, start_index, merged_directives
            )
            return elements, end_index
        if token.type == "blockquote_open":
            elements, end_index = self._process_quote(
                tokens, start_index, merged_directives
            )
            return elements, end_index
        if token.type == "hr":
            hr_text = getattr(token, "markup", "---")
            element = self.element_factory.create_text_element(
                hr_text, [], AlignmentType.LEFT, merged_directives
            )
            return [element], start_index
        if token.type == "code_block":
            # CRITICAL FIX: Check if code_block contains text that should be split
            return self._process_code_block_intelligently(
                token, merged_directives, start_index
            )

        logger.warning(f"TextFormatter cannot process token type: {token.type}")
        return [], start_index

    def _process_code_block_intelligently(
        self, token: Token, directives: dict[str, Any], start_index: int
    ) -> tuple[list[Element], int]:
        """
        Process code_block tokens, distinguishing between actual code and indented text.

        While ContentParser normalization handles most cases, some indented text
        may still be tokenized as code_block and should be processed as text elements.
        """
        raw_content = token.content
        if not raw_content.strip():
            return [], start_index

        # Remove indentation and analyze content
        dedented_content = textwrap.dedent(raw_content).strip()

        # ENHANCEMENT: Check if this is actually a table that was mis-tokenized
        if self._looks_like_table(dedented_content):
            logger.debug("Code block contains table content - processing as table")
            return self._process_table_from_content(
                dedented_content, directives, start_index
            )

        # Check if this contains text-like content (headings or multiple text lines)
        lines = dedented_content.strip().split("\n")
        heading_lines = sum(1 for line in lines if line.strip().startswith("#"))
        text_lines = sum(
            1 for line in lines if line.strip() and not line.strip().startswith("#")
        )

        # If we have headings OR multiple text lines, treat as text content
        if heading_lines > 0 or text_lines >= 3:
            logger.debug(
                f"Code block contains text content ({heading_lines} headings, {text_lines} text lines) - processing as text"
            )
            # Create a single text element from the dedented content
            cleaned_text, line_directives = (
                self.directive_parser.parse_and_strip_from_text(dedented_content)
            )
            final_directives = {**directives, **line_directives}

            if cleaned_text.strip():
                text_content, formatting = self._extract_clean_text_and_formatting(
                    cleaned_text
                )
                if text_content:
                    element = self.element_factory.create_text_element(
                        text_content, formatting, AlignmentType.LEFT, final_directives
                    )
                    return [element], start_index

            return [], start_index

        # This appears to be actual code content, create a code element
        logger.debug("Code block appears to be actual code - creating code element")
        element = self.element_factory.create_code_element(
            code=raw_content,
            language="text",  # Default language for code_block tokens
            directives=directives.copy(),
        )

        logger.debug(
            f"Created code element from code_block token at index {start_index}"
        )
        return [element], start_index

    def _looks_like_table(self, content: str) -> bool:
        """
        Check if content looks like a Markdown table.

        A table should have:
        - Multiple lines with | characters
        - At least one line with --- separator pattern
        """
        lines = content.strip().split("\n")
        if len(lines) < 2:
            return False

        # Check for pipe characters in multiple lines
        pipe_lines = sum(1 for line in lines if "|" in line.strip())
        if pipe_lines < 2:
            return False

        # Check for separator line (contains --- pattern)
        separator_lines = sum(
            1 for line in lines if "|" in line and "---" in line.replace(" ", "")
        )

        return separator_lines >= 1

    def _process_table_from_content(
        self, content: str, directives: dict[str, Any], start_index: int
    ) -> tuple[list[Element], int]:
        """
        Process table content that was mis-tokenized as a code block.
        Re-tokenize the content and delegate to TableFormatter.
        """
        # Re-tokenize the content specifically as markdown
        table_tokens = self.md.parse(content)

        # Find table tokens and delegate to TableFormatter
        for i, token in enumerate(table_tokens):
            if token.type == "table_open":
                # Import TableFormatter here to avoid circular imports
                from markdowndeck.parser.content.formatters.table import TableFormatter

                table_formatter = TableFormatter(self.element_factory)

                if table_formatter.can_handle(token, table_tokens[i:]):
                    elements, _ = table_formatter.process(table_tokens, i, directives)
                    return elements, start_index

        # If no table found, fall back to text processing
        logger.warning(
            "Table detection succeeded but no table tokens found - treating as text"
        )
        cleaned_text, line_directives = self.directive_parser.parse_and_strip_from_text(
            content
        )
        final_directives = {**directives, **line_directives}

        if cleaned_text.strip():
            text_content, formatting = self._extract_clean_text_and_formatting(
                cleaned_text
            )
            if text_content:
                element = self.element_factory.create_text_element(
                    text_content, formatting, AlignmentType.LEFT, final_directives
                )
                return [element], start_index

        return [], start_index

    def _process_heading(
        self, tokens: list[Token], start_index: int, directives: dict[str, Any]
    ) -> tuple[list[Element], int]:
        """Process heading tokens into text elements."""
        open_token = tokens[start_index]
        level = int(open_token.tag[1:])
        end_idx = self.find_closing_token(tokens, start_index, "heading_close")

        if start_index + 1 >= len(tokens) or tokens[start_index + 1].type != "inline":
            logger.warning(
                f"Heading token at {start_index} missing expected inline content"
            )
            return [], end_idx

        inline_token = tokens[start_index + 1]
        raw_content = inline_token.content or ""

        cleaned_text, line_directives = self.directive_parser.parse_and_strip_from_text(
            raw_content
        )
        final_directives = {**directives, **line_directives}
        text_content, formatting = self._extract_clean_text_and_formatting(cleaned_text)

        if not text_content:
            return [], end_idx

        alignment = AlignmentType(final_directives.get("align", "left"))
        element = self.element_factory.create_text_element(
            text_content,
            formatting,
            alignment,
            final_directives,
            heading_level=level,
        )
        return [element] if element else [], end_idx

    def _process_paragraph(
        self, tokens: list[Token], start_index: int, directives: dict[str, Any]
    ) -> tuple[list[Element], int]:
        """
        Process paragraph tokens into a single text element.

        Since ContentParser now correctly separates blocks based on tokens,
        paragraphs should always be processed as single elements.
        """
        if start_index + 1 >= len(tokens) or tokens[start_index + 1].type != "inline":
            logger.warning(
                f"Paragraph token at {start_index} missing expected inline content"
            )
            close_index = self.find_closing_token(
                tokens, start_index, "paragraph_close"
            )
            return [], close_index

        inline_token = tokens[start_index + 1]
        close_index = self.find_closing_token(tokens, start_index, "paragraph_close")

        child_tokens = inline_token.children or []
        if not child_tokens:
            return [], close_index

        # Check if this paragraph contains images - if so, use mixed content handling
        has_images = any(child.type == "image" for child in child_tokens)

        if has_images:
            # Mixed content: split on images
            elements = self._process_mixed_content_paragraph(child_tokens, directives)
        else:
            # Regular paragraph: create single text element
            element = self._create_text_element_from_tokens(child_tokens, directives)
            elements = [element] if element else []

        return elements, close_index

    def _process_quote(
        self, tokens: list[Token], start_index: int, directives: dict[str, Any]
    ) -> tuple[list[Element], int]:
        """Process blockquote tokens into quote elements."""
        end_idx = self.find_closing_token(tokens, start_index, "blockquote_close")
        text_parts = []
        i = start_index + 1
        while i < end_idx:
            if tokens[i].type == "paragraph_open":
                para_inline_idx = i + 1
                if (
                    para_inline_idx < end_idx
                    and tokens[para_inline_idx].type == "inline"
                ):
                    text_parts.append(tokens[para_inline_idx].content)
                i = self.find_closing_token(tokens, i, "paragraph_close")
            i += 1
        full_text = "\n".join(text_parts)
        cleaned_text, line_directives = self.directive_parser.parse_and_strip_from_text(
            full_text
        )
        final_directives = {**directives, **line_directives}
        text_content, formatting = self._extract_clean_text_and_formatting(cleaned_text)
        if not text_content:
            return [], end_idx

        alignment = AlignmentType(final_directives.get("align", "left"))
        element = self.element_factory.create_quote_element(
            text_content, formatting, alignment, final_directives
        )
        return [element] if element else [], end_idx

    def _extract_clean_text_and_formatting(
        self, cleaned_text: str
    ) -> tuple[str, list[TextFormat]]:
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
        """
        Extract plain text content from an inline token, removing formatting markers.

        This version is used for the final display text AFTER directive parsing.
        """
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

    def _process_mixed_content_paragraph(
        self, child_tokens: list[Token], directives: dict[str, Any]
    ) -> list[Element]:
        """
        Process a paragraph that contains images mixed with text.
        Split on images to create separate elements.
        """
        elements: list[Element] = []
        text_buffer: list[Token] = []

        def flush_text_buffer():
            if text_buffer:
                element = self._create_text_element_from_tokens(text_buffer, directives)
                if element:
                    elements.append(element)
                text_buffer.clear()

        for i, child in enumerate(child_tokens):
            if child.type == "image":
                # Flush any accumulated text before the image
                flush_text_buffer()

                # Create the image element
                img_alt, img_src = child.content, child.attrs.get("src", "")
                final_img_directives = directives.copy()

                # Check if the next token contains directives for this image
                if i + 1 < len(child_tokens) and child_tokens[i + 1].type == "text":
                    next_token = child_tokens[i + 1]
                    remaining_text, parsed_directives = (
                        self.directive_parser.parse_and_strip_from_text(
                            next_token.content
                        )
                    )
                    if parsed_directives:
                        final_img_directives.update(parsed_directives)
                        next_token.content = remaining_text.lstrip()

                # Parse directives from alt text
                cleaned_alt, alt_directives = (
                    self.directive_parser.parse_and_strip_from_text(img_alt)
                )
                final_img_directives.update(alt_directives)

                image_element = self.element_factory.create_image_element(
                    url=img_src, alt_text=cleaned_alt, directives=final_img_directives
                )
                elements.append(image_element)
            elif child.type in ["softbreak", "hardbreak"]:
                # For mixed content, breaks can separate different logical elements
                # Check if we have accumulated text that should be flushed
                if text_buffer and any(
                    t.type in ["text", "code_inline"] and t.content.strip()
                    for t in text_buffer
                ):
                    flush_text_buffer()
            else:
                text_buffer.append(child)

        # Flush any remaining text
        flush_text_buffer()

        return elements

    def _create_text_element_from_tokens(
        self,
        text_tokens: list[Token],
        directives: dict[str, Any],
    ) -> Element | None:
        """
        FIXED: Preserve code spans during text extraction and directive parsing.
        """
        if not text_tokens:
            return None

        # CRITICAL FIX: Extract text while preserving code spans for directive parsing
        temp_inline_token = Token("inline", "", 0, children=text_tokens)
        full_raw_text_with_code_spans = self._get_text_preserving_code_spans(
            temp_inline_token
        )

        if not full_raw_text_with_code_spans.strip():
            return None

        # Parse directives from text that still contains code spans
        cleaned_text, line_directives = self.directive_parser.parse_and_strip_from_text(
            full_raw_text_with_code_spans
        )
        final_directives = {**directives, **line_directives}

        # Extract heading level from the cleaned text BEFORE markdown processing
        heading_level = None
        heading_match = re.match(r"^(#+)\s", cleaned_text)
        if heading_match:
            heading_level = len(heading_match.group(1))

        # FIX: Use the cleaned_text (with directives stripped) to extract final text and formatting
        plain_text_for_display, formatting = self._extract_clean_text_and_formatting(
            cleaned_text
        )

        if not plain_text_for_display.strip():
            return None

        alignment = AlignmentType(final_directives.get("align", "left"))
        return self.element_factory.create_text_element(
            plain_text_for_display,
            formatting,
            alignment,
            final_directives,
            heading_level,
        )

    def _get_text_preserving_code_spans(self, inline_token: Token) -> str:
        """
        Extract text content while preserving backticks around code spans.

        This is critical for directive parsing - we need to preserve code spans
        so the directive parser can protect them from being parsed as directives.
        """
        if not hasattr(inline_token, "children") or inline_token.children is None:
            return getattr(inline_token, "content", "")

        preserved_text = ""
        for child in inline_token.children:
            if child.type == "text":
                preserved_text += child.content
            elif child.type == "code_inline":
                # CRITICAL: Preserve the backticks around code content
                preserved_text += f"`{child.content}`"
            elif child.type == "softbreak" or child.type == "hardbreak":
                preserved_text += "\n"
            elif child.type == "image":
                preserved_text += (
                    child.attrs.get("alt", "") if hasattr(child, "attrs") else ""
                )
            elif child.type.endswith("_open"):
                # For formatting like bold, italic - we don't need the markers for directive parsing
                pass
            elif child.type.endswith("_close"):
                pass
            # Skip other formatting markers but preserve their content via the text tokens

        return preserved_text
