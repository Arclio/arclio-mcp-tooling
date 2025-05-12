"""Parse sections within a slide with improved directive handling."""

import logging
import re
import uuid

from markdowndeck.models.slide import Section
from markdowndeck.parser.section.content_splitter import (
    ContentSplitter,
)  # Updated import path if necessary

logger = logging.getLogger(__name__)


class SectionParser:
    """Parse sections within a slide with improved directive handling."""

    def __init__(self):
        """Initialize the section parser."""
        self.content_splitter = ContentSplitter()
        # self.section_counter = 0 # Not strictly needed as instance var if IDs are UUID based

    def parse_sections(self, content: str) -> list[Section]:
        """
        Parse slide content into vertical and horizontal sections.

        Args:
            content: Slide content without title/footer

        Returns:
            List of Section model instances
        """
        logger.debug("Parsing slide content into sections using ContentSplitter")

        # Normalize content (mainly line endings) before splitting
        normalized_content = content.replace("\r\n", "\n").replace("\r", "\n").strip()
        if not normalized_content:
            logger.debug("No content to parse into sections")
            return []

        # Log content length to help with debugging
        content_preview = (
            normalized_content[:100] + "..."
            if len(normalized_content) > 100
            else normalized_content
        )
        logger.debug(f"Parsing content ({len(normalized_content)} chars): {content_preview}")

        return self._parse_vertical_sections(normalized_content)

    def _parse_vertical_sections(self, content: str) -> list[Section]:
        """
        Parse content into vertical sections (---), then each vertical section
        into horizontal sections (***).
        """
        vertical_separator = r"^\s*---\s*$"
        vertical_split_result = self.content_splitter.split_by_separator(
            content, vertical_separator
        )
        vertical_parts = vertical_split_result.parts

        # Log how many vertical sections were found
        logger.debug(
            f"Split content into {len(vertical_parts)} vertical parts using '---' separator"
        )

        final_sections = []
        if not vertical_parts:
            if content and not re.fullmatch(vertical_separator + r"\s*", content, re.MULTILINE):
                vertical_parts = [content]
                logger.debug(
                    "No vertical parts found but content exists. Creating a single section."
                )
            else:
                logger.debug("Content only contained separators. No sections created.")
                return []

        for v_idx, v_part_content in enumerate(vertical_parts):
            if not v_part_content.strip():
                logger.debug(f"Vertical part {v_idx + 1} is empty. Skipping.")
                continue

            # CRITICAL FIX: Extract and preserve headers at the beginning of sections
            # This ensures H2/H3 headers are preserved when they start a section
            # Log first few characters for debugging
            v_part_preview = (
                v_part_content[:50] + "..." if len(v_part_content) > 50 else v_part_content
            )
            logger.debug(f"Processing vertical part {v_idx + 1}: {v_part_preview}")

            horizontal_sections = self._parse_horizontal_sections(v_part_content, f"v{v_idx}")

            if len(horizontal_sections) > 1:
                # This vertical part contains multiple horizontal subsections, so it's a "row"
                row_id = f"row-{v_idx}-{self._generate_id()}"
                final_sections.append(
                    Section(
                        type="row",
                        directives={},
                        subsections=horizontal_sections,
                        id=row_id,
                        content=v_part_content,
                        elements=[],
                    )
                )
                logger.debug(
                    f"Added row section {row_id} with {len(horizontal_sections)} horizontal subsections."
                )
            elif horizontal_sections:
                final_sections.append(horizontal_sections[0])
                logger.debug(
                    f"Added single section {horizontal_sections[0].id} (no horizontal splits found)"
                )
            else:
                logger.debug(
                    f"Vertical part {v_idx + 1} produced no horizontal sections. Skipping."
                )

        logger.info(f"Parsed into {len(final_sections)} top-level section structures")
        return final_sections

    def _parse_horizontal_sections(
        self, vertical_part_content: str, v_id_prefix: str
    ) -> list[Section]:
        """
        Parse a given vertical section's content into horizontal sections (***).
        """
        horizontal_separator = r"^\s*\*\*\*\s*$"
        horizontal_split_result = self.content_splitter.split_by_separator(
            vertical_part_content, horizontal_separator
        )
        horizontal_parts = horizontal_split_result.parts

        logger.debug(
            f"Split vertical part into {len(horizontal_parts)} horizontal parts using '***' separator"
        )

        subsections = []
        if not horizontal_parts:
            if vertical_part_content and not re.fullmatch(
                horizontal_separator + r"\s*", vertical_part_content, re.MULTILINE
            ):
                horizontal_parts = [vertical_part_content]
                logger.debug(
                    "No horizontal parts found but content exists. Creating a single horizontal section."
                )
            else:
                logger.debug(
                    "Vertical part only contained separators. No horizontal sections created."
                )
                return []

        for h_idx, h_part_content in enumerate(horizontal_parts):
            if not h_part_content.strip():
                logger.debug(f"Horizontal part {h_idx + 1} is empty. Skipping.")
                continue

            # CRITICAL FIX: Preserve the full content including any headers
            # Log the content for debugging
            h_part_preview = (
                h_part_content[:50] + "..." if len(h_part_content) > 50 else h_part_content
            )
            logger.debug(f"Processing horizontal part {h_idx + 1}: {h_part_preview}")

            subsection_id = f"section-{v_id_prefix}-h{h_idx}-{self._generate_id()}"
            subsections.append(
                Section(
                    type="section",
                    content=h_part_content.strip(),
                    directives={},
                    id=subsection_id,
                    elements=[],
                )
            )
            logger.debug(f"Created horizontal subsection {subsection_id}")
        return subsections

    def _generate_id(self) -> str:
        """Generate a unique ID."""
        return uuid.uuid4().hex[:6]  # Shortened for readability

    def _log_section_hierarchy(self, sections: list[Section], indent: int = 0) -> None:
        """
        Log the section hierarchy for debugging purposes.

        Args:
            sections: List of sections to log
            indent: Current indentation level
        """
        if not sections or indent > 5:  # Prevent infinite recursion
            return

        indent_str = "  " * indent
        for section in sections:
            if section.type == "row":
                logger.debug(
                    f"{indent_str}Row section {section.id} with {len(section.subsections)} subsections"
                )
                self._log_section_hierarchy(section.subsections, indent + 1)
            else:
                content_preview = (
                    section.content[:30] + "..." if len(section.content) > 30 else section.content
                )
                content_preview = content_preview.replace("\n", "\\n")
                logger.debug(f"{indent_str}Section {section.id}: '{content_preview}'")
