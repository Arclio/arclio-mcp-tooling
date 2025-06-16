# MarkdownDeck Usage Guide

**Version:** 4.0
**Last Updated:** January 2025
**Purpose:** Complete guide for creating presentations with MarkdownDeck

---

## Table of Contents

1. [Introduction](#introduction)
2. [Core Philosophy](#core-philosophy)
3. [Basic Syntax](#basic-syntax)
4. [Layout System](#layout-system)
5. [Directives Reference](#directives-reference)
6. [Content Elements](#content-elements)
7. [Advanced Patterns](#advanced-patterns)
8. [Best Practices](#best-practices)
9. [Common Mistakes](#common-mistakes)
10. [Quick Reference](#quick-reference)

---

## Introduction

MarkdownDeck transforms Markdown into Google Slides presentations using a **blank canvas** approach. Unlike traditional presentation tools, MarkdownDeck:

- Creates every slide as a blank canvas with no theme inheritance
- Requires explicit directives for all styling and spacing
- Uses fenced blocks for precise layout control
- Handles content overflow automatically

### Key Principle

**Everything is explicit.** There are no hidden defaults, automatic spacing, or inherited properties. If you want specific formatting, you must specify it.

---

## Core Philosophy

### 1. Blank Canvas

Every slide starts as a 720×540 point blank canvas. The usable content area is 620×420 points after margins:

- Top margin: 70 points
- Bottom margin: 50 points
- Side margins: 50 points each

### 2. Fenced Block Layout

All layout structure is created using explicit fenced blocks:

- `:::section` - Creates a vertical container
- `:::row` - Creates a horizontal container
- `:::column` - Creates a column within a row

### 3. Same-Line Directives

Directives are **always** placed on the same line as what they modify:

```markdown
# Blue Title [color=blue]

:::section [padding=20]
![image](url) [width=300][height=200]
:::
```

### 4. Container-First Sizing

- **Sections**: Have absolute dimensions
- **Elements**: Have preferred dimensions (scaled down if needed to fit)

---

## Basic Syntax

### Slide Structure

```markdown
# Main Title [optional directives]

## Subtitle [optional directives]

[optional base directives for entire slide]

:::section [optional directives]
Body content goes here
:::

<!-- notes: Speaker notes for presenter view -->

@@@
Footer text [optional directives]
```

### Multiple Slides

Use `===` to separate slides:

```markdown
# First Slide

Content here

===

# Second Slide

More content
```

### Important Rules

1. Title (`#`) must be the first element on a slide (if present)
2. Subtitle (`##`) must immediately follow the title (if present)
3. Base directives affect all content on the slide
4. Footer (`@@@`) must be at the top level
5. Speaker notes use HTML comment syntax

---

## Layout System

### Vertical Sections

Use `:::section` to create vertical containers:

```markdown
:::section [padding=20]
This content is in a padded section
:::

:::section [background=#f0f0f0]
This section has a gray background
:::
```

### Horizontal Layout (Rows and Columns)

Use `:::row` with nested `:::column` blocks:

```markdown
:::row [gap=30]
:::column [width=60%]
Left column takes 60% of width
:::
:::column [width=40%]
Right column takes 40% of width
:::
:::
```

### Nested Layouts

You can nest sections within sections:

```markdown
:::section [padding=40][background=#e0e0e0] # Section Title

    :::row [gap=20][margin-top=20]
        :::column [width=50%]
            :::section [background=white][padding=15]
                Card 1 content
            :::
        :::
        :::column [width=50%]
            :::section [background=white][padding=15]
                Card 2 content
            :::
        :::
    :::

:::
```

### Layout Rules

1. Always close fenced blocks with `:::`
2. Indent nested blocks for readability (recommended)
3. Columns must be direct children of rows
4. Empty sections are allowed (useful for spacing)

---

## Directives Reference

### Syntax Rules

- Format: `[key=value]` or `[key1=value1][key2=value2]`
- No spaces around equals sign
- Keys are case-insensitive
- No abbreviations (use `background`, not `bg`)

### Sizing Directives

| Directive | Values              | Section Behavior     | Element Behavior                         | Example                                     |
| --------- | ------------------- | -------------------- | ---------------------------------------- | ------------------------------------------- |
| `width`   | points, %, fraction | Sets absolute width  | Sets preferred width (scaled if needed)  | `[width=300]`, `[width=50%]`, `[width=2/3]` |
| `height`  | points, %, fraction | Sets absolute height | Sets preferred height (scaled if needed) | `[height=200]`, `[height=100%]`             |

**Note**: Images MUST have both width and height specified.

### Alignment Directives

| Directive | Values                       | Inheritable | Example           |
| --------- | ---------------------------- | ----------- | ----------------- |
| `align`   | left, center, right, justify | ✅          | `[align=center]`  |
| `valign`  | top, middle, bottom          | ✅          | `[valign=middle]` |

### Spacing Directives

| Directive       | Applies To    | Values        | Example                                 |
| --------------- | ------------- | ------------- | --------------------------------------- |
| `padding`       | Sections only | points or set | `[padding=20]`, `[padding=10,20,10,20]` |
| `margin`        | All           | points or set | `[margin=15]`, `[margin=10,0]`          |
| `margin-top`    | All           | points        | `[margin-top=20]`                       |
| `margin-bottom` | All           | points        | `[margin-bottom=20]`                    |
| `margin-left`   | All           | points        | `[margin-left=10]`                      |
| `margin-right`  | All           | points        | `[margin-right=10]`                     |
| `gap`           | Sections only | points        | `[gap=15]`                              |

**Set notation**:

- 1 value: all sides
- 2 values: vertical, horizontal
- 4 values: top, right, bottom, left

### Visual Directives

| Directive       | Values            | Example                                          |
| --------------- | ----------------- | ------------------------------------------------ |
| `background`    | color             | `[background=#f0f0f0]`, `[background=lightblue]` |
| `color`         | color             | `[color=#333]`, `[color=red]`                    |
| `border`        | width style color | `[border=2pt solid black]`                       |
| `border-radius` | points            | `[border-radius=8]`                              |
| `opacity`       | 0-1               | `[opacity=0.8]`                                  |

### Typography Directives

| Directive      | Values     | Inheritable | Example                 |
| -------------- | ---------- | ----------- | ----------------------- |
| `fontsize`     | points     | ✅          | `[fontsize=18]`         |
| `font-family`  | font name  | ✅          | `[font-family="Arial"]` |
| `line-spacing` | multiplier | ✅          | `[line-spacing=1.5]`    |
| `bold`         | (flag)     | ✅          | `[bold]`                |
| `italic`       | (flag)     | ✅          | `[italic]`              |

### Directive Precedence

When directives conflict, the most specific wins:

1. **Highest**: Element's same-line directives
2. **High**: Container's directives
3. **Medium**: Parent section's inheritable directives
4. **Low**: Base slide directives
5. **Lowest**: System defaults

---

## Content Elements

### Text and Headings

```markdown
# Heading 1 [color=navy]

## Heading 2 [fontsize=24]

### Heading 3

#### Heading 4

##### Heading 5

###### Heading 6

Regular paragraph text.

**Bold text** and _italic text_ and `inline code`.

[color=red] This entire paragraph is red.
```

### Lists

```markdown
# Bullet Lists

- First item
- Second item [color=blue]
  - Nested item
  - Another nested item
- Third item

# Ordered Lists

1. First step
2. Second step
   1. Sub-step A
   2. Sub-step B
3. Third step [bold]
```

### Tables

Tables use a **dedicated final column** for row directives. The directive is placed on the row it styles.

```markdown
| Column 1 | Column 2 | Column 3 | [background=#333][color=white] |
| -------- | -------- | -------- | ------------------------------ |
| Data 1   | Data 2   | Data 3   |                                |
| Data 4   | Data 5   | Data 6   | [background=#f0f0f0]           |
```

**Important**: The final column is never rendered—it exists only for directives.

### Images

Images **must** have both width and height:

```markdown
![Alt text](https://example.com/image.png) [width=400][height=300]

:::section [align=center]
![Centered image](image.png) [width=200][height=150]
:::
```

### Code Blocks

````markdown
```python
def hello_world():
    print("Hello, MarkdownDeck!")
```

:::section [background=#2d2d2d][padding=20]
`javascript
    // Code block with dark background
    const greeting = "Hello!";
    console.log(greeting);
    `
:::
````

### Speaker Notes

```markdown
# Presentation Slide

Content here

<!-- notes:
These notes appear in presenter view.
Can be multiple lines.
-->
```

### Footer

```markdown
# Slide Content

@@@
© 2025 Company Name | Confidential [align=right][fontsize=10]
```

---

## Advanced Patterns

### Title Slide

```markdown
# Annual Report 2024 [fontsize=48][color=#1a73e8]

## Financial Performance & Strategic Outlook [fontsize=24][color=#666]

:::section [align=center][margin-top=100]
**Presented by**
Jennifer Smith, CFO

    January 15, 2025

:::

@@@
Confidential - Internal Use Only [align=center][fontsize=10][color=#999]
```

### Two-Column Comparison

```markdown
# Feature Comparison

:::row [gap=40][margin-top=30]
:::column [width=45%]
:::section [background=#e8f4f8][padding=20] ### Option A

            **Pros:**
            - Lower cost
            - Faster implementation
            - Proven technology

            **Cons:**
            - Limited scalability
            - Fewer features
        :::
    :::
    :::column [width=45%]
        :::section [background=#f8e8e8][padding=20]
            ### Option B

            **Pros:**
            - Highly scalable
            - Feature-rich
            - Future-proof

            **Cons:**
            - Higher initial cost
            - Longer timeline
        :::
    :::

:::
```

### Data Dashboard

```markdown
# Q4 Performance Dashboard

:::row [gap=20]
:::column [width=33%]
:::section [background=#f0f0f0][padding=15][align=center] ### Revenue
**$12.5M**
[color=green]+23% YoY
:::
:::
:::column [width=33%]
:::section [background=#f0f0f0][padding=15][align=center] ### Users
**2.1M**
[color=green]+18% YoY
:::
:::
:::column [width=33%]
:::section [background=#f0f0f0][padding=15][align=center] ### NPS Score
**72**
[color=red]-3 pts
:::
:::
:::

:::section [margin-top=30][align=center]
![Revenue Chart](chart.png) [width=600][height=300]
:::
```

### Process Flow

```markdown
# Implementation Timeline

:::section [padding=20]
:::row [gap=10]
:::column [width=20%]
:::section [background=#1a73e8][color=white][padding=10][align=center]
**Phase 1**
Planning
Q1 2025
:::
:::
:::column [width=20%]
:::section [background=#34a853][color=white][padding=10][align=center]
**Phase 2**
Development
Q2 2025
:::
:::
:::column [width=20%]
:::section [background=#fbbc04][color=white][padding=10][align=center]
**Phase 3**
Testing
Q3 2025
:::
:::
:::column [width=20%]
:::section [background=#ea4335][color=white][padding=10][align=center]
**Phase 4**
Launch
Q4 2025
:::
:::
:::column [width=20%]
:::section [background=#666][color=white][padding=10][align=center]
**Phase 5**
Support
2026+
:::
:::
:::
:::
```

---

## Best Practices

### 1. Use Indentation

While not required, indenting improves readability:

```markdown
:::section [padding=20]
:::row [gap=20]
:::column [width=50%]
Content here
:::
:::
:::
```

### 2. Plan Your Layout First

Design the section structure before adding content:

```markdown
# Slide Title

:::section
:::row
:::column
<!-- Left column content here -->
:::
:::column
<!-- Right column content here -->
:::
:::
:::
```

### 3. Be Explicit About Spacing

MarkdownDeck adds NO automatic spacing:

```markdown
:::section [gap=20]
First paragraph

    Second paragraph

:::
```

### 4. Test Overflow Behavior

Large content automatically flows to continuation slides:

```markdown
:::section [height=200]
If this content exceeds 200 points,
it will continue on the next slide
:::
```

### 5. Use Base Directives for Consistency

```markdown
[fontsize=14][color=#333]
All content on this slide uses these defaults

# But headings can override [fontsize=32]
```

---

## Common Mistakes

### ❌ Missing Image Dimensions

```markdown
# WRONG

![image](url.png) [width=400]

# CORRECT

![image](url.png) [width=400][height=300]
```

### ❌ Columns Outside Rows

```markdown
# WRONG

:::column [width=50%]
Content
:::

# CORRECT

:::row
:::column [width=50%]
Content
:::
:::
```

### ❌ Background on Elements

```markdown
# WRONG

Text with background [background=yellow]

# CORRECT (wrap in a section)

:::section [background=yellow][padding=10]
Text with background
:::
```

### ❌ Forgetting to Close Blocks

```markdown
# WRONG

:::section
Content
:::row
Nested content

# CORRECT

:::section
Content
:::row
Nested content
:::
:::
```

### ❌ Multi-line Directives

```markdown
# WRONG

:::section
[padding=20]
[background=gray]
Content
:::

# CORRECT

:::section [padding=20][background=gray]
Content
:::
```

---

## Quick Reference

### Fenced Blocks

```markdown
:::section [directives] # Vertical container
:::row [directives] # Horizontal container
:::column [directives] # Column in row
::: # Close any block
```

### Common Directives

```markdown
# Sizing

[width=300] [width=50%] [width=1/3]
[height=200] [height=100%]

# Alignment

[align=center] [align=left|right|justify]
[valign=middle] [valign=top|bottom]

# Spacing

[padding=20] [padding=10,20,10,20]
[margin=15] [margin-top=20]
[gap=20]

# Visual

[background=#f0f0f0] [color=blue]
[border=1pt solid black]
[opacity=0.8]

# Typography

[fontsize=18] [font-family="Arial"]
[bold] [italic]
[line-spacing=1.5]
```

### Slide Components

```markdown
# Title [directives]

## Subtitle [directives]

[base directives]

:::section
Body content
:::

<!-- notes: Speaker notes -->

@@@
Footer [directives]

===

# Next slide
```

### Size Values

- **Points**: `100` or `100pt`
- **Percentage**: `50%` (of parent)
- **Fraction**: `1/3`, `2/5`

### Color Values

- **Hex**: `#ff0000`, `#f00`
- **Named**: `red`, `blue`, `lightgray`

---

## Remember

1. **Everything is explicit** - No automatic formatting
2. **Directives on same line** - Always with their target
3. **Images need both dimensions** - Width AND height
4. **Tables have directive column** - Final column for styling
5. **Close all fenced blocks** - Every `:::block` needs `:::`
6. **Test with edge cases** - Large images, long text, deep nesting

For implementation details and API documentation, see the main README.
