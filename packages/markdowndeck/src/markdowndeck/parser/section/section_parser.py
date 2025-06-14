import logging
import re
import uuid

from markdowndeck.models.slide import Section
from markdowndeck.parser.directive import DirectiveParser

logger = logging.getLogger(__name__)


class SectionParser:
    """Parse sections within a slide based on explicit fenced block syntax."""

    def __init__(self):
        """Initialize the section parser."""
        self.directive_parser = DirectiveParser()
        self.fence_pattern = re.compile(
            r"^\s*:::\s*(?P<type>section|row|column)?(?P<directives>.*?)?$"
        )

    def parse_sections(self, content: str) -> Section:
        """
        Parse slide content into a single root section containing a hierarchy
        of explicitly defined fenced blocks.
        """
        root_section = Section(id=f"root-{self._generate_id()}", type="section")
        section_stack: list[Section] = [root_section]
        content_buffer: list[str] = []

        lines = content.split("\n")
        for line in lines:
            match = self.fence_pattern.match(line)

            if match:
                self._flush_content_buffer(content_buffer, section_stack)
                content_buffer = []

                fence_type = match.group("type")
                directives_str = (match.group("directives") or "").strip()

                if fence_type:  # Opening fence
                    new_section = self._create_new_section(fence_type, directives_str)
                    section_stack[-1].children.append(new_section)
                    section_stack.append(new_section)
                else:  # Closing fence :::
                    if len(section_stack) > 1:
                        section_stack.pop()
                    else:
                        logger.warning(
                            "Found a closing fence ':::' with no open section to close."
                        )
            else:
                content_buffer.append(line)

        self._flush_content_buffer(content_buffer, section_stack)

        if len(section_stack) > 1:
            logger.warning(
                f"Found {len(section_stack) - 1} unclosed section(s). Auto-closing."
            )

        return root_section

    def _flush_content_buffer(self, buffer: list[str], stack: list[Section]):
        """Appends the content buffer to the current section on the stack."""
        if buffer and stack:
            content_str = "\n".join(buffer).strip()
            if content_str:
                current_section = stack[-1]
                current_section.content = (
                    (current_section.content or "") + "\n" + content_str
                ).strip()

    def _create_new_section(self, fence_type: str, directives_str: str) -> Section:
        """Helper to create a new Section object from fence data."""
        _, directives = self.directive_parser.parse_and_strip_from_text(directives_str)
        section_type = "section" if fence_type == "column" else fence_type

        if fence_type == "column":
            directives["_is_column"] = True

        return Section(
            id=f"{section_type}-{self._generate_id()}",
            type=section_type,
            directives=directives,
            children=[],
        )

    def _generate_id(self) -> str:
        """Generate a unique ID."""
        return uuid.uuid4().hex[:6]
