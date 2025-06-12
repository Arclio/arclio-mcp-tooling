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

    ENHANCEMENTS:
    - P8: Enhanced CSS value parsing
    - Improved directive detection and validation
    - Better error handling and recovery
    """

    def __init__(self):
        """Initialize the directive parser with enhanced type support."""
        self.directive_block_pattern = re.compile(r"(\[[^\[\]]+\])")

        self.directive_types = {
            "width": "dimension",
            "height": "dimension",
            "align": "alignment",
            "valign": "alignment",
            "background": "style",
            "padding": "dimension",
            "margin": "dimension",
            "margin-top": "dimension",
            "margin-bottom": "dimension",
            "margin-left": "dimension",
            "margin-right": "dimension",
            "color": "style",
            "fontsize": "dimension",
            "font-size": "dimension",
            "opacity": "float",
            "border": "string",
            "border-radius": "dimension",
            "border-position": "string",
            "line-spacing": "float",
            "cell-align": "alignment",
            "cell-background": "style",
            "cell-range": "string",
            "vertical-align": "alignment",
            "paragraph-spacing": "dimension",
            "indent": "dimension",
            "indent-start": "dimension",
            "font-family": "string",
            "list-style": "string",
            "text-decoration": "string",
            "font-weight": "string",
            "box-shadow": "style",
            "transform": "style",
            "transition": "style",
            "gap": "dimension",
            "bold": "bool",
            "italic": "bool",
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
        if not section or not section.content:
            if section and section.directives is None:
                section.directives = {}
            return

        lines = section.content.lstrip("\n\r ").split("\n")
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
        """Internal helper to parse a string known to contain directives."""
        directives = {}
        # This pattern finds the content within each [...] block
        bracket_content_pattern = re.compile(r"\[([^\[\]]+)\]")
        # This pattern finds individual key=value or key pairs within a string.
        pair_pattern = re.compile(r'([\w-]+)(?:=([^"\'\s\]]+|"[^"]*"|\'[^\']*\'))?')

        for content in bracket_content_pattern.findall(directive_text):
            for key, value in pair_pattern.findall(content):
                key = key.strip().lower()
                value = value.strip().strip("'\"") if value else ""

                if key in self.directive_types:
                    directive_type = self.directive_types[key]
                    if not value and directive_type != "string":
                        directive_type = "bool"

                    converter = self.converters.get(directive_type)
                    if converter:
                        try:
                            converted_value = converter(value)
                            if directive_type == "style" and isinstance(
                                converted_value, tuple
                            ):
                                directives.update(
                                    self._process_style_directive_value(
                                        key, converted_value
                                    )
                                )
                            else:
                                directives[key] = converted_value
                        except ValueError:
                            logger.warning(
                                f"Could not convert directive '{key}={value}' using {directive_type} converter. Storing as string."
                            )
                            directives[key] = value
                    else:
                        directives[key] = value or True
                else:
                    logger.warning(f"Unknown directive key '{key}'. Storing as is.")
                    directives[key] = value or True
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
        """Process style directive tuples into clean format."""
        style_type, style_value = style_tuple
        result = {}

        if style_type == "color":
            result[key] = style_value
        elif style_type == "url":
            if key == "background":
                result["background_type"] = "image"
                result["background_image_url"] = style_value["value"]
            else:
                result[f"{key}_url"] = style_value["value"]
        elif style_type == "border":
            result[key] = style_value
        elif style_type == "border_style":
            result[key] = {"style": style_value}
        elif (
            style_type == "shadow"
            or style_type == "transform"
            or style_type == "animation"
            or style_type == "gradient"
        ):
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
                section.content = content[malformed_match.end() :].lstrip()

        if section.directives is None:
            section.directives = {}

    def _verify_directive_removal(self, section: Section) -> None:
        """Verify that all directives have been properly removed from content."""
        if re.match(r"^\s*\[[\w\-]+=", section.content):
            logger.warning(
                f"Potential directives remain in content: {section.content[:50]}"
            )
            section.content = re.sub(
                r"^\s*\[[^\[\]]+=[^\[\]]*\]", "", section.content
            ).lstrip()
