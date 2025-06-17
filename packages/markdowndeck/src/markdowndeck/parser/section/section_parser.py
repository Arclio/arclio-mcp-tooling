import logging
import re
import uuid

from markdowndeck.models.slide import Section
from markdowndeck.parser.directive import DirectiveParser
from markdowndeck.parser.errors import GrammarError

logger = logging.getLogger(__name__)


class SectionParser:
    """
    Parse sections within a slide based on explicit fenced block syntax,
    enforcing Grammar V2.0 rules.
    """

    def __init__(self):
        """Initialize the section parser."""
        self.directive_parser = DirectiveParser()
        self.fence_pattern = re.compile(
            r"^\s*:::\s*(?P<type>section|row|column)?(?P<directives>.*?)?$"
        )

    def parse_sections(self, content: str) -> Section:
        """
        Parse slide content into a single root section containing a hierarchy
        of explicitly defined fenced blocks, validating structure along the way.
        """
        # Use a special "root" type to detect content outside any user-defined section.
        root_section = Section(id=f"root-{self._generate_id()}", type="root")
        section_stack: list[Section] = [root_section]
        content_buffer: list[str] = []

        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            match = self.fence_pattern.match(line)

            if match:
                self._flush_content_buffer(content_buffer, section_stack, line_num)
                content_buffer = []

                fence_type = match.group("type")
                directives_str = (match.group("directives") or "").strip()

                if fence_type:  # Opening fence, e.g., `:::section`
                    parent_section = section_stack[-1]
                    self._validate_new_section_context(
                        fence_type, parent_section, line_num
                    )

                    new_section = self._create_new_section(fence_type, directives_str)
                    parent_section.children.append(new_section)
                    section_stack.append(new_section)
                else:  # Closing fence `:::`
                    if len(section_stack) > 1:
                        section_stack.pop()
                    else:
                        raise GrammarError(
                            f"Line {line_num}: Found a closing fence ':::' with no open section to close."
                        )
            else:
                content_buffer.append(line)

        self._flush_content_buffer(content_buffer, section_stack, len(lines))

        if len(section_stack) > 1:
            raise GrammarError(
                f"Found {len(section_stack) - 1} unclosed section(s). Every ':::' block must be closed with a ':::."
            )

        # Check if the root_section itself has raw content, which is illegal.
        if any(
            isinstance(child, str) and child.strip() for child in root_section.children
        ):
            raise GrammarError(
                "Found body content outside of a ':::section' block. All renderable content (text, images, etc.) must be inside a ':::section'."
            )

        root_section.type = "section"
        return root_section

    def _flush_content_buffer(
        self, buffer: list[str], stack: list[Section], line_num: int
    ):
        """
        Flushes the content buffer, splitting it into CommonMark blocks and appending
        each block as a raw string child to the current section.
        """
        if not buffer:
            return

        full_content = "\n".join(buffer)
        if not full_content.strip():
            return

        # Split content by one or more blank lines to get individual markdown blocks
        blocks = re.split(r"\n\s*\n", full_content.strip())

        current_section = stack[-1]

        for block in blocks:
            content_str = block.strip()
            if content_str:
                if current_section.type in ["row", "column"]:
                    raise GrammarError(
                        f"Line {line_num}: Found renderable content directly inside a ':::{current_section.type}' block. This content must be moved inside a ':::section' block."
                    )
                # Add the raw markdown block to the children list.
                # The ContentParser will process this later.
                current_section.children.append(content_str)

    def _validate_new_section_context(
        self, fence_type: str, parent_section: Section, line_num: int
    ):
        """Enforces Grammar V2.0 hierarchy rules."""
        if fence_type == "column" and parent_section.type != "row":
            raise GrammarError(
                f"Line {line_num}: Invalid nesting. A ':::column' block can only be a direct child of a ':::row' block, but found it inside a ':::{parent_section.type}'."
            )

        if fence_type in ["row", "column"] and parent_section.type == "section":
            raise GrammarError(
                f"Line {line_num}: Invalid nesting. A ':::{fence_type}' block cannot be a child of a ':::section' block. Sections can only contain content."
            )

        # REINSTATE: A section cannot directly contain another section.
        # This enforces the use of row/column for layout.
        if fence_type == "section" and parent_section.type == "section":
            raise GrammarError(
                f"Line {line_num}: Invalid nesting. A ':::section' block cannot be a child of a ':::section' block. Use :::row and :::column for layout."
            )

    def _create_new_section(self, fence_type: str, directives_str: str) -> Section:
        """Helper to create a new Section object from fence data."""
        _, directives = self.directive_parser.parse_and_strip_from_text(directives_str)
        return Section(
            id=f"{fence_type}-{self._generate_id()}",
            type=fence_type,
            directives=directives,
            children=[],
        )

    def _generate_id(self) -> str:
        """Generate a unique ID."""
        return uuid.uuid4().hex[:6]
