# MarkdownDeck

MarkdownDeck is a Python library that converts specially formatted Markdown content into professional Google Slides presentations. It provides a robust, high-fidelity conversion with precise control over slide layouts, positioning, and styling.

## Features

- **Composable Layouts**: Create sophisticated slide layouts with multiple sections and precise positioning
- **Flexible Formatting**: Control alignment, sizing, backgrounds, and other visual properties
- **High-fidelity Conversion**: Preserves structure, formatting, and visual elements
- **Intelligent Space Distribution**: Automatically calculates dimensions for sections without explicit sizing
- **Multi-slide Support**: Handles complex presentations with multiple slides
- **Rich Content Support**: Headers, lists, tables, code blocks, images, and more
- **Speaker Notes**: Add presenter notes to any slide
- **Command-line Interface**: Convert markdown files from the terminal
- **Multiple Authentication Options**: Flexible integration with Google OAuth

## Installation

```bash
# Install from PyPI (when available)
pip install markdowndeck

# Install from source
git clone https://github.com/yourusername/markdowndeck.git
cd markdowndeck
pip install -e .
```

## Markdown Format

MarkdownDeck uses a specialized markdown format with layout directives:

```markdown
# First Slide Title

Regular content goes here

- Bullet point 1
- Bullet point 2

===

# Second Slide Title

[width=2/3][align=center]
Main content section

---

[width=1/3]
Sidebar content

---

[background=#f5f5f5]
Another vertical section

@@@

Footer content with references
```

### Slide Structure

- `===` separates slides
- `---` creates vertical sections within a slide
- `***` creates horizontal sections within a slide
- `@@@` defines the slide footer

### Layout Directives

Control size, position, and styling with directives in square brackets:

```markdown
[width=2/3] # Element takes 2/3 of available width
[width=50%] # Element takes 50% of available width
[height=40%] # Element takes 40% of available height
[align=center] # Centers content horizontally
[align=right] # Right-aligns content
[valign=middle] # Vertically centers content
[background=#f5f5f5] # Sets background color
[background=url(image_url)] # Sets background image
```

Multiple directives can be combined: `[width=2/3][align=center][background=#f5f5f5]`

## Usage Examples

### Basic Example

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
    scopes=['https://www.googleapis.com/auth/presentations']
)

# Convert Markdown to a Google Slides presentation
result = create_presentation(
    markdown="""
    # Quarterly Results

    [align=center]
    Q3 2024 Financial Overview

    ---

    ## Key Metrics

    [width=1/2]
    * Revenue: $10.2M (+15% YoY)
    * EBITDA: $3.4M (+12% YoY)
    * Cash balance: $15M

    ***

    [width=1/2]
    ![Quarterly Chart](chart_url)

    @@@

    Confidential - Internal Use Only

    ===

    # Questions?

    [background=#f0f8ff][align=center]
    Contact: finance@example.com
    """,
    title="Quarterly Financial Results",
    credentials=credentials
)

print(f"Created presentation: {result['presentationUrl']}")
```

### CLI Usage

```bash
# Set up environment variables for authentication
export SLIDES_CLIENT_ID="your-client-id"
export SLIDES_CLIENT_SECRET="your-client-secret"
export SLIDES_REFRESH_TOKEN="your-refresh-token"

# Convert Markdown file to Slides
markdowndeck presentation.md --title "My Presentation"

# Read from stdin
cat presentation.md | markdowndeck - --title "My Presentation"
```

## Layout System

MarkdownDeck's layout system gives you precise control over slide composition:

### Vertical Stacking

```markdown
# Slide Title

First section content

---

Second section content (appears below first section)

---

Third section content (appears below second section)
```

### Horizontal Arrangement

```markdown
# Slide Title

[width=1/3]
Left column content

---

[width=2/3]
Right column content (wider than left column)
```

### Complex Layouts

```markdown
# Slide Title

[height=30%]
Top section

---

[width=50%]
Bottom left

---

[width=50%]
Bottom right
```

### Implicit Sizing

When some sections have explicit dimensions and others don't, MarkdownDeck automatically distributes the remaining space:

```markdown
# Slide Title

[width=1/4]
First column

---

# No width specified - will be allocated remaining 3/4 of space

Second column
```

## Supported Markdown Features

Beyond layouts, MarkdownDeck supports standard markdown features:

- Headers (`# H1`, `## H2` through `###### H6`)
- Paragraphs (blank line separation)
- Formatting: **bold**, _italic_, ~~strikethrough~~, `inline code`
- Lists (ordered and unordered, with nesting)
- Tables (`| Header | Header |`)
- Images (`![Alt text](URL)`)
- Links (`[Text](URL)`)
- Code blocks (` ```language ` blocks)
- Blockquotes (`> quote`)
- Speaker notes (`<!-- notes: Your notes here -->`)

## Authentication Options

MarkdownDeck supports several authentication methods:

1. **Pass Google OAuth credentials** directly to the `create_presentation` function
2. **Pass an existing Google API service** if you already have one initialized
3. **Use environment variables**:
   - `SLIDES_CLIENT_ID`
   - `SLIDES_CLIENT_SECRET`
   - `SLIDES_REFRESH_TOKEN`
4. **Use a service account** by setting `GOOGLE_APPLICATION_CREDENTIALS` to the path of your service account JSON file

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/markdowndeck.git
cd markdowndeck

# Create virtual environment (optional)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"
```

### Testing

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit

# Run integration tests (requires API credentials)
export RUN_INTEGRATION_TESTS=1
pytest tests/integration

# Run with coverage
pytest --cov=markdowndeck
```

## Architecture

MarkdownDeck uses a modular architecture:

1. **Parser**: Modular system that converts markdown to an intermediate representation:

   - SlideExtractor: Splits content into individual slides
   - SectionParser: Handles vertical and horizontal sections
   - DirectiveParser: Processes layout directives
   - ContentParser: Converts markdown elements to slide elements
   - LayoutProcessor: Handles layout calculations and implicit sizing

2. **Models**: Defines the data structures for presentations, slides, and elements

3. **Layout Manager**: Calculates element positions and handles overflow

4. **API Request Generator**: Converts the intermediate representation to Google Slides API requests

5. **API Client**: Handles communication with the Google Slides API

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
