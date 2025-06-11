from dataclasses import dataclass

from markdowndeck.models.elements.base import Element


@dataclass
class ImageElement(Element):
    """Image element with proactive scaling contract."""

    url: str = ""
    alt_text: str = ""
    # FIXED: Added aspect_ratio attribute per DATA_MODELS.md spec.
    aspect_ratio: float | None = None

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

    def split(
        self, available_height: float
    ) -> tuple["ImageElement | None", "ImageElement | None"]:
        """
        Image elements are proactively scaled and should never be split.

        Per DATA_MODELS.md (Sec 3.4): This method must raise a NotImplementedError
        if called. Images are pre-scaled by the Layout Manager to fit their
        containers, so an attempt to split one indicates a critical system error.

        Args:
            available_height: Unused, as images are pre-scaled.

        Returns:
            This method does not return; it always raises an error.

        Raises:
            NotImplementedError: Always, as images are unsplittable by design.
        """
        # REFACTORED: Aligned with DATA_MODELS.md (Sec 3.4).
        # MAINTAINS: The principle that images are atomic.
        # BREAKING_CHANGE: This method no longer returns (self, None). It raises an exception.
        # JUSTIFICATION: DATA_MODELS.md Sec 3.4 requires this behavior.
        raise NotImplementedError(
            "ImageElement.split should never be called. "
            "Images are proactively scaled by the LayoutManager and are considered atomic."
        )
