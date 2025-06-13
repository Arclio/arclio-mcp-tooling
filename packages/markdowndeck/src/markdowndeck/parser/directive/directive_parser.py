import logging
import re
from typing import Any

from markdowndeck.models.slide import Section
from markdowndeck.parser.directive.converters import (
    convert_alignment,
    convert_dimension,
    convert_style,
)

logger = logging.getLogger(__name__)


class DirectiveParser:
    """
    Parse layout directives with comprehensive value conversion.
    Updated to only include supported directives per DIRECTIVES.md.
    """

    def __init__(self):
        """Initialize the directive parser with only supported directives."""
        self.directive_block_pattern = re.compile(r"(\[[^\[\]]+\])")

        # FIXED: Removed unsupported directives per DIRECTIVES.md Section 10.1
        # Removed: cell-align, cell-background, cell-range
        self.directive_types = {
            # Sizing directives
            "width": "dimension",
            "height": "dimension",
            # Alignment directives
            "align": "alignment",
            "valign": "alignment",
            # Visual directives
            "background": "style",
            "color": "style",
            "border": "string",
            "border-radius": "dimension",
            "opacity": "float",
            # Spacing directives
            "padding": "dimension",
            "margin": "dimension",
            "margin-top": "dimension",
            "margin-bottom": "dimension",
            "margin-left": "dimension",
            "margin-right": "dimension",
            "gap": "dimension",
            # Typography directives
            "fontsize": "dimension",
            "font-size": "dimension",
            "font-family": "string",
            "line-spacing": "float",
            "bold": "bool",
            "italic": "bool",
            # Table directives (supported ones only)
            "column-widths": "string",
            # Additional supported directives
            "vertical-align": "alignment",
            "paragraph-spacing": "dimension",
            "indent": "dimension",
            "indent-start": "dimension",
            "list-style": "string",
            "text-decoration": "string",
            "font-weight": "string",
            "box-shadow": "style",
            "transform": "style",
            "transition": "style",
        }

        self.converters = {
            "dimension": convert_dimension,
            "alignment": convert_alignment,
            "style": self._enhanced_convert_style,
            "float": self._safe_float_convert,
            "string": str,
            "bool": lambda v: True,
        }

    def parse_and_strip_from_text(self, text_line: str) -> tuple[str, dict[str, Any]]:
        """Finds and parses all directive blocks in a string, returning the cleaned string and a dict of directives."""
        if not text_line or "[" not in text_line:
            return text_line, {}

        directives = {}

        def replacer(match):
            directive_text = match.group(0)
            parsed = self._parse_directive_text(directive_text)
            directives.update(parsed)
            return ""

        cleaned_text = self.directive_block_pattern.sub(replacer, text_line)
        return cleaned_text.strip(), directives

    def parse_directives(self, section: Section) -> None:
        """Parses leading directive-only lines from a section's content."""
        if not section or not hasattr(section, "content"):
            if section and section.directives is None:
                section.directives = {}
            return

        # FIXED: Handle missing content attribute gracefully
        content = getattr(section, "content", "")
        if not content:
            if section.directives is None:
                section.directives = {}
            return

        lines = content.lstrip("\n\r ").split("\n")
        consumed_line_count = 0
        directives = {}

        for line in lines:
            stripped = line.strip()
            if not stripped:
                consumed_line_count += 1
                continue

            line_directives, remaining_text = self.parse_inline_directives(stripped)
            if line_directives and not remaining_text:
                directives.update(line_directives)
                consumed_line_count += 1
            else:
                break

        if directives:
            merged_directives = (section.directives or {}).copy()
            merged_directives.update(directives)
            section.directives = merged_directives

            # FIXED: Only update content if it exists
            if hasattr(section, "content"):
                section.content = "\n".join(lines[consumed_line_count:]).lstrip()
                self._verify_directive_removal(section)

    def parse_inline_directives(self, text_line: str) -> tuple[dict[str, Any], str]:
        """Parses a line that is expected to be only directives."""
        text_line = text_line.strip()
        if not text_line:
            return {}, ""

        full_directive_pattern = r"^\s*((?:\s*\[[^\[\]]+\]\s*)+)\s*$"
        match = re.match(full_directive_pattern, text_line)
        if not match:
            return {}, text_line
        directive_text = match.group(1)
        directives = self._parse_directive_text(directive_text)
        return directives, ""

    def _parse_directive_text(self, directive_text: str) -> dict[str, Any]:
        """
        Internal helper to parse a string known to contain directives.
        REFACTORED: This is the core fix. It now correctly parses multiple
        space-separated key=value pairs within a single bracket block.
        """
        directives = {}
        # This pattern finds the content within each [...] block
        bracket_content_pattern = re.compile(r"\[([^\[\]]+)\]")

        for content in bracket_content_pattern.findall(directive_text):
            # Split the content by space, but keep quoted values together. A simpler
            # way is to just find all key=value or key pairs.
            pairs = re.findall(
                r'([\w-]+(?:-[\w-]+)*)(?:=([^"\'\s\]]+|"[^"]*"|\'[^\']*\'))?', content
            )
            for key, value in pairs:
                key = key.strip().lower()
                value = (value or "").strip().strip("'\"")

                if key in self.directive_types:
                    directive_type = self.directive_types[key]
                    # If value is empty, it might be a boolean flag
                    if not value and directive_type != "string":
                        directive_type = "bool"

                    converter = self.converters.get(directive_type)
                    if converter:
                        try:
                            converted_value = converter(value)
                            # This is the fix: Style directives are now processed correctly
                            if directive_type == "style":
                                directives.update(
                                    self._process_style_directive_value(
                                        key, converted_value
                                    )
                                )
                            else:
                                directives[key] = converted_value
                        except ValueError as e:
                            logger.warning(
                                f"Could not convert directive '{key}={value}' using {directive_type} converter. Storing as string. Error: {e}"
                            )
                            directives[key] = value
                    else:
                        directives[key] = value or True
                else:
                    # FIXED: Log unsupported directives but don't store them
                    logger.warning(
                        f"Unsupported directive key '{key}' (per DIRECTIVES.md). Ignoring."
                    )
        return directives

    def _enhanced_convert_style(self, value: str) -> tuple[str, Any]:
        return convert_style(value)

    def _safe_float_convert(self, value: str) -> float:
        try:
            return float(value)
        except ValueError:
            return 0.0

    def _process_style_directive_value(
        self, key: str, style_tuple: tuple[str, Any]
    ) -> dict[str, Any]:
        """Process style directive tuples into a clean, unified format."""
        style_type, style_value = style_tuple
        result = {}

        if key == "background":
            if style_type == "url":
                result[key] = {"type": "image", "value": style_value["value"]}
            else:
                result[key] = {"type": "color", "value": style_value}
        elif style_type == "color":
            result[key] = style_value
        else:
            result[key] = style_value

        return result

    def _handle_malformed_directives(self, section: Section, content: str) -> None:
        """Handle and clean up malformed directive patterns."""
        malformed_pattern = r"^\s*(\[[^\[\]]*=[^\[\]]*\]\s*)"
        malformed_match = re.match(malformed_pattern, content)

        if malformed_match:
            bracket_content = malformed_match.group(1).strip()
            if not re.match(r"^\s*\[[^=\[\]]+=[^\[\]]*\]\s*$", bracket_content):
                malformed_text = malformed_match.group(1)
                logger.warning(f"Removing malformed directive: {malformed_text!r}")
                if hasattr(section, "content"):
                    section.content = content[malformed_match.end() :].lstrip()

        if section.directives is None:
            section.directives = {}

    def _verify_directive_removal(self, section: Section) -> None:
        """Verify that all directives have been properly removed from content."""
        if not hasattr(section, "content"):
            return

        if re.match(r"^\s*\[[\w\-]+=", section.content):
            logger.warning(
                f"Potential directives remain in content: {section.content[:50]}"
            )
            section.content = re.sub(
                r"^\s*\[[^\[\]]+=[^\[\]]*\]", "", section.content
            ).lstrip()
