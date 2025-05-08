"""
Google Slides resource handlers for MCP-GSuite.
"""

import logging
from typing import Any

from arclio_mcp_gsuite.app import mcp

logger = logging.getLogger(__name__)


@mcp.resource("slides://markdown_formatting_guide")
async def get_markdown_deck_formatting_guide() -> dict[str, Any]:
    """
    Get comprehensive documentation on how to format Markdown for slide creation using markdowndeck.

    Maps to URI: markdowndeck://formatting_guide

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
                    "description": "Sets vertical alignment",
                },
                {
                    "name": "background",
                    "values": "color (e.g., #f5f5f5) or url(image_url)",
                    "description": "Sets background color or image",
                },
                {
                    "name": "color",
                    "values": "color (e.g., #333333)",
                    "description": "Sets text color",
                },
                {
                    "name": "fontsize",
                    "values": "numeric value (e.g., 18)",
                    "description": "Sets font size",
                },
            ],
            "combined_example": "[width=2/3][align=center][background=#f5f5f5]",
            "example": """
# Slide Title

[width=60%][align=center]
This content takes 60% of the width and is centered.

---

[width=40%][background=#f0f8ff]
This content has a light blue background.
""",
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
                "title": "Two-Column Layout",
                "description": "Main content and sidebar layout",
                "markdown": """
# Split Layout

[width=60%]

## Main Column

- Primary content
- Important details
- Key metrics

***

[width=40%][background=#f0f8ff]

## Sidebar

Supporting information and notes
""",
            },
            {
                "title": "Dashboard Layout",
                "description": "Complex layout with multiple sections",
                "markdown": """
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

***

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
""",
            },
        ],
        "best_practices": [
            "Start each slide with a clear title using # heading",
            "Keep content concise and visually balanced",
            "Use consistent styling across slides",
            "Limit the number of elements per slide",
            "Use layout directives to control positioning and sizing",
            "Test complex layouts to ensure they display as expected",
        ],
        "tips_for_llms": [
            "First plan the overall structure of the presentation",
            "Consider visual hierarchy and content flow",
            "Use layout directives to create visually appealing slides",
            "Balance text with visual elements",
            "For complex presentations, break down into logical sections",
            "Always test with simple layouts before attempting complex ones",
            "When designing sections, ensure width values add up to 1 (or 100%)",
        ],
    }
