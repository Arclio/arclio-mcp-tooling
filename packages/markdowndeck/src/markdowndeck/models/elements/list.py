"""List element models."""

from copy import deepcopy
from dataclasses import dataclass, field

from markdowndeck.models import ElementType
from markdowndeck.models.elements.base import Element
from markdowndeck.models.elements.text import TextElement, TextFormat
from markdowndeck.overflow.constants import CONTINUED_ELEMENT_TITLE_SUFFIX


@dataclass
class ListItem:
    """Represents an item in a list with optional nested items."""

    text: str
    level: int = 0
    formatting: list[TextFormat] = field(default_factory=list)
    children: list["ListItem"] = field(default_factory=list)

    def add_child(self, child: "ListItem") -> None:
        """
        Add a child item to this list item.

        Args:
            child: Child list item to add
        """
        # Set the correct level for the child
        child.level = self.level + 1
        self.children.append(child)

    def count_all_items(self) -> int:
        """
        Count this item and all child items recursively.

        Returns:
            Total number of items including this one and all children
        """
        count = 1  # Count self
        for child in self.children:
            count += child.count_all_items()
        return count

    def max_depth(self) -> int:
        """
        Calculate the maximum depth of nesting from this item.

        Returns:
            Maximum nesting depth (0 for items with no children)
        """
        if not self.children:
            return 0
        return 1 + max(child.max_depth() for child in self.children)


@dataclass
class ListElement(Element):
    """List element (bullet list, ordered list)."""

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
        Split this ListElement to fit within available_height.

        Args:
            available_height: The vertical space available for this element

        Returns:
            Tuple of (fitted_part, overflowing_part). Either can be None.
            fitted_part: Contains items that fit within available_height
            overflowing_part: Contains items that don't fit, potentially with continuation title
        """
        if not self.items:
            return None, None

        # Calculate current element width to determine item heights
        element_width = self.size[0] if self.size else 400.0  # fallback width

        # Find how many items fit within available height
        fitted_items = []
        current_height = 0.0

        for _i, item in enumerate(self.items):
            # Create temporary element with current items to measure height
            temp_element = deepcopy(self)
            temp_element.items = fitted_items + [item]

            # Calculate height this would require (local import to avoid circular dependency)
            from markdowndeck.layout.metrics import calculate_element_height

            required_height = calculate_element_height(temp_element, element_width)

            if required_height <= available_height:
                fitted_items.append(item)
                current_height = required_height
            else:
                # This item doesn't fit
                break

        # Determine split results
        if not fitted_items:
            # Nothing fits
            return None, deepcopy(self)

        if len(fitted_items) == len(self.items):
            # Everything fits
            return deepcopy(self), None

        # Create fitted part
        fitted_part = deepcopy(self)
        fitted_part.items = fitted_items
        fitted_part.size = (element_width, current_height)

        # Create overflowing part
        overflowing_items = self.items[len(fitted_items) :]
        overflowing_part = deepcopy(self)
        overflowing_part.items = overflowing_items

        # Handle context-aware title for overflowing part
        if hasattr(self, "related_to_prev") and self.related_to_prev:
            # Check if we have a preceding title element
            # This would be set by the layout system when elements are related
            preceding_title = getattr(self, "_preceding_title_text", None)

            if preceding_title:
                # Create continuation title element
                continuation_title = TextElement(
                    element_type=ElementType.TEXT,
                    text=f"{preceding_title} {CONTINUED_ELEMENT_TITLE_SUFFIX}",
                    horizontal_alignment=getattr(self, "horizontal_alignment", "left"),
                    directives=getattr(self, "directives", {}).copy(),
                )

                # Store this as a property on the overflowing part for the layout system
                overflowing_part._continuation_title = continuation_title

        return fitted_part, overflowing_part

    def set_preceding_title(self, title_text: str):
        """
        Set the text of the preceding title element for continuation purposes.

        Args:
            title_text: The text of the title element that precedes this list
        """
        self._preceding_title_text = title_text
