import logging
import re
import uuid
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

    REFACTORED Version 7.1:
    - Enhanced code span protection to prevent directive parsing in code
    - Bulletproof protection/restoration logic
    - Robust handling of nested backticks and edge cases
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
        """
        Enhanced directive parsing with bulletproof code span protection.

        FIXES: test_bug_directives_are_parsed_from_code_blocks

        The key insight is that inline code spans (content between backticks) should
        NEVER have their contents parsed for directives, even if they contain
        directive-like syntax such as [code=true].
        """
        if not text_line or "[" not in text_line:
            return text_line, {}

        logger.debug(f"Parsing directives from: {text_line}")

        # CRITICAL FIX: Bulletproof inline code protection
        protected_text, code_spans = self._protect_all_inline_code_bulletproof(
            text_line
        )

        logger.debug(f"After code protection: {protected_text}")
        logger.debug(
            f"Protected {len(code_spans)} code spans: {list(code_spans.keys())}"
        )

        directives = {}

        def replacer(match):
            directive_text = match.group(0)
            parsed = self._parse_directive_text(directive_text)
            directives.update(parsed)

            # Handle formatting preservation around directives
            start_pos = match.start()
            end_pos = match.end()

            # If directive is immediately after a markdown formatting start
            # and there's content after it that closes the formatting
            if start_pos > 0 and protected_text[start_pos - 1] in ["*", "_"]:
                # Check if there's a space after the directive that we can remove
                if end_pos < len(protected_text) and protected_text[end_pos] == " ":
                    return " "  # Replace with a single space to maintain formatting
                return ""
            return ""

        cleaned_text = self.directive_block_pattern.sub(replacer, protected_text)

        # Restore code spans with verification
        restored_text = self._restore_all_inline_code_bulletproof(
            cleaned_text, code_spans
        )

        # Post-process to fix broken markdown formatting
        # Handle cases like "*  text*" -> "*text*" and "**  text**" -> "**text**"
        restored_text = re.sub(r"\*\s+", "*", restored_text)
        restored_text = re.sub(r"\*\*\s+", "**", restored_text)
        restored_text = re.sub(r"_\s+", "_", restored_text)
        restored_text = re.sub(r"__\s+", "__", restored_text)

        logger.debug(f"Final result: {restored_text}")
        logger.debug(f"Extracted directives: {directives}")

        return restored_text.strip(), directives

    def _protect_all_inline_code_bulletproof(
        self, text: str
    ) -> tuple[str, dict[str, str]]:
        """
        Bulletproof inline code protection that handles all edge cases.

        This addresses the failure in test_bug_directives_are_parsed_from_code_blocks
        where `[code=true]` inside backticks was being parsed as a directive.

        Key improvements:
        1. Handles multiple backtick patterns (`, ``, ```)
        2. Preserves exact original content including brackets
        3. Uses unique placeholders to prevent conflicts
        4. Comprehensive logging for debugging
        """
        code_spans = {}
        protected_text = text

        # Multiple patterns to handle different backtick scenarios
        # Process in order from most specific to least specific
        patterns = [
            # Triple backticks (rare in inline, but possible)
            (re.compile(r"(```+)([^`]*?)\1"), "TRIPLE"),
            # Double backticks
            (re.compile(r"(``+)([^`]*?)\1"), "DOUBLE"),
            # Single backticks (most common)
            (re.compile(r"(`+)([^`]*?)\1"), "SINGLE"),
        ]

        for pattern, code_type in patterns:

            def replace_code_span(match):
                placeholder = f"__CODE_SPAN_{code_type}_{uuid.uuid4().hex[:8]}__"
                original_span = match.group(0)
                code_spans[placeholder] = original_span

                # Debug logging for the failing test case
                if "[code=true]" in original_span:
                    logger.debug(
                        f"CRITICAL: Protected code span containing directive-like text: {original_span}"
                    )
                elif "[" in original_span and "]" in original_span:
                    logger.debug(
                        f"Protected code span with bracket content: {original_span}"
                    )

                logger.debug(f"Protected code span: {placeholder} -> {original_span}")
                return placeholder

            protected_text = pattern.sub(replace_code_span, protected_text)

        logger.debug(f"Protection complete. Protected {len(code_spans)} code spans")
        logger.debug(f"Protected text: {protected_text}")

        return protected_text, code_spans

    def _restore_all_inline_code_bulletproof(
        self, text: str, code_spans: dict[str, str]
    ) -> str:
        """
        Restore code spans with comprehensive verification.

        Ensures that protected content is properly restored and wasn't
        accidentally modified during directive parsing.
        """
        restored_text = text

        for placeholder, original_span in code_spans.items():
            if placeholder in restored_text:
                restored_text = restored_text.replace(placeholder, original_span)
                logger.debug(f"Restored code span: {placeholder} -> {original_span}")
            else:
                logger.error(
                    f"CRITICAL: Code span placeholder missing during restoration: {placeholder}"
                )
                logger.error(f"Expected to find: {placeholder}")
                logger.error(f"In text: {restored_text}")

        # CRITICAL VERIFICATION: Ensure protected content wasn't lost
        for original_span in code_spans.values():
            if "[code=true]" in original_span:
                if original_span not in restored_text:
                    logger.error(
                        "CRITICAL: Protected code span was lost during processing!"
                    )
                    logger.error(f"Lost span: {original_span}")
                    logger.error(f"Final text: {restored_text}")
                else:
                    logger.debug(
                        "SUCCESS: Protected code span [code=true] preserved in final text"
                    )

        return restored_text

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
        """
        Parse directive text with robust compound value handling.

        This logic correctly handles compound string values (like for `border`)
        and safely ignores valueless directives that are not boolean flags.
        """
        directives = {}
        bracket_content_pattern = re.compile(r"\[([^\[\]]+)\]")

        for content in bracket_content_pattern.findall(directive_text):
            content = content.strip()
            key, value = "", ""

            # Split only on the first equals sign to handle compound values
            if "=" in content:
                key, value = content.split("=", 1)
            else:
                key = content  # This is a valueless directive

            key = key.strip().lower()
            value = value.strip().strip("'\"")

            # A valueless directive is only valid if it's a known boolean flag
            if not value:
                if key in ["bold", "italic", "fill"]:
                    directives[key] = True
                    logger.debug(f"Parsed boolean directive: {key}=True")
                else:
                    logger.warning(
                        f"Directive '[{key}]' used without a value and is not a boolean flag. Ignoring."
                    )
                continue  # Skip to the next directive in the block

            # Process directives that have a value
            if key in self.directive_types:
                directive_type = self.directive_types[key]
                converter = self.converters.get(directive_type)
                if converter:
                    try:
                        converted_value = converter(value)
                        if directive_type == "style":
                            directives.update(
                                self._process_style_directive_value(
                                    key, converted_value
                                )
                            )
                        else:
                            directives[key] = converted_value
                        logger.debug(f"Parsed directive: {key}={converted_value}")
                    except ValueError as e:
                        logger.warning(
                            f"Could not convert directive '{key}={value}': {e}"
                        )
                        directives[key] = value  # Store as raw string on failure
                else:
                    directives[key] = value
                    logger.debug(f"Parsed directive (no converter): {key}={value}")
            else:
                logger.warning(f"Unsupported directive key '{key}'. Ignoring.")

        return directives

    def _enhanced_convert_style(self, value: str) -> tuple[str, Any]:
        """Enhanced style conversion using the converters module."""
        return convert_style(value)

    def _safe_float_convert(self, value: str) -> float:
        """Safely convert string to float, defaulting to 0.0 on error."""
        try:
            return float(value)
        except ValueError:
            logger.warning(f"Could not convert '{value}' to float, using 0.0")
            return 0.0

    def _process_style_directive_value(
        self, key: str, style_tuple: tuple[str, Any]
    ) -> dict[str, Any]:
        """Process style directive tuples into a clean, unified format."""
        style_type, style_value = style_tuple
        result = {}

        if key in ["background", "color"]:
            if style_type == "url":
                result[key] = {"type": "image", "value": style_value["value"]}
            else:
                result[key] = {"type": "color", "value": style_value}
        else:
            result[key] = style_value
        return result
