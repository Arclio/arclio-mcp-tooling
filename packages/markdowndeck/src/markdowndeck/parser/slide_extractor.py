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
        Extract title and subtitle with their same-line directives per Rule 1 (Element-Scoped Directives).

        Per the Unified Hierarchical Directive Scoping model:
        - ONLY processes directives on the same line as title/subtitle (Rule 1)
        - NEVER consumes standalone directive lines (those are for Rule 2 - Section-Scoped)
        - Leaves all standalone directive lines in content for the section parser
        """
        lines = content.split("\n")
        title_directives = {}
        title_text = None
        subtitle_text = None
        consumed_lines = 0

        # Step 1: Find and process title with same-line directives only
        title_line_index = None
        for i, line in enumerate(lines):
            # Check if this is a title line
            title_match = re.match(r"^\s*#\s+(.+)$", line)
            if title_match:
                full_title_text = title_match.group(1).strip()
                title_line_index = i

                # Extract directives from the title line itself (Rule 1)
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

        # Track what we've consumed so far (just the title line)
        consumed_lines = title_line_index + 1

        # Step 2: Look for subtitle and extract same-line directives only
        for search_idx in range(consumed_lines, len(lines)):
            line = lines[search_idx]
            if not line.strip():
                continue

            subtitle_match = re.match(r"^\s*##\s+(.+)$", line)
            if subtitle_match:
                full_subtitle_text = subtitle_match.group(1).strip()
                consumed_lines = search_idx + 1

                # Extract directives from subtitle line (Rule 1)
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
                break

            # If we hit non-subtitle content, stop looking for subtitle
            # BUT IMPORTANT: Don't consume any standalone directive lines
            break

        # Step 3: Return remaining content (all standalone directives are preserved)
        # Include content before title AND content after consumed lines
        content_before_title = "\n".join(lines[:title_line_index])
        content_after_meta = "\n".join(lines[consumed_lines:])

        # Combine content, preserving standalone directives
        if content_before_title.strip() and content_after_meta.strip():
            final_content = content_before_title + "\n" + content_after_meta
        elif content_before_title.strip():
            final_content = content_before_title
        elif content_after_meta.strip():
            final_content = content_after_meta
        else:
            final_content = ""

        return title_text, subtitle_text, final_content, title_directives

    def _extract_notes(self, content: str) -> str | None:
        """Extract speaker notes from content."""
        notes_pattern = r"<!--\s*notes:\s*(.*?)\s*-->"
        match = re.search(notes_pattern, content, re.DOTALL)
        return match.group(1).strip() if match else None
