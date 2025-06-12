# File: packages/markdowndeck/src/markdowndeck/parser/content/element_factory.py
# Purpose: Creates slide element models.
# Key Changes:
# - REMOVED: Removed `_remove_directive_patterns` and `_strip_directives_from_code_content`. This logic is now centralized in `DirectiveParser` and used by formatters *before* calling the factory, simplifying the factory's responsibility. The factory now trusts it receives clean text.
# - REFACTORED: `extract_formatting_from_text` now expects pre-cleaned text.

import logging
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
    Factory for creating slide elements.

    This factory assumes it receives pre-cleaned text content where directives
    have already been processed and removed by the calling formatter.
    """

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
        Extracts formatting from a given text string.
        Assumes the input text has already been cleaned of directives.
        """
        if not text:
            return []

        try:
            tokens = md_parser.parse(text.strip())
            for token in tokens:
                if token.type == "inline":
                    return self._extract_formatting_from_inline_token(token)
        except Exception as e:
            logger.error(f"Failed to extract formatting from text '{text[:50]}': {e}")

        return []

    def _extract_formatting_from_inline_token(self, token: Token) -> list[TextFormat]:
        """
        Extract text formatting from an inline token's children.
        """
        if (
            token.type != "inline"
            or not hasattr(token, "children")
            or not token.children
        ):
            return []

        plain_text = ""
        formatting_data = []
        active_formats = []

        for child in token.children:
            child_type = getattr(child, "type", "")

            if child_type == "text":
                plain_text += child.content
            elif child_type == "code_inline":
                start_pos = len(plain_text)
                code_content = child.content
                plain_text += code_content
                if code_content.strip():
                    formatting_data.append(
                        TextFormat(
                            start=start_pos,
                            end=start_pos + len(code_content),
                            format_type=TextFormatType.CODE,
                        )
                    )
            elif child_type in ["softbreak", "hardbreak"]:
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
