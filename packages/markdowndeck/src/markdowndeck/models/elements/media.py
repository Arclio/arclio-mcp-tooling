"""Media element models."""

from dataclasses import dataclass

from markdowndeck.models.elements.base import Element


@dataclass
class ImageElement(Element):
    """Image element."""

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
