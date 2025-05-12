"""Text-based element models."""

from dataclasses import dataclass, field
from typing import Any

from markdowndeck.models.constants import (
    AlignmentType,
    TextFormatType,
    VerticalAlignmentType,
)
from markdowndeck.models.elements.base import Element


@dataclass
class TextFormat:
    """Text formatting information."""

    start: int
    end: int
    format_type: TextFormatType
    value: Any = True  # Boolean for bold/italic or values for colors/links


@dataclass
class TextElement(Element):
    """Text element (title, subtitle, paragraph, etc.)."""

    text: str = ""
    formatting: list[TextFormat] = field(default_factory=list)
    horizontal_alignment: AlignmentType = AlignmentType.LEFT
    vertical_alignment: VerticalAlignmentType = VerticalAlignmentType.TOP

    def has_formatting(self) -> bool:
        """Check if this element has any formatting applied."""
        return bool(self.formatting)

    def add_formatting(
        self, format_type: TextFormatType, start: int, end: int, value: Any = None
    ) -> None:
        """
        Add formatting to a portion of the text.

        Args:
            format_type: Type of formatting
            start: Start index of the formatting
            end: End index of the formatting
            value: Optional value for the formatting (e.g., URL for links)
        """
        if start >= end or start < 0 or end > len(self.text):
            return

        if value is None:
            value = True

        self.formatting.append(
            TextFormat(start=start, end=end, format_type=format_type, value=value)
        )

    def count_newlines(self) -> int:
        """Count the number of explicit newlines in the text."""
        return self.text.count("\n")
