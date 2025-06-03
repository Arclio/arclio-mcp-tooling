"""Parse layout directives from markdown sections with improved handling."""

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
    """Parse layout directives from markdown sections with improved handling."""

    def __init__(self):
        """Initialize the directive parser."""
        # Define supported directives and their types
        self.directive_types = {
            "width": "dimension",
            "height": "dimension",
            "align": "alignment",
            "valign": "alignment",
            "background": "style",
            "padding": "dimension",
            "margin": "dimension",
            "color": "style",
            "fontsize": "dimension",
            "opacity": "float",
            "border": "style",
            "border-position": "string",
            "line-spacing": "float",
            "cell-align": "alignment",
            "cell-background": "style",
            "cell-range": "string",
            "vertical-align": "alignment",
            "paragraph-spacing": "dimension",
            "indent": "dimension",
            "font-family": "string",
            "list-style": "string",
            # Add any additional directive types here
        }

        # Define value converters
        self.converters = {
            "dimension": convert_dimension,
            "alignment": convert_alignment,
            "style": convert_style,
            "float": float,
            "string": str,
        }

    def _process_style_directive_value(self, key: str, style_tuple: tuple[str, Any]) -> dict[str, Any]:
        """
        Process the tuple output from convert_style into a clean, directly consumable format.

        Args:
            key: The directive key (e.g., 'color', 'background', 'border')
            style_tuple: Tuple from convert_style with (type, structured_value)

        Returns:
            Dictionary with processed directives ready for direct consumption
        """
        style_type, style_value = style_tuple
        result = {}

        if style_type == "color":
            # Direct color value - store directly under the key
            result[key] = style_value

        elif style_type == "url":
            # Background image URL
            if key == "background":
                result["background_type"] = "image"
                result["background_image_url"] = style_value["value"]
            else:
                # For other keys that might have URL values
                result[f"{key}_url"] = style_value["value"]

        elif style_type == "border":
            # Structured border data - store directly under the key
            result[key] = style_value

        elif style_type == "border_style":
            # Simple border style - store as border with just the style
            result[key] = {"style": style_value}

        else:
            # Generic value - store directly
            result[key] = style_value

        return result

    def parse_inline_directives(self, text_line: str) -> tuple[dict[str, Any], str]:
        """
        Parse directives from a single line of text that may contain only directives.

        This method is used to identify and parse element-specific directives that appear
        immediately before block elements within section content.

        Args:
            text_line: A single line of text that might contain directives

        Returns:
            Tuple of (parsed_directives_dict, remaining_text) where:
            - parsed_directives_dict: Dictionary of parsed directives if the line contains only directives
            - remaining_text: The original text if it's not all directives, or empty string if it was
        """
        text_line = text_line.strip()
        if not text_line:
            return {}, ""

        # Check if the entire line consists only of directive patterns
        # This pattern matches a line that contains only directives (one or more)
        full_directive_pattern = r"^\s*((?:\s*\[[^\[\]]+=[^\[\]]*\]\s*)+)\s*$"

        match = re.match(full_directive_pattern, text_line)
        if not match:
            # Line contains non-directive content
            return {}, text_line

        directive_text = match.group(1)
        logger.debug(f"Found inline directives: {directive_text!r}")

        # Parse the directives using the same logic as parse_directives
        directives = {}
        directive_pattern = r"\[([^=\[\]]+)=([^\[\]]*)\]"
        matches = re.findall(directive_pattern, directive_text)

        for key, value in matches:
            key = key.strip().lower()
            value = value.strip()

            logger.debug(f"Processing inline directive: '{key}'='{value}'")

            if key in self.directive_types:
                directive_type = self.directive_types[key]
                converter = self.converters.get(directive_type)

                if converter:
                    try:
                        converted_value = converter(value)

                        # Handle style directives with special processing
                        if directive_type == "style" and isinstance(converted_value, tuple):
                            processed_directives = self._process_style_directive_value(key, converted_value)
                            directives.update(processed_directives)
                        else:
                            # Direct storage for non-style directives
                            directives[key] = converted_value

                        logger.debug(f"Processed inline directive: {key}={converted_value}")
                    except ValueError as e:
                        logger.warning(f"Error processing inline directive {key}={value}: {e}")
                    except Exception as e:
                        logger.warning(f"Unexpected error processing inline directive {key}={value}: {e}")
                else:
                    directives[key] = value
                    logger.debug(f"Added inline directive without conversion: {key}={value}")
            else:
                logger.warning(f"Unknown inline directive: {key}")
                directives[key] = value

        # Return the parsed directives and empty string since the line was consumed
        return directives, ""

    def parse_directives(self, section: Section) -> None:
        """
        Extract and parse directives from section content.

        Args:
            section: Section model instance to be modified in-place

        Example directive text:
            [width=2/3][align=center][background=#f5f5f5]
        """
        if not section or section.content == "":
            if section and section.directives is None:  # Should not happen with dataclass defaults
                section.directives = {}
            return

        content = section.content

        # CRITICAL FIX: Enhanced robust directive block detection
        # This pattern matches one or more directive blocks at the start of content,
        # each in the format [key=value] with optional whitespace
        directive_block_pattern = r"^\s*((?:\s*\[[^\[\]]+=[^\[\]]*\]\s*)+)"

        match = re.match(directive_block_pattern, content)
        if not match:
            if section.directives is None:  # Should not happen with dataclass defaults
                section.directives = {}
            return

        # Get exact matched text including all whitespace
        directive_text = match.group(1)
        logger.debug(f"Found directives block: {directive_text!r} for section {section.id or 'unknown'}")

        # Extract directives with improved handling
        directives = {}

        # Find all [key=value] pairs in the directive text
        # The pattern specifically looks for key=value pairs inside square brackets
        directive_pattern = r"\[([^=\[\]]+)=([^\[\]]*)\]"
        matches = re.findall(directive_pattern, directive_text)
        logger.debug(f"Directive matches found: {matches} in text: {directive_text!r}")

        # Process each directive
        for key, value in matches:
            # Strip whitespace from key and value to ensure consistent processing
            key = key.strip().lower()
            value = value.strip()

            logger.debug(f"Processing directive: '{key}'='{value}' for section '{section.id or 'unknown'}'")

            if key in self.directive_types:
                directive_type = self.directive_types[key]
                converter = self.converters.get(directive_type)

                if converter:
                    try:
                        converted_value = converter(value)

                        # Handle style directives with special processing
                        if directive_type == "style" and isinstance(converted_value, tuple):
                            processed_directives = self._process_style_directive_value(key, converted_value)
                            directives.update(processed_directives)
                        else:
                            # Direct storage for non-style directives
                            directives[key] = converted_value

                        logger.debug(f"Processed directive: {key}={converted_value}")
                    except ValueError as e:  # Catch specific errors
                        logger.warning(f"Error processing directive {key}={value}: {e}")
                    except Exception as e:
                        logger.warning(f"Unexpected error processing directive {key}={value}: {e}")
                else:
                    # Use as-is if no converter
                    directives[key] = value
                    logger.debug(f"Added directive without conversion: {key}={value}")
            else:
                # Handle unknown directives
                logger.warning(f"Unknown directive: {key}")
                directives[key] = value

        # Update section
        section.directives = directives

        # CRITICAL FIX: Remove directive text from content using exact match position
        # This ensures all directives are completely removed
        match_end = match.end(1)
        section.content = content[match_end:].lstrip()

        logger.debug(f"Section content after directive removal: {section.content[:50]}...")

        # Double-check that no directive patterns remain at the start
        if re.match(r"^\s*\[[\w\-]+=", section.content):
            logger.warning(f"Potential directive still present at start of content after removal: {section.content[:50]}...")
            # Try a more aggressive second pass if directives remain
            second_pass = re.sub(r"^\s*\[[^\[\]]+=[^\[\]]*\]", "", section.content)
            section.content = second_pass.lstrip()
            logger.debug(f"After aggressive second pass: {section.content[:50]}...")
