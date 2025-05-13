"""Extract individual slides from markdown content."""

import logging
import re
import uuid

logger = logging.getLogger(__name__)


class SlideExtractor:
    """Extract individual slides from markdown content."""

    def extract_slides(self, markdown: str) -> list[dict]:
        logger.debug("Extracting slides from markdown")
        normalized_content = markdown.replace("\r\n", "\n").replace("\r", "\n")
        slide_parts = self._split_content_with_code_block_awareness(
            normalized_content, r"^\s*===\s*$"
        )
        slides = []
        for i, slide_content in enumerate(slide_parts):
            slide_content = slide_content.strip()
            if not slide_content:
                continue
            logger.debug(f"Processing slide {i + 1}")
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
        lines = content.split("\n")
        parts = []
        current_part = []
        in_code_block = False
        for line in lines:
            # More robust check for code block delimiters (``` or ~~~)
            stripped_line = line.lstrip()
            is_code_marker = stripped_line.startswith(
                "```"
            ) or stripped_line.startswith("~~~")

            if is_code_marker:
                # Check if it's just the fence or has lang identifier
                fence_part = stripped_line.split(" ", 1)[0]  # Get just the fence part
                if fence_part == "```" or fence_part == "~~~":
                    in_code_block = not in_code_block
                current_part.append(line)
            elif in_code_block:
                # Inside a code block, always add to current part
                current_part.append(line)
            elif re.fullmatch(pattern, line.strip()):
                # Found separator (not inside code block)
                if current_part:
                    parts.append("\n".join(current_part))
                current_part = []
            else:
                # Normal line, not in code block, not a separator
                current_part.append(line)

        if current_part:
            parts.append("\n".join(current_part))
        return parts

    def _process_slide_content(
        self, content: str, index: int, slide_object_id: str
    ) -> dict:
        footer_parts = re.split(r"(?m)^\s*@@@\s*$", content)
        main_content = footer_parts[0]
        footer = footer_parts[1].strip() if len(footer_parts) > 1 else None

        title_match = re.search(r"^#\s+(.+)$", main_content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else None

        if title_match:
            main_content = main_content.replace(title_match.group(0), "", 1)

        notes = self._extract_notes(main_content)
        speaker_notes_placeholder_id = None
        if notes:
            notes_pattern_to_remove = (
                r"<!--\s*notes:\s*(?:.*?)\s*-->"  # Ensure this matches for removal
            )
            main_content = re.sub(
                notes_pattern_to_remove, "", main_content, flags=re.DOTALL
            )
            speaker_notes_placeholder_id = f"{slide_object_id}_notesShape"

        if footer:
            footer_notes = self._extract_notes(footer)
            if footer_notes:
                notes = footer_notes
                speaker_notes_placeholder_id = f"{slide_object_id}_notesShape"
                notes_pattern_to_remove = r"<!--\s*notes:\s*(?:.*?)\s*-->"
                footer = re.sub(
                    notes_pattern_to_remove, "", footer, flags=re.DOTALL
                ).strip()

        background = self._extract_background(main_content)
        if background:
            background_pattern = r"^\s*\[background=([^\]]+)\]\s*\n?"
            main_content = re.sub(
                background_pattern, "", main_content, flags=re.MULTILINE
            )

        return {
            "title": title,
            "content": main_content.strip(),
            "footer": footer,
            "notes": notes,
            "background": background,
            "index": index,
            "object_id": slide_object_id,
            "speaker_notes_object_id": speaker_notes_placeholder_id,
        }

    def _extract_notes(self, content: str) -> str | None:
        # Ensure this pattern is correct and used consistently
        notes_pattern = r"<!--\s*notes:\s*(.*?)\s*-->"
        match = re.search(notes_pattern, content, re.DOTALL)
        return match.group(1).strip() if match else None

    def _extract_background(self, content: str) -> dict | None:
        background_pattern = r"^\s*\[background=([^\]]+)\]"
        match = re.match(background_pattern, content.lstrip())
        if match:
            bg_value = match.group(1).strip()
            if bg_value.startswith("url(") and bg_value.endswith(")"):
                url = bg_value[4:-1].strip("\"'")
                return {"type": "image", "value": url}
            return {"type": "color", "value": bg_value}
        return None
