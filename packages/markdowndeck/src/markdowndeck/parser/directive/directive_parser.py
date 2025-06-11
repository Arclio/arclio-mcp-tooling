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
            # FIXED: Added 'gap' as a dimension type.
            "gap": "dimension",
        }

        self.converters = {
            "dimension": convert_dimension,
            "alignment": convert_alignment,
            "style": self._enhanced_convert_style,
            "float": self._safe_float_convert,
            "string": str,
        }

        # Enhanced value converters
        self.converters = {
            "dimension": convert_dimension,
            "alignment": convert_alignment,
            "style": self._enhanced_convert_style,  # Use enhanced version
            "float": self._safe_float_convert,
            "string": str,
        }

    def parse_directives(self, section: Section) -> None:
        if not section or not section.content:
            if section and section.directives is None:
                section.directives = {}
            return
        content = section.content.lstrip("\n\r ")
        directive_block_pattern = r"^\s*((?:\[[^\[\]]+=[^\[\]]*\]\s*)+)"
        match = re.match(directive_block_pattern, content)
        if not match:
            self._handle_malformed_directives(section, content)
            return
        directive_text = match.group(1).strip()
        remaining_content = content[match.end(0) :]
        directives = self._parse_directive_text(directive_text)
        merged_directives = (section.directives or {}).copy()
        merged_directives.update(directives)
        section.directives = merged_directives
        section.content = remaining_content.lstrip()
        self._verify_directive_removal(section)

    def parse_inline_directives(self, text_line: str) -> tuple[dict[str, Any], str]:
        text_line = text_line.strip()
        if not text_line:
            return {}, ""
        full_directive_pattern = r"^\s*((?:\s*\[[^\[\]]+=[^\[\]]*\]\s*)+)\s*$"
        match = re.match(full_directive_pattern, text_line)
        if not match:
            return {}, text_line
        directive_text = match.group(1)
        directives = self._parse_directive_text(directive_text)
        return directives, ""

    def _parse_directive_text(self, directive_text: str) -> dict[str, Any]:
        directives = {}
        directive_pattern = r"\[([^=\[\]]+)=([^\[\]]*)\]"
        matches = re.findall(directive_pattern, directive_text)
        for key, value in matches:
            key = key.strip().lower()
            value = value.strip()
            if key in self.directive_types:
                directive_type = self.directive_types[key]
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
                        directives[key] = value
            else:
                directives[key] = value
        return directives

    def _enhanced_convert_style(self, value: str) -> tuple[str, Any]:
        return convert_style(value)

    def _safe_float_convert(self, value: str) -> float:
        try:
            return float(value)
        except ValueError:
            return 0.0

    def _enhanced_convert_style(self, value: str) -> tuple[str, Any]:
        """
        Enhanced style conversion with better CSS support.

        ENHANCEMENT P8: Improved CSS value parsing.
        """
        value = value.strip()

        # Delegate to the main convert_style function which has comprehensive handling
        return convert_style(value)

    def _safe_float_convert(self, value: str) -> float:
        """Safely convert string to float with better error handling."""
        try:
            return float(value)
        except ValueError:
            logger.warning(f"Invalid float value: {value}, defaulting to 0.0")
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
            # For any other style types, just store the value
            result[key] = style_value

        return result

    def _handle_malformed_directives(self, section: Section, content: str) -> None:
        """Handle and clean up malformed directive patterns.

        TASK 2.1 FIX: Only clean up content that actually looks like intended directives,
        not markdown links or other bracket content.
        """
        # Only look for patterns that contain '=' which suggests they were intended as directives
        malformed_pattern = r"^\s*(\[[^\[\]]*=[^\[\]]*\]\s*)"
        malformed_match = re.match(malformed_pattern, content)

        if malformed_match:
            bracket_content = malformed_match.group(1).strip()
            # Check if it's a valid directive format
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
            # Aggressive cleanup
            section.content = re.sub(
                r"^\s*\[[^\[\]]+=[^\[\]]*\]", "", section.content
            ).lstrip()
