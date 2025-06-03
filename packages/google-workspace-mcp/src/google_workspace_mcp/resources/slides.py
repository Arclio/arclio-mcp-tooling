"""
Slides resources for Google Slides data access.
"""

import logging
from typing import Any

from google_workspace_mcp.app import mcp

logger = logging.getLogger(__name__)


@mcp.resource("slides://markdown_formatting_guide")
async def get_markdown_deck_formatting_guide() -> dict[str, Any]:
    """
    Get comprehensive documentation on how to format Markdown for slide creation using markdowndeck.

    Maps to URI: slides://markdown_formatting_guide

    Returns:
        A dictionary containing the formatting guide.
    """
    logger.info("Executing get_markdown_deck_formatting_guide resource")

    return {
        "title": "MarkdownDeck Formatting Guide",
        "description": "Comprehensive guide for formatting Markdown content for slide creation using markdowndeck.",
        "overview": "MarkdownDeck uses a specialized Markdown format with layout directives to create professional Google Slides presentations with precise control over slide layouts, positioning, and styling.",
        "basic_structure": {
            "slide_separator": "===",
            "description": "Use '===' on a line by itself to separate slides.",
            "example": """
# First Slide Title

Content for first slide

===

# Second Slide Title

Content for second slide
""",
        },
        "sections": {
            "vertical_sections": {
                "separator": "---",
                "description": "Creates vertical sections within a slide (stacked top to bottom).",
                "example": """
# Slide Title

Top section content

---

Bottom section content
""",
            },
            "horizontal_sections": {
                "separator": "***",
                "description": "Creates horizontal sections within a slide (side by side).",
                "example": """
# Slide Title

[width=1/3]
Left column content

***

[width=2/3]
Right column content
""",
            },
        },
        "layout_directives": {
            "description": "Control size, position, and styling with directives in square brackets at the start of a section.",
            "syntax": "[property=value]",
            "common_directives": [
                {
                    "name": "width",
                    "values": "fractions (e.g., 1/3, 2/3), percentages (e.g., 50%), or pixels (e.g., 300)",
                    "description": "Sets the width of the section or element",
                },
                {
                    "name": "height",
                    "values": "fractions, percentages, or pixels",
                    "description": "Sets the height of the section or element",
                },
                {
                    "name": "align",
                    "values": "left, center, right, justify",
                    "description": "Sets horizontal text alignment",
                },
                {
                    "name": "valign",
                    "values": "top, middle, bottom",
                    "description": "Sets vertical alignment of text within its container",
                },
                {
                    "name": "vertical-align",
                    "values": "top, middle, bottom",
                    "description": "Sets vertical alignment for text elements",
                },
                {
                    "name": "background",
                    "values": "color (e.g., #f5f5f5, ACCENT1) or url(image_url)",
                    "description": "Sets background color or image; can use theme colors",
                },
                {
                    "name": "color",
                    "values": "color (e.g., #333333, TEXT1)",
                    "description": "Sets text color; can use theme colors",
                },
                {
                    "name": "fontsize",
                    "values": "numeric value (e.g., 18)",
                    "description": "Sets font size",
                },
                {
                    "name": "font-family",
                    "values": "font name (e.g., Arial, Times New Roman)",
                    "description": "Sets the font family for text",
                },
                {
                    "name": "padding",
                    "values": "numeric value or percentage (e.g., 10, 5%)",
                    "description": "Sets padding around the content",
                },
                {
                    "name": "border",
                    "values": "width style color (e.g., 1pt solid #FF0000, 2pt dashed black)",
                    "description": "Sets border for elements or sections",
                },
                {
                    "name": "border-position",
                    "values": "ALL, OUTER, INNER, LEFT, RIGHT, TOP, BOTTOM, INNER_HORIZONTAL, INNER_VERTICAL",
                    "description": "Specifies which borders to apply in tables",
                },
                {
                    "name": "line-spacing",
                    "values": "numeric value (e.g., 1.5)",
                    "description": "Sets line spacing for paragraphs",
                },
                {
                    "name": "paragraph-spacing",
                    "values": "numeric value (e.g., 10)",
                    "description": "Sets spacing between paragraphs",
                },
                {
                    "name": "indent",
                    "values": "numeric value (e.g., 20)",
                    "description": "Sets text indentation",
                },
            ],
            "combined_example": "[width=2/3][align=center][background=#f5f5f5][line-spacing=1.5]",
            "example": """
# Slide Title

[width=60%][align=center][padding=10]
This content takes 60% of the width, is centered, and has 10pt padding.

---

[width=40%][background=ACCENT1][color=TEXT1][border=1pt solid black]
This content has a themed background, theme text color, and a black border.
""",
        },
        "list_styling": {
            "description": "Control the appearance of lists with directives and nesting",
            "nesting": {
                "description": "Indentation in Markdown translates to visual nesting levels in slides",
                "example": """
- First level item
  - Second level item
    - Third level item
      - Fourth level item
""",
            },
            "styling": {
                "description": "Apply styling to list sections using directives",
                "example": """
[color=#0000FF][fontsize=18][font-family=Arial]
- Blue list items
- With larger Arial font
  - Nested items inherit styling
  - [color=red] This item is red
""",
            },
        },
        "table_styling": {
            "description": "Enhanced control over table appearance",
            "directives": [
                {
                    "name": "cell-align",
                    "values": "left, center, right, top, middle, bottom",
                    "description": "Sets alignment for cells in the table",
                },
                {
                    "name": "cell-background",
                    "values": "color (e.g., #F0F0F0, ACCENT2)",
                    "description": "Sets background color for cells",
                },
                {
                    "name": "cell-range",
                    "values": "row1,col1:row2,col2 (e.g., 0,0:2,3)",
                    "description": "Specifies a range of cells to apply styling to",
                },
                {
                    "name": "border",
                    "values": "width style color (e.g., 1pt solid black)",
                    "description": "Sets border for the entire table",
                },
            ],
            "example": """
[cell-align=center][cell-background=#F0F0F0][border=1pt solid black]
| Header 1 | Header 2 | Header 3 |
|----------|----------|----------|
| Data 1   | Data 2   | Data 3   |
| Data 4   | Data 5   | Data 6   |
""",
        },
        "theme_integration": {
            "description": "Use Google Slides themes and theme colors in your Markdown",
            "theme_id": {
                "description": "Specify a Google Slides theme ID when creating a presentation",
                "note": "The theme_id is passed as a parameter to the create_presentation tool",
            },
            "layouts": {
                "description": "Standard slide layouts allow content to inherit theme styling via placeholders",
                "common_layouts": [
                    "TITLE",
                    "TITLE_AND_BODY",
                    "TITLE_AND_TWO_COLUMNS",
                    "TITLE_ONLY",
                    "SECTION_HEADER",
                    "CAPTION_ONLY",
                    "BIG_NUMBER",
                ],
            },
            "theme_colors": {
                "description": "Use theme color names in directives for consistent styling",
                "values": [
                    "TEXT1",
                    "TEXT2",
                    "BACKGROUND1",
                    "BACKGROUND2",
                    "ACCENT1",
                    "ACCENT2",
                    "ACCENT3",
                    "ACCENT4",
                    "ACCENT5",
                    "ACCENT6",
                ],
                "example": """
[background=BACKGROUND2][color=ACCENT1]
# Theme-Styled Content

This content uses theme colors for consistent branding.
""",
            },
        },
        "special_elements": {
            "footer": {
                "separator": "@@@",
                "description": "Define slide footer content (appears at the bottom of each slide).",
                "example": """
# Slide Content

Main content here

@@@

Footer text - Confidential
""",
            },
            "speaker_notes": {
                "syntax": "<!-- notes: Your notes here -->",
                "description": "Add presenter notes (visible in presenter view only).",
                "example": "<!-- notes: Remember to emphasize the quarterly growth figures -->",
            },
        },
        "supported_markdown": {
            "headings": "# H1, ## H2, through ###### H6",
            "text_formatting": "**bold**, *italic*, ~~strikethrough~~, `inline code`",
            "lists": {
                "unordered": "- Item 1\n- Item 2\n  - Nested item",
                "ordered": "1. First item\n2. Second item\n   1. Nested item",
            },
            "links": "[Link text](https://example.com)",
            "images": "![Alt text](https://example.com/image.jpg)",
            "code_blocks": "```language\ncode here\n```",
            "tables": "| Header 1 | Header 2 |\n|----------|----------|\n| Cell 1   | Cell 2   |",
            "blockquotes": "> Quote text",
        },
        "layout_examples": [
            {
                "title": "Title and Content Slide",
                "description": "A standard slide with title and bullet points",
                "markdown": """
# Quarterly Results

Q3 2024 Financial Overview

- Revenue: $10.2M (+15% YoY)
- EBITDA: $3.4M (+12% YoY)
- Cash balance: $15M
""",
            },
            {
                "title": "Two-Column Layout with Theme Colors",
                "description": "Main content and sidebar layout with theme colors",
                "markdown": """
# Split Layout

[width=60%]

## Main Column

- Primary content
- Important details
- Key metrics

***

[width=40%][background=ACCENT2][color=TEXT1]

## Sidebar

Supporting information and notes
""",
            },
            {
                "title": "Dashboard Layout with Enhanced Styling",
                "description": "Complex layout with multiple sections and styling",
                "markdown": """
# Dashboard Overview

[height=30%][align=center][line-spacing=1.2]

## Key Metrics

Revenue: $1.2M | Users: 45K | Conversion: 3.2%

---

[width=50%][padding=10]

## Regional Data
[font-family=Arial][color=ACCENT1]
- North America: 45%
- Europe: 30%
- Asia: 20%
- Other: 5%

***

[width=50%][background=BACKGROUND2][border=1pt solid ACCENT3]

## Quarterly Trend

![Chart](chart-url.jpg)

---

[height=20%]

## Action Items
[line-spacing=1.5]
1. Improve APAC conversion
2. Launch new pricing tier
3. Update dashboards

@@@

Confidential - Internal Use Only

<!-- notes: Discuss action items in detail and assign owners -->
""",
            },
            {
                "title": "Table with Enhanced Styling",
                "description": "Styled table with cell alignment and backgrounds",
                "markdown": """
# Product Comparison

[width=80%][align=center]

[cell-align=center][border=1pt solid black]
| Feature | Basic Plan | Pro Plan | Enterprise |
|---------|------------|----------|------------|
| Users | 5 | 50 | Unlimited |
| Storage | 10GB | 100GB | 1TB |
| Support | Email | Priority | 24/7 |
| Price | $10/mo | $50/mo | Custom |

<!-- notes: Emphasize the value proposition of the Pro plan -->
""",
            },
        ],
        "best_practices": [
            "Start each slide with a clear title using # heading",
            "Keep content concise and visually balanced",
            "Use consistent styling across slides",
            "Limit the number of elements per slide",
            "Use layout directives to control positioning and sizing",
            "Use theme colors for consistent branding",
            "Test complex layouts to ensure they display as expected",
            "Apply appropriate spacing for improved readability",
        ],
        "tips_for_llms": [
            "First plan the overall structure of the presentation",
            "Consider visual hierarchy and content flow",
            "Use layout directives to create visually appealing slides",
            "Balance text with visual elements",
            "For complex presentations, break down into logical sections",
            "Always test with simple layouts before attempting complex ones",
            "When designing sections, ensure width values add up to 1 (or 100%)",
            "Use theme colors (ACCENT1, TEXT1, etc.) for consistent branding",
            "Apply styling consistently for a professional look",
            "Consider line spacing and paragraph spacing for improved readability",
        ],
    }
