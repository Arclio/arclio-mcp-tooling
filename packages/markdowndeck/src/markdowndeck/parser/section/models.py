"""Models for section parsing."""

from dataclasses import dataclass


@dataclass
class ProtectedBlock:
    """A code block that needs to be protected during parsing."""

    content: str
    placeholder: str
    start_line: int
    end_line: int


@dataclass
class ContentSplit:
    """Result of content splitting operation."""

    parts: list[str]
    protected_blocks: dict[str, str]


@dataclass
class SectionInfo:
    """Information about a section in the slide."""

    content: str
    directives: dict = None
    type: str = "section"
    subsections: list["SectionInfo"] = None
    id: str | None = None

    def __post_init__(self):
        """Initialize default values."""
        if self.directives is None:
            self.directives = {}
        if self.subsections is None:
            self.subsections = []
