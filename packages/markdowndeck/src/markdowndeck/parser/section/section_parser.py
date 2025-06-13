"""Parse sections within a slide with improved directive handling."""

import logging
import re
import uuid

from markdowndeck.models.slide import Section
from markdowndeck.parser.directive import DirectiveParser
from markdowndeck.parser.section.content_splitter import (
    ContentSplitter,
)

logger = logging.getLogger(__name__)


class SectionParser:
    """Parse sections within a slide with improved directive handling."""

    def __init__(self):
        """Initialize the section parser."""
        self.content_splitter = ContentSplitter()
        self.directive_parser = DirectiveParser()

    def parse_sections(self, content: str) -> Section:
        """
        Parse slide content into a single root section containing a hierarchy
        of vertical and horizontal sections.

        Args:
            content: Slide content without title/footer

        Returns:
            A single root Section model instance. Per spec, this is never None.
        """
        logger.debug("Parsing slide content into a root section using ContentSplitter")

        normalized_content = content.replace("\r\n", "\n").replace("\r", "\n").strip()

        # REFACTORED: Removed early `return None` to ensure a root_section is always created.

        content_preview = (
            normalized_content[:100] + "..."
            if len(normalized_content) > 100
            else normalized_content
        )
        logger.debug(
            f"Parsing content ({len(normalized_content)} chars): {content_preview}"
        )

        # The top-level content is parsed into vertical sections.
        top_level_sections = self._parse_vertical_sections(normalized_content)

        # Create a single root section to hold all top-level content sections.
        root_section = Section(
            id=f"root-{self._generate_id()}",
            type="section",
            children=top_level_sections,
            directives={},  # Root section can have its own directives if any are at the very top.
        )
        # The content of the root section is the entire normalized content, which allows
        # root-level directives to be parsed. This is a temporary attribute.
        root_section.content = normalized_content
        self.directive_parser.parse_directives(root_section)
        # The content attribute is cleared by parse_directives, which is desired.

        logger.info(
            f"Created root section '{root_section.id}' with {len(top_level_sections)} top-level children."
        )

        return root_section

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

        logger.debug(
            f"Split content into {len(vertical_parts)} vertical parts using '---' separator"
        )

        final_sections = []
        if not vertical_parts:
            if content and not re.fullmatch(
                vertical_separator + r"\s*", content, re.MULTILINE
            ):
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

            v_part_preview = (
                v_part_content[:50] + "..."
                if len(v_part_content) > 50
                else v_part_content
            )
            logger.debug(f"Processing vertical part {v_idx + 1}: {v_part_preview}")

            horizontal_sections = self._parse_horizontal_sections(
                v_part_content, f"v{v_idx}"
            )

            if len(horizontal_sections) > 1:
                row_id = f"row-{v_idx}-{self._generate_id()}"
                row_section = Section(
                    type="row",
                    directives={},
                    children=horizontal_sections,
                    id=row_id,
                )
                # Attach content to parse directives for the row itself
                row_section.content = v_part_content
                self.directive_parser.parse_directives(row_section)
                final_sections.append(row_section)
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

            subsection_id = f"section-{v_id_prefix}-h{h_idx}-{self._generate_id()}"

            # FIXED: Instantiate Section without `content`, then set it as a temporary attribute.
            temp_section = Section(
                type="section",
                directives={},
                id=subsection_id,
            )
            # This temporary attribute allows the directive parser to read the content.
            temp_section.content = h_part_content.strip()

            self.directive_parser.parse_directives(temp_section)

            subsections.append(temp_section)
            logger.debug(
                f"Created horizontal subsection {subsection_id} with directives: {temp_section.directives}"
            )
        return subsections

    def _generate_id(self) -> str:
        """Generate a unique ID."""
        return uuid.uuid4().hex[:6]
