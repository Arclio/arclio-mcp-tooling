"""Base element model for slide elements."""

from dataclasses import dataclass, field
from typing import Any

from markdowndeck.models.constants import ElementType


@dataclass
class Element:
    """Base class for slide elements."""

    element_type: ElementType
    position: tuple[float, float] = field(default_factory=lambda: (100, 100))
    size: tuple[float, float] = field(default_factory=lambda: (600, 100))
    object_id: str | None = None
    directives: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure directives is a dictionary."""
        if self.directives is None:
            self.directives = {}
