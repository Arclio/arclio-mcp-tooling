# MarkdownDeck

[![Python Version][python-shield]][python-url]
[![PyPI Version][pypi-shield]][pypi-url]
[![License][license-shield]][license-url]
[![Build Status][build-shield]][build-url]

**Transform Markdown into professional Google Slides presentations with programmatic control, intelligent layout, and precise styling.**

MarkdownDeck is an enterprise-grade Python library that bridges the gap between content generation and the creation of structured, visually appealing Google Slides presentations. It converts an enhanced Markdown dialect into Google Slides, managing complex API interactions and layout calculations.

## Why MarkdownDeck?

Generating presentations through direct API calls is challenging, especially for automated systems and LLMs:

- **API Complexity Barrier:** The Google Slides API requires verbose, nested JSON with precise coordinates, object IDs, styling objects, and carefully sequenced requests—difficult even for developers, nearly impossible for LLMs to generate reliably.
- **Context Window Limitations:** Large JSON payloads for slide creation consume valuable context window space when using LLMs.
- **Debugging Challenges:** Troubleshooting API-level JSON errors is significantly more complex than validating Markdown syntax.

**MarkdownDeck solves these challenges** by providing a robust abstraction layer that enables developers, AI agents, and LLMs to define presentations using intuitive Markdown syntax while handling the complexity:

- **Intuitive Content Definition:** Define slides, layouts, and styling using familiar Markdown with simple directives.
- **Intelligent Layout Management:** Automatically calculate optimal element positioning, handle content overflow, and manage multi-column layouts.
- **Enterprise-Grade API Integration:** Generate precise, validated Google Slides API requests that work reliably at scale.

## Key Features

- **Enhanced Markdown-to-Slides Conversion:** Transform a specialized Markdown dialect directly into Google Slides presentations.
- **Sophisticated Layout Control:**
  - Multi-column and nested section layouts with automatic space distribution
  - Precise positioning with granular alignment and spacing controls
  - Intelligent overflow handling across slides for content-rich presentations
- **Complete Content Element Support:**
  - Titles, subtitles, and text with rich formatting
  - Bulleted and ordered lists with nesting support
  - Tables with header formatting and cell styling
  - Images with alt text and positioning
  - Code blocks with language-specific styling
  - Blockquotes and styled text
- **Comprehensive Styling Directives:**
  - Element dimensions: `[width]`, `[height]`
  - Alignment: `[align]`, `[valign]`
  - Visual styling: `[background]`, `[color]`, `[border]`
  - Typography: `[fontsize]`, `[font-family]`, `[line-spacing]`
  - Spacing: `[padding]`, `[margin]`, `[indent-start]`
- **Presentation Enhancements:**
  - Speaker notes for presenter view
  - Custom slide backgrounds (colors or images)
  - Footers with automatic page numbering
  - Google Slides theme integration
- **Flexible API Options:**
  - Direct presentation creation with `create_presentation()`
  - Request generation without execution via `markdown_to_requests()`
- **Complete Authentication Support:**
  - Service accounts for automated workflows
  - User credentials with OAuth flow
  - Environment variable configuration

## Installation

```bash
pip install markdowndeck
```

## MarkdownDeck Format

Define presentations using standard Markdown with special separators and layout directives:

### Slide Structure

- **`===`:** Slide separator
- **`---`:** Vertical section separator (stacked sections)
- **`\***`:\*\* Horizontal section separator (columns within a vertical section)
- **`@@@`:** Footer separator
- **`# Heading`:** First H1 becomes the slide title
- **`<!-- notes: ... -->`:** Speaker notes

### Layout Directives

Directives use square brackets at the beginning of sections: `[directive=value]`.

**Common Directives:**

```
[width=1/2]                   # Half width (fraction)
[width=75%]                   # Percentage width
[width=300]                   # Absolute width (points)
[height=1/3]                  # Fractional height
[align=center]                # Horizontal alignment
[valign=middle]               # Vertical alignment
[background=#f5f5f5]          # Background color
[background=url(image.jpg)]   # Background image
[padding=10]                  # Inner padding
[color=#333333]               # Text color
[fontsize=18]                 # Font size (points)
[border=1pt solid #cccccc]    # Border style
```

**Example:**

```markdown
# Monthly Sales Report

[width=1/2][background=#f0f0f0][padding=10]

## First Quarter Results

- Exceeded targets by 15%
- New client acquisition up 22%
- APAC region leading growth

---

[width=1/2][valign=middle]
![Quarterly Chart](https://example.com/chart.png)

---

[background=#f8f8f8]

### Regional Breakdown

| Region        | Sales | YOY Change |
| ------------- | ----- | ---------- |
| North America | $3.2M | +12%       |
| Europe        | $2.8M | +8%        |
| Asia Pacific  | $1.9M | +28%       |

@@@
Confidential | Q1 FY2025 | Page %p

<!-- notes: Highlight APAC performance during presentation -->
```

## Usage

### Python API

```python
from markdowndeck import create_presentation

# Define markdown content
markdown_text = """
# My First Slide
- Point 1 with **bold** text
- Point 2 with *italic* text

===

# Second Slide
[width=1/2]
## Left Column
Content here.
***
[width=1/2]
## Right Column
More content here.
"""

# Create presentation
result = create_presentation(
    markdown=markdown_text,
    title="My Presentation",
    # theme_id="THEME_ID"  # Optional
)

print(f"Presentation created: {result.get('presentationUrl')}")
```

### Command-Line Interface

```bash
# Convert markdown file to Google Slides
markdowndeck create presentation.md --title "My Presentation"

# With additional options
markdowndeck create presentation.md --theme THEME_ID -o output.json

# Read from stdin
cat presentation.md | markdowndeck create -
```

## Authentication

MarkdownDeck supports multiple authentication methods:

1. **Direct Credentials:**

   ```python
   from google.oauth2.credentials import Credentials

   credentials = Credentials(...)
   result = create_presentation(markdown=markdown, credentials=credentials)
   ```

2. **Service Account:**

   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
   ```

3. **OAuth Environment Variables:**

   ```bash
   export SLIDES_CLIENT_ID=your_client_id
   export SLIDES_CLIENT_SECRET=your_client_secret
   export SLIDES_REFRESH_TOKEN=your_refresh_token
   ```

4. **Local Token Files:**
   - `~/.markdowndeck/token.json`: Stores credentials after OAuth flow
   - `~/.markdowndeck/credentials.json`: Client ID file for OAuth

## Architecture Overview

MarkdownDeck uses a modular pipeline architecture:

1. **Parsing:** Converts Markdown into a structured representation

   - `SlideExtractor`: Splits content into slides
   - `SectionParser`: Handles layout sections
   - `DirectiveParser`: Processes layout directives
   - `ContentParser`: Creates element models

2. **Layout:** Calculates precise element positioning

   - `LayoutManager`: Orchestrates layout calculation
   - `PositionCalculator`: Determines element positions
   - `OverflowHandler`: Manages content across slides

3. **API Integration:** Generates and executes API requests
   - `ApiRequestGenerator`: Converts elements to API requests
   - `ApiClient`: Handles API communication

## Current Limitations

- **Single Large Element Overflow:** While content is distributed across slides, a single element too large for one slide may still visually overflow.
- **Layout Heuristics:** Text height calculation uses heuristics that may require adjustments for unusual content.
- **Dynamic Theme Discovery:** Theme listing provides a predefined set rather than dynamically discovering available themes.

## Future Development

**Planned Enhancements:**

- **Additional Slide Operations:**

  - Insert slides at specific positions
  - Update existing slides
  - Delete slides by ID

- **Advanced Styling:**

  - More granular list and text styling options
  - Enhanced shape and border controls

- **Other Presentation Platforms:**

  - Microsoft PowerPoint support
  - HTML slide deck export

- **Chart Integration:**
  - Simple, declarative chart creation syntax
  - Data-driven visualization options

## License

MarkdownDeck is licensed under the MIT License.

---

_MarkdownDeck: Enterprise-grade presentation generation for developers and AI systems._

[python-shield]: https://img.shields.io/badge/python-3.10+-blue.svg
[python-url]: https://www.python.org/downloads/release/python-3100/
[pypi-shield]: https://img.shields.io/pypi/v/markdowndeck.svg
[pypi-url]: https://pypi.org/project/markdowndeck/
[license-shield]: https://img.shields.io/badge/License-MIT-yellow.svg
[license-url]: https://opensource.org/licenses/MIT
[build-shield]: https://img.shields.io/github/actions/workflow/status/arclio/arclio-mcp-tooling/ci.yml?branch=main&label=build&logo=github
[build-url]: https://github.com/arclio/arclio-mcp-tooling/actions/workflows/ci.yml
