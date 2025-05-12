"""Parse layout directives from markdown sections with improved handling."""

import logging
import re

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
        }

        # Define value converters
        self.converters = {
            "dimension": convert_dimension,
            "alignment": convert_alignment,
            "style": convert_style,
            "float": float,
        }

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

        # Regex to find one or more [...] blocks at the start, allowing whitespace
        directive_block_pattern = r"^\s*(\s*\[.+?\]\s*)+\s*"

        match = re.match(directive_block_pattern, content)
        if not match:
            if section.directives is None:  # Should not happen with dataclass defaults
                section.directives = {}
            return

        directive_text = match.group(0)
        logger.debug(
            f"Found directives block: {directive_text!r} for section {section.id or 'unknown'}"
        )  # Use !r for clearer whitespace

        # Extract directives with improved handling
        directives = {}

        # Use a non-greedy pattern for all directive pairs
        # The pattern finds any directive in the format [key=value]
        # The non-greedy quantifier ? ensures we don't capture across multiple directives
        pattern = r"\[([^=\[\]]+?)=([^\[\]]*?)\]"
        matches = re.findall(pattern, directive_text)
        logger.debug(f"Directive matches found: {matches} in text: {directive_text!r}")

        # Process each directive
        for key, value in matches:
            # Strip whitespace from key and value to ensure consistent processing
            key = key.strip().lower()
            value = value.strip()

            logger.debug(
                f"Processing directive: '{key}'='{value}' for section '{section.id or 'unknown'}'"
            )

            if key in self.directive_types:
                directive_type = self.directive_types[key]
                converter = self.converters.get(directive_type)

                if converter:
                    try:
                        converted_value = converter(value)
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

        # Remove directive text from content
        # Use the length of the matched block to remove accurately
        section.content = content[len(directive_text) :].lstrip()
        logger.debug(f"Section content after directive removal: {section.content[:50]}...")
