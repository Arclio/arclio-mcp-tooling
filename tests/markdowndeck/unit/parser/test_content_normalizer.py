"""
Comprehensive test suite for ContentNormalizer.

This module contains pytest tests that validate all aspects of the ContentNormalizer
functionality, including indentation handling, block separation, code block preservation,
and edge cases.
"""

import pytest
from markdowndeck.parser.content.content_normalizer import ContentNormalizer


class TestContentNormalizer:
    """Test suite for the ContentNormalizer class."""

    @pytest.fixture
    def normalizer(self):
        """Provide a fresh ContentNormalizer instance for each test."""
        return ContentNormalizer()

    def test_strips_varied_leading_whitespace(self, normalizer):
        """Test 1: Strips varied and mixed (tabs/spaces) leading whitespace."""
        input_text = """    This line has 4 spaces
\t\tThis line has 2 tabs
  \t  This line has mixed indentation
No indentation here
\t   \t More mixed indentation"""

        expected = """This line has 4 spaces
This line has 2 tabs
This line has mixed indentation
No indentation here
More mixed indentation"""

        result = normalizer.normalize(input_text)
        assert result == expected

    def test_preserves_paragraph_integrity(self, normalizer):
        """Test 2: Multi-line paragraph should NOT be split by blank lines."""
        input_text = """This is the first line of a paragraph.
This is the second line of the same paragraph.
And this is the third line, still part of the paragraph."""

        # Should remain as one block with no blank lines inserted
        expected = input_text  # No changes expected for plain paragraph

        result = normalizer.normalize(input_text)
        assert result == expected

    def test_separates_heading_from_paragraph(self, normalizer):
        """Test 3: Heading followed by paragraph should be separated by blank line."""
        input_text = """# This is a heading
This is a paragraph that follows immediately."""

        expected = """# This is a heading

This is a paragraph that follows immediately."""

        result = normalizer.normalize(input_text)
        assert result == expected

    def test_separates_paragraph_from_list(self, normalizer):
        """Test 4: Paragraph followed by list should be separated."""
        input_text = """This is a paragraph.
- First list item
- Second list item"""

        expected = """This is a paragraph.

- First list item
- Second list item"""

        result = normalizer.normalize(input_text)
        assert result == expected

    def test_preserves_consecutive_list_items(self, normalizer):
        """Test 5: Consecutive list items should NOT be separated by blank lines."""
        input_text = """- First list item
- Second list item
- Third list item"""

        expected = """- First list item
- Second list item
- Third list item"""

        result = normalizer.normalize(input_text)
        assert result == expected

    def test_separates_mixed_list_types(self, normalizer):
        """Test 6: Different list types should be separated."""
        input_text = """- Unordered item
1. Ordered item"""

        expected = """- Unordered item

1. Ordered item"""

        result = normalizer.normalize(input_text)
        assert result == expected

    def test_preserves_code_block_indentation(self, normalizer):
        """Test 7: Code block outer indentation stripped, inner indentation preserved."""
        input_text = """    ```python
    def hello():
        print("Hello, world!")
        if True:
            print("Indented code")
    ```"""

        expected = """```python
def hello():
    print("Hello, world!")
    if True:
        print("Indented code")
```"""

        result = normalizer.normalize(input_text)
        assert result == expected

    def test_preserves_table_integrity(self, normalizer):
        """Test 8: Multi-line table should NOT have blank lines inserted between rows."""
        input_text = """| Header 1 | Header 2 | Header 3 |
|----------|----------|----------|
| Cell A1  | Cell B1  | Cell C1  |
| Cell A2  | Cell B2  | Cell C2  |
| Cell A3  | Cell B3  | Cell C3  |"""

        # Table should remain intact with no blank lines between rows
        expected = input_text

        result = normalizer.normalize(input_text)
        assert result == expected

    def test_separates_mixed_blocks_correctly(self, normalizer):
        """Test 9: Mixed blocks written back-to-back should be correctly separated."""
        input_text = """# Heading
This is a paragraph right after the heading.
- This is a list item
- Another list item
| Header | Data |
|--------|------|
| Row1   | Val1 |
> This is a blockquote"""

        expected = """# Heading

This is a paragraph right after the heading.

- This is a list item
- Another list item

| Header | Data |
|--------|------|
| Row1   | Val1 |

> This is a blockquote"""

        result = normalizer.normalize(input_text)
        assert result == expected

    def test_handles_empty_and_whitespace_input(self, normalizer):
        """Test 10: Empty or whitespace-only input should return empty string."""
        # Test completely empty string
        assert normalizer.normalize("") == ""

        # Test whitespace-only string
        assert normalizer.normalize("   \n\t  \n   ") == ""

        # Test string with only newlines
        assert normalizer.normalize("\n\n\n") == ""

    def test_handles_pure_code_block_input(self, normalizer):
        """Test 11: Input that is entirely a code block should be handled correctly."""
        input_text = """    ```javascript
    function greet(name) {
        console.log(`Hello, ${name}!`);
        return name.toUpperCase();
    }
    ```"""

        expected = """```javascript
function greet(name) {
    console.log(`Hello, ${name}!`);
    return name.toUpperCase();
}
```"""

        result = normalizer.normalize(input_text)
        assert result == expected

    def test_handles_multiple_code_blocks(self, normalizer):
        """Test 12: Multiple code blocks with text between should be handled correctly."""
        input_text = """    Here is some explanatory text.
    ```python
    def first_function():
        return "first"
    ```
    Here is some text between code blocks.
    ```javascript
    function secondFunction() {
        return "second";
    }
    ```
    Final explanatory text."""

        expected = """Here is some explanatory text.

```python
def first_function():
    return "first"
```

Here is some text between code blocks.

```javascript
function secondFunction() {
    return "second";
}
```

Final explanatory text."""

        result = normalizer.normalize(input_text)
        assert result == expected

    def test_separates_blockquotes(self, normalizer):
        """Test 13: Text followed by blockquote should be separated."""
        input_text = """This is regular text.
> This is a blockquote that should be separated."""

        expected = """This is regular text.

> This is a blockquote that should be separated."""

        result = normalizer.normalize(input_text)
        assert result == expected

    def test_no_extra_blank_lines_at_end(self, normalizer):
        """Test 14: No extra blank lines should be added at the end."""
        input_text = """# Heading
Content here
- List item"""

        expected = """# Heading

Content here

- List item"""

        result = normalizer.normalize(input_text)
        assert result == expected

        # Ensure no trailing newlines were added beyond what was intended
        assert not result.endswith("\n\n")

    def test_handles_code_blocks_with_tildes(self, normalizer):
        """Test 15: Both ``` and ~~~ code block styles should be preserved."""
        input_text = """    Some text before.
    ```python
    def with_triple_backticks():
        pass
    ```
    Text between blocks.
    ~~~bash
    echo "with triple tildes"
    ls -la
    ~~~
    Text after."""

        expected = """Some text before.

```python
def with_triple_backticks():
    pass
```

Text between blocks.

~~~bash
echo "with triple tildes"
ls -la
~~~

Text after."""

        result = normalizer.normalize(input_text)
        assert result == expected


class TestContentNormalizerAdvanced:
    """Additional advanced tests for ContentNormalizer edge cases."""

    @pytest.fixture
    def normalizer(self):
        """Provide a fresh ContentNormalizer instance for each test."""
        return ContentNormalizer()

    def test_handles_nested_backticks_in_code(self, normalizer):
        """Test 16: Code blocks containing backticks should be preserved correctly."""
        input_text = """    ```markdown
    Use `inline code` like this.
    Or use ```triple backticks``` for blocks.
    ```"""

        expected = """```markdown
Use `inline code` like this.
Or use ```triple backticks``` for blocks.
```"""

        result = normalizer.normalize(input_text)
        assert result == expected

    def test_handles_code_with_directives_syntax(self, normalizer):
        """Test 17: Code containing directive-like syntax should not be parsed."""
        input_text = """```python
# This should print [align=center] literally
print("[align=center]")
data = {"items": ["[width=100]", "[height=50]"]}
```"""

        # The code content should be preserved exactly
        expected = input_text

        result = normalizer.normalize(input_text)
        assert result == expected

    def test_preserves_inline_code_spans(self, normalizer):
        """Test 18: Inline code spans should be protected from processing."""
        input_text = """This text has `inline [code=true]` that should be preserved.
And here's another `example with [directives]` inside."""

        # Inline code should be preserved
        expected = input_text

        result = normalizer.normalize(input_text)
        assert result == expected

    def test_handles_complex_nested_structures(self, normalizer):
        """Test 19: Complex nested structures with various block types."""
        input_text = """# Main Title
## Subtitle
Here's a paragraph with some text.
### Subsection
- List item 1
  - Nested item
- List item 2
```python
def complex_function():
    # Complex code here
    pass
```
> A blockquote
> spanning multiple lines
Final paragraph."""

        expected = """# Main Title

## Subtitle

Here's a paragraph with some text.

### Subsection

- List item 1
  - Nested item
- List item 2

```python
def complex_function():
    # Complex code here
    pass
```

> A blockquote
> spanning multiple lines

Final paragraph."""

        result = normalizer.normalize(input_text)
        assert result == expected

    def test_handles_code_blocks_with_language_specifiers(self, normalizer):
        """Test 20: Code blocks with various language specifiers."""
        input_text = """```python
print("Python code")
```
```javascript
console.log("JavaScript code");
```
```bash
echo "Bash script"
```
```
Plain code block without language
```"""

        # All code blocks should be preserved with their language specifiers
        expected = input_text

        result = normalizer.normalize(input_text)
        assert result == expected

    def test_handles_ordered_lists_with_different_markers(self, normalizer):
        """Test 21: Ordered lists with different number styles."""
        input_text = """1. First item
2. Second item
10. Tenth item
1) Item with parenthesis
2) Another item"""

        expected = """1. First item
2. Second item
10. Tenth item

1) Item with parenthesis
2) Another item"""

        result = normalizer.normalize(input_text)
        assert result == expected

    def test_handles_horizontal_rules(self, normalizer):
        """Test 22: Horizontal rules should be treated as block elements."""
        input_text = """Text before rule
---
Text after rule
***
Another rule
___
Final text"""

        expected = """Text before rule

---

Text after rule

***

Another rule

___

Final text"""

        result = normalizer.normalize(input_text)
        assert result == expected

    def test_preserves_existing_blank_lines(self, normalizer):
        """Test 23: Existing blank lines should be preserved appropriately."""
        input_text = """# Heading

This paragraph already has proper spacing.

- List item with existing spacing

Another paragraph with proper spacing."""

        # Should not add extra blank lines where they already exist
        expected = """# Heading

This paragraph already has proper spacing.

- List item with existing spacing

Another paragraph with proper spacing."""

        result = normalizer.normalize(input_text)
        assert result == expected

    def test_handles_deeply_indented_content(self, normalizer):
        """Test 24: Deeply indented content mixed with code blocks."""
        input_text = """        # Very indented heading
            This paragraph is also deeply indented.
        ```python
        # This code block is indented too
        def deeply_nested():
            if True:
                print("Deep nesting preserved")
        ```
            Final indented paragraph."""

        expected = """# Very indented heading

This paragraph is also deeply indented.

```python
# This code block is indented too
def deeply_nested():
    if True:
        print("Deep nesting preserved")
```

Final indented paragraph."""

        result = normalizer.normalize(input_text)
        assert result == expected

    def test_handles_mixed_list_markers(self, normalizer):
        """Test 25: Mixed unordered list markers should be handled correctly."""
        input_text = """- Item with dash
* Item with asterisk
+ Item with plus
- Back to dash"""

        # Different markers are still the same list type, so no separation
        expected = """- Item with dash
* Item with asterisk
+ Item with plus
- Back to dash"""

        result = normalizer.normalize(input_text)
        assert result == expected

    def test_handles_multiline_blockquotes(self, normalizer):
        """Test 26: Multi-line blockquotes should stay together."""
        input_text = """> First line of quote
> Second line of quote
> Third line of quote"""

        expected = """> First line of quote
> Second line of quote
> Third line of quote"""

        result = normalizer.normalize(input_text)
        assert result == expected

    def test_handles_code_fences_with_extra_backticks(self, normalizer):
        """Test 27: Code fences with more than 3 backticks."""
        input_text = """````python
```
This is a code block that contains triple backticks
```
````"""

        # Should preserve the outer fence with 4 backticks
        expected = input_text

        result = normalizer.normalize(input_text)
        assert result == expected

    def test_handles_empty_code_blocks(self, normalizer):
        """Test 28: Empty code blocks should be preserved."""
        input_text = """Text before

```
```

Text after"""

        expected = """Text before

```
```

Text after"""

        result = normalizer.normalize(input_text)
        assert result == expected

    def test_handles_tab_indented_content(self, normalizer):
        """Test 29: Tab-indented content should be properly dedented."""
        input_text = """\t\t# Heading with tabs
\t\tParagraph with tabs
\t\t- List with tabs
\t\t```python
\t\tdef function():
\t\t\tpass
\t\t```"""

        expected = """# Heading with tabs

Paragraph with tabs

- List with tabs

```python
def function():
\tpass
```"""

        result = normalizer.normalize(input_text)
        assert result == expected

    def test_handles_multiple_sequential_headings(self, normalizer):
        """Test 30: Multiple sequential headings should each be separated."""
        input_text = """# Heading 1
## Heading 2
### Heading 3
#### Heading 4"""

        expected = """# Heading 1

## Heading 2

### Heading 3

#### Heading 4"""

        result = normalizer.normalize(input_text)
        assert result == expected

    def test_separates_consecutive_paragraphs_with_blank_lines(self, normalizer):
        """Test 31: Consecutive paragraphs separated by blank lines should remain separate."""
        input_text = """First paragraph with
multiple lines that should
stay together as one element.

Second paragraph that should
be completely separate from the first.

Third paragraph here."""

        # The blank lines should be preserved to maintain paragraph separation
        expected = """First paragraph with
multiple lines that should
stay together as one element.

Second paragraph that should
be completely separate from the first.

Third paragraph here."""

        result = normalizer.normalize(input_text)
        assert result == expected

    def test_parser_bug_reproduction_case(self, normalizer):
        """Test 32: Reproduce the exact case from the failing parser test."""
        input_text = """[color=blue][fontsize=16] Directive text should be clean.

    ### Indented Heading [align=center]

Text block with
multiple lines that should
stay together as one element.

Another paragraph [style=bold] with directives."""

        # This should preserve the blank lines between distinct blocks
        expected = """[color=blue][fontsize=16] Directive text should be clean.

### Indented Heading [align=center]

Text block with
multiple lines that should
stay together as one element.

Another paragraph [style=bold] with directives."""

        result = normalizer.normalize(input_text)
        assert result == expected
