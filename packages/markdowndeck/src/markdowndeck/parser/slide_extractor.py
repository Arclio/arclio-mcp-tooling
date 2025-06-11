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
        slide_parts = self._split_content_with_code_block_awareness(
            normalized_content, r"^\s*===\s*$"
        )
        logger.debug(f"Initial slide part count: {len(slide_parts)}")
        slides = []
        for i, slide_content_part in enumerate(slide_parts):
            if not slide_content_part.strip():
                continue
            stripped_content = slide_content_part.strip()
            content_without_separators = re.sub(
                r"^\s*---\s*$|^\s*\*\*\*\s*$", "", stripped_content, flags=re.MULTILINE
            )
            if not content_without_separators.strip():
                continue
            processed_slide = self._process_slide_content(
                slide_content_part, i, f"slide_{i}_{uuid.uuid4().hex[:6]}"
            )
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
        lines = content.split("\n")
        parts = []
        current_part_lines = []
        in_code_block = False
        current_fence = None
        fence_patterns = ["```", "~~~", "````"]
        try:
            separator_re = re.compile(pattern)
        except re.error as e:
            logger.error(f"Invalid regex pattern '{pattern}': {e}")
            return [content] if content.strip() else []
        for _line_idx, line in enumerate(lines):
            stripped_line = line.strip()
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
                elif potential_fence == current_fence:
                    in_code_block = False
                    current_fence = None
            if separator_re.match(line) and not in_code_block:
                if current_part_lines:
                    parts.append("\n".join(current_part_lines))
                current_part_lines = []
                continue
            current_part_lines.append(line)
        if current_part_lines:
            parts.append("\n".join(current_part_lines))
        return parts

    def _process_slide_content(
        self, content: str, index: int, slide_object_id: str
    ) -> dict:
        """
        Process slide content with robust title, subtitle, and metadata handling.
        """
        footer_parts = re.split(r"^\s*@@@\s*$", content, maxsplit=1, flags=re.MULTILINE)
        main_content_segment = footer_parts[0]
        footer = footer_parts[1].strip() if len(footer_parts) > 1 else None
        notes = self._extract_notes(content)

        if notes:
            main_content_segment = re.sub(
                r"<!--\s*notes:\s*.*?\s*-->", "", main_content_segment, flags=re.DOTALL
            )
        if footer and notes:
            footer = re.sub(
                r"<!--\s*notes:\s*.*?\s*-->", "", footer, flags=re.DOTALL
            ).strip()

        # FIXED: Correctly parse slide-level directives (like background).
        slide_level_directives, main_content_segment = (
            self._extract_slide_level_directives(main_content_segment)
        )
        background = slide_level_directives.get("background")

        title, subtitle, final_slide_content, title_directives, subtitle_directives = (
            self._extract_title_with_directives(main_content_segment)
        )
        final_slide_content = final_slide_content.strip()

        slide = {
            "title": title,
            "subtitle": subtitle,
            "content": final_slide_content,
            "footer": footer,
            "notes": notes,
            "background": background,
            "index": index,
            "object_id": slide_object_id,
            "speaker_notes_object_id": (
                f"{slide_object_id}_notesShape" if notes else None
            ),
            "title_directives": title_directives,
            "subtitle_directives": subtitle_directives,
        }

        logger.debug(f"Processed slide {index + 1}: title='{title or 'None'}'")
        return slide

    def _extract_slide_level_directives(self, content: str) -> tuple[dict, str]:
        """Extracts slide-level directives from the top of the content block."""
        lines = content.lstrip().split("\n")
        directives = {}
        consumed_lines = []
        content_started = False

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith("<!--"):
                if not content_started:
                    consumed_lines.append(i)
                continue

            match = re.match(r"^\[(\w+)=(.+)\]$", stripped)
            if match and not content_started:
                key = match.group(1).lower()
                value = match.group(2).strip()
                # ONLY consume truly slide-level directives like background
                if key == "background":
                    if value.lower().startswith("url("):
                        url = value[4:-1].strip("'\"")
                        directives["background"] = {"type": "image", "value": url}
                    else:
                        directives["background"] = {"type": "color", "value": value}
                    consumed_lines.append(i)
                else:
                    # Non-slide-level directive: stop processing and leave for section parser
                    content_started = True
                    break
            else:
                content_started = True
                break

        # Reconstruct remaining content, excluding only consumed slide-level directive lines
        remaining_lines = []
        for i, line in enumerate(lines):
            if i not in consumed_lines:
                remaining_lines.append(line)

        remaining_content = "\n".join(remaining_lines)
        return directives, remaining_content

    def _extract_title_with_directives(
        self, content: str
    ) -> tuple[str | None, str | None, str, dict, dict]:
        lines = content.split("\n")
        title_text, subtitle_text = None, None
        title_directives, subtitle_directives = {}, {}

        title_line_index = -1
        subtitle_line_index = -1
        all_h1_indices = []  # Track ALL H1 lines to remove them

        # Find the first non-empty line
        first_content_line_index = -1
        for i, line in enumerate(lines):
            if line.strip():
                first_content_line_index = i
                break

        # Find ALL H1 lines (for removal) and identify title
        for i, line in enumerate(lines):
            stripped_line = line.strip()
            if stripped_line.startswith("# "):
                all_h1_indices.append(i)
                # Only use the FIRST H1 as the title
                if title_line_index == -1:
                    title_line_index = i
                    title_text, title_directives = self._parse_text_and_directives(
                        stripped_line[2:].strip()
                    )

        # Check if the first content line is a subtitle (if no title found)
        if title_line_index == -1 and first_content_line_index != -1:
            first_line = lines[first_content_line_index].strip()
            if first_line.startswith("## "):
                # Handle standalone subtitle (without title)
                subtitle_line_index = first_content_line_index
                subtitle_text, subtitle_directives = self._parse_text_and_directives(
                    first_line[3:].strip()
                )

        # Look for an immediately following subtitle (if we have a title)
        if title_line_index != -1:
            next_content_line_index = -1
            for i in range(title_line_index + 1, len(lines)):
                if lines[i].strip():
                    next_content_line_index = i
                    break

            if next_content_line_index != -1:
                next_line = lines[next_content_line_index].strip()
                if next_line.startswith("## "):
                    subtitle_line_index = next_content_line_index
                    subtitle_text, subtitle_directives = (
                        self._parse_text_and_directives(next_line[3:].strip())
                    )

        # Reconstruct remaining content by removing ALL H1 lines and the subtitle line
        consumed_indices = set(all_h1_indices)
        if subtitle_line_index != -1:
            consumed_indices.add(subtitle_line_index)

        remaining_lines = []
        for i, line in enumerate(lines):
            if i not in consumed_indices:
                remaining_lines.append(line)

        final_content = "\n".join(remaining_lines)

        return (
            title_text,
            subtitle_text,
            final_content,
            title_directives,
            subtitle_directives,
        )

    def _parse_text_and_directives(self, line_content: str) -> tuple[str, dict]:
        # ENHANCED: Use the centralized DirectiveParser for consistent logic.
        directives = {}
        # This regex finds directives at the end of the string.
        directive_pattern = r"\s*((?:\[[^\[\]]+=[^\[\]]*\]\s*)+)$"
        match = re.search(directive_pattern, line_content)

        if match:
            directive_text = match.group(1)
            # The cleaned text is everything before the directive match.
            cleaned_text = line_content[: match.start()].strip()
            # Use the injected directive_parser to parse the text.
            directives, _ = self.directive_parser.parse_inline_directives(
                directive_text
            )
        else:
            cleaned_text = line_content.strip()

        return cleaned_text, directives

    def _extract_notes(self, content: str) -> str | None:
        notes_pattern = r"<!--\s*notes:\s*(.*?)\s*-->"
        match = re.search(notes_pattern, content, re.DOTALL)
        return match.group(1).strip() if match else None
