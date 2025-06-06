"""Text-based element models."""

from copy import deepcopy
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

    def split(
        self, available_height: float
    ) -> tuple["TextElement | None", "TextElement | None"]:
        """
        Split this TextElement to fit within available_height.
        Splits at line boundaries to preserve line structure.
        """
        from markdowndeck.layout.metrics.text import calculate_text_element_height

        # Handle empty text case
        if not self.text.strip():
            return None, None

        if available_height <= 1:
            return None, deepcopy(self)

        element_width = self.size[0] if self.size and self.size[0] > 0 else 400.0
        full_height = calculate_text_element_height(self, element_width)

        if full_height <= available_height:
            return deepcopy(self), None

        # Split at line boundaries to preserve line count integrity
        lines = self.text.split("\n")
        if len(lines) <= 1:
            # Single line that doesn't fit - promote entire element
            return None, deepcopy(self)

        # Calculate height per line estimate
        height_per_line = full_height / len(lines)
        max_lines_that_fit = int(available_height / height_per_line)

        if max_lines_that_fit <= 0:
            # Nothing fits - promote entire element
            return None, deepcopy(self)

        if max_lines_that_fit >= len(lines):
            # Everything fits (shouldn't happen due to earlier check, but safety)
            return deepcopy(self), None

        # Split the lines
        fitted_lines = lines[:max_lines_that_fit]
        overflowing_lines = lines[max_lines_that_fit:]

        # Create fitted part
        fitted_part = deepcopy(self)
        fitted_part.text = "\n".join(fitted_lines)

        # Create overflowing part
        overflowing_part = deepcopy(self)
        overflowing_part.text = "\n".join(overflowing_lines)

        # Calculate split point for formatting
        split_index = len(fitted_part.text)
        if fitted_part.text:
            split_index += 1  # Account for the newline we'll be skipping

        # Partition formatting
        fitted_part.formatting = [
            fmt for fmt in self.formatting if fmt.start < split_index
        ]
        for fmt in fitted_part.formatting:
            fmt.end = min(fmt.end, split_index)

        overflowing_formatting = []
        for fmt in self.formatting:
            if fmt.end > split_index:
                new_fmt = deepcopy(fmt)
                new_fmt.start = max(0, fmt.start - split_index)
                new_fmt.end = fmt.end - split_index
                overflowing_formatting.append(new_fmt)
        overflowing_part.formatting = overflowing_formatting

        # Recalculate sizes
        fitted_part.size = (
            element_width,
            calculate_text_element_height(fitted_part, element_width),
        )
        overflowing_part.size = (
            element_width,
            calculate_text_element_height(overflowing_part, element_width),
        )

        return fitted_part, overflowing_part
