"""Code block element models."""

import logging
from copy import deepcopy
from dataclasses import dataclass

from markdowndeck.models.elements.base import Element

logger = logging.getLogger(__name__)


@dataclass
class CodeElement(Element):
    """Code block element with splittable contract."""

    code: str = ""
    language: str = "text"

    def count_lines(self) -> int:
        """
        Count the number of lines in the code block.

        Returns:
            Number of lines in the code
        """
        if not self.code:
            return 0
        return self.code.count("\n") + 1

    def get_display_language(self) -> str:
        """
        Get a display-friendly language name.

        Returns:
            Display language name
        """
        if self.language == "text" or not self.language:
            return "Text"

        # Map common language ids to display names
        language_map = {
            "py": "Python",
            "js": "JavaScript",
            "ts": "TypeScript",
            "html": "HTML",
            "css": "CSS",
            "java": "Java",
            "c": "C",
            "cpp": "C++",
            "csharp": "C#",
            "go": "Go",
            "rust": "Rust",
            "ruby": "Ruby",
            "php": "PHP",
            "shell": "Shell",
            "bash": "Bash",
            "sql": "SQL",
            "json": "JSON",
            "xml": "XML",
            "yaml": "YAML",
            "md": "Markdown",
        }

        # Return mapped name or capitalize the language
        return language_map.get(self.language.lower(), self.language.capitalize())

    def split(
        self, available_height: float
    ) -> tuple["CodeElement | None", "CodeElement | None"]:
        """
        Split code element following the Minimum Requirements Splitting Contract.

        Rule: Will only split if at least 2 lines of code can fit.
        If rule is met, splits the code content between lines.
        If not, returns (None, self) treating the element as atomic for this operation.

        Args:
            available_height: The vertical space available for this element

        Returns:
            Tuple of (fitted_part, overflowing_part). Either can be None.
        """
        from markdowndeck.layout.metrics.code import calculate_code_element_height

        # Handle empty code case
        if not self.code.strip():
            return None, None

        if available_height <= 1:
            return None, deepcopy(self)

        element_width = self.size[0] if self.size and self.size[0] > 0 else 400.0
        full_height = calculate_code_element_height(self, element_width)

        if full_height <= available_height:
            # Entire code block fits
            return deepcopy(self), None

        # Split at line boundaries to preserve code structure
        # Strip trailing newlines to avoid empty string at end of split
        # This prevents the bug where trailing newlines create empty overflowing parts
        code_content = self.code.rstrip("\n")
        lines = code_content.split("\n")
        total_lines = len(lines)

        if total_lines <= 1:
            logger.debug("Single line code doesn't fit - treating as atomic")
            return None, deepcopy(self)

        # Calculate height per line estimate
        height_per_line = full_height / total_lines
        max_lines_that_fit = int(available_height / height_per_line)

        if max_lines_that_fit <= 0:
            logger.debug("No code lines fit in available space")
            return None, deepcopy(self)

        if max_lines_that_fit >= total_lines:
            return deepcopy(self), None

        # MINIMUM REQUIREMENTS CHECK: Must fit at least 2 lines
        minimum_lines_required = 2
        fitted_line_count = max_lines_that_fit

        if fitted_line_count < minimum_lines_required:
            logger.info(
                f"Code split rejected: Only {fitted_line_count} lines fit, need minimum {minimum_lines_required}"
            )
            return None, deepcopy(self)

        # Minimum met - proceed with split
        fitted_lines = lines[:max_lines_that_fit]
        overflowing_lines = lines[max_lines_that_fit:]

        # Create fitted part
        fitted_part = deepcopy(self)
        fitted_part.code = "\n".join(fitted_lines)

        # Create overflowing part
        overflowing_part = deepcopy(self)
        overflowing_part.code = "\n".join(overflowing_lines)
        overflowing_part.position = None  # Reset position for continuation slide

        # Recalculate sizes
        fitted_part.size = (
            element_width,
            calculate_code_element_height(fitted_part, element_width),
        )
        overflowing_part.size = (
            element_width,
            calculate_code_element_height(overflowing_part, element_width),
        )

        logger.info(
            f"Code split successful: {fitted_line_count} lines fitted, {len(overflowing_lines)} lines overflowing"
        )
        return fitted_part, overflowing_part
