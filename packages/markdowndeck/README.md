# MarkdownDeck

[![Python Version][python-shield]][python-url]
[![PyPI Version][pypi-shield]][pypi-url]
[![License][license-shield]][license-url]
[![Build Status][build-shield]][build-url]

<div align="center">

**Transform Markdown into professional Google Slides presentations with programmatic control, intelligent layout, and precise styling.**

</div>

MarkdownDeck is an enterprise-grade Python library that bridges the gap between simple content generation and the creation of structured, visually appealing Google Slides presentations. It converts an enhanced Markdown dialect into Google Slides, transparently managing complex API interactions, layout calculations, and content overflow.

## Why MarkdownDeck?

Generating presentations through direct API calls is notoriously difficult, especially for automated systems and Large Language Models (LLMs):

- **API Complexity Barrier:** The Google Slides API requires verbose, nested JSON with precise coordinates, object IDs, and carefully sequenced requests. This is difficult for developers and nearly impossible for LLMs to generate reliably.
- **The Layout Problem:** Content must be manually positioned. Calculating the space required for wrapped text, lists, or tables and then distributing that content across multiple slides is a significant engineering challenge.
- **Context Window Limitations:** Large, raw JSON payloads for slide creation consume valuable context window space when interacting with LLMs, limiting their ability to handle complex presentations.

**MarkdownDeck solves these challenges** by providing a robust abstraction layer that enables developers and AI agents to define presentations using an intuitive Markdown dialect, while it handles all the underlying complexity.

## Key Features

- **Enhanced Markdown-to-Slides Conversion:** Transform a specialized Markdown dialect directly into fully-formed Google Slides presentations.
- **Sophisticated Layout Engine:**
  - Multi-column and nested section layouts with automatic space distribution.
  - Intelligent overflow handling that automatically splits content across multiple, well-formatted slides.
  - Precise positioning with granular alignment and spacing controls.
- **Complete Content Element Support:**
  - Titles, subtitles, and text with rich formatting.
  - Bulleted and ordered lists with nesting support.
  - Tables with automatic header styling and formatting.
  - Images with alt text and flexible positioning.
  - Code blocks with language-specific styling.
- **Comprehensive Styling Directives:**
  - **Sizing:** `[width]`, `[height]` (supports fractions, percentages, and absolute points).
  - **Alignment:** `[align]`, `[valign]` for horizontal and vertical control.
  - **Visuals:** `[background]`, `[color]`, `[border]` for sections and elements.
  - **Typography:** `[fontsize]`, `[font-family]`, `[line-spacing]`.
  - **Spacing:** `[padding]`, `[margin]`, `[indent-start]`.
- **Presentation Enhancements:**
  - Speaker notes for presenter view.
  - Custom slide backgrounds (colors or images).
  - Slide footers.
  - Google Slides theme integration.
- **Flexible API:**
  - Direct presentation creation with `create_presentation()`.
  - Pure request generation without execution via `markdown_to_requests()` for custom workflows.
- **Full Authentication Support:**
  - Service accounts for automated, server-side workflows.
  - User credentials with a built-in OAuth flow.
  - Secure configuration via environment variables.

## Installation

```bash
pip install markdowndeck
```

## Architecture Overview

MarkdownDeck uses a robust, four-stage pipeline to convert Markdown into a final presentation. This separation of concerns ensures predictability and stability.

1.  **Parse (`Parser`)**: The initial Markdown text is parsed into a structured `Deck` object. This stage identifies slides, sections, and content elements, converting them into internal data models.

2.  **Layout (`LayoutCalculator`)**: This is a pure, "overflow-blind" spatial planner. Its sole responsibility is to calculate the ideal position and size for every element and section based on layout rules. It correctly signals overflow by placing content beyond slide boundaries but does not attempt to solve it.

3.  **Overflow (`OverflowHandler`)**: This is a dedicated, recursive content distribution engine. It takes the potentially overflowing output from the calculator and intelligently partitions it across one or more well-formatted, non-overflowing slides.

4.  **Generate (`ApiRequestGenerator`)**: The final list of clean, non-overflowing `Slide` objects is consumed to generate the precise, validated JSON payloads required for the Google Slides API.

This architecture ensures that layout logic is completely decoupled from overflow handling, creating a highly predictable and maintainable system.

## Quick Usage

```python
from markdowndeck import create_presentation
# Make sure to configure authentication (see below)

# Define markdown content
markdown_text = """
# Monthly Sales Report
[align=center]
A summary of our performance in Q1 FY2025.

===

# Q1 Performance

[width=1/2][background=#f0f0f0][padding=10]
## Key Results
- Exceeded targets by 15%
- New client acquisition up 22%
- APAC region leading growth
***
[width=1/2][valign=middle]
![Quarterly Chart](https://www.gstatic.com/charts/images/google-default-bar-chart.png)

---

[background=#f8f8f8]
### Regional Breakdown
| Region        | Sales | YOY Change |
| ------------- | ----- | ---------- |
| North America | $3.2M | +12%       |
| Europe        | $2.8M | +8%        |
| Asia Pacific  | $1.9M | +28%       |

@@@
Confidential | Q1 FY2025

<!-- notes: Highlight APAC performance during presentation -->
"""

# Create the presentation
# This example assumes you have credentials configured via environment variables
result = create_presentation(
    markdown=markdown_text,
    title="Q1 Sales Report"
)

print(f"Presentation created: {result.get('presentationUrl')}")
```

For detailed syntax and examples, please refer to the **[Full Usage Guide](docs/MD_USAGE.md)**.

## Authentication

MarkdownDeck supports multiple authentication methods, loaded in this order:

1.  **Service Account:** Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to the path of your service account JSON file. Ideal for automated, server-side workflows.
2.  **OAuth Environment Variables:** Set the following variables for user-based authentication without a local file flow:
    - `SLIDES_CLIENT_ID`
    - `SLIDES_CLIENT_SECRET`
    - `SLIDES_REFRESH_TOKEN`
3.  **Local Token Files (OAuth Flow):** If no environment variables are found, MarkdownDeck will attempt to use:
    - `~/.markdowndeck/credentials.json`: Your client secrets file.
    - `~/.markdowndeck/token.json`: Your token, which is saved here after the first successful interactive OAuth flow.

## Relationship to Other Packages

MarkdownDeck is a foundational library within the `arclio-mcp-tooling` monorepo. It serves as the core engine for presentation generation and is designed to be used by other packages.

For example, the `google-workspace-mcp` package depends on MarkdownDeck to provide its `create_presentation_from_markdown` tool, exposing this capability to AI models through the Model Context Protocol.

## Future Work

- **Partial Slide Updates:** The current version of MarkdownDeck is optimized for creating complete presentations in a single operation. A key planned enhancement is to support partial updates, such as modifying or replacing a single slide within an existing presentation without regenerating the entire deck.
- **Advanced Styling:** Introduce more granular styling options for lists, text, and shapes.
- **Chart Integration:** Add a simple, declarative syntax for creating data-driven charts.

## License

MarkdownDeck is licensed under the MIT License.

---

[python-shield]: https://img.shields.io/badge/python-3.10+-blue.svg
[python-url]: https://www.python.org/downloads/release/python-3100/
[pypi-shield]: https://img.shields.io/pypi/v/markdowndeck.svg
[pypi-url]: https://pypi.org/project/markdowndeck/
[license-shield]: https://img.shields.io/badge/License-MIT-yellow.svg
[license-url]: https://opensource.org/licenses/MIT
[build-shield]: https://img.shields.io/github/actions/workflow/status/arclio/arclio-mcp-tooling/ci.yml?branch=main&label=build&logo=github
[build-url]: https://github.com/arclio/arclio-mcp-tooling/actions/workflows/ci.yml
