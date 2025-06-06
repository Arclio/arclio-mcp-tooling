# MarkdownDeck Usage Guide

This guide provides a comprehensive overview of the MarkdownDeck library, from basic syntax to advanced layout control. It is designed for both developers and for LLMs that generate presentation content.

## Table of Contents

- [MarkdownDeck Usage Guide](#markdowndeck-usage-guide)
  - [Table of Contents](#table-of-contents)
  - [Core Concepts: How the Layout Engine Thinks](#core-concepts-how-the-layout-engine-thinks)
    - [1. The Universal Section Model](#1-the-universal-section-model)
    - [2. Stacking with Vertical Sections (`---`)](#2-stacking-with-vertical-sections----)
    - [3. Columns with Horizontal Sections (`***`)](#3-columns-with-horizontal-sections-)
    - [4. Overflow Handling](#4-overflow-handling)
  - [Markdown Syntax Reference](#markdown-syntax-reference)
  - [Layout Directives Reference](#layout-directives-reference)
  - [Styling and Content](#styling-and-content)
  - [Usage](#usage)
    - [Python API](#python-api)
    - [Command-Line Interface (CLI)](#command-line-interface-cli)
  - [Examples](#examples)
    - [Simple Two-Column Slide](#simple-two-column-slide)
    - [Complex Nested Layout](#complex-nested-layout)
- [Dashboard Analysis](#dashboard-analysis)
  - [Main Content Area](#main-content-area)
    - [Sidebar](#sidebar)

## Core Concepts: How the Layout Engine Thinks

To use MarkdownDeck effectively, it's essential to understand its layout philosophy.

#### 1. The Universal Section Model

Every slide's content area is composed of **sections**. Even if you don't define any sections with `---` or `***`, your content is placed into a single "root" section that fills the slide body.

#### 2. Stacking with Vertical Sections (`---`)

Using the `---` separator creates a new **vertical section** stacked below the previous one. The layout engine calculates the height each section needs based on its content and places them sequentially from top to bottom. This is the primary mechanism for creating content that may **overflow** onto subsequent slides.

```markdown
# Vertical Sections

[height=30%]
This is the top section.

---

This section is stacked below the first.
Its height will be calculated automatically.
```

#### 3. Columns with Horizontal Sections (`***`)

Using the `***` separator inside a vertical section creates **horizontal sections (columns)**. The layout engine divides the available horizontal space among these columns. If columns don't have an explicit `[width]` directive, the space is divided equally.

```markdown
# Two-Column Layout

[width=1/2]
This is the left column.

---

[width=1/2]
This is the right column.
```

#### 4. Overflow Handling

MarkdownDeck's layout engine is "overflow-blind"—it will calculate the required space for all content, even if it runs off the slide. A separate **Overflow Handler** then takes this overflowing slide and intelligently splits it into multiple, correctly formatted slides, ensuring nothing is cut off. This process is automatic.

## Markdown Syntax Reference

| Syntax                | Purpose                                                                                   |
| --------------------- | ----------------------------------------------------------------------------------------- |
| `# My Title`          | The first H1 heading (`#`) on a slide becomes its title.                                  |
| `===`                 | **Slide separator.** Creates a new slide.                                                 |
| `---`                 | **Vertical section separator.** Stacks content vertically.                                |
| `***`                 | **Horizontal section separator.** Creates columns within a vertical section.              |
| `@@@`                 | **Footer separator.** Content below this line becomes the slide's footer.                 |
| `<!-- notes: ... -->` | **Speaker Notes.** Adds notes visible only in presenter view. Can be anywhere on a slide. |

## Layout Directives Reference

Directives are placed in `[key=value]` format at the beginning of a section or element to control its layout and style.

| Directive            | Description                                            | Example Values                                   |
| -------------------- | ------------------------------------------------------ | ------------------------------------------------ |
| **Sizing**           |                                                        |                                                  |
| `width`              | Sets the width of a section or element.                | `1/2`, `75%`, `300` (points)                     |
| `height`             | Sets the height of a section.                          | `1/3`, `25%`, `200` (points)                     |
| **Alignment**        |                                                        |                                                  |
| `align`              | Horizontal alignment of content within a section.      | `left`, `center`, `right`, `justify`             |
| `valign`             | Vertical alignment of content within a section.        | `top`, `middle`, `bottom`                        |
| **Visual Styling**   |                                                        |                                                  |
| `background`         | Sets the background for a section.                     | `#f0f8ff`, `url(https://.../img.png)`, `ACCENT1` |
| `color`              | Sets the text color for the section.                   | `#333333`, `red`, `TEXT2`                        |
| `border`             | Sets a border around a section.                        | `1pt solid #cccccc`, `2px dashed red`            |
| `border-radius`      | Sets the corner radius for a section's border.         | `8`, `10px`                                      |
| `opacity`            | Sets the opacity of a section.                         | `0.8`, `0.5`                                     |
| **Typography**       |                                                        |                                                  |
| `fontsize`           | Sets the font size for text in the section.            | `18`, `12.5`                                     |
| `font-family`        | Sets the font family for text.                         | `Arial`, `"Times New Roman"`                     |
| `line-spacing`       | Sets the line spacing for paragraphs.                  | `1.5` (for 150% spacing)                         |
| **Spacing & Indent** |                                                        |                                                  |
| `padding`            | Sets the inner padding for a section.                  | `10`, `15.5`                                     |
| `margin-top`         | Adds a margin above an element.                        | `10`                                             |
| `margin-bottom`      | Adds a margin below an element.                        | `20`                                             |
| `indent-start`       | Indents all lines of a paragraph.                      | `25`                                             |
| `indent-first-line`  | Indents only the first line of a paragraph.            | `30`                                             |
| **Table Specific**   |                                                        |                                                  |
| `cell-align`         | Sets vertical alignment for table cells.               | `top`, `middle`, `bottom`                        |
| `cell-background`    | Sets the background color for cells in a `cell-range`. | `#eeeeee`, `ACCENT1`                             |
| `cell-range`         | Specifies a range for cell styling (row,col:row,col).  | `0,0:0,2` (first row, three columns)             |

## Styling and Content

MarkdownDeck supports standard Markdown for rich text formatting:

- `**bold**` or `__bold__`
- `*italic*` or `_italic_`
- `~strikethrough~`
- `` `inline code` ``
- `[link text](https://example.com)`
- `![Alt text](https://.../image.png)`
- Code blocks using triple backticks (``````)
- Tables using pipe `|` and dash `-` syntax.

## Usage

### Python API

```python
from markdowndeck import create_presentation
# Ensure you have credentials configured via environment variables or a local file.
# See the main README for authentication details.

markdown = """
# My Presentation Title
Content for the first slide.
===
# Second Slide
More content.
"""

# Create the presentation
result = create_presentation(
    markdown=markdown,
    title="My API Presentation"
)

print(f"Presentation created: {result.get('presentationUrl')}")
```

### Command-Line Interface (CLI)

```bash
# Create a presentation from a file
markdowndeck create presentation.md --title "My CLI Presentation"

# Read from stdin and specify a theme
cat presentation.md | markdowndeck create - --theme "THEME_ID"
```

## Examples

### Simple Two-Column Slide

```markdown
# Product Features

[width=1/2]

### Feature A

- Detail 1
- Detail 2
- Detail 3

---

[width=1/2]

### Feature B

- Detail 1
- Detail 2
- Detail 3
```

### Complex Nested Layout

This example shows a slide with a main content area on the left and a sidebar on the right. The sidebar itself is split into two vertical sections.

```markdown
# Dashboard Analysis

[width=2/3]

## Main Content Area

This section takes up two-thirds of the slide width. It can contain any content, like this text block, lists, or tables.

- Point one
- Point two

![A relevant chart](https://www.gstatic.com/charts/images/google-default-line-chart.png)

---

[width=1/3][background=#f5f5f5][padding=15]

### Sidebar

This sidebar takes up one-third of the width.

---

[valign=bottom]
This is a second section within the sidebar, aligned to the bottom. It's useful for summary notes or calls to action.
```
