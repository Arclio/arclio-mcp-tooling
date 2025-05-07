import logging
import re

logger = logging.getLogger(__name__)


class SlideExtractor:
    """Extract individual slides from markdown content."""

    def extract_slides(self, markdown: str) -> list[dict]:
        """
        Split markdown content into individual slides.

        Args:
            markdown: Full markdown string

        Returns:
            List of dictionaries with slide data
        """
        logger.debug("Extracting slides from markdown")

        # Normalize line endings
        normalized_content = markdown.replace("\r\n", "\n").replace("\r", "\n")

        # Split on slide separator - use a more precise pattern that won't match inside code blocks
        # The pattern looks for a line that contains only '===' with optional whitespace
        slide_parts = re.split(r"(?m)^\s*===\s*$", normalized_content)

        slides = []
        for i, slide_content in enumerate(slide_parts):
            slide_content = slide_content.strip()
            if not slide_content:
                continue

            logger.debug(f"Processing slide {i + 1}")

            # Process slide content
            processed_slide = self._process_slide_content(slide_content, i)
            slides.append(processed_slide)

        logger.info(f"Extracted {len(slides)} slides from markdown")
        return slides

    def _process_slide_content(self, content: str, index: int) -> dict:
        """
        Process slide content to extract components.

        Args:
            content: Raw slide content
            index: Slide index for logging

        Returns:
            Dictionary with processed slide data
        """
        # Extract footer if present - use a more precise pattern
        # The pattern looks for a line that contains only '@@@' with optional whitespace
        footer_parts = re.split(r"(?m)^\s*@@@\s*$", content)
        main_content = footer_parts[0]
        footer = footer_parts[1].strip() if len(footer_parts) > 1 else None

        # Extract title
        title_match = re.search(r"^#\s+(.+)$", main_content, re.MULTILINE)
        title = title_match.group(1) if title_match else None

        # Remove title from content if found
        if title_match:
            main_content = main_content.replace(title_match.group(0), "", 1)

        # Extract notes from HTML comments
        notes = self._extract_notes(main_content)
        if notes:
            # Remove notes comment from content
            notes_pattern = r"<!--\s*notes:\s*(.*?)\s*-->"
            main_content = re.sub(notes_pattern, "", main_content, flags=re.DOTALL)

        # Extract background if specified
        background = self._extract_background(main_content)

        # Create slide data
        return {
            "title": title,
            "content": main_content.strip(),
            "footer": footer,
            "notes": notes,
            "background": background,
            "index": index,
        }

    def _extract_notes(self, content: str) -> str | None:
        """
        Extract speaker notes from HTML comments.

        Args:
            content: Slide content

        Returns:
            Extracted notes or None
        """
        notes_pattern = r"<!--\s*notes:\s*(.*?)\s*-->"
        match = re.search(notes_pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    def _extract_background(self, content: str) -> dict | None:
        """
        Extract slide background directives.

        Args:
            content: Slide content

        Returns:
            Background settings or None
        """
        # Look for [background=...] directive at the start
        background_pattern = r"^\s*\[background=([^\]]+)\]"
        match = re.search(background_pattern, content, re.MULTILINE)

        if match:
            bg_value = match.group(1).strip()

            # Check if it's a color
            if bg_value.startswith("#") or bg_value in [
                "white",
                "black",
                "transparent",
            ]:
                return {"type": "color", "value": bg_value}

            # Check if it's an image URL
            if bg_value.startswith("url(") and bg_value.endswith(")"):
                url = bg_value[4:-1].strip("\"'")
                return {"type": "image", "value": url}

        return None
