import logging
import re

logger = logging.getLogger(__name__)


class SectionParser:
    """Parse sections within a slide."""

    def parse_sections(self, content: str) -> list[dict]:
        """
        Parse slide content into vertical and horizontal sections.

        Args:
            content: Slide content without title/footer

        Returns:
            List of section dictionaries
        """
        logger.debug("Parsing slide content into sections")

        # Check if content has horizontal separators (***) and no vertical separators (---)
        # If so, treat the whole content as a row with subsections
        if "***" in content and "---" not in content:
            horizontal_parts = self._split_content_by_pattern(content, r"(?m)^\s*\*\*\*\s*$")
            if len(horizontal_parts) > 1:
                # Create a row with subsections
                subsections = []
                for h_index, h_part in enumerate(horizontal_parts):
                    h_part = h_part.strip()
                    if not h_part:
                        continue

                    subsection = {
                        "type": "section",
                        "content": h_part,
                        "directives": {},
                        "id": f"section-0-{h_index}",
                    }
                    subsections.append(subsection)
                    logger.debug(f"Added subsection: {subsection['id']}")

                # Create the row section
                row_section = {
                    "type": "row",
                    "directives": {},
                    "subsections": subsections,
                    "id": "row-0",
                    "content": content,  # Store the original content
                }

                logger.debug(f"Created row section with {len(subsections)} subsections")
                return [row_section]

        # If we get here, use the normal vertical+horizontal parsing
        return self._parse_mixed_sections(content)

    def _parse_mixed_sections(self, content: str) -> list[dict]:
        """
        Parse content with a mix of vertical and horizontal sections.

        Args:
            content: Slide content

        Returns:
            List of section dictionaries
        """
        # Split into vertical sections
        vertical_parts = self._split_content_by_pattern(content, r"(?m)^\s*---\s*$")

        sections = []
        for v_index, v_part in enumerate(vertical_parts):
            v_part = v_part.strip()
            if not v_part:
                continue

            logger.debug(f"Processing vertical section {v_index + 1}")

            # Split into horizontal sections
            horizontal_parts = self._split_content_by_pattern(v_part, r"(?m)^\s*\*\*\*\s*$")

            if len(horizontal_parts) == 1:
                # No horizontal splitting, single section
                section = {
                    "type": "section",
                    "content": horizontal_parts[0].strip(),
                    "directives": {},
                    "id": f"section-{v_index}",
                }
                sections.append(section)
                logger.debug(f"Added single section: {section['id']}")
            else:
                # Horizontal row with subsections
                subsections = []
                for h_index, h_part in enumerate(horizontal_parts):
                    h_part = h_part.strip()
                    if not h_part:
                        continue

                    subsection = {
                        "type": "section",
                        "content": h_part,
                        "directives": {},
                        "id": f"section-{v_index}-{h_index}",
                    }
                    subsections.append(subsection)
                    logger.debug(f"Added subsection: {subsection['id']}")

                # Create the row section
                section = {
                    "type": "row",
                    "directives": {},
                    "subsections": subsections,
                    "id": f"row-{v_index}",
                    "content": v_part,  # Store the original content
                }
                sections.append(section)
                logger.debug(
                    f"Added row section with {len(subsections)} subsections: {section['id']}"
                )

        logger.info(f"Parsed {len(sections)} top-level sections")
        return sections

    def _split_content_by_pattern(self, content: str, pattern: str) -> list[str]:
        """
        Split content using a regex pattern.

        Args:
            content: Content to split
            pattern: Regex pattern to use

        Returns:
            List of content parts
        """
        parts = re.split(pattern, content)
        return [part for part in parts if part.strip()]

    def extract_content_without_directives(self, section: dict) -> str:
        """
        Extract section content without directives.

        Args:
            section: Section dictionary

        Returns:
            Content with directives removed
        """
        content = section.get("content", "")

        # Remove directives
        directive_pattern = r"^\s*(\[.+?\])+\s*"
        return re.sub(directive_pattern, "", content, count=1).strip()
