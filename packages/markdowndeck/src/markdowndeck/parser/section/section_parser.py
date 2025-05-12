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
            return []

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

        final_sections = []
        if not vertical_parts:  # Handle case where content might have been only a separator
            if content and not re.fullmatch(
                vertical_separator + r"\s*", content, re.MULTILINE
            ):  # Original content was not just separator(s)
                # If splitting resulted in no parts but there was content, treat as one section
                vertical_parts = [content]
            else:
                return []

        for v_idx, v_part_content in enumerate(vertical_parts):
            if not v_part_content.strip():  # Should already be stripped by splitter
                continue

            logger.debug(f"Processing vertical part {v_idx + 1}")
            horizontal_sections = self._parse_horizontal_sections(v_part_content, f"v{v_idx}")

            if len(horizontal_sections) > 1:
                # This vertical part contains multiple horizontal subsections, so it's a "row"
                row_id = f"row-{v_idx}-{self._generate_id()}"
                # The "content" of the row itself could be seen as the joined content of its children,
                # or the original v_part_content. Storing v_part_content is safer for directive parsing.
                final_sections.append(
                    Section(
                        type="row",
                        directives={},  # Directives for the row itself will be parsed later
                        subsections=horizontal_sections,
                        id=row_id,
                        content=v_part_content,  # Store the original content of the vertical part for directive parsing
                        elements=[],  # Initialize empty elements list
                    )
                )
                logger.debug(
                    f"Added row section {row_id} with {len(horizontal_sections)} subsections."
                )
            elif horizontal_sections:  # Exactly one horizontal section (i.e., no *** split)
                final_sections.append(horizontal_sections[0])  # Promote it to a main section

        logger.info(f"Parsed into {len(final_sections)} top-level section structures.")
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

        subsections = []
        if not horizontal_parts:
            if vertical_part_content and not re.fullmatch(
                horizontal_separator + r"\s*", vertical_part_content, re.MULTILINE
            ):
                horizontal_parts = [vertical_part_content]
            else:
                return []

        for h_idx, h_part_content in enumerate(horizontal_parts):
            if not h_part_content.strip():
                continue
            subsection_id = f"section-{v_id_prefix}-h{h_idx}-{self._generate_id()}"
            subsections.append(
                Section(
                    type="section",  # Individual horizontal parts are basic sections
                    content=h_part_content.strip(),
                    directives={},
                    id=subsection_id,
                    elements=[],  # Initialize empty elements list
                )
            )
            logger.debug(f"Created horizontal subsection {subsection_id}")
        return subsections

    def _generate_id(self) -> str:
        """Generate a unique ID."""
        return uuid.uuid4().hex[:6]  # Shortened for readability
