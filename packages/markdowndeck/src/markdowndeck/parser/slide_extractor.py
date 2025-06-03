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
        Process slide content with improved title handling.

        CRITICAL FIXES:
        - P3: Proper indented title removal
        - Enhanced title directive extraction
        - FIXED: Remove special background extraction to allow normal directive processing
        """
        original_content = content

        # Split by footer separator
        footer_parts = re.split(
            r"^\s*@@@\s*$", original_content, maxsplit=1, flags=re.MULTILINE
        )
        main_content_segment = footer_parts[0]
        footer = footer_parts[1].strip() if len(footer_parts) > 1 else None

        # CRITICAL FIX P3: Enhanced title extraction with indentation support
        title, content_after_title, title_directives = (
            self._extract_title_with_directives(main_content_segment)
        )

        # Extract notes
        notes_from_content = self._extract_notes(content_after_title)
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

        # CRITICAL FIX: Remove special background extraction - let it be processed as normal directive
        # This allows background directives to work alongside other directives like [background=black][color=lime]
        # background = self._extract_background(content_after_title)
        # if background:
        #     content_after_title = re.sub(
        #         r"^\s*\[background=([^\]]+)\]\s*\n?",
        #         "",
        #         content_after_title,
        #         count=1,
        #         flags=re.MULTILINE,
        #     )

        # Remove all notes from content
        content_after_title = re.sub(
            r"<!--\s*notes:\s*.*?\s*-->", "", content_after_title, flags=re.DOTALL
        )

        final_slide_content = content_after_title.strip()

        slide = {
            "title": title,
            "content": final_slide_content,
            "footer": footer,
            "notes": final_notes,
            "background": None,  # Let background be handled as regular directive
            "index": index,
            "object_id": slide_object_id,
            "speaker_notes_object_id": (
                f"{slide_object_id}_notesShape" if final_notes else None
            ),
            "title_directives": title_directives,
        }

        logger.debug(
            f"Processed slide {index + 1}: title='{title or 'None'}', "
            f"content_length={len(slide['content'])}, directives={title_directives}"
        )
        return slide

    def _extract_title_with_directives(
        self, content: str
    ) -> tuple[str | None, str, dict]:
        """
        Extract title and directives with improved indentation support.

        CRITICAL FIXES:
        - P3: Support for indented titles
        - Enhanced title directive extraction with proper color directive structure
        """
        # CRITICAL FIX P3: Pattern now supports leading whitespace
        title_match = re.search(r"^\s*#\s+(.+)$", content.lstrip(), re.MULTILINE)

        if not title_match:
            return None, content, {}

        full_title_text = title_match.group(1).strip()
        title_directives = {}

        # Extract directives from title using regex (original logic but improved)
        directive_pattern = r"^\s*(\s*\[[^\[\]]+=[^\[\]]*\]\s*)+"
        title_directive_match = re.match(directive_pattern, full_title_text)

        clean_title = full_title_text
        if title_directive_match:
            directive_text = title_directive_match.group(0)
            clean_title = full_title_text[len(directive_text) :].strip()

            # Parse directives with proper structure
            directive_matches = re.findall(
                r"\[([^=\[\]]+)=([^\[\]]*)\]", directive_text
            )
            for key, value in directive_matches:
                key = key.strip().lower()
                value = value.strip()

                # Process common directive types with proper structure
                if key == "align":
                    title_directives[key] = value.lower()
                elif key == "fontsize":
                    try:
                        title_directives[key] = float(value)
                    except ValueError:
                        logger.warning(f"Invalid fontsize in title: {value}")
                elif key == "color":
                    # CRITICAL FIX: Use proper color directive structure
                    title_directives[key] = {"type": "named", "value": value}
                else:
                    title_directives[key] = value

        # CRITICAL FIX P3: Enhanced title removal with indentation support
        if title_match:
            # Create pattern that matches the original title line with any indentation
            escaped_title = re.escape(full_title_text)
            title_removal_pattern = rf"^\s*#\s+{escaped_title}\s*(\n|$)"

            content_after_title = re.sub(
                title_removal_pattern, "", content, count=1, flags=re.MULTILINE
            )

            # Verify removal worked
            if content_after_title == content:
                logger.warning(
                    f"Title removal may have failed for: {full_title_text[:50]}"
                )

            return clean_title, content_after_title, title_directives

        return None, content, {}

    def _extract_notes(self, content: str) -> str | None:
        """Extract speaker notes from content."""
        notes_pattern = r"<!--\s*notes:\s*(.*?)\s*-->"
        match = re.search(notes_pattern, content, re.DOTALL)
        return match.group(1).strip() if match else None

    def _extract_background(self, content: str) -> dict | None:
        """Extract background directive from content."""
        background_pattern = r"^\s*\[background=([^\]]+)\]"
        match = re.match(background_pattern, content)

        if match:
            bg_value = match.group(1).strip()
            if bg_value.startswith("url(") and bg_value.endswith(")"):
                try:
                    url = bg_value[4:-1].strip("\"'")
                    from urllib.parse import urlparse

                    parsed_url = urlparse(url)
                    if not all([parsed_url.scheme, parsed_url.netloc]):
                        logger.warning(f"Invalid background image URL: {url}")
                        return None
                    return {"type": "image", "value": url}
                except Exception as e:
                    logger.warning(f"Error parsing background URL '{bg_value}': {e}")
                    return None
            return {"type": "color", "value": bg_value}
        return None
