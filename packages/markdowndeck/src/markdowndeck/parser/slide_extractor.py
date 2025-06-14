import logging
import re
import uuid

from markdowndeck.parser.directive import DirectiveParser

logger = logging.getLogger(__name__)


class SlideExtractor:
    """Extract individual slides from markdown content with improved parsing."""

    def __init__(self):
        """Initialize the SlideExtractor with a DirectiveParser instance."""
        self.directive_parser = DirectiveParser()

    def extract_slides(self, markdown: str) -> list[dict]:
        """
        Extract individual slides from markdown content.
        """
        logger.debug("Extracting slides from markdown")
        normalized_content = markdown.replace("\r\n", "\n").replace("\r", "\n")
        slide_parts = re.split(r"^\s*===\s*$", normalized_content, flags=re.MULTILINE)

        slides = []
        for i, slide_content_part in enumerate(slide_parts):
            if not slide_content_part.strip():
                continue
            processed_slide = self._process_slide_content(slide_content_part, i, f"slide_{i}_{uuid.uuid4().hex[:6]}")
            slides.append(processed_slide)
        logger.info(f"Extracted {len(slides)} slides from markdown")
        return slides

    def _process_slide_content(self, content: str, index: int, slide_object_id: str) -> dict:
        """
        Process slide content with robust title, subtitle, and metadata handling.
        """
        content_no_notes, notes = self._extract_notes(content)
        content_no_footer, footer = self._extract_footer(content_no_notes)
        (
            base_directives,
            background,
            content_no_directives,
        ) = self._extract_slide_level_directives(content_no_footer)

        (
            title,
            subtitle,
            final_slide_content,
            title_directives,
            subtitle_directives,
        ) = self._extract_title_and_subtitle(content_no_directives)

        cleaned_footer, footer_directives = self.directive_parser.parse_and_strip_from_text(footer or "")

        return {
            "title": title,
            "subtitle": subtitle,
            "content": final_slide_content.strip(),
            "footer": cleaned_footer,
            "notes": notes,
            "background": background,
            "index": index,
            "object_id": slide_object_id,
            "speaker_notes_object_id": (f"{slide_object_id}_notesShape" if notes else None),
            "base_directives": base_directives,
            "title_directives": title_directives,
            "subtitle_directives": subtitle_directives,
            "footer_directives": footer_directives,
        }

    def _extract_notes(self, content: str) -> tuple[str, str | None]:
        notes_pattern = r"<!--\s*notes:\s*(.*?)-->"
        match = re.search(notes_pattern, content, re.DOTALL)
        if match:
            notes = match.group(1).strip()
            content_without_notes = content.replace(match.group(0), "")
            return content_without_notes, notes
        return content, None

    def _extract_footer(self, content: str) -> tuple[str, str | None]:
        parts = re.split(r"^\s*@@@\s*$", content, maxsplit=1, flags=re.MULTILINE)
        if len(parts) > 1:
            return parts[0], parts[1].strip()
        return content, None

    def _extract_slide_level_directives(self, content: str) -> tuple[dict, dict, str]:
        """FINAL FIX: Robustly consumes all consecutive directive-only lines."""
        lines = content.lstrip().split("\n")
        all_directives = {}
        consumed_lines_count = 0

        for line in lines:
            stripped_line = line.strip()
            if not stripped_line:
                consumed_lines_count += 1
                continue

            # A line is a base directive line if it ONLY contains directives.
            # Check if there's any content left after removing all [...] blocks.
            remaining_text = re.sub(r"\[[^\]]+\]", "", stripped_line).strip()
            if remaining_text:
                break  # This line has content, stop consuming.

            # Parse directives from the line
            _, line_directives = self.directive_parser.parse_and_strip_from_text(stripped_line)
            if line_directives:
                all_directives.update(line_directives)
                consumed_lines_count += 1
            else:  # Should not happen if remaining_text is empty, but as a safeguard.
                break

        background = all_directives.pop("background", None)
        remaining_content = "\n".join(lines[consumed_lines_count:])

        return all_directives, background, remaining_content

    def _extract_title_and_subtitle(self, content: str) -> tuple[str | None, str | None, str, dict, dict]:
        lines = content.strip().split("\n")
        title, subtitle = None, None
        title_directives, subtitle_directives = {}, {}
        consumed_indices = set()

        if lines and lines[0]:
            first_line = lines[0].strip()
            if first_line.startswith("# ") and not first_line.startswith("##"):
                title, title_directives = self.directive_parser.parse_and_strip_from_text(first_line[2:].strip())
                consumed_indices.add(0)

                if len(lines) > 1:
                    second_line = lines[1].strip()
                    if second_line.startswith("## "):
                        subtitle, subtitle_directives = self.directive_parser.parse_and_strip_from_text(
                            second_line[3:].strip()
                        )
                        consumed_indices.add(1)

        remaining_lines = [line for i, line in enumerate(lines) if i not in consumed_indices]
        final_content = "\n".join(remaining_lines)
        return title, subtitle, final_content, title_directives, subtitle_directives
