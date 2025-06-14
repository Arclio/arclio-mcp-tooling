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
        self.directive_types = {
            "width": "dimension",
            "height": "dimension",
            "align": "alignment",
            "valign": "alignment",
            "background": "style",
            "color": "style",
            "border": "string",
            "border-radius": "dimension",
            "opacity": "float",
            "padding": "dimension",
            "margin": "dimension",
            "margin-top": "dimension",
            "margin-bottom": "dimension",
            "margin-left": "dimension",
            "margin-right": "dimension",
            "gap": "dimension",
            "fontsize": "dimension",
            "font-size": "dimension",
            "font-family": "string",
            "line-spacing": "float",
            "bold": "bool",
            "italic": "bool",
            "column-widths": "string",
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
        if not section or not hasattr(section, "content") or not section.content:
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
        bracket_content_pattern = re.compile(r"\[([^\[\]]+)\]")
        for content in bracket_content_pattern.findall(directive_text):
            pairs = re.findall(r'([\w-]+(?:-[\w-]+)*)(?:=([^"\'\s\]]+|"[^"]*"|\'[^\']*\'))?', content)
            for key, value in pairs:
                key = key.strip().lower()
                value = (value or "").strip().strip("'\"")
                if key in self.directive_types:
                    directive_type = self.directive_types[key]
                    if not value and directive_type != "string":
                        directive_type = "bool"
                    converter = self.converters.get(directive_type)
                    if converter:
                        try:
                            converted_value = converter(value)
                            if directive_type == "style":
                                directives.update(self._process_style_directive_value(key, converted_value))
                            else:
                                directives[key] = converted_value
                        except ValueError as e:
                            logger.warning(f"Could not convert directive '{key}={value}': {e}")
                            directives[key] = value
                    else:
                        directives[key] = value or True
                else:
                    logger.warning(f"Unsupported directive key '{key}'. Ignoring.")
        return directives

    def _enhanced_convert_style(self, value: str) -> tuple[str, Any]:
        return convert_style(value)

    def _safe_float_convert(self, value: str) -> float:
        try:
            return float(value)
        except ValueError:
            return 0.0

    def _process_style_directive_value(self, key: str, style_tuple: tuple[str, Any]) -> dict[str, Any]:
        """Process style directive tuples into a clean, unified format."""
        # REFACTORED: Consistently wrap color/background values for a standard format.
        # MAINTAINS: Support for URL-based backgrounds and other style types.
        # JUSTIFICATION: The previous implementation was inconsistent, causing assertion errors. This
        # version applies a standard wrapper to all color-based directives ('background', 'color'),
        # resolving the test failures.
        style_type, style_value = style_tuple
        result = {}

        if key in ["background", "color"]:
            if style_type == "url":  # Specific to background
                result[key] = {"type": "image", "value": style_value["value"]}
            else:  # It's a color for either background or color
                result[key] = {"type": "color", "value": style_value}
        else:
            # For other style types like 'box-shadow', 'transform'
            result[key] = style_value
        return result
