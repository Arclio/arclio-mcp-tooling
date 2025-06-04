"""Factory for creating slide elements with enhanced directive handling."""

import logging
import re
from typing import Any

from markdown_it import MarkdownIt
from markdown_it.token import Token

from markdowndeck.models import (
    AlignmentType,
    CodeElement,
    ElementType,
    ImageElement,
    ListElement,
    ListItem,
    TableElement,
    TextElement,
    TextFormat,
    TextFormatType,
    VerticalAlignmentType,
)

logger = logging.getLogger(__name__)


class ElementFactory:
    """
    Factory for creating slide elements with enhanced directive support.

    IMPROVEMENTS:
    - Better directive pattern detection
    - Enhanced formatting extraction
    - Robust text cleaning methods
    """

    def __init__(self):
        """Initialize the ElementFactory with enhanced directive patterns."""
        # Enhanced directive pattern for better detection
        self.directive_pattern = re.compile(r"^\s*((?:\s*\[[^\[\]]+=[^\[\]]*\]\s*)+)")

    def create_title_element(
        self,
        title: str,
        formatting: list[TextFormat] = None,
        directives: dict[str, Any] = None,
    ) -> TextElement:
        """Create a title element with directive support."""
        alignment = AlignmentType.CENTER

        if directives and "align" in directives:
            alignment_value = directives["align"].lower()
            if alignment_value in ["left", "center", "right", "justify"]:
                alignment = AlignmentType(alignment_value)

        return TextElement(
            element_type=ElementType.TITLE,
            text=title,
            formatting=formatting or [],
            horizontal_alignment=alignment,
            vertical_alignment=VerticalAlignmentType.TOP,
            directives=directives or {},
        )

    def create_subtitle_element(
        self,
        text: str,
        formatting: list[TextFormat] = None,
        alignment: AlignmentType = AlignmentType.CENTER,
        directives: dict[str, Any] = None,
    ) -> TextElement:
        """Create a subtitle element."""
        return TextElement(
            element_type=ElementType.SUBTITLE,
            text=text,
            formatting=formatting or [],
            horizontal_alignment=alignment,
            vertical_alignment=VerticalAlignmentType.TOP,
            directives=directives or {},
        )

    def create_text_element(
        self,
        text: str,
        formatting: list[TextFormat] = None,
        alignment: AlignmentType = AlignmentType.LEFT,
        directives: dict[str, Any] = None,
    ) -> TextElement:
        """Create a text element."""
        return TextElement(
            element_type=ElementType.TEXT,
            text=text,
            formatting=formatting or [],
            horizontal_alignment=alignment,
            vertical_alignment=VerticalAlignmentType.TOP,
            directives=directives or {},
        )

    def create_quote_element(
        self,
        text: str,
        formatting: list[TextFormat] = None,
        alignment: AlignmentType = AlignmentType.LEFT,
        directives: dict[str, Any] = None,
    ) -> TextElement:
        """Create a quote element."""
        return TextElement(
            element_type=ElementType.QUOTE,
            text=text,
            formatting=formatting or [],
            horizontal_alignment=alignment,
            vertical_alignment=VerticalAlignmentType.TOP,
            directives=directives or {},
        )

    def create_footer_element(
        self,
        text: str,
        formatting: list[TextFormat] = None,
        alignment: AlignmentType = AlignmentType.LEFT,
    ) -> TextElement:
        """Create a footer element."""
        return TextElement(
            element_type=ElementType.FOOTER,
            text=text,
            formatting=formatting or [],
            horizontal_alignment=alignment,
            vertical_alignment=VerticalAlignmentType.BOTTOM,
        )

    def create_list_element(
        self,
        items: list[ListItem],
        ordered: bool = False,
        directives: dict[str, Any] = None,
    ) -> ListElement:
        """Create a list element."""
        element_type = ElementType.ORDERED_LIST if ordered else ElementType.BULLET_LIST
        return ListElement(
            element_type=element_type,
            items=items,
            directives=directives or {},
        )

    def create_image_element(
        self, url: str, alt_text: str = "", directives: dict[str, Any] = None
    ) -> ImageElement:
        """Create an image element."""
        return ImageElement(
            element_type=ElementType.IMAGE,
            url=url,
            alt_text=alt_text,
            directives=directives or {},
        )

    def create_table_element(
        self,
        headers: list[str],
        rows: list[list[str]],
        directives: dict[str, Any] = None,
    ) -> TableElement:
        """Create a table element."""
        return TableElement(
            element_type=ElementType.TABLE,
            headers=headers,
            rows=rows,
            directives=directives or {},
        )

    def create_code_element(
        self, code: str, language: str = "text", directives: dict[str, Any] = None
    ) -> CodeElement:
        """Create a code element."""
        return CodeElement(
            element_type=ElementType.CODE,
            code=code,
            language=language,
            directives=directives or {},
        )

    def extract_formatting_from_text(
        self, text: str, md_parser: MarkdownIt
    ) -> list[TextFormat]:
        """
        Extract formatting from text with enhanced directive handling.

        CRITICAL FIX: Returns formatting relative to plain text (without markdown syntax).
        """
        if not text:
            return []

        try:
            # Clean text of directives before processing
            cleaned_text = self._remove_directive_patterns(text)

            # Parse the cleaned text to get proper tokens
            tokens = md_parser.parse(cleaned_text.strip())
            for token in tokens:
                if token.type == "inline":
                    # Return formatting relative to plain text, not cleaned text
                    return self._extract_formatting_from_inline_token(token)
        except Exception as e:
            logger.error(f"Failed to extract formatting from text '{text[:50]}': {e}")

        return []

    def _remove_directive_patterns(self, text: str) -> str:
        """
        Remove directive patterns from text for cleaner formatting extraction.

        ENHANCEMENT: Better directive detection and removal.
        """
        # Remove directive patterns from the beginning of text
        return re.sub(r"^\s*(?:\[[^\[\]]+=[^\[\]]*\]\s*)+", "", text)

    def _strip_directives_from_code_content(self, code_content: str) -> str:
        """
        Strip directive patterns from code content.

        ENHANCEMENT: Improved directive detection in code spans.
        """
        if not code_content:
            return code_content

        match = self.directive_pattern.match(code_content)
        if match:
            directive_text = match.group(1)
            remaining_content = code_content[len(directive_text) :].strip()

            logger.debug(
                f"Stripped directives from code: '{directive_text}' -> '{remaining_content}'"
            )
            return remaining_content

        return code_content

    def _extract_formatting_from_inline_token(self, token: Token) -> list[TextFormat]:
        """
        Extract text formatting from inline token with enhanced processing.

        CRITICAL FIX: Always returns formatting for plain text, preserves code content as-is.
        """
        if (
            token.type != "inline"
            or not hasattr(token, "children")
            or not token.children
        ):
            return []

        # Build plain text and track formatting in a single pass
        plain_text = ""
        formatting_data = []
        active_formats = []

        for child in token.children:
            child_type = getattr(child, "type", "")

            if child_type == "text":
                plain_text += child.content

            elif child_type == "code_inline":
                # CRITICAL FIX: Preserve code content exactly as-is (no directive stripping)
                start_pos = len(plain_text)
                plain_text += child.content

                # Create code formatting for the exact content
                if child.content.strip():
                    formatting_data.append(
                        TextFormat(
                            start=start_pos,
                            end=start_pos + len(child.content),
                            format_type=TextFormatType.CODE,
                            value=True,
                        )
                    )

            elif child_type == "softbreak" or child_type == "hardbreak":
                plain_text += "\n"

            elif child_type == "image":
                alt_text = child.attrs.get("alt", "") if hasattr(child, "attrs") else ""
                plain_text += alt_text

            elif child_type.endswith("_open"):
                base_type = child_type.split("_")[0]
                format_type_enum = None
                value: Any = True

                if base_type == "strong":
                    format_type_enum = TextFormatType.BOLD
                elif base_type == "em":
                    format_type_enum = TextFormatType.ITALIC
                elif base_type == "s":
                    format_type_enum = TextFormatType.STRIKETHROUGH
                elif base_type == "link":
                    format_type_enum = TextFormatType.LINK
                    value = (
                        child.attrs.get("href", "") if hasattr(child, "attrs") else ""
                    )

                if format_type_enum:
                    # Record the current position where the formatted content starts
                    active_formats.append((format_type_enum, len(plain_text), value))

            elif child_type.endswith("_close"):
                base_type = child_type.split("_")[0]
                expected_format_type = None

                if base_type == "strong":
                    expected_format_type = TextFormatType.BOLD
                elif base_type == "em":
                    expected_format_type = TextFormatType.ITALIC
                elif base_type == "s":
                    expected_format_type = TextFormatType.STRIKETHROUGH
                elif base_type == "link":
                    expected_format_type = TextFormatType.LINK

                # Find and close matching format
                for i in range(len(active_formats) - 1, -1, -1):
                    fmt_type, start_pos, fmt_value = active_formats[i]
                    if fmt_type == expected_format_type:
                        if start_pos < len(plain_text):
                            formatting_data.append(
                                TextFormat(
                                    start=start_pos,
                                    end=len(plain_text),
                                    format_type=fmt_type,
                                    value=fmt_value,
                                )
                            )
                        active_formats.pop(i)
                        break

        return formatting_data
