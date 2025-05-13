"""Content splitter for section parsing with robust code block handling."""

import logging
import re
import uuid

from markdowndeck.parser.section.models import ContentSplit

logger = logging.getLogger(__name__)


class ContentSplitter:
    """Handles content splitting while preserving code blocks."""

    def __init__(self):
        """Initialize the content splitter."""
        # Update the regex to correctly match both ```and ~~~ code blocks
        # The previous regex was having issues with the ~~~ style blocks
        self.code_block_regex = re.compile(
            r"^(```|~~~)[\w-]*\n.*?\n\1\s*$", re.MULTILINE | re.DOTALL
        )
        self.placeholder_prefix = f"__MD_DECK_CODE_BLOCK_PLACEHOLDER_{uuid.uuid4().hex[:8]}__"

    def split_by_separator(self, content: str, separator_pattern: str) -> ContentSplit:
        r"""
        Split content by a separator regex pattern while preserving code blocks.

        Args:
            content: The content string to split.
            separator_pattern: The regex pattern string for the separator.
                          (e.g., r"^\s*---\s*$")

        Returns:
            A ContentSplit object containing the list of split parts and
            a dictionary of protected blocks.
        """
        logger.debug(f"Attempting to split content by separator: '{separator_pattern}'")

        # Initialize separator_regex outside the try block so it's available in the wider scope
        separator_regex = None

        # Check if content is only a separator (matches entire content)
        try:
            separator_regex = re.compile(separator_pattern, re.MULTILINE)
            if re.fullmatch(separator_regex, content.strip()):
                logger.debug("Content is only a separator, returning empty parts list")
                return ContentSplit(parts=[], protected_blocks={})
        except re.error as e:
            logger.error(f"Invalid regex pattern for separator check: {e}")
            # If the regex is invalid, return the content as a single part
            return ContentSplit(parts=[content] if content.strip() else [], protected_blocks={})

        # First protect the code blocks
        protected_content, protected_blocks_dict = self._protect_blocks(
            content, self.code_block_regex, "CODE"
        )
        logger.debug(f"Protected {len(protected_blocks_dict)} code blocks.")

        try:
            # Split the protected content by the separator
            temp_parts = []
            lines = protected_content.split("\n")
            current_part = []

            for line in lines:
                if separator_regex and separator_regex.fullmatch(line.strip()):
                    # We found a separator, so add the current part and start a new one
                    if current_part:
                        temp_parts.append("\n".join(current_part))
                        current_part = []
                else:
                    current_part.append(line)

            # Add the last part if not empty
            if current_part:
                temp_parts.append("\n".join(current_part))

        except re.error as e:
            logger.error(f"Invalid separator regex pattern '{separator_pattern}': {e}")
            # Fallback: return the original content as a single part if regex fails
            restored_content = self._restore_blocks(content, protected_blocks_dict)
            return ContentSplit(
                parts=[restored_content.strip()] if restored_content.strip() else [],
                protected_blocks=protected_blocks_dict,
            )

        # Now restore the code blocks in each part
        restored_parts = []
        for part in temp_parts:
            restored_part = self._restore_blocks(part, protected_blocks_dict)
            stripped_part = restored_part.strip()
            if stripped_part:  # Only add non-empty parts after stripping
                restored_parts.append(stripped_part)

        # Handle case where content might be empty or only separators
        if not restored_parts and not content.strip():
            logger.debug("Content was empty or only separators, resulting in no parts.")
            return ContentSplit(parts=[], protected_blocks=protected_blocks_dict)
        if not restored_parts and content.strip():
            # This can happen if content IS a code block and there are no separators outside it
            # or if content is just whitespace around separators
            # If original content was not empty, and it wasn't just separators, there should be one part.
            fully_restored_original = self._restore_blocks(protected_content, protected_blocks_dict)
            if fully_restored_original.strip():
                restored_parts = [fully_restored_original.strip()]

        logger.debug(
            f"Content split into {len(restored_parts)} parts after restoration and filtering."
        )
        return ContentSplit(parts=restored_parts, protected_blocks=protected_blocks_dict)

    def _protect_blocks(
        self, content: str, block_regex: re.Pattern, block_type_label: str
    ) -> tuple[str, dict[str, str]]:
        """
        Replaces blocks matching the regex with unique placeholders.

        Args:
            content: The string content to process.
            block_regex: Compiled regular expression to find blocks.
            block_type_label: A label for the placeholder (e.g., "CODE", "COMMENT").

        Returns:
            A tuple: (content_with_placeholders, dictionary_of_placeholders_to_blocks).
        """
        protected_blocks: dict[str, str] = {}

        # Instead of using re.sub, use finditer to process each match individually
        last_end = 0
        content_parts = []

        for match in block_regex.finditer(content):
            content_parts.append(content[last_end : match.start()])
            block_content = match.group(0)
            placeholder = f"__{block_type_label}_PLACEHOLDER_{uuid.uuid4().hex}__"
            protected_blocks[placeholder] = block_content
            content_parts.append(placeholder)
            last_end = match.end()

        # Add the remaining content after the last match
        content_parts.append(content[last_end:])
        content_with_placeholders = "".join(content_parts)

        return content_with_placeholders, protected_blocks

    def _restore_blocks(
        self, content_with_placeholders: str, protected_blocks: dict[str, str]
    ) -> str:
        """
        Restores original blocks from their placeholders in the content.

        Args:
            content_with_placeholders: The string content with placeholders.
            protected_blocks: Dictionary mapping placeholders to original block content.

        Returns:
            The content with original blocks restored.
        """
        restored_content = content_with_placeholders
        for placeholder, original_block in protected_blocks.items():
            # Use re.escape on placeholder for safety, though UUIDs should be fine.
            restored_content = restored_content.replace(placeholder, original_block)
        return restored_content


def extract_directive_text(content: str) -> tuple[str, str]:
    """
    Extract directive text from the beginning of content if present.
    (This utility function seems fine as is, assuming its usage context is correct)
    """
    directive_pattern = r"^\s*(\s*\[.+?\]\s*)+\s*"
    match = re.match(directive_pattern, content)
    if not match:
        return "", content
    directive_text = match.group(0)
    remainder = content[len(directive_text) :]
    return directive_text, remainder
