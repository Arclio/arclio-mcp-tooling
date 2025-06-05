"""Data models for overflow detection and handling."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from markdowndeck.models import Element


class OverflowStrategy(str, Enum):
    """Available overflow handling strategies."""

    STANDARD = "standard"  # Balanced approach with smart content grouping
    AGGRESSIVE = "aggressive"  # Maximize content per slide, minimal whitespace
    CONSERVATIVE = "conservative"  # More whitespace, cleaner breaks
    CUSTOM = "custom"  # User-defined strategy


class OverflowType(str, Enum):
    """Types of overflow conditions."""

    VERTICAL = "vertical"  # Content extends below slide boundary
    HORIZONTAL = "horizontal"  # Content extends beyond slide width
    ELEMENT_TOO_LARGE = "element_too_large"  # Single element exceeds slide capacity


@dataclass
class OverflowElement:
    """Information about an element that overflows."""

    element: Element
    overflow_amount: float  # How much it overflows by (in points)
    overflow_type: OverflowType
    can_split: bool = False  # Whether element can be split across slides
    related_elements: list[Element] = field(default_factory=list)  # Elements that should move with this one


@dataclass
class OverflowInfo:
    """Complete overflow analysis for a slide."""

    has_overflow: bool
    overflow_elements: list[OverflowElement] = field(default_factory=list)
    total_content_height: float = 0.0
    available_height: float = 0.0
    overflow_amount: float = 0.0
    affected_zones: list[str] = field(default_factory=list)  # Which zones have overflow
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for backwards compatibility."""
        return {
            "has_overflow": self.has_overflow,
            "overflow_elements": len(self.overflow_elements),
            "total_content_height": self.total_content_height,
            "available_height": self.available_height,
            "overflow_amount": self.overflow_amount,
            "affected_zones": self.affected_zones,
            "summary": self.summary,
        }


@dataclass
class ContentGroup:
    """A group of related elements that should be kept together."""

    elements: list[Element]
    total_height: float
    group_type: str  # "related", "single", "header_with_content", etc.
    priority: int = 0  # Higher priority groups are kept together more strongly
    can_break_after: bool = True  # Whether a slide break is acceptable after this group

    def __post_init__(self):
        """Calculate total height if not provided."""
        if self.total_height == 0.0:
            self.total_height = sum((elem.size[1] if elem.size else 0) for elem in self.elements)


@dataclass
class SlideCapacity:
    """Information about slide capacity and zones."""

    total_height: float
    total_width: float

    # Zone boundaries
    header_top: float
    header_bottom: float
    body_top: float
    body_bottom: float
    footer_top: float
    footer_bottom: float

    # Available space in each zone
    header_height: float
    body_height: float
    footer_height: float
    content_width: float

    # Margins
    margins: dict[str, float]

    def is_in_body_zone(self, element: Element) -> bool:
        """Check if element is positioned in the body zone."""
        if not element.position:
            return False

        element_top = element.position[1]
        element_bottom = element_top + (element.size[1] if element.size else 0)

        return element_top >= self.body_top and element_bottom <= self.body_bottom

    def get_overflow_amount(self, element: Element) -> float:
        """Calculate how much an element overflows the body zone."""
        if not element.position or not element.size:
            return 0.0

        element_bottom = element.position[1] + element.size[1]

        if element_bottom > self.body_bottom:
            return element_bottom - self.body_bottom

        return 0.0


@dataclass
class DistributionPlan:
    """Plan for distributing content across slides."""

    slides: list[list[ContentGroup]]  # Groups per slide
    slide_metadata: list[dict] = field(default_factory=list)  # Metadata per slide
    total_slides: int = 0

    def __post_init__(self):
        """Update total slides count."""
        self.total_slides = len(self.slides)
