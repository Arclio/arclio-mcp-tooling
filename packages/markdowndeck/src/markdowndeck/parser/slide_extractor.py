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
            # FIXED: Ignore empty parts that can result from re.split, preventing empty slides.
            if not slide_content_part.strip():
                continue
            processed_slide = self._process_slide_content(
                slide_content_part, i, f"slide_{i}_{uuid.uuid4().hex[:6]}"
            )
            slides.append(processed_slide)
        logger.info(f"Extracted {len(slides)} slides from markdown")
        return slides

    def _process_slide_content(
        self, content: str, index: int, slide_object_id: str
    ) -> dict:
        """
        Process slide content with robust meta-element parsing that handles blank lines.
        Implements the new iterative approach that properly separates Meta Zone from Body Zone.
        """
        # 1. First, handle notes and footers as they have distinct separators.
        content_no_notes, notes = self._extract_notes(content)
        content_no_footer, footer = self._extract_footer(content_no_notes)

        # 2. Now, process the remaining content line-by-line for meta-elements.
        lines = content_no_footer.strip().split("\n")

        title, subtitle = None, None
        title_directives, subtitle_directives = {}, {}
        base_directives = {}

        body_content_lines = []
        consumed_line_indices = set()

        # --- Iteration Pass 1: Find Title (outside code blocks only) ---
        in_code_block = False
        for i, line in enumerate(lines):
            stripped_line = line.strip()

            # Track code block boundaries
            if stripped_line.startswith("```") or stripped_line.startswith("~~~"):
                in_code_block = not in_code_block
                continue

            # Only extract titles when NOT inside a code block
            if (
                not in_code_block
                and stripped_line.startswith("# ")
                and not stripped_line.startswith("##")
            ):
                title, title_directives = (
                    self.directive_parser.parse_and_strip_from_text(stripped_line[2:])
                )
                consumed_line_indices.add(i)
                # Find the subtitle ONLY immediately after the title (allowing for blank lines)
                for j in range(i + 1, len(lines)):
                    if not lines[j].strip():  # Skip blank lines
                        consumed_line_indices.add(j)
                        continue
                    if lines[j].strip().startswith("## "):
                        subtitle, subtitle_directives = (
                            self.directive_parser.parse_and_strip_from_text(
                                lines[j].strip()[3:]
                            )
                        )
                        consumed_line_indices.add(j)
                    break  # Stop looking for a subtitle after the first non-blank line
                break  # Stop looking for a title after the first one is found

        # --- Iteration Pass 2: Find Base Directives and Body Content ---
        for i, line in enumerate(lines):
            if i in consumed_line_indices:
                continue

            stripped_line = line.strip()
            if not stripped_line:  # Skip blank lines between elements
                continue

            # Check if the line consists ONLY of directives
            remaining_text, line_directives = (
                self.directive_parser.parse_and_strip_from_text(stripped_line)
            )
            if not remaining_text.strip() and line_directives:
                base_directives.update(line_directives)
                consumed_line_indices.add(i)
            else:
                # If it's not a consumed meta-element or a base directive, it must be body content
                body_content_lines.append(line)

        final_body_content = "\n".join(body_content_lines)

        # 3. Extract background from base directives and process footer
        background = base_directives.pop("background", None)
        cleaned_footer, footer_directives = (
            self.directive_parser.parse_and_strip_from_text(footer or "")
        )

        return {
            "title": title,
            "subtitle": subtitle,
            "content": final_body_content.strip(),
            "footer": cleaned_footer,
            "notes": notes,
            "background": background,
            "index": index,
            "object_id": slide_object_id,
            "speaker_notes_object_id": (
                f"{slide_object_id}_notesShape" if notes else None
            ),
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
