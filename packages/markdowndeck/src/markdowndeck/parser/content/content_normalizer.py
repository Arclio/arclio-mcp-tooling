"""
Content normalizer for MarkdownDeck parser.

This module provides a ContentNormalizer class that pre-processes raw Markdown strings
into a canonical format for the ContentParser. It uses a block-based approach:
1) Parse content into semantic blocks (lists, code blocks, paragraphs, etc.)
2) Normalize each block individually (remove outer indentation, preserve internal structure)
3) Reassemble blocks with proper spacing
"""

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Block:
    """Represents a semantic block of content."""

    type: str  # 'paragraph', 'list', 'code_block', 'header', etc.
    content: str
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ContentNormalizer:
    """
    Normalizes Markdown content using a block-based approach.

    This class parses content into semantic blocks, normalizes each block
    individually, then reassembles them with proper spacing.
    """

    def __init__(self):
        """Initialize the content normalizer with block patterns."""
        # Pattern to match fenced code blocks
        self.fenced_code_pattern = re.compile(
            r"^(?P<indent>\s*)(?P<fence>```+|~~~+)(?P<lang>[^\n]*)?$\n"
            r"(?P<content>.*?)"
            r"^(?P=indent)(?P=fence)\s*$",
            re.MULTILINE | re.DOTALL,
        )

        # Patterns for block detection
        self.block_patterns = {
            "heading": re.compile(r"^(\s*)#{1,6}\s+"),
            "list_item": re.compile(r"^(\s*)([-*+]|\d+[.)])\s+"),
            "blockquote": re.compile(r"^(\s*)>\s*"),
            "table_row": re.compile(r"^(\s*)\|"),
            "horizontal_rule": re.compile(r"^(\s*)(\*{3,}|_{3,}|-{3,})\s*$"),
        }

    def normalize(self, text: str) -> str:
        """
        Normalize Markdown content using block-based approach.

        Args:
            text: Raw Markdown string to normalize

        Returns:
            Normalized Markdown string ready for parsing
        """
        if not text or not text.strip():
            return ""

        logger.debug(
            f"Starting block-based normalization of {len(text)} character content"
        )

        # Step 1: Parse into semantic blocks
        blocks = self._parse_into_blocks(text)
        logger.debug(f"Parsed into {len(blocks)} blocks")

        # Step 2: Normalize each block individually
        normalized_blocks = []
        for block in blocks:
            normalized_block = self._normalize_block(block)
            normalized_blocks.append(normalized_block)

        # Step 3: Reassemble with proper spacing
        result = self._reassemble_blocks(normalized_blocks)
        logger.debug(f"Reassembled into {len(result)} character result")

        return result

    def _parse_into_blocks(self, text: str) -> list[Block]:
        """
        Parse text into semantic blocks.

        Args:
            text: Input text

        Returns:
            List of semantic blocks
        """
        blocks = []
        lines = text.split("\n")
        i = 0

        while i < len(lines):
            # Check for fenced code blocks first
            if self._is_fenced_code_start(lines[i]):
                block, lines_consumed = self._parse_code_block(lines, i)
                blocks.append(block)
                i += lines_consumed
                continue

            # Check for other block types
            block_type = self._detect_block_type(lines[i])

            if block_type == "heading":
                blocks.append(Block("heading", lines[i]))
                i += 1
            elif block_type == "horizontal_rule":
                blocks.append(Block("horizontal_rule", lines[i]))
                i += 1
            elif block_type == "list_item":
                block, lines_consumed = self._parse_list_block(lines, i)
                blocks.append(block)
                i += lines_consumed
            elif block_type == "blockquote":
                block, lines_consumed = self._parse_blockquote_block(lines, i)
                blocks.append(block)
                i += lines_consumed
            elif block_type == "table_row":
                block, lines_consumed = self._parse_table_block(lines, i)
                blocks.append(block)
                i += lines_consumed
            else:
                # Regular paragraph
                block, lines_consumed = self._parse_paragraph_block(lines, i)
                blocks.append(block)
                i += lines_consumed

        return blocks

    def _is_fenced_code_start(self, line: str) -> bool:
        """Check if line starts a fenced code block."""
        return bool(re.match(r"^\s*(```+|~~~+)", line))

    def _detect_block_type(self, line: str) -> str | None:
        """Detect the type of block a line represents."""
        if not line.strip():
            return None

        for block_type, pattern in self.block_patterns.items():
            if pattern.match(line):
                return block_type
        return None

    def _parse_code_block(self, lines: list[str], start_idx: int) -> tuple[Block, int]:
        """Parse a fenced code block."""
        # Find the complete code block using regex
        remaining_text = "\n".join(lines[start_idx:])
        match = self.fenced_code_pattern.match(remaining_text)

        if match:
            full_block = match.group(0)
            lines_consumed = full_block.count("\n") + 1

            # Extract metadata
            indent = match.group("indent")
            fence = match.group("fence")
            lang = (match.group("lang") or "").strip()
            match.group("content")

            metadata = {
                "indent": indent,
                "fence_type": fence[0],  # '`' or '~'
                "fence_length": len(fence),
                "language": lang,
            }

            return Block("code_block", full_block, metadata), lines_consumed
        # Fallback if regex doesn't match
        return Block("paragraph", lines[start_idx]), 1

    def _parse_list_block(self, lines: list[str], start_idx: int) -> tuple[Block, int]:
        """Parse a complete list block (including nested items)."""
        list_lines = []
        i = start_idx

        # Get the list type of the starting item
        starting_list_metadata = self._analyze_list_metadata(lines[start_idx])
        starting_list_type = starting_list_metadata.get("list_type", "")

        while i < len(lines):
            line = lines[i]

            # Empty lines are part of the list if followed by more list content
            if not line.strip():
                # Look ahead to see if there are more list items of the same type
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                if j < len(lines) and self._is_same_list_continuation(
                    lines[j], starting_list_type
                ):
                    list_lines.append(line)
                    i += 1
                    continue
                break

            # Check if this line is part of the same list
            if self._is_same_list_continuation(line, starting_list_type):
                list_lines.append(line)
                i += 1
            else:
                break

        return Block("list", "\n".join(list_lines), starting_list_metadata), len(
            list_lines
        )

    def _is_same_list_continuation(self, line: str, expected_list_type: str) -> bool:
        """Check if line continues the same list type."""
        if not line.strip():
            return False

        # Fenced code blocks always start a new block, regardless of indentation
        if self._is_fenced_code_start(line):
            return False

        # Check if it's a direct list item
        if self.block_patterns["list_item"].match(line):
            # Analyze the list type of this item
            line_metadata = self._analyze_list_metadata(line)
            line_list_type = line_metadata.get("list_type", "")

            # Only continue if it's the same list type
            return line_list_type == expected_list_type

        # Check if it's indented content (list item continuation)
        # But exclude other block types that might be indented
        if re.match(r"^\s{2,}", line):
            # Don't treat block-starting lines as list continuation
            return not self._detect_block_type(line)

        return False

    def _parse_blockquote_block(
        self, lines: list[str], start_idx: int
    ) -> tuple[Block, int]:
        """Parse a blockquote block."""
        quote_lines = []
        i = start_idx

        while i < len(lines):
            line = lines[i]
            if line.strip() == "" or re.match(r"^\s*>", line):
                quote_lines.append(line)
                i += 1
            else:
                break

        return Block("blockquote", "\n".join(quote_lines)), len(quote_lines)

    def _parse_table_block(self, lines: list[str], start_idx: int) -> tuple[Block, int]:
        """Parse a table block."""
        table_lines = []
        i = start_idx

        while i < len(lines):
            line = lines[i]
            if re.match(r"^\s*\|", line) or re.match(r"^\s*\|[\s\-:]+\|?\s*$", line):
                table_lines.append(line)
                i += 1
            else:
                break

        return Block("table", "\n".join(table_lines)), len(table_lines)

    def _parse_paragraph_block(
        self, lines: list[str], start_idx: int
    ) -> tuple[Block, int]:
        """Parse a paragraph block."""
        para_lines = []
        i = start_idx

        while i < len(lines):
            line = lines[i]

            # Empty line ends paragraph
            if not line.strip():
                break

            # Block-starting line ends paragraph
            if self._detect_block_type(line) or self._is_fenced_code_start(line):
                break

            para_lines.append(line)
            i += 1

        # Skip trailing empty lines in paragraph
        while para_lines and not para_lines[-1].strip():
            para_lines.pop()

        if not para_lines:
            para_lines = [lines[start_idx] if start_idx < len(lines) else ""]

        return Block("paragraph", "\n".join(para_lines)), len(para_lines)

    def _analyze_list_metadata(self, first_item: str) -> dict:
        """Analyze list metadata from first item."""
        match = self.block_patterns["list_item"].match(first_item)
        if not match:
            return {}

        indent = match.group(1)
        marker = match.group(2)

        if re.match(r"\d+[.]", marker):
            list_type = "ordered_dot"
        elif re.match(r"\d+[)]", marker):
            list_type = "ordered_paren"
        else:
            list_type = "unordered"

        return {"indent": indent, "marker": marker, "list_type": list_type}

    def _normalize_block(self, block: Block) -> Block:
        """
        Normalize a single block by removing outer indentation.

        Args:
            block: Block to normalize

        Returns:
            Normalized block
        """
        if block.type == "code_block":
            return self._normalize_code_block(block)
        if block.type in ["list", "blockquote", "table"]:
            return self._normalize_indented_block(block)
        # Headers and paragraphs - just remove leading/trailing whitespace
        normalized_content = "\n".join(
            line.lstrip() for line in block.content.split("\n")
        ).strip()
        return Block(block.type, normalized_content, block.metadata)

    def _normalize_code_block(self, block: Block) -> Block:
        """Normalize a code block according to CommonMark spec."""
        content = block.content
        lines = content.split("\n")

        if not lines:
            return block

        # Find the opening fence indentation (count actual characters, not logical width)
        opening_line = lines[0]
        opening_indent = len(opening_line) - len(opening_line.lstrip())

        # Process each line according to CommonMark rules
        processed_lines = []
        for i, line in enumerate(lines):
            if i == 0 or i == len(lines) - 1:
                # Opening and closing fence: remove all leading whitespace
                processed_lines.append(line.lstrip())
            else:
                # Content lines: remove up to opening_indent characters from start
                if line.strip():  # Non-empty line
                    # Count leading whitespace characters (tabs and spaces)
                    leading_chars = 0
                    for char in line:
                        if char in " \t":
                            leading_chars += 1
                        else:
                            break

                    # Remove up to opening_indent characters
                    chars_to_remove = min(opening_indent, leading_chars)
                    if chars_to_remove > 0:
                        # Remove exactly chars_to_remove characters from the start
                        remaining_line = line
                        removed = 0
                        while removed < chars_to_remove and remaining_line:
                            if remaining_line[0] in " \t":
                                remaining_line = remaining_line[1:]
                                removed += 1
                            else:
                                break
                        processed_lines.append(remaining_line)
                    else:
                        processed_lines.append(line)
                else:
                    processed_lines.append("")  # Empty line

        normalized_content = "\n".join(processed_lines)
        return Block(block.type, normalized_content, block.metadata)

    def _normalize_indented_block(self, block: Block) -> Block:
        """Normalize blocks that may have meaningful internal indentation."""
        lines = block.content.split("\n")
        if not lines:
            return block

        # Find common leading indentation
        non_empty_lines = [line for line in lines if line.strip()]
        if not non_empty_lines:
            return block

        min_indent = min(len(line) - len(line.lstrip()) for line in non_empty_lines)

        # Remove common indentation while preserving relative structure
        normalized_lines = []
        for line in lines:
            if line.strip():  # Non-empty line
                if len(line) >= min_indent and len(line[:min_indent].strip()) == 0:
                    normalized_lines.append(line[min_indent:])
                else:
                    normalized_lines.append(line.lstrip())
            else:
                normalized_lines.append("")  # Empty line

        normalized_content = "\n".join(normalized_lines)
        return Block(block.type, normalized_content, block.metadata)

    def _reassemble_blocks(self, blocks: list[Block]) -> str:
        """
        Reassemble normalized blocks with proper spacing.

        Args:
            blocks: List of normalized blocks

        Returns:
            Final assembled content
        """
        if not blocks:
            return ""

        result_parts = []

        for i, block in enumerate(blocks):
            # Add the block content
            result_parts.append(block.content)

            # Determine if we need a separator after this block
            if i < len(blocks) - 1:  # Not the last block
                next_block = blocks[i + 1]

                if self._needs_separator(block, next_block):
                    result_parts.append("")  # Add blank line

        # Join and clean up
        result = "\n".join(result_parts)

        # Remove excessive blank lines (no more than one blank line between blocks)
        result = re.sub(r"\n\n\n+", "\n\n", result)

        return result.strip()

    def _needs_separator(self, current_block: Block, next_block: Block) -> bool:
        """
        Determine if two blocks need a blank line between them.

        Args:
            current_block: Current block
            next_block: Next block

        Returns:
            True if blocks should be separated by blank line
        """
        # Always separate different block types (except some special cases)
        if current_block.type != next_block.type:
            return True

        # Same block types that should be separated
        if current_block.type == "heading":
            return True  # Always separate headers

        if current_block.type == "list":
            # Separate lists with different types (unordered vs ordered, dot vs paren)
            current_list_type = current_block.metadata.get("list_type", "")
            next_list_type = next_block.metadata.get("list_type", "")

            if current_list_type != next_list_type:
                return True

        # For paragraph blocks, separate them from each other
        if current_block.type == "paragraph" and next_block.type == "paragraph":
            return True

        # Default: no separation for same block types (except those handled above)
        return False
