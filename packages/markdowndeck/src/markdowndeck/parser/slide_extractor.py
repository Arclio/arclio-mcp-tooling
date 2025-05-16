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

        logger.debug(f"Initial slide part count: {len(slide_parts)}")

        slides = []
        for i, slide_content_part in enumerate(slide_parts):
            # Process the raw part first, then strip for content checks
            processed_slide = self._process_slide_content(
                slide_content_part, i, f"slide_{i}_{uuid.uuid4().hex[:6]}"
            )
            # Only add if processed slide has meaningful content or title
            if (
                processed_slide["title"]
                or processed_slide["content"].strip()
                or processed_slide["footer"]
                or processed_slide["notes"]
            ):
                slides.append(processed_slide)
            else:
                logger.debug(
                    f"Skipping effectively empty slide part at index {i} after processing."
                )

        logger.info(f"Extracted {len(slides)} slides from markdown")
        return slides

    def _split_content_with_code_block_awareness(
        self, content: str, pattern: str
    ) -> list[str]:
        """
        Split content by a pattern, but ignore the pattern if it appears inside a code block.
        Slide separators (pattern) are given precedence to break out of misidentified code blocks.

        Args:
            content: The content to split
            pattern: Regular expression pattern to match separators

        Returns:
            List of content parts
        """
        lines = content.split("\n")
        parts = []
        current_part_lines = []  # Changed name for clarity

        in_code_block = False
        current_fence = None

        # Compile the separator regex pattern
        try:
            separator_re = re.compile(pattern)
        except re.error as e:
            logger.error(f"Invalid regex pattern for slide separator '{pattern}': {e}")
            # If pattern is invalid, return content as a single part to prevent data loss
            if content.strip():
                return [content]
            return []

        for line_idx, line in enumerate(lines):
            stripped_line = (
                line.lstrip()
            )  # Use lstrip for checking prefixes, original line for content

            # Priority 1: Check for slide separator
            if separator_re.match(line):  # Match on the original line to respect ^\s*
                if in_code_block:
                    logger.warning(
                        f"Slide separator '===' found at line {line_idx + 1} and overriding active code block state. Current fence: {current_fence}"
                    )
                    in_code_block = False
                    current_fence = None

                if current_part_lines:
                    parts.append("\n".join(current_part_lines))
                current_part_lines = []
                # Separator line itself is not added to any part
                continue

            # Priority 2: Handle code block boundaries if not a slide separator
            is_code_fence_line = False
            potential_fence = None
            if stripped_line.startswith("```") or stripped_line.startswith("~~~"):
                potential_fence = stripped_line[0:3]
                # A line is a fence if it's just the fence or fence + language identifier
                if stripped_line == potential_fence or (
                    len(stripped_line) > 3 and stripped_line[3:].isalnum()
                ):
                    is_code_fence_line = True
                elif (
                    len(stripped_line) > 3 and not stripped_line[3].isspace()
                ):  # e.g. ```python
                    is_code_fence_line = True

            if is_code_fence_line:
                if not in_code_block:
                    in_code_block = True
                    current_fence = potential_fence
                    current_part_lines.append(line)
                elif potential_fence == current_fence:  # Matching closing fence
                    in_code_block = False
                    current_fence = None
                    current_part_lines.append(line)
                else:  # Different fence type inside an existing code block (treat as content)
                    current_part_lines.append(line)
            elif in_code_block:
                current_part_lines.append(line)
            else:  # Normal content line
                current_part_lines.append(line)

        # Add the last part if it has content
        if current_part_lines:
            final_segment = "\n".join(current_part_lines)
            # No need to strip here, _process_slide_content will handle it.
            # This ensures that a slide consisting of, e.g. just newlines before a title, is preserved.
            parts.append(final_segment)
            logger.debug(
                f"Added final slide content segment: {len(current_part_lines)} lines"
            )

        # Filter out parts that become empty *after* stripping, unless they are the only part
        # This filtering is now effectively done in the calling `extract_slides` method
        # by checking if `_process_slide_content` results in an empty slide.
        return parts

    def _process_slide_content(
        self, content: str, index: int, slide_object_id: str
    ) -> dict:
        """
        Process slide content to extract title, footer, notes, etc.

        Args:
            content: The content of an individual slide (can be multi-line string)
            index: The index of the slide in the presentation
            slide_object_id: Generated unique ID for this slide

        Returns:
            Processed slide dictionary with components extracted
        """
        # Preserve original content for logging/debugging before stripping
        original_content_for_processing = content

        # First split content by footer separator @@@
        # Use re.split with a limit of 1 to ensure only the first @@@ acts as a footer separator
        footer_parts = re.split(
            r"^\s*@@@\s*$",
            original_content_for_processing,
            maxsplit=1,
            flags=re.MULTILINE,
        )
        main_content_segment = footer_parts[0]
        footer = footer_parts[1].strip() if len(footer_parts) > 1 else None

        # Extract title from H1 header from the main_content_segment
        title_match = re.search(
            r"^#\s+(.+)$", main_content_segment.lstrip(), re.MULTILINE
        )  # lstrip to catch titles at start of part
        title = None
        content_after_title = main_content_segment
        title_directives = {}  # Store any directives from the title

        if title_match:
            title = title_match.group(1).strip()

            # Extract directives from the title
            directive_pattern = r"^\s*(\s*\[[^\[\]]+=[^\[\]]*\]\s*)+"
            title_directive_match = re.match(directive_pattern, title)

            if title_directive_match:
                # Extract directive text
                directive_text = title_directive_match.group(0)
                # Remove directives from the title
                title = title[len(directive_text) :].strip()

                # Parse directives
                directive_pattern = r"\[([^=\[\]]+)=([^\[\]]*)\]"
                directive_matches = re.findall(directive_pattern, directive_text)

                # Process each directive
                for key, value in directive_matches:
                    key = key.strip().lower()
                    value = value.strip()

                    # Handle special directive conversions
                    if key == "align":
                        title_directives[key] = value.lower()
                    elif key == "fontsize":
                        try:
                            title_directives[key] = float(value)
                        except ValueError:
                            logger.warning(f"Invalid fontsize value in title: {value}")
                    elif key == "color":
                        title_directives[key] = value
                    else:
                        title_directives[key] = value

                logger.debug(f"Extracted directives from title: {title_directives}")

            # Continue with existing code...
            title_line_pattern = (
                r"^#\s+" + re.escape(title_match.group(1).strip()) + r"\s*(\n|$)"
            )
            content_after_title = re.sub(
                title_line_pattern, "", content_after_title, count=1, flags=re.MULTILINE
            )

        # Extract speaker notes from content_after_title
        notes_from_content = self._extract_notes(content_after_title)
        if notes_from_content:
            notes_pattern_to_remove = r""  # Non-greedy match for notes
            content_after_title = re.sub(
                notes_pattern_to_remove, "", content_after_title, flags=re.DOTALL
            )

        final_notes = notes_from_content
        speaker_notes_placeholder_id = (
            f"{slide_object_id}_notesShape" if final_notes else None
        )

        # Also check for notes in the footer (these override content notes if present)
        if footer:
            notes_from_footer = self._extract_notes(footer)
            if notes_from_footer:
                final_notes = notes_from_footer  # Footer notes take precedence
                speaker_notes_placeholder_id = (
                    f"{slide_object_id}_notesShape"  # Ensure ID is set
                )
                notes_pattern_to_remove = r""
                footer = re.sub(
                    notes_pattern_to_remove, "", footer, flags=re.DOTALL
                ).strip()

        # Extract background directives from content_after_title
        background = self._extract_background(content_after_title)
        if background:
            background_pattern = r"^\s*\[background=([^\]]+)\]\s*\n?"
            content_after_title = re.sub(
                background_pattern, "", content_after_title, count=1, flags=re.MULTILINE
            )

        # The final slide content is what remains of content_after_title after stripping
        final_slide_content = content_after_title.strip()

        slide = {
            "title": title,
            "content": final_slide_content,  # This is now correctly the content *without* title, notes, background directives
            "footer": footer,
            "notes": final_notes,
            "background": background,
            "index": index,
            "object_id": slide_object_id,
            "speaker_notes_object_id": speaker_notes_placeholder_id,
            "title_directives": title_directives,  # Add title directives to slide data
        }

        logger.debug(
            f"Processed slide {index + 1}: title='{title or 'None'}', "
            f"content_length={len(slide['content'])}, has_footer={footer is not None}, has_notes={final_notes is not None}"
        )
        return slide

    def _extract_notes(self, content: str) -> str | None:
        """Extract speaker notes from content. Notes are non-greedy."""
        notes_pattern = r"<!--\s*notes:\s*(.*?)\s*-->"  # Non-greedy match
        match = re.search(notes_pattern, content, re.DOTALL)
        return match.group(1).strip() if match else None

    def _extract_background(self, content: str) -> dict | None:
        """Extract background directive from content."""
        # Match background directive only if it's at the very beginning of the content string (after optional whitespace)
        background_pattern = r"^\s*\[background=([^\]]+)\]"
        match = re.match(
            background_pattern, content
        )  # content is already stripped or lstripped by caller usually
        if match:
            bg_value = match.group(1).strip()
            if bg_value.startswith("url(") and bg_value.endswith(")"):
                try:
                    url = bg_value[4:-1].strip("\"'")
                    from urllib.parse import urlparse  # Local import fine for utility

                    parsed_url = urlparse(url)
                    if not all([parsed_url.scheme, parsed_url.netloc]):
                        logger.warning(f"Invalid background image URL format: {url}")
                        return None  # Changed from fallback to None, let slide default handle it
                    return {"type": "image", "value": url}
                except Exception as e:
                    logger.warning(f"Error parsing background URL '{bg_value}': {e}")
                    return None
            return {"type": "color", "value": bg_value}  # Assume color if not URL
        return None
