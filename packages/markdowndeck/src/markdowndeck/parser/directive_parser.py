import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class DirectiveParser:
    """Parse layout directives from markdown sections."""

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
        }

        # Define value converters
        self.converters = {
            "dimension": self._convert_dimension,
            "alignment": self._convert_alignment,
            "style": self._convert_style,
            "float": float,
        }

    def parse_directives(self, section: dict[str, Any]) -> None:
        """
        Extract and parse directives from section content.

        Args:
            section: Section dictionary to be modified in-place

        Example directive text:
            [width=2/3][align=center][background=#f5f5f5]
        """
        content = section["content"]
        # Regex to find one or more [...] blocks at the start, allowing whitespace
        directive_block_pattern = r"^\s*(\s*\[.+?\]\s*)+\s*"

        match = re.match(directive_block_pattern, content)
        if not match:
            section["directives"] = {}
            return

        directive_text = match.group(0)
        logger.debug(
            f"Found directives block: {directive_text!r} for section {section.get('id', 'unknown')}"
        )  # Use !r for clearer whitespace

        # Extract directives
        directives = {}

        # Special case for adjacent directives that are common in the test
        if "[width=" in directive_text and "[align=" in directive_text:
            logger.info(f"Processing adjacent width and align directives: {directive_text}")

        # Use a non-greedy pattern for all directive pairs
        # The pattern finds any directive in the format [key=value]
        # The non-greedy quantifier ? ensures we don't capture across multiple directives
        pattern = r"\[([^=\]]+?)=([^\]]*?)\]"
        matches = re.findall(pattern, directive_text)
        logger.info(f"Directive matches found: {matches} in text: {directive_text!r}")

        # Process each directive
        for key, value in matches:
            # Strip whitespace from key and value to ensure consistent processing
            key = key.strip().lower()
            value = value.strip()

            logger.debug(
                f"Processing directive: '{key}'='{value}' for section '{section.get('id', 'unknown')}'"
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
        section["directives"] = directives

        # Remove directive text from content
        # Use the length of the matched block to remove accurately
        section["content"] = content[
            len(directive_text) :
        ].lstrip()  # Use lstrip to remove leading newline/space after directives
        logger.debug(f"Section content after directive removal: {section['content'][:50]}...")

    def _convert_dimension(self, value: str) -> float | int:  # Allow int for pixels
        """
        Convert dimension value (fraction, percentage, or value).

        Args:
            value: Dimension as string (e.g., "2/3", "50%", "300")

        Returns:
            Normalized float value between 0 and 1 for fractions/percentages,
            or integer for pixel-like values.
        """
        value = value.strip()  # Ensure no leading/trailing spaces
        logger.debug(f"Converting dimension value: '{value}'")

        # Handle fraction values (e.g., 2/3)
        if "/" in value:
            parts = value.split("/")
            if len(parts) == 2 and all(part.strip().isdigit() for part in parts):
                num = int(parts[0].strip())
                denom = int(parts[1].strip())
                logger.debug(f"Parsed fraction: {num}/{denom}")
                if denom == 0:
                    # Match test expectation - raise ValueError with 'division by zero'
                    logger.warning(f"Division by zero in dimension value: '{value}'")
                    raise ValueError("division by zero")
                return num / denom
            raise ValueError(f"Invalid dimension format: '{value}'")

        # Handle percentage values (e.g., 50%)
        if value.endswith("%"):
            # Handle percentage values with improved flexibility
            percentage_str = value.rstrip("%").strip()
            logger.debug(f"Parsed percentage string: '{percentage_str}'")
            try:
                percentage = float(percentage_str)
                logger.debug(f"Converted percentage: {percentage}%")
                return percentage / 100.0
            except ValueError:
                logger.warning(f"Invalid percentage format: '{value}'")
                raise ValueError(f"Invalid dimension format: '{value}'")

        # Handle numeric values (pixels)
        try:
            numeric_value = value.strip()
            logger.debug(f"Parsing as numeric value: '{numeric_value}'")
            if numeric_value.isdigit():
                return int(numeric_value)
            return float(numeric_value)
        except ValueError:
            logger.warning(f"Invalid numeric format: '{value}'")
            raise ValueError(f"Invalid dimension format: '{value}'")

        # If we get here, we couldn't parse the value
        logger.warning(f"Failed to parse dimension value: '{value}'")
        raise ValueError(f"Invalid dimension format: '{value}'")

    def _convert_alignment(self, value: str) -> str:
        """
        Convert alignment value.

        Args:
            value: Alignment as string (e.g., "center", "right")

        Returns:
            Normalized alignment value
        """
        value = value.strip().lower()  # Ensure stripped and lower case
        valid_alignments = [
            "left",
            "center",
            "right",
            "justify",
            "top",
            "middle",
            "bottom",
        ]

        if value in valid_alignments:
            return value

        # Handle aliases
        aliases = {
            "start": "left",
            "end": "right",
        }

        if value in aliases:
            return aliases[value]

        # Return as-is if not recognized, but log warning
        logger.warning(f"Unrecognized alignment value: '{value}', using as is.")
        return value

    def _convert_style(self, value: str) -> tuple[str, Any]:
        """
        Convert style value.

        Args:
            value: Style as string (e.g., "#f5f5f5", "url(image.jpg)")

        Returns:
            Tuple of (type, value)
        """
        value = value.strip()  # Ensure stripped

        # Handle colors
        if value.startswith("#") or value in ["white", "black", "transparent"]:
            # Basic hex validation (allows 3 or 6 digits)
            if value.startswith("#") and not re.fullmatch(
                r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?", value
            ):
                logger.warning(f"Potentially invalid hex color format: '{value}'")
            return ("color", value)

        # Handle URLs
        url_match = re.fullmatch(r"url\(\s*['\"]?(.+?)['\"]?\s*\)", value, re.IGNORECASE)
        if url_match:
            url = url_match.group(1)
            return ("url", url)

        # Return as-is for other values
        logger.debug(f"Directive style value '{value}' treated as generic value.")
        return ("value", value)
