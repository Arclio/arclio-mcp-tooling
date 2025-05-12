"""List element models."""

from dataclasses import dataclass, field

from markdowndeck.models.elements.base import Element
from markdowndeck.models.elements.text import TextFormat


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

    def count_total_items(self) -> int:
        """Count the total number of items in the list, including nested items."""
        return sum(item.count_all_items() for item in self.items)

    def max_nesting_level(self) -> int:
        """Get the maximum nesting level in the list."""
        if not self.items:
            return 0
        return max(item.max_depth() for item in self.items)
