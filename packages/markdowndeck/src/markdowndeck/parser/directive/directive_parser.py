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

    def parse_directives(self, section: Section) -> None:
        """
        Extract and parse directives from section content.

        Args:
            section: Section model instance to be modified in-place

        Example directive text:
            [width=2/3][align=center][background=#f5f5f5]
        """
        if not section or section.content == "":
            if (
                section and section.directives is None
            ):  # Should not happen with dataclass defaults
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
        logger.debug(
            f"Found directives block: {directive_text!r} for section {section.id or 'unknown'}"
        )

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
                        logger.warning(
                            f"Unexpected error processing directive {key}={value}: {e}"
                        )
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

        logger.debug(
            f"Section content after directive removal: {section.content[:50]}..."
        )

        # Double-check that no directive patterns remain at the start
        if re.match(r"^\s*\[[\w\-]+=", section.content):
            logger.warning(
                f"Potential directive still present at start of content after removal: "
                f"{section.content[:50]}..."
            )
            # Try a more aggressive second pass if directives remain
            second_pass = re.sub(r"^\s*\[[^\[\]]+=[^\[\]]*\]", "", section.content)
            section.content = second_pass.lstrip()
            logger.debug(f"After aggressive second pass: {section.content[:50]}...")
