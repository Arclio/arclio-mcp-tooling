import pytest
from markdowndeck.parser.section.content_splitter import (
    ContentSplitter,
)


class TestContentSplitter:
    """Unit tests for the ContentSplitter component."""

    @pytest.fixture
    def splitter(self) -> ContentSplitter:
        return ContentSplitter()

    def test_no_code_blocks(self, splitter: ContentSplitter):
        content = "Simple content\n---\nMore simple content"
        protected_content, blocks = splitter._protect_blocks(
            content, splitter.code_block_regex, "CODE"
        )
        assert not blocks
        assert protected_content == content
        restored_content = splitter._restore_blocks(protected_content, blocks)
        assert restored_content == content

    def test_single_code_block_protection_restoration(self, splitter: ContentSplitter):
        code = "def hello():\n    print('world')"
        content = f"Before\n```python\n{code}\n```\nAfter"
        protected_content, blocks = splitter._protect_blocks(
            content, splitter.code_block_regex, "CODE"
        )
        assert len(blocks) == 1
        placeholder = list(blocks.keys())[0]
        assert placeholder in protected_content
        assert f"```python\n{code}\n```" == blocks[placeholder]
        assert "def hello()" not in protected_content
        restored_content = splitter._restore_blocks(protected_content, blocks)
        assert restored_content == content

    def test_multiple_code_blocks(self, splitter: ContentSplitter):
        content = "Text1\n```\ncode1\n```\nText2\n```\ncode2\n```\nText3"
        protected_content, blocks = splitter._protect_blocks(
            content, splitter.code_block_regex, "CODE"
        )
        assert len(blocks) == 2
        restored_content = splitter._restore_blocks(protected_content, blocks)
        assert restored_content == content

    def test_code_block_with_internal_separator_like_patterns(self, splitter: ContentSplitter):
        content = "Section A\n```\n---\n***\n```\nSection B"
        protected_content, blocks = splitter._protect_blocks(
            content, splitter.code_block_regex, "CODE"
        )
        assert "---" not in protected_content
        assert "***" not in protected_content
        restored_content = splitter._restore_blocks(protected_content, blocks)
        assert restored_content == content

    def test_unterminated_code_block(self, splitter: ContentSplitter):
        content = "Text before\n```python\ncode here\nOops, no closing fence."
        protected_content, blocks = splitter._protect_blocks(
            content, splitter.code_block_regex, "CODE"
        )
        assert len(blocks) == 0
        assert protected_content == content

    @pytest.mark.parametrize("separator", [r"^\s*---\s*$", r"^\s*\*\*\*\s*$"])
    def test_split_simple_content(self, splitter: ContentSplitter, separator: str):
        content = "Part 1\n---\nPart 2\n***\nPart 3"
        if "---" in separator:
            result = splitter.split_by_separator(content, separator)
            assert result.parts == ["Part 1", "Part 2\n***\nPart 3"]
        elif "***" in separator:
            result = splitter.split_by_separator(content, separator)
            assert result.parts == ["Part 1\n---\nPart 2", "Part 3"]

    @pytest.mark.parametrize("separator", [r"^\s*---\s*$", r"^\s*\*\*\*\s*$"])
    def test_split_with_code_blocks_containing_separators(
        self, splitter: ContentSplitter, separator: str
    ):
        content = "First part\n```\nContent with --- inside code\n```\nActualSeparator\n---\nThird part\n```\nAnother --- in code\n```"
        result = splitter.split_by_separator(content, r"^\s*---\s*$")
        assert len(result.parts) == 2
        assert "Content with --- inside code" in result.parts[0]
        assert "ActualSeparator" in result.parts[0]
        assert "Another --- in code" in result.parts[1]
        assert "Third part" in result.parts[1]

    def test_split_no_separators(self, splitter: ContentSplitter):
        content = "Just one part\n```\ncode\n```\nend"
        result = splitter.split_by_separator(content, r"^\s*---\s*$")
        assert result.parts == [content]

    def test_split_content_is_only_separator(self, splitter: ContentSplitter):
        result = splitter.split_by_separator("---", r"^\s*---\s*$")
        assert result.parts == []
        result2 = splitter.split_by_separator("   *** \n", r"^\s*\*\*\*\s*$")
        assert result2.parts == []

    def test_split_empty_content(self, splitter: ContentSplitter):
        result = splitter.split_by_separator("", r"^\s*---\s*$")
        assert result.parts == []

    def test_split_adjacent_separators(self, splitter: ContentSplitter):
        content = "A\n---\n---\nB"
        result = splitter.split_by_separator(content, r"^\s*---\s*$")
        assert result.parts == ["A", "B"]
        content2 = "A\n***\n   *** \nB"
        result2 = splitter.split_by_separator(content2, r"^\s*\*\*\*\s*$")
        assert result2.parts == ["A", "B"]

    def test_split_leading_and_trailing_separators(self, splitter: ContentSplitter):
        content = "---\nA\n---\nB\n---"
        result = splitter.split_by_separator(content, r"^\s*---\s*$")
        assert result.parts == ["A", "B"]

    def test_split_complex_interleaving(self, splitter: ContentSplitter):
        content = """
Part 1
```text
--- Code A ---
*** Code B ***
```

---

Part 2

```text
Code C
```

---

## Part 3

Part 4

```text
~~~ Separator D ~~~
```

"""
        vertical_split = splitter.split_by_separator(content, r"^\s*---\s*$")
        assert len(vertical_split.parts) == 3, f"Vertical split parts: {vertical_split.parts}"

        assert "Part 1" in vertical_split.parts[0]
        assert "--- Code A ---" in vertical_split.parts[0]
        assert "*** Code B ***" in vertical_split.parts[0]
        assert "Part 2" in vertical_split.parts[1]
        assert "Code C" in vertical_split.parts[1]
        assert "## Part 3" in vertical_split.parts[2]
        assert "Part 4" in vertical_split.parts[2]
        assert "~~~ Separator D ~~~" in vertical_split.parts[2]

        # Try horizontal splitting on part 2
        part2 = vertical_split.parts[2]
        horizontal_split = splitter.split_by_separator(part2, r"^\s*\*\*\*\s*$")
        assert len(horizontal_split.parts) == 1
        assert horizontal_split.parts[0] == part2

    def test_invalid_regex_pattern_for_separator(self, splitter: ContentSplitter, caplog):
        content = "Some content"
        invalid_pattern = "["  # Invalid regex
        # The message in the log might vary, but should contain "Invalid regex pattern"
        result = splitter.split_by_separator(content, invalid_pattern)
        assert "Invalid regex pattern for separator check" in caplog.text  # Check logging
        assert result.parts == [content]  # Fallback should be the original content

    def test_split_content_that_is_only_code_block(self, splitter: ContentSplitter):
        content = "```\ncode\n---\nmore code\n```"
        result_v = splitter.split_by_separator(content, r"^\s*---\s*$")
        assert len(result_v.parts) == 1
        assert result_v.parts[0] == content

        result_h = splitter.split_by_separator(content, r"^\s*\*\*\*\s*$")
        assert len(result_h.parts) == 1
        assert result_h.parts[0] == content
