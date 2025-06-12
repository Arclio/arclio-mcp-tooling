import logging
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from markdowndeck.models.constants import (
    AlignmentType,
    TextFormatType,
    VerticalAlignmentType,
)
from markdowndeck.models.elements.base import Element

logger = logging.getLogger(__name__)


@dataclass
class TextFormat:
    """Text formatting information."""

    start: int
    end: int
    format_type: TextFormatType
    value: Any = True  # Boolean for bold/italic or values for colors/links


@dataclass
class TextElement(Element):
    """Text element with simple splitting logic."""

    text: str = ""
    formatting: list[TextFormat] = field(default_factory=list)
    horizontal_alignment: AlignmentType = AlignmentType.LEFT
    vertical_alignment: VerticalAlignmentType = VerticalAlignmentType.TOP
    related_to_next: bool = False

    def has_formatting(self) -> bool:
        """Check if this element has any formatting applied."""
        return bool(self.formatting)

    def add_formatting(
        self, format_type: TextFormatType, start: int, end: int, value: Any = None
    ) -> None:
        """Add formatting to a portion of the text."""
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
        Split this TextElement with word wrapping support.

        This method now handles both explicit line breaks (\n) and word wrapping
        for long single lines, preventing infinite overflow loops.

        Rule: Must fit at least 2 lines to split.
        If minimum not met, promote entire text to next slide.
        If minimum met, split off what fits.

        Args:
            available_height: The vertical space available for this element

        Returns:
            Tuple of (fitted_part, overflowing_part). Either can be None.
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

        # FIXED: Get all display lines, including wrapped lines for long single lines
        all_lines = self._get_all_display_lines(element_width)
        total_lines = len(all_lines)

        logger.debug(
            f"Text wrapping analysis: element_width={element_width}, total_lines={total_lines}"
        )

        if total_lines <= 1:
            logger.debug("Single line text doesn't fit - treating as atomic")
            return None, deepcopy(self)

        # Calculate height per line estimate
        height_per_line = full_height / total_lines
        max_lines_that_fit = int(available_height / height_per_line)

        if max_lines_that_fit <= 0:
            logger.debug("No text lines fit in available space")
            return None, deepcopy(self)

        if max_lines_that_fit >= total_lines:
            return deepcopy(self), None

        # MINIMUM REQUIREMENTS CHECK: Must fit at least 2 lines
        minimum_lines_required = 2
        fitted_line_count = max_lines_that_fit

        if fitted_line_count < minimum_lines_required:
            logger.info(
                f"Text split rejected: Only {fitted_line_count} lines fit, need minimum {minimum_lines_required}"
            )
            return None, deepcopy(self)

        # Minimum met - proceed with split
        fitted_lines = all_lines[:max_lines_that_fit]
        overflowing_lines = all_lines[max_lines_that_fit:]

        # Create fitted part
        fitted_part = deepcopy(self)
        fitted_part.text = "\n".join(fitted_lines)

        # Create overflowing part
        overflowing_part = deepcopy(self)
        overflowing_part.text = "\n".join(overflowing_lines)
        overflowing_part.position = None  # Reset position for continuation slide

        # Calculate split point for formatting (approximate)
        split_index = len(fitted_part.text)
        if fitted_part.text:
            split_index += 1  # Account for the newline we'll be skipping

        # Partition formatting (simplified for wrapped text)
        fitted_part.formatting = [
            fmt for fmt in self.formatting if fmt.start < split_index
        ]
        for fmt in fitted_part.formatting:
            fmt.end = min(fmt.end, len(fitted_part.text))

        overflowing_formatting = []
        for fmt in self.formatting:
            if fmt.end > split_index:
                new_fmt = deepcopy(fmt)
                new_fmt.start = max(0, fmt.start - split_index)
                new_fmt.end = fmt.end - split_index
                # Adjust for potential text length changes due to wrapping
                new_fmt.end = min(new_fmt.end, len(overflowing_part.text))
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

        logger.info(
            f"Text split successful: {fitted_line_count} lines fitted, {len(overflowing_lines)} lines overflowing"
        )
        return fitted_part, overflowing_part

    def _get_all_display_lines(self, element_width: float) -> list[str]:
        """
        Get all display lines including wrapped lines for long text.

        This method handles both explicit line breaks (\n) and word wrapping
        for long single lines that exceed the available width.

        Args:
            element_width: The available width for text display

        Returns:
            List of all display lines that would be rendered
        """
        from markdowndeck.layout.constants import P_FONT_SIZE
        from markdowndeck.layout.metrics.font_metrics import (
            _get_font,
            _wrap_text_to_lines,
        )

        # Get font for wrapping calculations
        font_size = P_FONT_SIZE  # Default font size, could be customized later
        font = _get_font(font_size)

        # Effective width for text (account for padding)
        effective_width = max(50.0, element_width - 40.0)  # Conservative padding

        # Split by explicit newlines first
        paragraphs = self.text.split("\n")
        all_lines = []

        for paragraph in paragraphs:
            if not paragraph.strip():
                # Empty line
                all_lines.append("")
            else:
                # Wrap this paragraph based on available width
                wrapped_lines = _wrap_text_to_lines(paragraph, font, effective_width)
                all_lines.extend(wrapped_lines)

        return all_lines if all_lines else [""]
