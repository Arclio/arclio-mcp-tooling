"""Deck model for presentations."""

from dataclasses import dataclass, field

from markdowndeck.models.slide import Slide


@dataclass
class Deck:
    """Represents a complete presentation."""

    slides: list[Slide] = field(default_factory=list)
    title: str = "Untitled Presentation"
    theme_id: str | None = None

    def add_slide(self, slide: Slide) -> None:
        """Add a slide to the deck."""
        self.slides.append(slide)

    def get_slide_count(self) -> int:
        """Get the number of slides in the deck."""
        return len(self.slides)

    def get_slide(self, index: int) -> Slide | None:
        """Get a slide by index."""
        if 0 <= index < len(self.slides):
            return self.slides[index]
        return None
