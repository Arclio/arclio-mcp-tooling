# MarkdownDeck Usage Guide

MarkdownDeck allows you to create professional Google Slides presentations from Markdown content. This guide covers the basics of using MarkdownDeck, from simple slide creation to advanced layout controls.

## Table of Contents

- [Markdown Format](#markdown-format)
- [Command Line Usage](#command-line-usage)
- [Python API Usage](#python-api-usage)
- [Advanced Layout Controls](#advanced-layout-controls)
- [Styling Options](#styling-options)
- [Examples](#examples)

## Markdown Format

MarkdownDeck uses a specialized Markdown format designed for presentations:

### Slide Structure

- `===` separates slides
- `---` creates vertical sections within a slide
- `***` creates horizontal sections (columns) within a slide
- `@@@` defines the slide footer
- `<!-- notes: Your speaker notes -->` adds speaker notes

### Basic Example

```markdown
# First Slide Title

This is the content of the first slide.

- Bullet point 1
- Bullet point 2

===

# Second Slide Title

More content here.

<!-- notes: Remember to explain this in detail -->
```

## Command Line Usage

MarkdownDeck provides a command-line interface for quick presentation creation:

```bash
# Create a presentation from a markdown file
markdowndeck create presentation.md --title "My Presentation"

# Read from stdin
cat presentation.md | markdowndeck create - --title "My Presentation"

# List available themes
markdowndeck themes

# Create with a specific theme
markdowndeck create presentation.md --theme THEME_ID

# Save output details to a file
markdowndeck create presentation.md -o output.json
```

For more options:

```bash
markdowndeck --help
markdowndeck create --help
```

## Python API Usage

### Basic Usage

```python
from markdowndeck import create_presentation
from google.oauth2.credentials import Credentials

# Prepare credentials
credentials = Credentials(
    token=None,
    refresh_token="your-refresh-token",
    token_uri="https://oauth2.googleapis.com/token",
    client_id="your-client-id",
    client_secret="your-client-secret",
    scopes=["https://www.googleapis.com/auth/presentations"]
)

# Create presentation
result = create_presentation(
    markdown="""
    # Example Presentation

    This is a simple example slide.

    * Bullet point 1
    * Bullet point 2
    """,
    title="API Example",
    credentials=credentials
)

print(f"Created presentation: {result['presentationUrl']}")
```

### Get Available Themes

```python
from markdowndeck import get_themes

themes = get_themes(credentials=credentials)
for theme in themes:
    print(f"{theme['name']} (ID: {theme['id']})")
```

### Generate API Requests Without Execution

```python
from markdowndeck import markdown_to_requests

requests = markdown_to_requests(
    markdown="# Title\n\nContent",
    title="Request Example"
)

# Use the requests with your own API client
print(requests["title"])
print(f"Generated {len(requests['slide_batches'])} batches")
```

## Advanced Layout Controls

MarkdownDeck provides fine-grained layout control through directives:

### Layout Directives

Directives control size, position, and styling:

```markdown
[width=2/3][align=center][background=#f5f5f5]
Content with these properties
```

### Common Directives

- `[width=X]` - Set width (fraction, percentage, or pixels)
- `[height=X]` - Set height (fraction, percentage, or pixels)
- `[align=X]` - Horizontal alignment (left, center, right)
- `[valign=X]` - Vertical alignment (top, middle, bottom)
- `[background=X]` - Background color or image URL
- `[color=X]` - Text color
- `[fontsize=X]` - Font size

### Vertical Layout Example

```markdown
# Slide Title

[height=30%]
Top section content

---

[height=70%]
Bottom section content
```

### Horizontal Layout Example

```markdown
# Slide Title

[width=2/3]
Main content area

---

[width=1/3][background=#f5f5f5]
Sidebar content
```

## Styling Options

MarkdownDeck supports standard Markdown formatting:

- `**bold**` or `__bold__`
- `*italic*` or `_italic_`
- `` `code` ``
- `[link text](https://example.com)`
- `![Alt text](image-url.jpg)`
- Code blocks with \`\`\`
- Tables using `|` and `-`

## Examples

### Title and Content Slide

```markdown
# Quarterly Results

Q3 2024 Financial Overview

- Revenue: $10.2M (+15% YoY)
- EBITDA: $3.4M (+12% YoY)
- Cash balance: $15M
```

### Two-Column Layout

```markdown
# Split Layout

[width=60%]

## Main Column

- Primary content
- Important details
- Key metrics

---

[width=40%][background=#f0f8ff]

## Sidebar

Supporting information and notes
```

### Image with Caption

```markdown
# Product Overview

[align=center]
![Product Screenshot](image-url.jpg)

[align=center]
Our latest product design
```

### Complex Layout

```markdown
# Dashboard Overview

[height=30%][align=center]

## Key Metrics

Revenue: $1.2M | Users: 45K | Conversion: 3.2%

---

[width=50%]

## Regional Data

- North America: 45%
- Europe: 30%
- Asia: 20%
- Other: 5%

---

[width=50%][background=#f5f5f5]

## Quarterly Trend

![Chart](chart-url.jpg)

---

[height=20%]

## Action Items

1. Improve APAC conversion
2. Launch new pricing tier
3. Update dashboards

@@@

Confidential - Internal Use Only

<!-- notes: Discuss action items in detail and assign owners -->
```

For more examples and advanced usage, refer to the full documentation.
