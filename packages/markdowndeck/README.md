# MarkdownDeck

[![Python Version][python-shield]][python-url]
[![PyPI Version][pypi-shield]][pypi-url]
[![License][license-shield]][license-url]
[![Build Status][build-shield]][build-url] **Transform your Markdown into polished Google Slides presentations with programmatic control and intelligent layout.**

MarkdownDeck is a Python library designed to bridge the gap between LLM-generated content and structured, visually appealing presentations. It converts a specialized Markdown dialect, augmented with intuitive layout directives, into Google Slides, handling the complexities of API interactions and layout calculations.

## Why MarkdownDeck? The Challenge with LLMs and Presentation APIs

Large Language Models (LLMs) excel at generating structured, human-readable text like Markdown. However, tasking them to directly produce the verbose, deeply nested, and perfectly validated JSON required by rich APIs, such as Google Slides, is often:

- **Error-Prone & Complex for LLMs:** Managing object IDs, styling objects, precise coordinates, and relationships for numerous slide elements is a difficult task for LLMs, leading to unreliable outputs.
- **Hard to Debug:** If an LLM generates faulty API JSON, debugging it is a significant challenge. Markdown, in contrast, is human-readable and easier to troubleshoot.
- **Inefficient for Context Windows:** Large JSON payloads for API requests can consume a significant portion of an LLM's context window, reducing efficiency.

**MarkdownDeck solves these problems by providing a powerful abstraction layer.** It allows LLMs (and developers) to define presentation structure and content using a simple, intuitive Markdown-based syntax, while MarkdownDeck handles the heavy lifting of:

- **Parsing and Interpretation:** Understanding the Markdown structure and custom layout directives.
- **Intelligent Layout Management:** Calculating element positions, sizes, and handling overflow across slides. This includes managing complex multi-column layouts and distributing space automatically.
- **API Request Generation:** Translating the high-level Markdown representation into the precise Google Slides API calls.

This approach leads to:

- **Simplicity & Intuition:** LLMs can "think" in terms of slide structure (title, columns, lists, images) more naturally using Markdown.
- **Maintainability:** Changes to the Google Slides API are handled within MarkdownDeck, shielding the LLM logic.
- **Decoupling:** The AI's content generation is decoupled from API specifics, making the system more robust and adaptable.
- **Testability:** MarkdownDeck itself is a well-defined, testable utility with clear inputs and outputs.

## Key Features

- **Markdown-to-Slides:** Convert specially formatted Markdown into Google Slides presentations.
- **Composable Layouts:** Define slides with multiple vertical and horizontal sections for sophisticated layouts.
- **Layout Directives:** Fine-tune element `width`, `height`, `align` (horizontal), `valign` (vertical), `background`, `padding`, `color`, `fontsize`, and more using simple bracketed commands.
- **Intelligent Space Distribution:** Automatic calculation of dimensions for sections without explicit sizing.
- **Rich Content Support:** Handles headings, paragraphs, bulleted and ordered lists (with nesting), tables, images, code blocks (with syntax highlighting hints), blockquotes, and inline formatting (bold, italic, strikethrough, inline code, links).
- **Speaker Notes & Footers:** Easily add presenter notes and consistent footers to your slides.
- **Slide Backgrounds:** Set solid color or image backgrounds for slides.
- **Overflow Handling:** Automatically moves content that exceeds slide boundaries to new continuation slides.
- **API Abstraction:** Provides both a high-level `create_presentation` function and a `markdown_to_requests` function to generate API request bodies for more control.
- **Authentication Options:** Supports various Google OAuth methods, including service accounts and user credentials via environment variables or token files.
- **Command-Line Interface (CLI):** Convert Markdown files directly from your terminal.
- **Core Component of Arclio MCP GSuite:** Used by the `create_presentation_from_markdown` tool within the Arclio MCP GSuite package, enabling AI agents to generate presentations.

## Installation

MarkdownDeck requires Python 3.10 or higher.

```bash
pip install markdowndeck
```

To install from source (e.g., for development):

```bash
# Clone the repository (assuming part of the arclio-mcp-tooling monorepo)
# git clone [https://github.com/arclio/arclio-mcp-tooling.git](https://github.com/arclio/arclio-mcp-tooling.git)
# cd arclio-mcp-tooling/packages/markdowndeck
#
# Or if checking out markdowndeck standalone (see Development section for full monorepo context)
# git clone [https://github.com/your-org/markdowndeck.git](https://github.com/your-org/markdowndeck.git)
# cd markdowndeck

pip install -e .
```

## MarkdownDeck Format

Define your presentation structure and content using standard Markdown, enhanced with special separators and layout directives.

### Slide Structure

- **`===` (Slide Separator):** Use three or more equals signs on a line by themselves to denote the end of one slide and the beginning of the next.
- **`---` (Vertical Section Separator):** Use three or more hyphens on a line by themselves to split the content of a slide into vertical sections (stacked one above the other).
- **`\***` (Horizontal Section Separator):\** Use three or more asterisks on a line by themselves to split the content *within\* a vertical section into horizontal sections (columns, arranged side-by-side).
- **`@@@` (Footer Separator):** Content below three or more '@' symbols on a line by themselves will be treated as the slide's footer.
- **`# Slide Title` (H1 for Slide Title):** The first H1 heading on a slide is typically treated as the slide's main title. Subsequent H1 or H2 headings can be used as subtitles or section titles.
- **\`\` (Speaker Notes):** Add speaker notes using an HTML comment block.

### Layout Directives

Directives are placed at the beginning of a section's content (before any visible Markdown) and enclosed in square brackets (`[]`). They control the layout and styling of the section they precede.

- `[width=<value>]`: Sets the width of a section.
  - Fraction: `[width=1/2]` (50% of available width)
  - Percentage: `[width=75%]`
  - Absolute: `[width=300]` (in points; primarily for fixed-size elements if ever applied directly, section widths are usually relative)
- `[height=<value>]`: Sets the height of a section.
  - Fraction: `[height=1/3]` (33% of available height for that section's row)
  - Percentage: `[height=60%]`
  - Absolute: `[height=200]` (in points)
- `[align=<value>]`: Horizontal alignment of content within the section or for a specific element.
  - Values: `left` (default), `center`, `right`, `justify`
- `[valign=<value>]`: Vertical alignment of content within the section.
  - Values: `top` (default), `middle`, `bottom`
- `[background=<value>]`: Sets the background of a section or slide.
  - Color (hex): `[background=#f0f0f0]`
  - Color (named): `[background=lightblue]`
  - Image URL: `[background=url(http://example.com/bg.png)]`
- `[padding=<value>]`: Inner padding for a section (e.g., `[padding=20]`).
- `[color=<value>]`: Text color for elements within the section (e.g., `[color=#333333]`).
- `[fontsize=<value>]`: Font size for text elements (e.g., `[fontsize=18]`).

**Example:**

```markdown
# Monthly Review - March

[height=1/3][background=#eeeeee]

## Key Achievements

- Launched Project Phoenix
- Exceeded Q1 targets by 15%

---

[height=2/3]

### Detailed Breakdown

[width=1/2][padding=10]

#### Sales Performance

- North America: +20%
- Europe: +12%
  - Germany: +15%
  - France: +8%
- Asia: +18%

---

[width=1/2][background=url(images/chart.png)]
@@@
Confidential | © 2025 Arclio Inc.
```

## Usage

### Python API

```python
from markdowndeck import create_presentation, markdown_to_requests
from google.oauth2.credentials import Credentials

# --- Option 1: Create presentation directly (requires auth) ---
# Setup your Google OAuth credentials
# See Authentication section for more details
# Example (replace with your actual credential mechanism):
# credentials = Credentials(...)

markdown_text = """
# My First Slide
This is content for my first slide.

===

# My Second Slide
- Point A
- Point B
"""

try:
    # Ensure you have credentials configured (see Authentication section)
    # For this example, we'll assume credentials are set up via environment variables
    # or a local token.json / credentials.json recognized by `get_credentials()`.
    # If not, pass credentials explicitly:
    # result = create_presentation(markdown=markdown_text, title="My Presentation", credentials=your_credentials_object)

    result = create_presentation(markdown=markdown_text, title="My Awesome Presentation")
    print(f"Presentation created: {result.get('presentationUrl')}")
    print(f"Presentation ID: {result.get('presentationId')}")
except Exception as e:
    print(f"An error occurred: {e}")


# --- Option 2: Generate API requests only (no auth needed for this step) ---
# This is useful if you want to manage the Google Slides API calls yourself.
requests_payload = markdown_to_requests(markdown=markdown_text, title="My Request-Only Presentation")
print(f"\nTitle for API: {requests_payload['title']}")
# print(f"Generated API request batches: {requests_payload['slide_batches']}") # This can be very verbose
print(f"Number of slide batches: {len(requests_payload['slide_batches'])}")
# Each batch corresponds to a slide and contains a list of API requests.
# The 'presentationId' in these batches will be 'PLACEHOLDER_PRESENTATION_ID'.
```

### Command-Line Interface (CLI)

MarkdownDeck provides a CLI for quick conversions. Ensure your Google credentials are set up (see Authentication).

```bash
# Convert a markdown file to a Google Slides presentation
markdowndeck create path/to/your/presentation.md --title "My CLI Presentation"

# Read markdown from stdin
cat path/to/your/presentation.md | markdowndeck create - --title "Stdin Presentation"

# Specify a theme
markdowndeck create presentation.md --theme YOUR_THEME_ID

# Save presentation details (ID, URL) to a JSON file
markdowndeck create presentation.md -o output_details.json

# List available themes (basic list provided by MarkdownDeck)
markdowndeck themes

# Enable verbose logging
markdowndeck -v create presentation.md
```

## Architecture Overview

MarkdownDeck processes Markdown and transforms it into a Google Slides presentation through a modular pipeline:

1.  **Input**: Specially formatted Markdown text.
2.  **Parsing (`markdowndeck.parser`)**:
    - **`SlideExtractor`**: Splits the raw Markdown into chunks, each representing a slide. It also extracts top-level slide metadata like notes, footers, and background directives.
    - **`SectionParser`**: Takes the content of each slide and divides it into structural sections based on `---` (vertical) and `***` (horizontal) separators. This builds a tree-like structure for the slide layout. It uses a `ContentSplitter` to ensure code blocks are not broken during splitting.
    - **`DirectiveParser`**: Scans the beginning of each section's content for `[...]` directives, parses them, and converts their values (e.g., "1/2" to 0.5, "\#FF0000" to a color style).
    - **`ContentParser`**: For each section (now with its directives understood), this component uses `markdown-it-py` to tokenize the actual Markdown content. It then dispatches these tokens to a series of specialized **Formatters** (e.g., `TextFormatter`, `ListFormatter`, `CodeFormatter`, `ImageFormatter`, `TableFormatter`).
    - **Formatters (`markdowndeck.parser.content.formatters`)**: Each formatter is responsible for handling specific Markdown token types (e.g., `fence` tokens for code blocks, `bullet_list_open` for lists). They use the `ElementFactory` to create corresponding element model instances.
    - **`ElementFactory`**: A factory class that constructs specific `Element` model instances (e.g., `TextElement`, `ImageElement`) based on the parsed token data and directives. It also handles the extraction of inline formatting (bold, italic, links) into `TextFormat` objects.
3.  **Intermediate Representation (`markdowndeck.models`)**:
    - The parsing process generates a structured representation of the presentation using dataclasses:
      - `Deck`: Represents the entire presentation.
      - `Slide`: Represents a single slide, containing a list of `Element` objects and `Section` objects (which in turn contain their own `Element` objects post-parsing by `ContentParser`).
      - `Section`: Defines a layout region within a slide, holding its own content, directives, and potentially subsections (for rows).
      - `Element` (and its subclasses like `TextElement`, `ImageElement`, `ListElement`, `CodeElement`, `TableElement`): Represent individual content pieces on a slide.
4.  **Layout Management (`markdowndeck.layout`)**:
    - **`LayoutManager`**: Orchestrates the layout process for each slide.
    - **`PositionCalculator`**: Iterates through the `Slide`'s sections and elements. It interprets layout directives (like `width`, `height`, `align`, `valign`, `padding`) and calculates the precise size (width, height) and (x, y) position for each element on the slide. It handles both explicitly defined dimensions and implicitly distributes space for sections that don't have sizes specified. It uses `Metrics` for content-aware height estimation.
    - **`Metrics` (`markdowndeck.layout.metrics`)**: A collection of heuristic functions to estimate the height of different element types (text, lists, code, tables) based on their content and available width.
    - **`OverflowHandler`**: If content (after positioning) exceeds the available slide height, this component moves the overflowing elements to new, subsequent "continuation" slides.
5.  **API Request Generation (`markdowndeck.api`)**:
    - **`ApiRequestGenerator`**: Takes the processed `Deck` object (with all elements sized and positioned) and translates it into a sequence of JSON objects that conform to the Google Slides API `batchUpdate` request structure.
6.  **API Interaction (`markdowndeck.api`)**:
    - **`ApiClient`**: (Used by `create_presentation`) Handles authentication and sends the generated batch requests to the Google Slides API to create and populate the presentation.

This layered approach ensures separation of concerns, making the system more modular, testable, and easier to maintain.

## Supported Markdown Features

MarkdownDeck supports a wide range of standard Markdown features, which are then mapped to Google Slides elements:

- **Headers**: `# H1` through `###### H6` (H1 often becomes slide title, H2 as subtitle, others as styled text).
- **Paragraphs**: Standard text blocks.
- **Inline Formatting**:
  - `**Bold text**` or `__Bold text__`
  - `*Italic text*` or `_Italic text_`
  - `~~Strikethrough text~~`
  - `` `Inline code` ``
  - `[Link text](http://example.com)`
- **Lists**:
  - Unordered lists (`*`, `-`, `+`)
  - Ordered lists (`1.`, `2.`)
  - Nested lists
- **Tables**: GitHub Flavored Markdown style tables.
- **Images**: `![Alt text](image_url "Optional title")`
- **Code Blocks**: Fenced code blocks with language specification for syntax highlighting hints.
  ````markdown
  ```python
  print("Hello, MarkdownDeck!")
  ```
  ````
- **Blockquotes**: `> Quoted text`
- **Thematic Breaks / Horizontal Rules**: `---`, `***`, `___` (Note: `---` and `***` are also used as section separators if they are on a line by themselves).
- **Speaker Notes**: \`\`
- **Custom Layout Directives**: As described in the "MarkdownDeck Format" section.

## Authentication

MarkdownDeck offers several ways to authenticate with Google APIs:

1.  **Pass `Credentials` Object**: Directly provide a `google.oauth2.credentials.Credentials` object to the `create_presentation()` function.
2.  **Pass Google API `Service` Object**: If you have an existing Google API service resource initialized, you can pass it directly.
3.  **Environment Variables (for user OAuth flow)**:
    - `SLIDES_CLIENT_ID`
    - `SLIDES_CLIENT_SECRET`
    - `SLIDES_REFRESH_TOKEN`
      These are typically obtained from your Google Cloud project's OAuth 2.0 client credentials.
4.  **Service Account**: Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to the path of your service account JSON key file. The necessary scopes (primarily `https://www.googleapis.com/auth/presentations`) will be requested.

The CLI primarily uses environment variables or attempts to find locally saved `token.json` / `credentials.json` from a previous OAuth flow (typically stored in `~/.markdowndeck/`).

## Current Limitations

- **Overflow Handling for Single Large Elements**: While MarkdownDeck handles content overflow by moving elements to new slides, a single element that is itself too large to fit on an empty slide (e.g., a very long table or an extremely tall image) will be moved to a new slide but may still visually overflow that new slide. The system does not currently split individual elements (like table rows or text content) across slides.
- **No Reverse Transformation**: MarkdownDeck currently supports conversion from Markdown _to_ Google Slides only. It does not provide functionality to convert existing Google Slides presentations _back_ into Markdown.
- **Layout Heuristics**: Element height calculation (especially for text) is based on heuristics. While generally effective, complex content or custom fonts (not directly controllable via MarkdownDeck) might lead to slight inaccuracies in layout that could require adjustments in the Markdown.
- **Theme Support for `get_themes`**: The `get_themes()` function currently returns a static, predefined list of common theme IDs as the Google Slides API does not provide a direct endpoint to list all user-available themes dynamically.

## Future Development

If MarkdownDeck proves to be a widely useful tool, future enhancements could include:

- **Advanced Overflow Handling**: Implementing strategies to intelligently split large elements (e.g., tables, lists, code blocks) across multiple slides.
- **Reverse Transformation**: Adding functionality to convert Google Slides presentations back into the MarkdownDeck Markdown format.
- **More Sophisticated Styling Options**: Expanding the directive system or providing more granular control over Google Slides styling features (e.g., specific fonts, more complex shape styling).
- **Direct Support for Google Drive Images**: Easier embedding of images stored in Google Drive.
- **Improved Theme Integration**: If Google APIs evolve, provide better dynamic theme discovery.

## Development & Contribution

MarkdownDeck is an independently installable Python package. However, its primary development and testing occur within the `arclio-mcp-tooling` monorepo.

### Monorepo Context

- **Shared Tooling**: Tests, linting (Ruff), formatting, and build tools (UV, Hatch) are configured and run from the monorepo root.
- **Cross-Package Dependencies**: MarkdownDeck is a dependency of other packages within the monorepo, such as `arclio-mcp-gsuite`.
- **Full Experience**: For a complete development and testing experience, contributors will typically need to work within the context of the cloned `arclio-mcp-tooling` monorepo.

Please refer to the `CONTRIBUTING.md` file in the root of the `arclio-mcp-tooling` monorepo for detailed guidelines on setting up the development environment, running tests, linting, and the contribution process.

### Basic Local Setup (for `markdowndeck` focus)

While monorepo setup is recommended for full contribution, if you are working primarily on `markdowndeck` itself:

```bash
# 1. Clone the monorepo (or just the markdowndeck package if separated)
# Assuming monorepo:
# git clone https://github.com/arclio/arclio-mcp-tooling.git
# cd arclio-mcp-tooling

# 2. Setup development environment (from monorepo root)
make setup # This sets up uv and syncs dependencies

# 3. To work on markdowndeck in editable mode
# From monorepo root (if markdowndeck is listed in workspace.members):
# make install-editable PKGS="markdowndeck"
# Or if in the markdowndeck package directory:
# cd packages/markdowndeck
# uv pip install -e .[dev] # Assuming a [dev] extra for test tools if not covered by monorepo
```

### Running Tests for MarkdownDeck

From the root of the `arclio-mcp-tooling` monorepo:

```bash
# Run all tests for markdowndeck (unit and integration)
make test markdowndeck

# Run only unit tests for markdowndeck
make test-unit markdowndeck

# Run integration tests for markdowndeck (requires API credentials)
# Ensure RUN_INTEGRATION_TESTS=1 is set in your environment or .env
make test-integration markdowndeck
```

## License

MarkdownDeck is licensed under the MIT License. See the [suspicious link removed] file in the monorepo root for details (or a local `LICENSE` file if distributed standalone).

---

_MarkdownDeck: Effortless Presentation Generation for Developers and AI._
