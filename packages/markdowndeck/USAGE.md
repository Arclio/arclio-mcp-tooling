# MarkdownDeck Usage Guide

**Version:** 8.0  
**Status:** AUTHORITATIVE  
**Purpose:** The definitive, unambiguous guide for generating valid MarkdownDeck syntax  
**Audience:** Large Language Models and developers creating MarkdownDeck presentations  

---

## Table of Contents

1. [CRITICAL: The Three Fundamental Rules](#critical-the-three-fundamental-rules)
2. [The Strict Hierarchy Model](#the-strict-hierarchy-model)
3. [Blank Line Rules - When They Matter](#blank-line-rules---when-they-matter)
4. [Image Dimension Requirements](#image-dimension-requirements)
5. [Table Directive Column](#table-directive-column)
6. [Complete Syntax Reference](#complete-syntax-reference)
7. [Common Errors and How to Fix Them](#common-errors-and-how-to-fix-them)
8. [Known Limitations](#known-limitations)

---

## CRITICAL: The Three Fundamental Rules

### Rule 1: Blank Canvas Philosophy
- **EVERY slide starts with ZERO formatting**
- **NO themes, NO templates, NO inherited properties**
- **ALL spacing defaults to ZERO** - you MUST specify every padding, margin, and gap

### Rule 2: Explicit Fenced Block Structure
- **ALL body content MUST be inside `:::section` blocks**
- **NO content is allowed directly in slides, rows, or columns**
- **The hierarchy is STRICT and ENFORCED**

### Rule 3: Same-Line Directives
- **Directives MUST be on the SAME LINE as what they modify**
- **NEVER put directives on separate lines**
- **This rule has NO exceptions**

---

## The Strict Hierarchy Model

### The ONLY Valid Structure

```
Slide Body
    └── :::section (can contain ONLY content elements)
            └── Content Elements (text, images, tables, lists, code)
    
    └── :::row (can ONLY contain :::column blocks)
            └── :::column (can contain :::section blocks)
                    └── :::section (can contain ONLY content elements)
                    └── :::row (EXPERIMENTAL - nested row inside column)
```

### Visual Diagram of Valid Nesting

```markdown
# ✅ CORRECT - Valid patterns

# Pattern 1: Simple section
:::section
    Text content goes here
    More content in the same section
    - Lists work too
    - All vertically stacked
:::

# Pattern 2: Row with columns
:::row
    :::column [width=50%]
        :::section
            Left column content
        :::
    :::
    :::column [width=50%]
        :::section
            Right column content
        :::
    :::
:::

# Pattern 3: Multiple sections at top level
:::section
    First section content
:::

:::section [margin-top=20]
    Second section content - vertically stacked
:::
```

### ❌ INVALID Structures That Will FAIL

```markdown
# ❌ WRONG - Content directly in slide body
This text is NOT in a section - PARSER ERROR!

# ❌ WRONG - Content directly in row
:::row
    This text will cause GRAMMAR ERROR
:::

# ❌ WRONG - Content directly in column
:::column
    This text will cause GRAMMAR ERROR
:::

# ❌ WRONG - Row inside section
:::section
    :::row  # GRAMMAR ERROR - rows cannot be inside sections
    :::
:::

# ❌ WRONG - Column outside row
:::column  # GRAMMAR ERROR - columns MUST be in rows
:::

# ❌ WRONG - Content directly in row or column
:::row
    This text will cause GRAMMAR ERROR
:::

:::column
    This text will also cause GRAMMAR ERROR
:::
```

### The Golden Rule Table

| Container | Can Contain | CANNOT Contain |
|-----------|-------------|----------------|
| `:::section` | • Text, images, tables, lists<br>• Code blocks<br>• Any content elements | • `:::row` blocks<br>• `:::column` blocks<br>• Another `:::section` |
| `:::row` | • ONLY `:::column` blocks | • ANY content<br>• `:::section` blocks |
| `:::column` | • `:::section` blocks<br>• `:::row` blocks (EXPERIMENTAL) | • ANY content directly |

---

## Blank Line Rules - When They Matter

### Rule 1: Between Different Block Types (OPTIONAL)

When you have different types of blocks in sequence, blank lines are **OPTIONAL** - the parser will separate them automatically:

```markdown
# ✅ CORRECT - No blank line needed
:::section
# Heading
This paragraph is automatically recognized as separate.
- List items are also automatically separated
:::

# ✅ ALSO CORRECT - With blank lines for readability
:::section
# Heading

This paragraph is visually separated in the source.

- List items with visual separation
:::
```

### Rule 2: Between Similar Block Types (REQUIRED)

When you have consecutive blocks of the **SAME TYPE**, blank lines are **REQUIRED** to create separate elements:

```markdown
# ❌ WRONG - These become ONE paragraph
:::section
This is paragraph one.
This is paragraph two.
:::
# Result: "This is paragraph one. This is paragraph two." (single element)

# ✅ CORRECT - These are TWO paragraphs
:::section
This is paragraph one.

This is paragraph two.
:::
# Result: Two separate paragraph elements
```

### More Examples of the Blank Line Rule

```markdown
# ❌ WRONG - Multiple headings without separation
:::section
### Heading One
### Heading Two
:::
# Result: Parsed as a single malformed element

# ✅ CORRECT - Headings properly separated
:::section
### Heading One

### Heading Two
:::
# Result: Two separate heading elements

# ✅ CORRECT - Mixed content (blank lines optional between different types)
:::section
### My Heading
This paragraph follows the heading.
- First list item
- Second list item

Another paragraph after the list.
:::
```

---

## Image Dimension Requirements

### ABSOLUTE RULE: All Images MUST Have Dimensions

Every image **MUST** have BOTH `[width=X]` and `[height=Y]` directives, with ONE exception.

```markdown
# ❌ WRONG - Missing height
![Logo](https://example.com/logo.png) [width=200]

# ❌ WRONG - No dimensions at all
![Logo](https://example.com/logo.png)

# ✅ CORRECT - Both dimensions specified
![Logo](https://example.com/logo.png) [width=200][height=150]
```

### The ONLY Exception: `[fill]` Directive

The `[fill]` directive is the ONLY case where width/height are not required on the image itself:

```markdown
# ✅ CORRECT - Using [fill] directive
:::section [width=400][height=300]  # Parent MUST have dimensions
    ![Background](image.png) [fill]
:::

# ❌ WRONG - [fill] without sized parent
:::section  # No dimensions on parent!
    ![Background](image.png) [fill]  # WILL FAIL
:::
```

### `[fill]` Requirements Summary
1. Parent `:::section` MUST have explicit `[width=X]` AND `[height=Y]`
2. The image will fill the entire parent container
3. Aspect ratio is ignored - image may be stretched

---

## Table Directive Column

### CRITICAL: Tables Have a Hidden Final Column

**EVERY table in MarkdownDeck has a dedicated final column for row directives that is NEVER rendered.**

### Correct Table Structure

```markdown
# ✅ CORRECT - Proper directive column
:::section
| Product | Price | Stock | Directives |
|---------|-------|-------|------------|
|         |       |       | [background=#333][color=white] |
| Widget  | $10   | 50    | |
| Gadget  | $25   | 0     | [background=#ffcccc] |
:::
```

### Common Table Mistakes

```markdown
# ❌ WRONG - Missing directive column in separator
| Product | Price | Stock |
|---------|-------|-------|  # WRONG - need 4th column
| Widget  | $10   | 50    | [background=gray] |

# ❌ WRONG - Trying to use 3 columns
| Product | Price | Stock |
|---------|-------|-------|
| Widget  | $10   | 50    |  # Directives have nowhere to go!

# ✅ CORRECT - Full example with all requirements
| Header 1 | Header 2 | Header 3 | |
|----------|----------|----------|--|
|          |          |          | [background=darkblue][color=white] |
| Data 1   | Data 2   | Data 3   | |
| Data 4   | Data 5   | Data 6   | [background=#f0f0f0] |
```

### Table Rules Summary
1. **ALWAYS** add a 4th column for directives
2. The separator line `|---|---|---|--|` MUST extend to cover all columns
3. The final column header text is arbitrary (can be empty or "Directives")
4. First data row directives apply to the header row
5. The final column content is NEVER rendered

---

## Complete Syntax Reference

### Slide Structure

```markdown
# Title (optional) [color=blue][fontsize=36]

## Subtitle (optional) [fontsize=20]

[color=darkgray][fontsize=14]  # Base directives for slide

:::section [padding=20]
    All body content MUST be in sections
:::

<!-- notes: Speaker notes go here -->

@@@
Footer text [align=center]

===

# Next slide starts here
```

### Fenced Block Reference

```markdown
# Vertical content container
:::section [padding=20][background=#f0f0f0]
    Content goes here
:::

# Vertical stacking in sections
:::section [gap=20]
    ### First Element
    This content is vertically stacked.
    
    ### Second Element  
    More content below with 20pt gap.
    
    ### Third Element
    All elements stack vertically within the section.
:::

# Horizontal layout with rows and columns
:::row [gap=30]
    :::column [width=60%]
        :::section
            Left content
        :::
    :::
    :::column [width=40%]
        :::section
            Right content
        :::
    :::
:::

# Nested layouts (EXPERIMENTAL)
:::row
    :::column [width=50%]
        :::section
            Left content
        :::
        
        # ⚠️ EXPERIMENTAL: Nested row inside column
        :::row [gap=10]
            :::column [width=50%]
                :::section
                    Nested left
                :::
            :::
            :::column [width=50%]
                :::section
                    Nested right
                :::
            :::
        :::
    :::
    :::column [width=50%]
        :::section
            Right content
        :::
    :::
:::
```

### Directive Quick Reference

```markdown
# Sizing (REQUIRED for images unless using [fill])
[width=300] [width=50%] [width=1/3]
[height=200] [height=100%]

# Spacing (remember: ALL default to ZERO)
[padding=20] [padding=10,20,10,20]  # all sides or top,right,bottom,left
[margin=15] [margin-top=20] [margin-bottom=10]
[gap=20]  # Space between children (NOT inherited!)

# Alignment
[align=left|center|right|justify]
[valign=top|middle|bottom]

# Visual
[background=#f0f0f0] [background=lightblue]
[color=#333] [color=red]
[border=2pt solid black]
[border-radius=8]
[opacity=0.8]

# Typography
[fontsize=18]
[font-family="Arial"]
[line-spacing=1.5]
[bold] [italic]
```

---

## Common Errors and How to Fix Them

### Error 1: Content Outside Sections

```markdown
# ❌ WRONG
This text is not in a section!

# ✅ CORRECT
:::section
This text is properly contained
:::
```

### Error 2: Missing Blank Lines Between Same Elements

```markdown
# ❌ WRONG - Creates one paragraph
:::section
First paragraph.
Second paragraph.
:::

# ✅ CORRECT - Creates two paragraphs
:::section
First paragraph.

Second paragraph.
:::
```

### Error 3: Images Without Dimensions

```markdown
# ❌ WRONG
![Chart](chart.png)

# ✅ CORRECT
![Chart](chart.png) [width=400][height=300]
```

### Error 4: Invalid Hierarchy

```markdown
# ❌ WRONG - Column outside row
:::column
    :::section
        Content
    :::
:::

# ✅ CORRECT - Column inside row
:::row
    :::column
        :::section
            Content
        :::
    :::
:::
```

### Error 5: Table Without Directive Column

```markdown
# ❌ WRONG
| A | B | C |
|---|---|---|
| 1 | 2 | 3 |

# ✅ CORRECT
| A | B | C | |
|---|---|---|--|
| 1 | 2 | 3 | |
```

---

## Known Limitations

This section documents current limitations in MarkdownDeck. These are actively being addressed in future versions.

### Table Indentation
**It is strongly recommended to avoid indenting tables within your markdown source.** While the parser attempts to handle indentation, complex tables may not parse correctly when indented. Please define tables with no leading whitespace.

```markdown
# ❌ AVOID - Indented table
:::section
    | Col1 | Col2 | |
    |------|------|--|
    | Data | Data | |
:::

# ✅ RECOMMENDED - No indentation
:::section
| Col1 | Col2 | |
|------|------|--|
| Data | Data | |
:::
```

### Overflow with `[fill]` Images
**The overflow handling for content adjacent to a `[fill]` image is currently limited.** Ensure that content in columns next to a `[fill]` image does not overflow its vertical space, as the automatic splitting may not behave as expected in this specific context.

```markdown
# ⚠️ USE WITH CAUTION
:::row
    :::column [width=40%]
        :::section [width=100%][height=400]
            ![Image](url.png) [fill]
        :::
    :::
    :::column [width=60%]
        :::section
            # Avoid very long content here that might overflow
        :::
    :::
:::
```

### `line-spacing` Directive
**The `[line-spacing]` directive is an experimental feature.** While it is parsed correctly, its effect on layout height calculation for multi-line text blocks is currently being refined and may not produce pixel-perfect results in all cases.

```markdown
# ⚠️ EXPERIMENTAL
:::section [line-spacing=2.0]
    This text may not calculate height perfectly
    when using non-standard line spacing values.
:::
```

---

## Final Reminders

1. **EVERY image needs width AND height** (except with `[fill]`)
2. **ALL content goes in `:::section` blocks** - NO exceptions
3. **Directives ALWAYS on the same line** - NEVER separate
4. **Tables ALWAYS have a directive column** - even if empty
5. **Blank lines separate same-type elements** - required for multiple paragraphs
6. **The hierarchy is STRICT** - row→column→section→content
7. **ALL spacing defaults to ZERO** - specify everything explicitly

When in doubt, refer to the examples in this guide. They represent the ONLY correct way to write MarkdownDeck.