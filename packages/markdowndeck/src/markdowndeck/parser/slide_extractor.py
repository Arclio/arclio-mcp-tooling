import logging
import re
import uuid

logger = logging.getLogger(__name__)


class SlideExtractor:
    """Extract individual slides from markdown content with improved parsing."""

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
            # Skip empty slide content parts (containing only whitespace and separators)
            if not slide_content_part.strip():
                logger.debug(f"Skipping empty slide content part at index {i}")
                continue

            # Skip slide content parts that only contain section separators
            stripped_content = slide_content_part.strip()
            # Remove all section separators and check if anything meaningful remains
            content_without_separators = re.sub(
                r"^\s*---\s*$|^\s*\*\*\*\s*$", "", stripped_content, flags=re.MULTILINE
            )
            if not content_without_separators.strip():
                logger.debug(
                    f"Skipping slide content part with only separators at index {i}"
                )
                continue

            processed_slide = self._process_slide_content(
                slide_content_part, i, f"slide_{i}_{uuid.uuid4().hex[:6]}"
            )

            # Only add slides with meaningful content
            if (
                processed_slide["title"]
                or processed_slide["content"].strip()
                or processed_slide["footer"]
                or processed_slide["notes"]
                or processed_slide["background"]
            ):
                slides.append(processed_slide)
            else:
                logger.debug(f"Skipping empty slide part at index {i}")

        logger.info(f"Extracted {len(slides)} slides from markdown")
        return slides

    def _split_content_with_code_block_awareness(
        self, content: str, pattern: str
    ) -> list[str]:
        """
        Split content by pattern while respecting code block boundaries.

        ENHANCEMENT P7: Improved code fence detection.
        """
        lines = content.split("\n")
        parts = []
        current_part_lines = []

        in_code_block = False
        current_fence = None

        # ENHANCEMENT P7: Support for more fence types
        fence_patterns = ["```", "~~~", "````"]  # Extended support

        try:
            separator_re = re.compile(pattern)
        except re.error as e:
            logger.error(f"Invalid regex pattern '{pattern}': {e}")
            return [content] if content.strip() else []

        for line_idx, line in enumerate(lines):
            stripped_line = line.strip()

            # Check for code fence
            is_code_fence_line = False
            potential_fence = None

            for fence in fence_patterns:
                if stripped_line.startswith(fence):
                    potential_fence = fence
                    is_code_fence_line = True
                    break

            if is_code_fence_line:
                if not in_code_block:
                    in_code_block = True
                    current_fence = potential_fence
                    logger.debug(
                        f"Opening code block with {potential_fence} at line {line_idx + 1}"
                    )
                elif potential_fence == current_fence:
                    in_code_block = False
                    current_fence = None
                    logger.debug(
                        f"Closing code block with {potential_fence} at line {line_idx + 1}"
                    )

            # Check for slide separator (only outside code blocks)
            if separator_re.match(line) and not in_code_block:
                if current_part_lines:
                    parts.append("\n".join(current_part_lines))
                current_part_lines = []
                continue
            if separator_re.match(line) and in_code_block:
                logger.debug(
                    f"Slide separator inside code block at line {line_idx + 1}"
                )

            current_part_lines.append(line)

        # Add final part
        if current_part_lines:
            parts.append("\n".join(current_part_lines))

        return parts

    def _process_slide_content(
        self, content: str, index: int, slide_object_id: str
    ) -> dict:
        """
        Process slide content with improved title and subtitle handling.
        """
        original_content = content

        # Split by footer separator
        footer_parts = re.split(
            r"^\s*@@@\s*$", original_content, maxsplit=1, flags=re.MULTILINE
        )
        main_content_segment = footer_parts[0]
        footer = footer_parts[1].strip() if len(footer_parts) > 1 else None

        # Extract title, subtitle, and directives
        title, subtitle, content_after_meta, title_directives = (
            self._extract_title_with_directives(main_content_segment)
        )

        # Extract notes
        notes_from_content = self._extract_notes(content_after_meta)
        final_notes = notes_from_content

        # Check for notes in footer (override content notes)
        if footer:
            notes_from_footer = self._extract_notes(footer)
            if notes_from_footer:
                final_notes = notes_from_footer
                # Remove notes from footer
                footer = re.sub(
                    r"<!--\s*notes:\s*.*?\s*-->", "", footer, flags=re.DOTALL
                ).strip()

        # Remove all notes from content
        content_after_meta = re.sub(
            r"<!--\s*notes:\s*.*?\s*-->", "", content_after_meta, flags=re.DOTALL
        )

        final_slide_content = content_after_meta.strip()

        slide = {
            "title": title,
            "subtitle": subtitle,  # Add subtitle field
            "content": final_slide_content,
            "footer": footer,
            "notes": final_notes,
            "background": None,
            "index": index,
            "object_id": slide_object_id,
            "speaker_notes_object_id": (
                f"{slide_object_id}_notesShape" if final_notes else None
            ),
            "title_directives": title_directives,
        }

        logger.debug(
            f"Processed slide {index + 1}: title='{title or 'None'}', "
            f"subtitle='{subtitle or 'None'}', "
            f"content_length={len(slide['content'])}, directives={title_directives}"
        )
        return slide

    def _extract_title_with_directives(
        self, content: str
    ) -> tuple[str | None, str | None, str, dict]:
        """
        Extract title, subtitle, and directives with improved multi-line directive support.
        This method is "block-aware" and consumes the entire metadata block including
        directives on subsequent lines.
        """
        lines = content.split("\n")
        title_directives = {}
        title_text = None
        subtitle_text = None
        consumed_lines = 0

        # Pattern to match directive-only lines
        directive_only_pattern = r"^\s*((?:\s*\[[^\[\]]+=[^\[\]]*\]\s*)+)\s*$"

        # Step 1: Find and process title
        for i, line in enumerate(lines):
            if not line.strip():
                consumed_lines += 1
                continue

            # Check if this is a title line
            title_match = re.match(r"^\s*#\s+(.+)$", line)
            if title_match:
                full_title_text = title_match.group(1).strip()
                consumed_lines = i + 1

                # Extract directives from the title line itself
                directive_pattern = r"(\s*\[[^\[\]]+=[^\[\]]*\]\s*)+"
                start_directive_match = re.match(directive_pattern, full_title_text)
                end_directive_match = re.search(
                    directive_pattern + r"\s*$", full_title_text
                )

                if start_directive_match:
                    directive_text = start_directive_match.group(0)
                    title_text = full_title_text[len(directive_text) :].strip()
                elif end_directive_match:
                    directive_text = end_directive_match.group(0)
                    title_text = full_title_text[: end_directive_match.start()].strip()
                else:
                    title_text = full_title_text
                    directive_text = ""

                # Parse directives from title line
                if directive_text:
                    directive_matches = re.findall(
                        r"\[([^=\[\]]+)=([^\[\]]*)\]", directive_text
                    )
                    for key, value in directive_matches:
                        key = key.strip().lower()
                        value = value.strip()
                        title_directives[key] = value
                break
        else:
            # No title found
            return None, None, content, {}

        # Step 2: Consume post-title directive-only lines
        while consumed_lines < len(lines):
            line = lines[consumed_lines]
            if re.match(directive_only_pattern, line.strip()):
                # Parse directives from this line
                directive_matches = re.findall(r"\[([^=\[\]]+)=([^\[\]]*)\]", line)
                for key, value in directive_matches:
                    key = key.strip().lower()
                    value = value.strip()
                    title_directives[key] = value
                consumed_lines += 1
            elif not line.strip():
                # Skip empty lines
                consumed_lines += 1
            else:
                # Non-directive, non-empty line found
                break

        # Step 3: Check for subtitle
        if consumed_lines < len(lines):
            line = lines[consumed_lines]
            subtitle_match = re.match(r"^\s*##\s+(.+)$", line)
            if subtitle_match:
                full_subtitle_text = subtitle_match.group(1).strip()
                consumed_lines += 1

                # Extract directives from subtitle line
                directive_pattern = r"(\s*\[[^\[\]]+=[^\[\]]*\]\s*)+"
                start_directive_match = re.match(directive_pattern, full_subtitle_text)
                end_directive_match = re.search(
                    directive_pattern + r"\s*$", full_subtitle_text
                )

                if start_directive_match:
                    directive_text = start_directive_match.group(0)
                    subtitle_text = full_subtitle_text[len(directive_text) :].strip()
                elif end_directive_match:
                    directive_text = end_directive_match.group(0)
                    subtitle_text = full_subtitle_text[
                        : end_directive_match.start()
                    ].strip()
                else:
                    subtitle_text = full_subtitle_text
                    directive_text = ""

                # Parse directives from subtitle line
                if directive_text:
                    directive_matches = re.findall(
                        r"\[([^=\[\]]+)=([^\[\]]*)\]", directive_text
                    )
                    for key, value in directive_matches:
                        key = key.strip().lower()
                        value = value.strip()
                        title_directives[key] = value

                # Step 4: Consume post-subtitle directive-only lines
                while consumed_lines < len(lines):
                    line = lines[consumed_lines]
                    if re.match(directive_only_pattern, line.strip()):
                        # Parse directives from this line
                        directive_matches = re.findall(
                            r"\[([^=\[\]]+)=([^\[\]]*)\]", line
                        )
                        for key, value in directive_matches:
                            key = key.strip().lower()
                            value = value.strip()
                            title_directives[key] = value
                        consumed_lines += 1
                    elif not line.strip():
                        # Skip empty lines
                        consumed_lines += 1
                    else:
                        # Non-directive, non-empty line found
                        break

        # Step 5: Reconstruct remaining content
        content_after_meta = "\n".join(lines[consumed_lines:])

        return title_text, subtitle_text, content_after_meta, title_directives

    def _extract_notes(self, content: str) -> str | None:
        """Extract speaker notes from content."""
        notes_pattern = r"<!--\s*notes:\s*(.*?)\s*-->"
        match = re.search(notes_pattern, content, re.DOTALL)
        return match.group(1).strip() if match else None
