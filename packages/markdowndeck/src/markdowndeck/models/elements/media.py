"""Media element models."""

from dataclasses import dataclass

from markdowndeck.models.elements.base import Element


@dataclass
class ImageElement(Element):
    """Image element with proactive scaling contract."""

    url: str = ""
    alt_text: str = ""

    def is_valid(self) -> bool:
        """
        Check if the image element has a valid URL.

        Returns:
            True if the URL is valid, False otherwise
        """
        return bool(self.url)

    def is_web_image(self) -> bool:
        """
        Check if this is a web image (versus data URL).

        Returns:
            True if this is a web image, False otherwise
        """
        return self.url.startswith(("http://", "https://"))

    def split(self, available_height: float) -> tuple["ImageElement | None", "ImageElement | None"]:
        """
        Image elements are proactively scaled by the Layout Calculator to fit their containers.
        Since they are pre-scaled, they will always fit and never need to be split.

        Per the specification: Images return (self, None) because they are sized to prevent
        overflow in the first place.

        Args:
            available_height: Unused, as images are pre-scaled

        Returns:
            (self, None) - image always fits because it's pre-scaled
        """
        # Images are proactively scaled by the Layout Calculator, so they always fit
        return self, None
