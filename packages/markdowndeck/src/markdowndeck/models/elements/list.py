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
        REFACTORED: Split this ListElement with robust progress guarantees.

        Rule: Must fit at least 2 items to split.
        If minimum not met, promote entire list to next slide.
        This implementation now reliably makes progress to prevent infinite loops.
        """
        from markdowndeck.layout.metrics import calculate_element_height

        if not self.items:
            return None, None

        element_width = self.size[0] if self.size and self.size[0] > 0 else 400.0
        full_height = calculate_element_height(self, element_width)

        if full_height <= available_height:
            return deepcopy(self), None

        # Find how many items fit within available height
        fitted_items_count = 0
        current_height = 0.0

        for i in range(len(self.items)):
            # Create a temporary element with one more item to measure its height
            items_to_measure = self.items[: i + 1]
            temp_element = deepcopy(self)
            temp_element.items = items_to_measure
            required_height = calculate_element_height(temp_element, element_width)

            if required_height <= available_height:
                fitted_items_count = i + 1
                current_height = required_height
            else:
                # This item caused an overflow, so we can't include it.
                break

        # If no items fit at all, move the whole element.
        if fitted_items_count == 0:
            logger.debug("No list items fit in available space, moving entire list.")
            return None, deepcopy(self)

        # If all items fit (should have been caught by full_height check, but for safety)
        if fitted_items_count == len(self.items):
            return deepcopy(self), None

        # MINIMUM REQUIREMENTS CHECK: Must fit at least 2 items.
        minimum_items_required = 2
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
        fitted_part.size = (element_width, current_height)

        overflowing_part = deepcopy(self)
        overflowing_part.items = overflowing_items
        overflowing_part.position = None

        logger.info(
            f"List split successful: {len(fitted_items)} items fitted, {len(overflowing_items)} items overflowing."
        )
        return fitted_part, overflowing_part

    def set_preceding_title(self, title_text: str):
        """Set the text of the preceding title element for continuation purposes."""
        self._preceding_title_text = title_text
