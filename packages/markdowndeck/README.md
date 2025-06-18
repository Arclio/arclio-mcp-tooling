# MarkdownDeck

[![Python Version][python-shield]][python-url]
[![PyPI Version][pypi-shield]][pypi-url]
[![License][license-shield]][license-url]
[![Build Status][build-shield]][build-url]

<div align="center">

**Transform Markdown into professional Google Slides presentations with complete control over layout and styling.**

</div>

## What is MarkdownDeck?

MarkdownDeck is a Python library that converts specially-formatted Markdown into Google Slides presentations. Unlike traditional presentation tools, MarkdownDeck:

- **Creates every slide as a blank canvas** - No themes, no templates, no inherited properties
- **Requires explicit layout structure** - All content MUST be inside fenced blocks (`:::section`, `:::row`, `:::column`)
- **Uses inline directives for all styling** - Directives MUST be on the same line as their target
- **Enforces strict parsing rules** - Content MUST follow the grammar exactly or parsing will fail

## Why MarkdownDeck?

Creating presentations through the Google Slides API requires:

- Complex JSON with exact coordinates
- Sophisticated layout calculations
- Overflow handling across slides
- Proper API request sequencing

MarkdownDeck handles all this complexity while giving you complete control through Markdown.

## Installation

```bash
pip install markdowndeck
```

## Quick Start

```python
from markdowndeck import create_presentation

# Note: Indentation is now fully supported for better readability
markdown_content = """
# Welcome to MarkdownDeck [color=blue][fontsize=36]

## Creating Presentations with Explicit Control

:::section [padding=40][background=#f0f0f0]
    ### Why MarkdownDeck?

    **Key Features:**

    - Every slide is a blank canvas
    - All layout is explicit through fenced blocks
    - Complete control over positioning and styling
    - Automatic overflow to continuation slides

    :::row [gap=30][margin-top=20]
        :::column [width=60%]
            Write your content in the left column.
            All spacing is explicit.
        :::
        :::column [width=40%][align=center]
            ![logo](https://example.com/logo.png) [width=200][height=150]
        :::
    :::
:::

<!-- notes: Remember to explain the blank line rule -->

@@@
Built with MarkdownDeck | 2025
"""

# Create the presentation
result = create_presentation(
    markdown=markdown_content,
    title="My First MarkdownDeck Presentation"
)

print(f"Presentation created: {result['presentationUrl']}")
```

## Critical Rules (MUST READ)

### 1. All Body Content MUST Be Inside Sections

```markdown
# WRONG - Content outside section

This text is not allowed here

# CORRECT - Content inside section

:::section
This text is properly contained
:::
```

### 2. Images MUST Have Both Dimensions

```markdown
# WRONG - Missing height

![image](url.png) [width=400]

# CORRECT - Both width and height specified

![image](url.png) [width=400][height=300]
```

### 3. Directives MUST Be On Same Line

```markdown
# WRONG - Directive on separate line

:::section
[padding=20]
Content here
:::

# CORRECT - Directive on same line as target

:::section [padding=20]
Content here
:::
```

### 4. Strict Fenced Block Hierarchy

- `:::row` can ONLY contain `:::column` blocks
- `:::column` MUST be inside a `:::row`
- `:::section` can ONLY contain content elements (text, images, etc.)

## Core Concepts

### Blank Canvas Philosophy

- Every slide starts with NO formatting or spacing
- The slide is 720×540 points (10×7.5 inches)
- Usable content area is 620×420 points after margins
- You MUST specify all spacing explicitly

### Explicit Fenced Block Layout

All layout structure uses three types of fenced blocks:

```markdown
:::section [directives]
Vertical container for content
:::

:::row [directives]
:::column [directives]
Horizontal layout container
:::
:::

:::column [directives]
Column within a row
:::
```

### Same-Line Directives

All styling and layout control uses directives on the same line:

```markdown
# Blue Title [color=blue][fontsize=36]

:::section [background=#e0e0e0][padding=20]
Content with gray background
:::

![image](url.jpg) [width=400][height=300]
```

## Key Features

- **Automatic Overflow Handling**: Content that exceeds slide boundaries automatically flows to continuation slides
- **Table Row Styling**: Use a dedicated final column for row-specific directives
- **Nested Layouts**: Create complex layouts with multiple levels of sections, rows, and columns
- **Indentation Support**: Full support for indented content to improve readability
- **Speaker Notes**: Add presenter notes with `<!-- notes: your notes here -->`
- **No Default Spacing**: All padding, margins, and gaps default to zero

## Authentication

MarkdownDeck supports multiple authentication methods:

1. **Service Account** (Recommended):

   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
   ```

2. **OAuth with Environment Variables**:
   ```bash
   export SLIDES_CLIENT_ID=your-client-id
   export SLIDES_CLIENT_SECRET=your-client-secret
   export SLIDES_REFRESH_TOKEN=your-refresh-token
   ```

## Common Patterns

### Two-Column Layout

```markdown
:::section [padding=20]
:::row [gap=30]
:::column [width=50%]
Left column content here.
Remember the blank line rule.
:::
:::column [width=50%]
Right column content here.
Each column is independent.
:::
:::
:::
```

### Table with Row Styling

```markdown
:::section

| Product | Price | Stock | [background=#333][color=white] |
| ------- | ----- | ----- | ------------------------------ |
| Widget  | $10   | 50    |                                |
| Gadget  | $25   | 0     | [background=#ffcccc]           |

:::
```

**IMPORTANT**: The final column is NEVER rendered. It exists ONLY for directives.

## API Reference

```python
# Create a presentation
result = create_presentation(
    markdown="Your markdown content",
    title="Presentation Title"
)

# Generate API requests without executing
requests = markdown_to_requests(
    markdown="Your markdown content"
)
```

## Limitations

- NO animations or transitions
- NO video or audio embedding
- NO escape sequences for special characters
- NO theme inheritance - everything is explicit
- All images MUST be publicly accessible via HTTPS

## Best Practices

1. **Use indentation** to improve readability of nested structures
2. **Always specify both dimensions** for images
3. **Always close fenced blocks** with `:::`
4. **Never put content** directly in rows or columns
5. **Test overflow behavior** with large content

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

## MIT License. See [LICENSE](LICENSE) for details.

[python-shield]: https://img.shields.io/badge/python-3.10+-blue.svg
[python-url]: https://www.python.org/downloads/
[pypi-shield]: https://img.shields.io/pypi/v/markdowndeck.svg
[pypi-url]: https://pypi.org/project/markdowndeck/
[license-shield]: https://img.shields.io/badge/License-MIT-yellow.svg
[license-url]: https://opensource.org/licenses/MIT
[build-shield]: https://img.shields.io/github/actions/workflow/status/arclio/markdowndeck/ci.yml?branch=main
[build-url]: https://github.com/arclio/markdowndeck/actions
