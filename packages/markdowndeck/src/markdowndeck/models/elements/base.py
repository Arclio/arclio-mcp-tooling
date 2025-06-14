from dataclasses import dataclass, field
from typing import Any

from markdowndeck.models.constants import ElementType


@dataclass
class Element:
    """Base class for slide elements."""

    element_type: ElementType
    position: tuple[float, float] | None = field(default=None)
    size: tuple[float, float] | None = None
    object_id: str | None = None
    directives: dict[str, Any] = field(default_factory=dict)
    # ADDED: Internal flag for overflow circuit breaker per DATA_MODELS.md
    _overflow_moved: bool = False

    def __post_init__(self):
        """Ensure directives is a dictionary."""
        if self.directives is None:
            self.directives = {}
