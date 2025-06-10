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
        Process slide content with robust title, subtitle, and metadata handling.
        This version ensures that consumed metadata lines are NOT passed to the content parser.
        """
        # --- Stage 1: Isolate Footer and Notes ---
        # Split by footer separator first to isolate the main content block
        footer_parts = re.split(r"^\s*@@@\s*$", content, maxsplit=1, flags=re.MULTILINE)
        main_content_segment = footer_parts[0]
        footer = footer_parts[1].strip() if len(footer_parts) > 1 else None

        # Extract notes from the entire original content block to catch all cases
        notes = self._extract_notes(content)

        # Remove notes from the main content segment to prevent re-parsing
        if notes:
            main_content_segment = re.sub(
                r"<!--\s*notes:\s*.*?\s*-->", "", main_content_segment, flags=re.DOTALL
            )
        # Also remove notes from the footer if they were there
        if footer and notes:
            footer = re.sub(
                r"<!--\s*notes:\s*.*?\s*-->", "", footer, flags=re.DOTALL
            ).strip()

        # --- Stage 2: Extract Title/Subtitle and Finalize Content ---
        # The _extract_title_with_directives method is now responsible for returning
        # ONLY the content that is NOT a title or subtitle.
        title, subtitle, final_slide_content, title_directives, subtitle_directives = (
            self._extract_title_with_directives(main_content_segment)
        )

        # Ensure final content is clean
        final_slide_content = final_slide_content.strip()

        # --- Stage 3: Assemble the Slide Dictionary ---
        slide = {
            "title": title,
            "subtitle": subtitle,
            "content": final_slide_content,
            "footer": footer,
            "notes": notes,
            "background": None,  # Will be parsed from section directives later
            "index": index,
            "object_id": slide_object_id,
            "speaker_notes_object_id": (
                f"{slide_object_id}_notesShape" if notes else None
            ),
            "title_directives": title_directives,
            "subtitle_directives": subtitle_directives,
        }

        logger.debug(
            f"Processed slide {index + 1}: title='{title or 'None'}', "
            f"subtitle='{subtitle or 'None'}', "
            f"content_length={len(slide['content'])}, title_directives={title_directives}, "
            f"subtitle_directives={subtitle_directives}"
        )
        return slide

    def _extract_title_with_directives(
        self, content: str
    ) -> tuple[str | None, str | None, str, dict, dict]:
        """
        Extract title and subtitle with their same-line directives per Rule 1 (Element-Scoped Directives).

        This is a more robust implementation that correctly handles complex slide content
        by iterating through lines, processing titles/subtitles, and then reassembling the
        remaining content.

        Returns:
            Tuple of (title_text, subtitle_text, remaining_content, title_directives, subtitle_directives)
        """
        lines = content.split("\n")
        title_text, subtitle_text = None, None
        title_directives, subtitle_directives = {}, {}
        remaining_lines = list(lines)

        # Find and process ALL H1 Titles (to prevent duplication in content)
        # The first meaningful H1 becomes the slide title, subsequent H1s are consumed to prevent duplication
        found_primary_title = False

        for i, line in enumerate(lines):
            # Regular expression to find H1 markdown syntax at the start of a line
            title_match = re.match(r"^\s*#\s+(.+)$", line)
            if title_match:
                full_title_text = title_match.group(1).strip()

                # Always remove H1 lines from remaining content to prevent duplication
                remaining_lines[i] = ""  # Mark for removal

                # Only use the first meaningful H1 as the slide title
                if not found_primary_title:
                    # Use a helper to parse directives from the line
                    title_text, title_directives = self._parse_text_and_directives(
                        full_title_text
                    )
                    found_primary_title = True

                    # Look for a subtitle only immediately after the title (skip only comments and empty lines)
                    # We should NOT consume H2 headers that are meant to be content
                    for j in range(i + 1, len(lines)):
                        next_line = lines[j].strip()
                        if not next_line:  # Skip empty lines
                            continue

                        # Skip comment lines but continue looking
                        if next_line.startswith("<!--"):
                            continue

                        # Check if this is an H2 that could be a subtitle
                        subtitle_match = re.match(r"^\s*##\s+(.+)$", next_line)
                        if subtitle_match:
                            # Only treat as subtitle if we haven't hit any real content yet
                            # (content between title and potential subtitle invalidates subtitle interpretation)
                            full_subtitle_text = subtitle_match.group(1).strip()
                            subtitle_text, subtitle_directives = (
                                self._parse_text_and_directives(full_subtitle_text)
                            )
                            remaining_lines[j] = ""  # Mark for removal
                            break
                        # If we hit any other content (not comments/empty), stop looking for subtitle
                        # This H2 should be treated as content, not a slide subtitle
                        break

        # If no H1 title was found, check if the slide starts with a single H2 that could be a subtitle
        # Only treat H2 as subtitle if it's the first meaningful content (no other content before it)
        if not title_text:
            for i, line in enumerate(lines):
                stripped_line = line.strip()
                if not stripped_line:  # Skip empty lines
                    continue

                # If we find an H2 as the first non-empty line, treat it as a subtitle
                subtitle_match = re.match(r"^\s*##\s+(.+)$", line)
                if subtitle_match:
                    full_subtitle_text = subtitle_match.group(1).strip()
                    subtitle_text, subtitle_directives = (
                        self._parse_text_and_directives(full_subtitle_text)
                    )
                    remaining_lines[i] = ""  # Mark for removal
                    break
                # If the first non-empty line is not an H2, don't look for subtitles
                # This preserves H2 headers that appear after other content
                break

        # Reconstruct the remaining content
        final_content = "\n".join(line for line in remaining_lines if line is not None)

        return (
            title_text,
            subtitle_text,
            final_content,
            title_directives,
            subtitle_directives,
        )

    def _parse_text_and_directives(self, line_content: str) -> tuple[str, dict]:
        """
        Helper method to parse a line of text for same-line directives.

        Args:
            line_content: The text content of a line (e.g., from a title or subtitle).

        Returns:
            A tuple of (cleaned_text, directives_dict).
        """
        directives = {}
        # Regex to find any number of [key=value] pairs at the end of the string
        directive_pattern = r"\s*((?:\[[^\[\]]+=[^\[\]]*\]\s*)+)$"
        match = re.search(directive_pattern, line_content)

        if match:
            directive_text = match.group(1)
            # The cleaned text is everything before the directives
            cleaned_text = line_content[: match.start()].strip()

            # Parse the found directives
            directive_matches = re.findall(
                r"\[([^=\[\]]+)=([^\[\]]*)\]", directive_text
            )
            for key, value in directive_matches:
                directives[key.strip().lower()] = value.strip()
        else:
            cleaned_text = line_content.strip()

        return cleaned_text, directives

    def _extract_notes(self, content: str) -> str | None:
        """Extract speaker notes from content."""
        notes_pattern = r"<!--\s*notes:\s*(.*?)\s*-->"
        match = re.search(notes_pattern, content, re.DOTALL)
        return match.group(1).strip() if match else None
