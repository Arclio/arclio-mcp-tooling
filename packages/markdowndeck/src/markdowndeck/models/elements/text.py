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

        Args:
            available_height: The vertical space available for this element

        Returns:
            Tuple of (fitted_part, overflowing_part). Either can be None.
            fitted_part: Contains text that fits within available_height
            overflowing_part: Contains text that doesn't fit
        """
        if not self.text or not self.text.strip():
            return None, None

        # Calculate current element width to determine line heights
        element_width = self.size[0] if self.size else 400.0  # fallback width

        # Split text into lines
        lines = self.text.split("\n")

        if not lines:
            return None, None

        # Find how many lines fit within available height
        fitted_lines = []
        current_height = 0.0

        for _i, line in enumerate(lines):
            # Create temporary element with current lines to measure height
            temp_text = "\n".join(fitted_lines + [line])
            temp_element = deepcopy(self)
            temp_element.text = temp_text

            # Calculate height this would require (local import to avoid circular dependency)
            from markdowndeck.layout.metrics import calculate_element_height

            required_height = calculate_element_height(temp_element, element_width)

            if required_height <= available_height:
                fitted_lines.append(line)
                current_height = required_height
            else:
                # This line doesn't fit
                break

        # Determine split results
        if not fitted_lines:
            # Nothing fits
            return None, deepcopy(self)

        if len(fitted_lines) == len(lines):
            # Everything fits
            return deepcopy(self), None

        # Create fitted part
        fitted_text = "\n".join(fitted_lines)
        fitted_part = deepcopy(self)
        fitted_part.text = fitted_text
        fitted_part.size = (element_width, current_height)

        # Adjust formatting for fitted part
        fitted_formatting = []
        fitted_text_len = len(fitted_text)

        for fmt in self.formatting:
            if fmt.end <= fitted_text_len:
                # Formatting entirely within fitted part
                fitted_formatting.append(deepcopy(fmt))
            elif fmt.start < fitted_text_len:
                # Formatting partially within fitted part - truncate
                truncated_fmt = deepcopy(fmt)
                truncated_fmt.end = fitted_text_len
                fitted_formatting.append(truncated_fmt)

        fitted_part.formatting = fitted_formatting

        # Create overflowing part
        overflowing_lines = lines[len(fitted_lines) :]
        overflowing_text = "\n".join(overflowing_lines)
        overflowing_part = deepcopy(self)
        overflowing_part.text = overflowing_text

        # Adjust formatting for overflowing part
        overflowing_formatting = []
        text_offset = fitted_text_len + 1  # +1 for the newline

        for fmt in self.formatting:
            if fmt.start >= text_offset:
                # Formatting entirely within overflowing part
                adjusted_fmt = deepcopy(fmt)
                adjusted_fmt.start -= text_offset
                adjusted_fmt.end -= text_offset
                overflowing_formatting.append(adjusted_fmt)
            elif fmt.end > text_offset:
                # Formatting partially within overflowing part
                adjusted_fmt = deepcopy(fmt)
                adjusted_fmt.start = max(0, fmt.start - text_offset)
                adjusted_fmt.end = fmt.end - text_offset
                overflowing_formatting.append(adjusted_fmt)

        overflowing_part.formatting = overflowing_formatting

        return fitted_part, overflowing_part
