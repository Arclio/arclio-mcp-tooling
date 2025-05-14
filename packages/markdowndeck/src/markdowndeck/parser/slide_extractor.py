"""Extract individual slides from markdown content."""

import logging
import re
import uuid

logger = logging.getLogger(__name__)


class SlideExtractor:
    """Extract individual slides from markdown content."""

    def extract_slides(self, markdown: str) -> list[dict]:
        """
        Extract individual slides from markdown content.

        Args:
            markdown: The markdown content containing slides separated by ===

        Returns:
            List of slide dictionaries with title, content, etc.
        """
        logger.debug("Extracting slides from markdown")
        normalized_content = markdown.replace("\r\n", "\n").replace("\r", "\n")

        # Split content into slides using code-block-aware splitter
        slide_parts = self._split_content_with_code_block_awareness(
            normalized_content, r"^\s*===\s*$"
        )

        # Log the number of slide parts found
        logger.debug(f"Initial slide part count: {len(slide_parts)}")

        slides = []
        for i, slide_content in enumerate(slide_parts):
            slide_content = slide_content.strip()
            if not slide_content:
                logger.debug(f"Skipping empty slide at index {i}")
                continue

            logger.debug(
                f"Processing slide {i + 1} with {len(slide_content)} characters"
            )
            current_slide_object_id = f"slide_{i}_{uuid.uuid4().hex[:6]}"
            processed_slide = self._process_slide_content(
                slide_content, i, current_slide_object_id
            )
            slides.append(processed_slide)

        logger.info(f"Extracted {len(slides)} slides from markdown")
        return slides

    def _split_content_with_code_block_awareness(
        self, content: str, pattern: str
    ) -> list[str]:
        """
        Split content by a pattern, but ignore the pattern if it appears inside a code block.

        Args:
            content: The content to split
            pattern: Regular expression pattern to match separators

        Returns:
            List of content parts
        """
        lines = content.split("\n")
        parts = []
        current_part = []

        # Track if we're inside a code block and which delimiter started it
        in_code_block = False
        current_fence = None

        for line in lines:
            stripped_line = line.lstrip()

            # Detect code block markers more precisely
            is_code_marker = False
            fence_match = None

            # Look for code fence markers (``` or ~~~)
            if stripped_line.startswith("```") or stripped_line.startswith("~~~"):
                fence_marker = stripped_line[0:3]  # Get just the fence characters

                # Check if it's a valid fence marker (not part of content)
                # Valid markers are either just the fence or fence+language
                if (
                    stripped_line == fence_marker
                    or " " in stripped_line[3:]
                    or len(stripped_line) == 3
                ):
                    is_code_marker = True
                    fence_match = fence_marker

            # Handle code block boundaries
            if is_code_marker:
                if not in_code_block:
                    # Starting a new code block
                    in_code_block = True
                    current_fence = fence_match
                    current_part.append(line)
                elif fence_match == current_fence:
                    # Ending the current code block if the fence matches
                    in_code_block = False
                    current_fence = None
                    current_part.append(line)
                else:
                    # This is either a nested code block (not standard in Markdown)
                    # or a code block with a different fence inside another code block
                    # Treat it as content
                    current_part.append(line)
            elif in_code_block:
                # Inside a code block, always add to current part
                current_part.append(line)
            elif re.match(pattern, line):
                # Found a separator (not inside code block)
                if current_part:  # Only start a new part if we have content
                    parts.append("\n".join(current_part))
                    current_part = []
            else:
                # Normal line, not in code block, not a separator
                current_part.append(line)

        # CRITICAL FIX: Always add the remaining content as the last slide
        # even if there's no trailing separator
        if current_part:
            logger.debug(f"Adding final slide content: {len(current_part)} lines")
            parts.append("\n".join(current_part))

        return parts

    def _process_slide_content(
        self, content: str, index: int, slide_object_id: str
    ) -> dict:
        """
        Process slide content to extract title, footer, notes, etc.

        Args:
            content: The content of an individual slide
            index: The index of the slide in the presentation
            slide_object_id: Generated unique ID for this slide

        Returns:
            Processed slide dictionary with components extracted
        """
        # First split content by footer separator @@@
        footer_parts = re.split(r"(?m)^\s*@@@\s*$", content)
        main_content = footer_parts[0]
        footer = footer_parts[1].strip() if len(footer_parts) > 1 else None

        # Extract title from H1 header
        title_match = re.search(r"^#\s+(.+)$", main_content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else None

        # Remove title from content to avoid duplicate rendering
        if title_match:
            main_content = main_content.replace(title_match.group(0), "", 1)

        # Extract speaker notes
        notes = self._extract_notes(main_content)
        speaker_notes_placeholder_id = None
        if notes:
            notes_pattern_to_remove = r"<!--\s*notes:\s*(?:.*?)\s*-->"
            main_content = re.sub(
                notes_pattern_to_remove, "", main_content, flags=re.DOTALL
            )
            speaker_notes_placeholder_id = f"{slide_object_id}_notesShape"

        # Also check for notes in the footer
        if footer:
            footer_notes = self._extract_notes(footer)
            if footer_notes:
                notes = footer_notes
                speaker_notes_placeholder_id = f"{slide_object_id}_notesShape"
                notes_pattern_to_remove = r"<!--\s*notes:\s*(?:.*?)\s*-->"
                footer = re.sub(
                    notes_pattern_to_remove, "", footer, flags=re.DOTALL
                ).strip()

        # Extract background directives
        background = self._extract_background(main_content)
        if background:
            background_pattern = r"^\s*\[background=([^\]]+)\]\s*\n?"
            main_content = re.sub(
                background_pattern, "", main_content, flags=re.MULTILINE
            )

        # Create the slide dictionary
        slide = {
            "title": title,
            "content": main_content.strip(),
            "footer": footer,
            "notes": notes,
            "background": background,
            "index": index,
            "object_id": slide_object_id,
            "speaker_notes_object_id": speaker_notes_placeholder_id,
        }

        logger.debug(
            f"Processed slide {index}: title='{title or 'None'}', "
            f"content_length={len(slide['content'])}, has_footer={footer is not None}"
        )

        return slide

    def _extract_notes(self, content: str) -> str | None:
        """
        Extract speaker notes from content.

        Args:
            content: The content to extract notes from

        Returns:
            Extracted notes or None if no notes found
        """
        # Ensure this pattern is correct and used consistently
        notes_pattern = r"<!--\s*notes:\s*(.*?)\s*-->"
        match = re.search(notes_pattern, content, re.DOTALL)
        return match.group(1).strip() if match else None

    def _extract_background(self, content: str) -> dict | None:
        """
        Extract background directive from content.

        Args:
            content: The content to extract background from

        Returns:
            Dictionary with background type and value, or None
        """
        background_pattern = r"^\s*\[background=([^\]]+)\]"
        match = re.match(background_pattern, content.lstrip())
        if match:
            bg_value = match.group(1).strip()

            # Handle URL backgrounds
            if bg_value.startswith("url(") and bg_value.endswith(")"):
                try:
                    # Extract URL from url(...) format
                    url = bg_value[4:-1].strip("\"'")

                    # Basic URL validation
                    from urllib.parse import urlparse

                    parsed_url = urlparse(url)
                    if not all([parsed_url.scheme, parsed_url.netloc]):
                        logger.warning(f"Invalid background image URL format: {url}")
                        # Return a fallback background color instead
                        return {"type": "color", "value": "#f5f5f5"}

                    return {"type": "image", "value": url}
                except Exception as e:
                    logger.warning(f"Error parsing background URL: {e}")
                    # Return a fallback background color
                    return {"type": "color", "value": "#f5f5f5"}

            # Handle color backgrounds
            return {"type": "color", "value": bg_value}

        return None
