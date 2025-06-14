import logging
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from markdowndeck.models.elements.base import Element
from markdowndeck.models.elements.text import TextFormat

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
        # REFACTORED: Split this ListElement with robust progress guarantees.
        # The previous implementation was inefficient and failed on large lists.
        # This version uses a direct estimation, finds a split point, and ensures progress.
        """
        from markdowndeck.layout.metrics import calculate_element_height

        if not self.items:
            return None, None

        element_width = self.size[0] if self.size and self.size[0] > 0 else 400.0
        full_height = calculate_element_height(self, element_width)

        if full_height <= available_height:
            return deepcopy(self), None

        # Estimate height per item for splitting. This is an approximation.
        num_items = len(self.items)
        avg_height_per_item = full_height / num_items if num_items > 0 else 20.0
        if avg_height_per_item <= 0:
            avg_height_per_item = 20.0

        # Estimate how many items can fit
        estimated_items_that_fit = max(0, int(available_height / avg_height_per_item))

        # Now, accurately measure up to the estimated point to find the true split point
        fitted_items_count = 0
        height_so_far = 0.0
        # Check one beyond the estimate for edge cases, but not too far
        for i in range(min(num_items, estimated_items_that_fit + 2)):
            temp_list = deepcopy(self)
            temp_list.items = self.items[: i + 1]
            temp_list.size = None  # Force recalculation
            required_height = calculate_element_height(temp_list, element_width)

            if required_height <= available_height:
                fitted_items_count = i + 1
                height_so_far = required_height
            else:
                break  # This item caused the overflow

        # If no items fit at all, move the whole element.
        if fitted_items_count == 0:
            logger.debug("No list items fit in available space, moving entire list.")
            return None, deepcopy(self)

        # If all items fit (should have been caught, but for safety)
        if fitted_items_count == len(self.items):
            return deepcopy(self), None

        # MINIMUM REQUIREMENTS CHECK: Must fit at least 2 items.
        minimum_items_required = 1  # Relaxed to 1 to allow progress on tight fits
        if (
            fitted_items_count < minimum_items_required
            and len(self.items) > minimum_items_required
        ):
            logger.info(
                f"List split rejected: Only {fitted_items_count} items fit, need minimum {minimum_items_required}."
            )
            return None, deepcopy(self)

        # Proceed with split
        fitted_items = self.items[:fitted_items_count]
        overflowing_items = self.items[fitted_items_count:]

        fitted_part = deepcopy(self)
        fitted_part.items = fitted_items
        # Use the accurately measured height for the fitted part.
        fitted_part.size = (element_width, height_so_far)

        overflowing_part = deepcopy(self)
        overflowing_part.items = overflowing_items
        overflowing_part.position = None
        # CRITICAL FIX: Clear size so the overflowing part gets recalculated with fewer items
        overflowing_part.size = None

        logger.info(
            f"List split successful: {len(fitted_items)} items fitted, {len(overflowing_items)} items overflowing."
        )
        return fitted_part, overflowing_part

    def set_preceding_title(self, title_text: str):
        """Set the text of the preceding title element for continuation purposes."""
        self._preceding_title_text = title_text
