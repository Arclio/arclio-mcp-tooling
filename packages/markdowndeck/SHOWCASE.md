
# MarkdownDeck Showcase

## The Definitive Guide & Feature Tour

[fontsize=14][color=#475569]

:::section [align=center][margin-top=80]
    ![MarkdownDeck Logo](https://placehold.co/150x150/0A74DA/FFFFFF?text=MD) [width=150][height=150]
    ### MarkdownDeck [fontsize=36][font-family="Arial"][color=#1E293B][bold]
    Transform Markdown into Professional Presentations [fontsize=18][color=#475569]
:::

<!-- notes: Welcome to MarkdownDeck v8 showcase. This version demonstrates automatic block separation and full indentation support. -->

@@@
MarkdownDeck Showcase v8 | Slide 1 of 56

===

# Table of Contents

## A Tour of MarkdownDeck's Capabilities

:::row [gap=30][margin-top=40]
    :::column [width=1/3]
        :::section
            **1. Core Concepts** [fontsize=18][bold][color=#0A74DA]
            - Text & Typography
            - Colors & Fonts
            - Alignment
        :::
    :::
    :::column [width=1/3]
        :::section
            **2. Layout System** [fontsize=18][bold][color=#0A74DA]
            - Sections & Styling
            - Rows & Columns
            - Nested Layouts
        :::
    :::
    :::column [width=1/3]
        :::section
            **3. Content Elements** [fontsize=18][bold][color=#0A74DA]
            - Lists & Tables
            - Images & Code
            - Advanced Features
        :::
    :::
:::

@@@
MarkdownDeck Showcase v8 | Slide 2 of 56

===

# Text & Typography

## Basic Text Formatting

:::row[padding=30]
    :::column [width=2/3]
        :::section [background=#F8FAFC][gap=20]
            ### Inline Formatting Examples
            This is **bold text** using double asterisks.

            This is *italic text* using single asterisks.

            This is `inline code` using backticks.

            You can combine **bold and *italic* text** together.
        :::
    :::
    :::column [width=1/3]
        :::section [margin-top=30][gap=30][background=#F8FAFC]
            ### Markdown Syntax
            ```markdown
            **bold text**
            *italic text*
            `inline code`
            **bold and *italic* text**
            ```
        :::
    :::
:::

@@@
MarkdownDeck Showcase v8 | Slide 3 of 56

===

# Heading Levels

## All Six Heading Sizes

:::section
    # Heading 1 (24pt default) [color=#0A74DA]
    ## Heading 2 (20pt default) [color=#1E293B]
    ### Heading 3 (18pt default) [color=#475569]
    #### Heading 4 (16pt default)
    ##### Heading 5 (14pt default)
    ###### Heading 6 (12pt default)
:::

:::section [background=#F1F5F9][padding=20][margin-top=30]
    **Note:** H1 and H2 have special meaning at slide level (title/subtitle).
:::

@@@
MarkdownDeck Showcase v8 | Slide 4 of 56

===

# Text Alignment

## Three Alignment Options

:::section [background=#F1F5F9][padding=30]
    ### Left Aligned (Default)
    This text is left-aligned, which is the default behavior.
:::

:::section [background=#E0F2FE][padding=30][margin-top=20][align=center]
    ### Center Aligned
    This section uses `[align=center]` directive.
:::

:::section [background=#DCFCE7][padding=30][margin-top=20][align=right]
    ### Right Aligned
    This section uses `[align=right]` directive.
:::

@@@
MarkdownDeck Showcase v8 | Slide 5 of 56

===

# Text Colors

## Using Color Directives

:::section
    This text uses red hex color. [color=#EF4444]

    This text uses blue hex color. [color=#0A74DA]

    This text uses green hex color. [color=#10B981]

    This text uses amber hex color. [color=#F59E0B]
:::

:::section [background=#1E293B][padding=30][margin-top=30]
    White text on dark background. [color=white]

    Accent color for emphasis. [color=#F59E0B]
:::

@@@
MarkdownDeck Showcase v8 | Slide 6 of 56

===

# Font Sizes

## Various Text Sizes

:::section
    Huge Text (48pt) [fontsize=48]

    Large Text (36pt) [fontsize=36]

    Medium Text (24pt) [fontsize=24]

    Normal Text (18pt) [fontsize=18]

    Small Text (12pt) [fontsize=12]
:::

@@@
MarkdownDeck Showcase v8 | Slide 7 of 56

===

# Font Families

## Different Font Options

:::section [gap=10]
    This text uses Arial (sans-serif). [font-family="Arial"]

    This text uses Times New Roman (serif). [font-family="Times New Roman"]

    This text uses Courier New (monospace). [font-family="Courier New"]

    This text uses Georgia (serif). [font-family="Georgia"]

    This text uses Playfair Display (serif). [font-family="Playfair Display"]

    This text uses Plus Jakarta Sans (sans-serif). [font-family="Plus Jakarta Sans"]

    This text uses Roboto (sans-serif). [font-family="Roboto"]

    This text uses Victor Mono (monospace). [font-family="Victor Mono"]
:::

@@@
MarkdownDeck Showcase v8 | Slide 8 of 56

===

# Basic Sections

## The Building Blocks

:::section
    A section is a container for content. This is the root section.
:::

:::section [background=#F8FAFC][padding=20]
    This section has a background and padding.
:::

:::section [background=#E0F2FE][padding=20][margin-top=20]
    This section adds a top margin for spacing.
:::

@@@
MarkdownDeck Showcase v8 | Slide 9 of 56

===

# Section Backgrounds

## Color Options

:::section [background=#EFF6FF][padding=20]
    ### Light Blue Background
    Using `[background=#EFF6FF]`
:::

:::section [background=#F0FDF4][padding=20][margin-top=20]
    ### Light Green Background
    Using `[background=#F0FDF4]`
:::

:::section [background=#FEF3C7][padding=20][margin-top=20]
    ### Light Yellow Background
    Using `[background=#FEF3C7]`
:::

@@@
MarkdownDeck Showcase v8 | Slide 10 of 56

===

# Section Padding

## Controlling Inner Space

:::section [background=#F1F5F9]
    No padding - text touches edges.
:::

:::section [background=#F1F5F9][padding=20][margin-top=20]
    Uniform 20pt padding on all sides.
:::

:::section [background=#F1F5F9][padding=10,30][margin-top=20]
    10pt vertical, 30pt horizontal padding.
:::

:::section [background=#F1F5F9][padding=5,15,25,35][margin-top=20]
    Custom padding: top(5) right(15) bottom(25) left(35).
:::

@@@
MarkdownDeck Showcase v8 | Slide 11 of 56

===

# Section Margins

## Controlling Outer Space

:::section [background=#E0F2FE][padding=15]
    First section (no margin)
:::

:::section [background=#E0F2FE][padding=15][margin-top=30]
    Second section with 30pt top margin
:::

:::section [background=#E0F2FE][padding=15][margin=20]
    Third section with 20pt margin on all sides
:::

@@@
MarkdownDeck Showcase v8 | Slide 12 of 56

===

# Section Borders

## Border Styles

:::section [border="1pt solid #94A3B8"][padding=20]
    Basic gray border (1pt solid)
:::

:::section [border="2pt solid #EF4444"][padding=20][margin-top=20]
    Red border (2pt solid)
:::

:::section [border="3pt dashed #0A74DA"][padding=20][margin-top=20]
    Blue dashed border (3pt)
:::

:::section [border="2pt dotted #10B981"][padding=20][margin-top=20][border-radius=8]
    Green dotted border with rounded corners
:::

@@@
MarkdownDeck Showcase v8 | Slide 13 of 56

===

# Two-Column Layout

## Basic Row and Column

:::row [gap=30]
    :::column [width=50%]
        :::section
            ### Left Column
            This is the left column content.
            - Easy to create
            - Flexible widths
            - Automatic spacing
        :::
    :::
    :::column [width=50%]
        :::section
            ### Right Column
            This is the right column content.
            The gap directive adds 30pt between columns.
        :::
    :::
:::

@@@
MarkdownDeck Showcase v8 | Slide 14 of 56

===

# Three-Column Layout

## Equal Width Columns

:::row [gap=20]
    :::column [width=1/3]
        :::section [background=#FEF3C7][padding=15]
            ### Column 1
            First of three columns.
        :::
    :::
    :::column [width=1/3]
        :::section [background=#DBEAFE][padding=15]
            ### Column 2
            Second column content.
        :::
    :::
    :::column [width=1/3]
        :::section [background=#DCFCE7][padding=15]
            ### Column 3
            Third column content.
        :::
    :::
:::

@@@
MarkdownDeck Showcase v8 | Slide 15 of 56

===

# Four-Column Grid

## Icon Layout Example

:::row [gap=15]
    :::column [width=25%]
        :::section [align=center]
            ![Chart Icon](https://api.iconify.design/ph/chart-line-duotone.svg?color=%230A74DA) [width=60][height=60]
            **Analytics**
        :::
    :::
    :::column [width=25%]
        :::section [align=center]
            ![Users Icon](https://api.iconify.design/ph/users-three-duotone.svg?color=%230A74DA) [width=60][height=60]
            **Team**
        :::
    :::
    :::column [width=25%]
        :::section [align=center]
            ![Rocket Icon](https://api.iconify.design/ph/rocket-launch-duotone.svg?color=%230A74DA) [width=60][height=60]
            **Launch**
        :::
    :::
    :::column [width=25%]
        :::section [align=center]
            ![Shield Icon](https://api.iconify.design/ph/shield-check-duotone.svg?color=%230A74DA) [width=60][height=60]
            **Security**
        :::
    :::
:::

@@@
MarkdownDeck Showcase v8 | Slide 16 of 56

===

# Uneven Columns

## 65/35 Split

:::row
    :::column [width=65%][background=#F0FDF4]
        :::section [padding=30]
            ### Main Content (65%)
            This wider column is perfect for primary content, detailed explanations, or charts. The asymmetric layout helps guide viewer focus.
        :::
    :::
    :::column [width=35%][background=#EFF6FF]
        :::section [padding=30]
            ### Sidebar (35%)
            Great for:
            - Key points
            - Quick facts
            - Callouts
        :::
    :::
:::

@@@
MarkdownDeck Showcase v8 | Slide 17 of 56


===

# Column Gap Demonstration

## Comparing Different Gaps

:::section [background=#F1F5F9][padding=20]
    ### No Gap (gap=0)
:::

:::row
    :::column [width=50%]
        :::section [background=#DBEAFE][padding=20]
            Left column
        :::
    :::
    :::column [width=50%]
        :::section [background=#DCFCE7][padding=20]
            Right column
        :::
    :::
:::

:::section [background=#F1F5F9][padding=20][margin-top=30]
    ### With 40pt Gap
:::

:::row [gap=40]
    :::column [width=50%]
        :::section [background=#DBEAFE][padding=20]
            Left column
        :::
    :::
    :::column [width=50%]
        :::section [background=#DCFCE7][padding=20]
            Right column
        :::
    :::
:::

@@@
MarkdownDeck Showcase v8 | Slide 18 of 56

===

# Vertical Alignment

## Aligning Content Vertically

:::row [gap=20]
    :::column [width=1/3]
        :::section [background=#F1F5F9][padding=20][height=254][valign=top]
            ### Top Aligned
            Default alignment
        :::
    :::
    :::column [width=1/3]
        :::section [background=#F1F5F9][padding=20][height=254][valign=middle]
            ### Middle Aligned
            Centered vertically
        :::
    :::
    :::column [width=1/3]
        :::section [background=#F1F5F9][padding=20][height=254][valign=bottom]
            ### Bottom Aligned
            Aligned to bottom
        :::
    :::
:::

@@@
MarkdownDeck Showcase v8 | Slide 19 of 56

===
:::row
    :::column [width=40%]
        :::section [height=100%][width=100%]
            ![Man working on a laptop in a modern office](https://images.unsplash.com/photo-1556742502-ec7c0e9f34b1?q=80&w=1887) [fill]
        :::
    :::
    :::column [width=60%][gap=60][padding=20]
        :::section
            ## Fill Section [fontsize=32]
        :::
        :::section
            This is the slide copy block. It contains the main narrative of the slide, explaining the data and statistics shown below. It provides the story behind the numbers.
        :::
        :::row [gap=2.5]
            :::column [width=25%][padding=0]
                :::section [align=center][background=#EFF6FF]
                    **Stat A**
                :::
            :::
            :::column [width=25%]
                :::section [align=center][background=#F0FDF4]
                    **Stat B**
                :::
            :::
            :::column [width=25%]
                :::section [align=center][background=#F0FDF4]
                    **Stat C**
                :::
            :::
            :::column [width=25%]
                :::section [align=center][background=#FEF3C7]
                    **Stat D**
                :::
            :::
        :::
        :::section
            MarkdownDeck Showcase v8 | Slide 20 of 56
        :::
    :::
:::
===

# Bullet Lists

## Basic and Styled

:::section
    ### Basic List
    - First item
    - Second item
    - Third item

    ### Styled Items
    - Regular item
    - Blue colored item [color=#0A74DA]
    - **Bold item** [bold]
    - *Italic item* [italic][color=#EF4444]
:::

@@@
MarkdownDeck Showcase v8 | Slide 21 of 56

===

# Ordered Lists

## Numbered Lists

:::section
    ### Basic Ordered List
    1. First step
    2. Second step
    3. Third step

    ### Styled Ordered List
    1. Complete this first [color=#10B981]
    2. **Important step** [bold]
    3. Optional review [color=#475569][italic]
:::

@@@
MarkdownDeck Showcase v8 | Slide 22 of 56

===

# Nested Lists

## Multi-Level Lists

:::row
    :::column
        :::section
            ### Bullet List Nesting
            - Top level item 1
                - Second level item
                    - Third level item
                - Another second level
            - Top level item 2
        :::
    :::
    :::column
        :::section
            ### Mixed List Types
            1. Ordered item
                - Bullet sub-item
                - Another bullet
            2. Second ordered item
                1. Nested ordered
                2. Another nested
        :::
    :::
:::

@@@
MarkdownDeck Showcase v8 | Slide 23 of 56
===

# Basic Tables

## Simple Data Display

:::section [padding=20]
| Product | Price | Stock | |
|---------|-------|-------|-|
| Widget  | $10   | 50    | |
| Gadget  | $25   | 30    | |
| Tool    | $15   | 0     | |
:::

@@@
MarkdownDeck Showcase v8 | Slide 24 of 56
===

# Table Row Styling

## Colored Rows

:::section [padding=20]
| Department | Q1 Sales | Q2 Sales | [background=#1E293B][color=white]|
|------------|----------|----------|---------------------------------|
| North      | $50,000  | $55,000  | |
| South      | $48,000  | $51,000  | [background=#F8FAFC] |
| East       | $52,000  | $49,000  | |
| West       | $61,000  | $65,000  | [background=#F8FAFC] |
| **Total**  | **$211k** | **$220k** | [background=#FEF3C7] |
:::

@@@
MarkdownDeck Showcase v8 | Slide 25 of 56

===

# Images

## Basic Image Display

:::section [align=center]
    ![Sample Chart](https://via.placeholder.com/400x300/0A74DA/FFFFFF?text=Chart) [width=400][height=300]
    Figure 1: Sample visualization [fontsize=12][color=#475569]
:::

@@@
MarkdownDeck Showcase v8 | Slide 26 of 56

===

# Side-by-Side Images

## Image Comparison

:::row [gap=20]
    :::column [width=50%]
        :::section [align=center]
            ![Before](https://via.placeholder.com/300x200/94A3B8/FFFFFF?text=Before) [width=300][height=200]
            **Before**
        :::
    :::
    :::column [width=50%]
        :::section [align=center]
            ![After](https://via.placeholder.com/300x200/10B981/FFFFFF?text=After) [width=300][height=200]
            **After**
        :::
    :::
:::

@@@
MarkdownDeck Showcase v8 | Slide 27 of 56

===

# Image Alignment

## Three Alignment Options

:::section [background=#F1F5F9][padding=20]
    ![Left](https://via.placeholder.com/150x100/0A74DA/FFFFFF?text=Left) [width=150][height=100]
    Left aligned (default)
:::

:::section [background=#F1F5F9][padding=20][margin-top=20][align=center]
    ![Center](https://via.placeholder.com/150x100/0A74DA/FFFFFF?text=Center) [width=150][height=100]
    Center aligned
:::

:::section [background=#F1F5F9][padding=20][margin-top=20][align=right]
    ![Right](https://via.placeholder.com/150x100/0A74DA/FFFFFF?text=Right) [width=150][height=100]
    Right aligned
:::

@@@
MarkdownDeck Showcase v8 | Slide 28 of 56

===

# Code Blocks

## Syntax Highlighting

:::section
    ### Python Example
    ```python
    def create_presentation(markdown_content):
        deck = parser.parse(markdown_content)
        for slide in deck.slides:
            layout_manager.position_elements(slide)
        return api_generator.create_requests(deck)
    ```

    ### JavaScript Example
    ```javascript
    const slides = document.querySelectorAll('.slide');
    slides.forEach(slide => {
        slide.classList.add('formatted');
    });
    ```
:::

@@@
MarkdownDeck Showcase v8 | Slide 29 of 56

===

# Inline Code

## Code Within Text

:::section
    Use `backticks` for inline code like `variable_name` or `function()`.
    You can mention `file.py` or reference `Class.method()` inline.
    Commands like `pip install markdowndeck` stand out in text.
:::

@@@
MarkdownDeck Showcase v8 | Slide 30 of 56

===

# Base Directives

## Slide-Wide Styling

[fontsize=14][color=#475569]

:::section
    All content inherits these base directives: 14pt font and gray color.
    ### Headers Still Use Their Sizes

    But inherit the color unless overridden.

    This text overrides to blue. [color=#0A74DA]

    This overrides both size and color. [fontsize=18][color=#EF4444]
:::

@@@
MarkdownDeck Showcase v8 | Slide 31 of 56

===

# Directive Precedence

## Override Hierarchy

:::section [color=blue][fontsize=16]
    Section sets blue color and 16pt font.

    This paragraph overrides to red. [color=red]

    A nested-style paragraph with green text. [color=green]

    This text overrides to purple. [color=purple]

    Back to blue in parent section.
:::

@@@
MarkdownDeck Showcase v8 | Slide 32 of 56
===

# Speaker Notes

## Presenter View Content

:::section
    This slide has speaker notes that appear in presenter view.
    Key features:
    - Hidden from audience
    - Support multiple lines
    - Use HTML comment syntax
:::

<!-- notes:
Remember to:
- Make eye contact
- Speak clearly
- Check the time
- Ask for questions
-->

@@@
MarkdownDeck Showcase v8 | Slide 33 of 56

===

# Footers

## Consistent Bottom Content

:::section
    Footers appear at the bottom of slides.
    They're useful for:
    - Slide numbers
    - Copyright notices
    - Event names
    - Confidentiality marks
:::

@@@
© 2025 MarkdownDeck | Internal Use Only [align=center][fontsize=10]

===

# Overflow Handling

## Automatic Content Flow

:::section [height=150][background=#F1F5F9][padding=20][gap=20]
    This section has fixed height. When content exceeds the available space, MarkdownDeck automatically creates continuation slides.
    The system handles:
    - Text splitting
    - List continuation
    - Table splitting with header repetition
    - Image movement to next slide
    This ensures your presentation always renders correctly.
:::

@@@
MarkdownDeck Showcase v8 | Slide 34 of 56

===

# Gap Directive

## Spacing Between Children

:::section [gap=30]
    First paragraph in section with gap=30.

    Second paragraph has 30pt space above.

    Third paragraph also has 30pt space above.

    Nested section - gap is NOT inherited. These paragraphs have no automatic spacing.
:::

@@@
MarkdownDeck Showcase v8 | Slide 35 of 56
===

# Fill Directive

## Container-Based Image Sizing

:::row
    :::column [width=40%]
        :::section [width=100%][height=300]
            ![Filled Image](https://via.placeholder.com/400x600/0A74DA/FFFFFF?text=Fill) [fill]
        :::
    :::
    :::column [width=60%]
        :::section [padding=20]
            ### The [fill] Directive
            - Image fills its container
            - Ignores aspect ratio
            - Container MUST have explicit width AND height
        :::
    :::
:::

@@@
MarkdownDeck Showcase v8 | Slide 36 of 56

===

# Complex Dashboard

## Multi-Component Layout

:::row [gap=20]
    :::column [width=70%]
        :::section
            ### Main Chart Area

            ![Dashboard](https://via.placeholder.com/450x250/0A74DA/FFFFFF?text=Analytics) [width=450][height=250][background=#F8FAFC][padding=20][border="1pt solid #E2E8F0"]
        :::
    :::
    :::column [width=30%][gap=20]
        :::section
            ### Metrics

            **Revenue** [background=#DCFCE7][padding=15][margin-bottom=10]
            +15% ↑ [color=#10B981]

            **Costs** [background=#FEE2E2][padding=15]
            +5% ↑ [color=#EF4444]
        :::
    :::
:::

@@@
MarkdownDeck Showcase v8 | Slide 37 of 56

===

# Team Cards

## Profile Layout

:::row [gap=20]
    :::column [width=1/3]
        :::section [align=center]
            ![Avatar](https://via.placeholder.com/120x120/94A3B8/FFFFFF?text=AJ) [width=120][height=120][border-radius=60]
            **Alex Johnson**
            Lead Developer
        :::
    :::
    :::column [width=1/3]
        :::section [align=center]
            ![Avatar](https://via.placeholder.com/120x120/94A3B8/FFFFFF?text=MG) [width=120][height=120][border-radius=60]
            **Maria Garcia**
            Product Manager
        :::
    :::
    :::column [width=1/3]
        :::section [align=center]
            ![Avatar](https://via.placeholder.com/120x120/94A3B8/FFFFFF?text=DC) [width=120][height=120][border-radius=60]
            **David Chen**
            UX Designer
        :::
    :::
:::

@@@
MarkdownDeck Showcase v8 | Slide 38 of 56

===

# Quote Slide

## Centered Impact

:::section [height=420][valign=middle][align=center]
    *"The key to great design is capturing the spirit of the client and the essence of the space."* [font-family="Georgia"][fontsize=28][italic]
    — Famous Designer [fontsize=16][color=#475569]
:::

@@@
MarkdownDeck Showcase v8 | Slide 39 of 56

===

# Feature Comparison

## Product Tiers

:::section
    | Feature | Basic | Pro | Enterprise |[background=#0A74DA][color=white] |
    |---------|-------|-----|------------|---------------------------------|
    | Users | 10 | 100 | Unlimited | |
    | Storage | 10GB | 100GB | 1TB | [background=#F8FAFC] |
    | Support | Email | Priority | Dedicated | |
    | API Access | ❌ | ✓ | ✓ | [background=#F8FAFC] |
    | **Price** | **$9** | **$49** | **Custom** | [background=#FEF3C7] |
:::

@@@
MarkdownDeck Showcase v8 | Slide 40 of 56

===

# Process Timeline

## Four Phases

:::row [gap=10]
    :::column [width=24%]
        :::section [background=#DBEAFE][padding=20][align=center]
            **Phase 1** [bold]
            Discovery
        :::
    :::
    :::column [width=2%]
        :::section [align=center]
            →
        :::
    :::
    :::column [width=24%]
        :::section [background=#DCFCE7][padding=20][align=center]
            **Phase 2** [bold]
            Design
        :::
    :::
    :::column [width=2%]
        :::section [align=center]
            →
        :::
    :::
    :::column [width=24%]
        :::section [background=#FEF3C7][padding=20][align=center]
            **Phase 3** [bold]
            Develop
        :::
    :::
    :::column [width=2%]
        :::section [align=center]
            →
        :::
    :::
    :::column [width=24%]
        :::section [background=#FEE2E2][padding=20][align=center]
            **Phase 4** [bold]
            Deploy
        :::
    :::
:::

@@@
MarkdownDeck Showcase v8 | Slide 41 of 56

===

# Icon List

## Visual Bullets

:::row [gap=20][padding=20]
    :::column [width=10%]
        :::section
            ![Check](https://api.iconify.design/ph/check-circle-duotone.svg?color=%2310B981) [width=40][height=40]
        :::
    :::
    :::column [width=90%]
        :::section
            ### Completed Tasks
            All project milestones achieved on schedule.
        :::
    :::
:::

:::row [gap=20]
    :::column [width=10%]
        :::section
            ![Warning](https://api.iconify.design/ph/warning-circle-duotone.svg?color=%23F59E0B) [width=40][height=40]
        :::
    :::
    :::column [width=90%]
        :::section
            ### Pending Items
            Two deliverables awaiting client approval.
        :::
    :::
:::

@@@
MarkdownDeck Showcase v8 | Slide 42 of 56

===

# Metric Cards

## KPI Dashboard

:::row [gap=20]
    :::column [width=1/3]
        :::section [background=#F8FAFC][padding=20][align=center][border="1pt solid #E2E8F0"]
            Active Users [fontsize=14][color=#475569]
            **4,281** [fontsize=36][bold]
            +12% ↑ [fontsize=14][color=#10B981]
        :::
    :::
    :::column [width=1/3]
        :::section [background=#F8FAFC][padding=20][align=center][border="1pt solid #E2E8F0"]
            Revenue [fontsize=14][color=#475569]
            **$125K** [fontsize=36][bold]
            +23% ↑ [fontsize=14][color=#10B981]
        :::
    :::
    :::column [width=1/3]
        :::section [background=#F8FAFC][padding=20][align=center][border="1pt solid #E2E8F0"]
            Churn Rate [fontsize=14][color=#475569]
            **2.1%** [fontsize=36][bold]
            -0.3% ↓ [fontsize=14][color=#EF4444]
        :::
    :::
:::

@@@
MarkdownDeck Showcase v8 | Slide 43 of 56

===

# Opacity Example

## Transparency Effects

:::section[gap=20]
    ### Full Opacity (1.0)

    This section is fully opaque. [background=#0A74DA][padding=20][color=white]

    ### Semi-Transparent (0.7)

    This section is 70% opaque. [background=#0A74DA][padding=20][color=white][opacity=0.7]

    ### More Transparent (0.4)

    This section is 40% opaque. [background=#0A74DA][padding=20][color=white][opacity=0.4]
:::

@@@
MarkdownDeck Showcase v8 | Slide 44 of 56

===

# Border Radius

## Rounded Corners

:::row [gap=20]
    :::column [width=1/3]
        :::section [background=#F8FAFC][padding=30][border="2pt solid #E2E8F0"]
            No radius
            Sharp corners
        :::
    :::
    :::column [width=1/3]
        :::section [background=#F8FAFC][padding=30][border="2pt solid #E2E8F0"][border-radius=8]
            8pt radius
            Slightly rounded
        :::
    :::
    :::column [width=1/3]
        :::section [background=#F8FAFC][padding=30][border="2pt solid #E2E8F0"][border-radius=20]
            20pt radius
            Very rounded
        :::
    :::
:::

@@@
MarkdownDeck Showcase v8 | Slide 45 of 56

===
# Line Spacing

## Text Density Control

:::row
    :::column [gap=20]
        :::section [line-spacing=1.0][background=#EFF6FF]
            ### Single Spacing (1.0)
            This paragraph uses single line spacing. The lines are closer together, creating a more compact appearance. Good for fitting more content.
        :::

        :::section [line-spacing=1.25][margin-top=40][background=#F0FDF4]
            ### 1.25x Line Spacing
            This paragraph uses 1.25x line spacing. The extra space between lines improves readability, especially for longer blocks of text.
        :::

        :::section [line-spacing=1.5][margin-top=30][background=#F0FDF4]
            ### 1.5x Line Spacing
            This paragraph uses double line spacing. Maximum readability but uses more vertical space on the slide.
        :::
    :::
:::
@@@
MarkdownDeck Showcase v8 | Slide 46 of 56
===

# Combined Directives

## Multiple Styles Together

:::section [background=#1E293B][padding=30][border-radius=12][color=white]
    ### Dark Theme Card [fontsize=24]
    Combining background, padding, border-radius, and color. [fontsize=16]
    - White text on dark background [bold]
    - Rounded corners for modern look
    - Ample padding for breathing room
:::

@@@
MarkdownDeck Showcase v8 | Slide 47 of 56

===

# Width Formats

## Points, Percentages, and Fractions

:::row [gap=20]
    :::column [width=200]
        :::section [background=#DBEAFE][padding=15][align=center]
            200 points
        :::
    :::
    :::column [width=40%]
        :::section [background=#DCFCE7][padding=15][align=center]
            40 percent
        :::
    :::
    :::column [width=1/5]
        :::section [background=#FEF3C7][padding=15][align=center]
            1/5 fraction
        :::
    :::
:::

@@@
MarkdownDeck Showcase v8 | Slide 48 of 56

===

# Height Control

## Fixed vs Dynamic Heights

:::section [background=#F1F5F9][padding=20][height=100]
    This section has fixed 100pt height.
:::

:::section [background=#E0F2FE][padding=20][margin-top=20]
    This section has dynamic height based on content. It expands to fit whatever is inside.
:::

@@@
MarkdownDeck Showcase v8 | Slide 49 of 56

===

# Bold and Italic Flags

## Text Weight and Style

:::section
    Regular text for comparison.
    **Bold using markdown syntax**
    Bold using directive flag [bold]
    *Italic using markdown syntax*
    Italic using directive flag [italic]
    Combined bold and italic [bold][italic]
:::

@@@
MarkdownDeck Showcase v8 | Slide 50 of 56

===

# Common Mistakes to Avoid

## What NOT to Do

:::section
    ### ❌ Don't put content outside sections
    ### ❌ Don't forget image dimensions
    ### ❌ Don't use columns outside rows
    ### ❌ Don't forget to close fenced blocks
    ### ❌ Don't place directives on separate lines
:::

@@@
MarkdownDeck Showcase v8 | Slide 51 of 56

===

# Best Practices

## Tips for Success

:::row [gap=40]
    :::column [width=50%]
        :::section
            ### DO ✓
            - Use indentation for readability
            - Specify all dimensions explicitly
            - Close every fenced block
            - Test overflow behavior
        :::
    :::
    :::column [width=50%]
        :::section
            ### DON'T ✗
            - Assume default spacing
            - Nest too deeply
            - Mix unrelated features
            - Use invalid syntax
        :::
    :::
:::

@@@
MarkdownDeck Showcase v8 | Slide 52 of 56

===

# What's New in v8

## Content Normalization

:::section [background=#E8F4F8][padding=30]
    ### Automatic Block Separation
    The parser now automatically separates different block elements!
    No more manual blank lines between headings, paragraphs, and lists.

    ### Full Indentation Support
    You can now indent your content for better readability.
    The parser intelligently strips common indentation while preserving structure.
:::

@@@
MarkdownDeck Showcase v8 | Slide 53 of 56

===
# Quick Reference

## Essential Syntax

:::section
    ### Fenced Blocks
    ```markdown
    :::section [directives]
    :::row [directives]
    :::column [directives]
    :::
    ```

    ### Directives
    ```markdown
    [width=300] [height=200]
    [padding=20] [margin=15]
    [background=#F0F0F0]
    [align=center] [valign=middle]
    ```:::

@@@
MarkdownDeck Showcase v8 | Slide 54 of 56

===
# Color Reference

## Common Colors

:::row [gap=10]
    :::column [width=20%]
        :::section [background=#0A74DA][height=120]
            `#0A74DA`
        :::
    :::
    :::column [width=20%]
        :::section [background=#10B981][height=120]
            `#10B981`
        :::
    :::
    :::column [width=20%]
        :::section [background=#F59E0B][height=120]
            `#F59E0B`
        :::
    :::
    :::column [width=20%]
        :::section [background=#EF4444][height=120]
            `#EF4444`
        :::
    :::
    :::column [width=20%]
        :::section [background=#475569][height=120]
            `#475569`
        :::
    :::
:::

@@@
MarkdownDeck Showcase v8 | Slide 55 of 56
===

# Resources

## Learn More

:::section [align=center]
    ### Documentation
    github.com/arclio/markdowndeck

    ### Support
    Open an issue on GitHub

    ### Contributing
    Pull requests welcome!
:::

@@@
MarkdownDeck Showcase v8 | Slide 56 of 56

===

# Thank You!

## Start Building Amazing Presentations

:::section [align=center][margin-top=100]
    ![MarkdownDeck](https://placehold.co/200x200/0A74DA/FFFFFF?text=MD) [width=200][height=200]
    **MarkdownDeck v8** [fontsize=36][margin-top=20]
    Transform your ideas into beautiful slides [fontsize=18][color=#475569]
:::

<!-- notes:
Thank you for exploring MarkdownDeck v8!
Key improvements in this version:
- Automatic block separation
- Full indentation support
- More natural markdown writing
-->

@@@
© 2025 MarkdownDeck v8 | The End [align=center]

