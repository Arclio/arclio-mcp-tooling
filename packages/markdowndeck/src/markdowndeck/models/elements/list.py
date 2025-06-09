"""List element with simple, minimum-requirement splitting logic."""

import logging
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from markdowndeck.models import ElementType
from markdowndeck.models.elements.base import Element
from markdowndeck.models.elements.text import TextElement, TextFormat
from markdowndeck.overflow.constants import CONTINUED_ELEMENT_TITLE_SUFFIX

logger = logging.getLogger(__name__)


@dataclass
class ListItem:
    """Represents an item in a list with optional nested items."""

    text: str
    level: int = 0
    formatting: list[TextFormat] = field(default_factory=list)
    children: list["ListItem"] = field(default_factory=list)
    directives: dict[str, Any] = field(default_factory=dict)

    def add_child(self, child: "ListItem") -> None:
        """Add a child item to this list item."""
        child.level = self.level + 1
        self.children.append(child)

    def count_all_items(self) -> int:
        """Count this item and all child items recursively."""
        count = 1  # Count self
        for child in self.children:
            count += child.count_all_items()
        return count

    def max_depth(self) -> int:
        """Calculate the maximum depth of nesting from this item."""
        if not self.children:
            return 0
        return 1 + max(child.max_depth() for child in self.children)


@dataclass
class ListElement(Element):
    """List element with simple splitting logic."""

    items: list[ListItem] = field(default_factory=list)
    related_to_prev: bool = False

    def count_total_items(self) -> int:
        """Count the total number of items in the list, including nested items."""
        return sum(item.count_all_items() for item in self.items)

    def max_nesting_level(self) -> int:
        """Get the maximum nesting level in the list."""
        if not self.items:
            return 0
        return max(item.max_depth() for item in self.items)

    def split(
        self, available_height: float
    ) -> tuple["ListElement | None", "ListElement | None"]:
        """
        Split this ListElement using simple minimum requirements.

        Rule: Must fit at least 2 items to split.
        If minimum not met, promote entire list to next slide.
        If minimum met, split off what fits.

        Args:
            available_height: The vertical space available for this element

        Returns:
            Tuple of (fitted_part, overflowing_part). Either can be None.
        """
        if not self.items:
            return None, None

        # Calculate current element width to determine item heights
        element_width = self.size[0] if self.size else 400.0

        # Find how many items fit within available height
        fitted_items = []
        current_height = 0.0

        for _i, item in enumerate(self.items):
            # Create temporary element with current items to measure height
            temp_element = deepcopy(self)
            temp_element.items = fitted_items + [item]

            from markdowndeck.layout.metrics import calculate_element_height

            required_height = calculate_element_height(temp_element, element_width)

            if required_height <= available_height:
                fitted_items.append(item)
                current_height = required_height
            else:
                break

        # Check if any items fit
        if not fitted_items:
            logger.debug("No list items fit in available space")
            return None, deepcopy(self)

        # Check if all items fit
        if len(fitted_items) == len(self.items):
            return deepcopy(self), None

        # SIMPLE CHECK: Do we meet minimum requirement?
        minimum_items_required = 2
        fitted_item_count = len(fitted_items)

        if fitted_item_count < minimum_items_required:
            logger.info(
                f"List split rejected: Only {fitted_item_count} items fit, need minimum {minimum_items_required}"
            )
            return None, deepcopy(self)

        # Minimum met - proceed with split
        fitted_part = deepcopy(self)
        fitted_part.items = fitted_items
        fitted_part.size = (element_width, current_height)

        # Create overflowing part
        overflowing_items = self.items[len(fitted_items) :]
        overflowing_part = deepcopy(self)
        overflowing_part.items = overflowing_items
        overflowing_part.position = None  # Reset position for continuation slide

        # Handle context-aware title for overflowing part
        if hasattr(self, "related_to_prev") and self.related_to_prev:
            preceding_title = getattr(self, "_preceding_title_text", None)
            if preceding_title:
                continuation_title = TextElement(
                    element_type=ElementType.TEXT,
                    text=f"{preceding_title} {CONTINUED_ELEMENT_TITLE_SUFFIX}",
                    horizontal_alignment=getattr(self, "horizontal_alignment", "left"),
                    directives=getattr(self, "directives", {}).copy(),
                )
                overflowing_part._continuation_title = continuation_title

        logger.info(
            f"List split successful: {fitted_item_count} items fitted, {len(overflowing_items)} items overflowing"
        )
        return fitted_part, overflowing_part

    def set_preceding_title(self, title_text: str):
        """Set the text of the preceding title element for continuation purposes."""
        self._preceding_title_text = title_text
