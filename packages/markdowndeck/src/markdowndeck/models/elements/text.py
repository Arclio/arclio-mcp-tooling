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
    value: Any = True


@dataclass
class TextElement(Element):
    """Text element with simple splitting logic."""

    text: str = ""
    formatting: list[TextFormat] = field(default_factory=list)
    horizontal_alignment: AlignmentType = AlignmentType.LEFT
    vertical_alignment: VerticalAlignmentType = VerticalAlignmentType.TOP
    related_to_next: bool = False
    heading_level: int | None = None
    _line_metrics: list[dict] | None = None

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
        Split this TextElement using pre-calculated line metrics.
        REFACTORED: This method is now self-consistent.
        """
        logger.debug(
            f"--- TextElement Split initiated for element {self.object_id} ---"
        )
        logger.debug(f"Input available_height: {available_height:.2f}")
        logger.debug(f"Element's current size: {self.size}")

        if not self.text or not self._line_metrics or not self.size:
            logger.warning(
                "Split called but element state is incomplete (no text, metrics, or size). Cannot split."
            )
            return None, deepcopy(self)

        logger.debug(f"Line metrics: {self._line_metrics}")

        if self.size[1] <= available_height:
            logger.debug("Element fits entirely, no split needed.")
            return deepcopy(self), None

        full_content_height = sum(line["height"] for line in self._line_metrics)
        logger.debug(
            f"Calculated full_content_height from metrics: {full_content_height:.2f}"
        )

        vertical_padding = max(0, self.size[1] - full_content_height)
        logger.debug(
            f"Calculated vertical_padding (size.h - content.h): {vertical_padding:.2f}"
        )

        content_height_available = available_height - vertical_padding
        logger.debug(
            f"Calculated initial content_height_available (available_height - padding): {content_height_available:.2f}"
        )

        # HYPOTHESIS: If padding prevents any content from fitting, but we have *some* available height,
        # we must sacrifice padding to ensure progress.
        if content_height_available <= 0 and available_height > 0:
            logger.warning(
                f"Padding ({vertical_padding:.2f}) exceeds or meets available height ({available_height:.2f}). "
                f"Ignoring padding for the fitted part to attempt fitting minimal content."
            )
            content_height_available = available_height
            vertical_padding = 0  # The fitted part will have no padding.
            logger.debug(
                f"Revised content_height_available to {content_height_available:.2f} and vertical_padding to 0 for fitted part."
            )

        if content_height_available <= 0:
            logger.warning(
                "No space available for content. Cannot split. Moving entire element to overflow."
            )
            return None, deepcopy(self)

        height_so_far = 0.0
        split_line_index = -1
        for i, line_metric in enumerate(self._line_metrics):
            if height_so_far + line_metric["height"] <= content_height_available:
                height_so_far += line_metric["height"]
                split_line_index = i
            else:
                break

        logger.debug(
            f"Determined split_line_index: {split_line_index}. This many lines will fit."
        )

        if split_line_index == -1:
            logger.debug(
                "No single line could fit in the available content height. Moving entire element."
            )
            return None, deepcopy(self)

        split_char_index = self._line_metrics[split_line_index]["end"]
        while (
            split_char_index < len(self.text) and self.text[split_char_index].isspace()
        ):
            split_char_index += 1

        fitted_text = self.text[:split_char_index]
        overflowing_text = self.text[split_char_index:]

        if not overflowing_text.strip():
            logger.debug(
                "Split resulted in no overflowing text. Treating as a single fitting element."
            )
            return deepcopy(self), None

        fitted_part = deepcopy(self)
        fitted_part.text = fitted_text
        fitted_part._line_metrics = self._line_metrics[: split_line_index + 1]

        overflowing_part = deepcopy(self)
        overflowing_part.text = overflowing_text
        overflowing_part.position = None
        overflowing_part._line_metrics = None

        fitted_part.formatting = [
            fmt for fmt in self.formatting if fmt.start < len(fitted_text)
        ]
        for fmt in fitted_part.formatting:
            fmt.end = min(fmt.end, len(fitted_text))

        overflowing_formatting = []
        for fmt in self.formatting:
            if fmt.end > len(fitted_text):
                new_fmt = deepcopy(fmt)
                new_fmt.start = max(0, fmt.start - len(fitted_text))
                new_fmt.end = fmt.end - len(fitted_text)
                if new_fmt.start < new_fmt.end:
                    overflowing_formatting.append(new_fmt)
        overflowing_part.formatting = overflowing_formatting

        element_width = self.size[0]
        # The fitted part's height is the content it could fit plus whatever padding was accounted for.
        fitted_part.size = (element_width, height_so_far + vertical_padding)
        overflowing_part.size = None

        logger.debug(
            f"Split successful. Fitted part size: {fitted_part.size}. Overflowing text length: {len(overflowing_part.text)}"
        )
        return fitted_part, overflowing_part
