"""Enhanced layout constants for MarkdownDeck - Single Source of Truth."""

# =============================================================================
# SLIDE ZONES AND SPACING
# =============================================================================

# Zone Heights (Fixed zones on slide)
HEADER_HEIGHT = 90.0  # Height reserved for title/subtitle zone
FOOTER_HEIGHT = 30.0  # Height reserved for footer zone

# Inter-Zone Spacing (Clear spacing between major slide zones)
# REFACTORED: Set to 0.0 per "Zero Default Spacing" principle.
HEADER_TO_BODY_SPACING = 0.0  # Gap between header and body zones
BODY_TO_FOOTER_SPACING = 0.0  # Gap between body and footer zones

# Element Spacing (Within zones and sections)
# REFACTORED: Set to 0.0 per "Zero Default Spacing" principle.
VERTICAL_SPACING = 0.0  # Default vertical spacing between elements
HORIZONTAL_SPACING = 0.0  # Default horizontal spacing between elements
VERTICAL_SPACING_REDUCTION = 0.6  # Multiplier for related elements (40% reduction)

# =============================================================================
# TYPOGRAPHY AND FONT CONSTANTS
# =============================================================================

# Font Sizes (in points)
H1_FONT_SIZE = 24.0  # Main title font size
H2_FONT_SIZE = 20.0  # Subtitle font size
H3_FONT_SIZE = 18.0  # Section heading font size
H4_FONT_SIZE = 16.0  # Sub-section heading font size
H5_FONT_SIZE = 14.0  # Small heading font size
H6_FONT_SIZE = 12.0  # Smallest heading font size
P_FONT_SIZE = 14.0  # Paragraph text font size
CODE_FONT_SIZE = 12.0  # Code block font size
FOOTER_FONT_SIZE = 10.0  # Footer text font size

# Line Height Multipliers (relative to font size)
H1_LINE_HEIGHT_MULTIPLIER = 1.2  # Title line height
H2_LINE_HEIGHT_MULTIPLIER = 1.2  # Subtitle line height
P_LINE_HEIGHT_MULTIPLIER = 1.4  # Paragraph line height
CODE_LINE_HEIGHT_MULTIPLIER = 1.2  # Code line height
LIST_LINE_HEIGHT_MULTIPLIER = 1.3  # List item line height

# Character Width Estimates (for wrapping calculations)
STANDARD_CHAR_WIDTH = 5.0  # Points per character for standard text
MONOSPACE_CHAR_WIDTH = 7.5  # Points per character for monospace text
TITLE_CHAR_WIDTH = 5.5  # Points per character for title text

# =============================================================================
# ELEMENT PADDING CONSTANTS
# =============================================================================

# Internal Padding (space inside element boundaries)
TITLE_PADDING = 8.0  # Padding for title elements
SUBTITLE_PADDING = 6.0  # Padding for subtitle elements
TEXT_PADDING = 4.0  # Padding for regular text elements
QUOTE_PADDING = 12.0  # Padding for quote elements
CODE_PADDING = 8.0  # Padding for code blocks
LIST_PADDING = 6.0  # Padding for list elements
TABLE_PADDING = 6.0  # Padding for table elements
# REFACTORED: Set to 0.0 per "Zero Default Spacing" principle.
SECTION_PADDING = 0.0  # Default section padding (can be overridden)

# =============================================================================
# MINIMUM DIMENSIONS
# =============================================================================

# Minimum Heights (absolute minimums for visibility)
MIN_ELEMENT_HEIGHT = 16.0  # Absolute minimum for any visible element
MIN_SECTION_HEIGHT = 20.0  # Minimum section height
MIN_TITLE_HEIGHT = 30.0  # Minimum title height
MIN_SUBTITLE_HEIGHT = 25.0  # Minimum subtitle height
MIN_TEXT_HEIGHT = 18.0  # Minimum text height
MIN_LIST_HEIGHT = 25.0  # Minimum list height
MIN_TABLE_HEIGHT = 35.0  # Minimum table height
MIN_CODE_HEIGHT = 30.0  # Minimum code block height
MIN_QUOTE_HEIGHT = 25.0  # Minimum quote height
MIN_IMAGE_HEIGHT = 100.0  # Minimum image height

# Minimum Widths
MIN_ELEMENT_WIDTH = 10.0  # Absolute minimum element width
MIN_SECTION_WIDTH = 20.0  # Minimum section width

# =============================================================================
# DEFAULT ELEMENT PROPORTIONS
# =============================================================================

# Width Fractions (relative to container width)
TITLE_WIDTH_FRACTION = 0.9  # Title uses 90% of container width
SUBTITLE_WIDTH_FRACTION = 0.85  # Subtitle uses 85% of container width
QUOTE_WIDTH_FRACTION = 0.9  # Quote uses 90% of container width
IMAGE_WIDTH_FRACTION = 0.8  # Default image width fraction
TABLE_WIDTH_FRACTION = 1.0  # Tables use full width by default
CODE_WIDTH_FRACTION = 1.0  # Code blocks use full width
LIST_WIDTH_FRACTION = 1.0  # Lists use full width

# Height Fractions (for images and special elements)
IMAGE_HEIGHT_FRACTION = 0.6  # Default image height relative to container

# =============================================================================
# LIST-SPECIFIC CONSTANTS
# =============================================================================

# List Layout
LIST_INDENT_PER_LEVEL = 20.0  # Points of indentation per nesting level
LIST_BULLET_WIDTH = 12.0  # Space reserved for bullet/number
LIST_ITEM_SPACING = 4.0  # Vertical spacing between list items

# =============================================================================
# TABLE-SPECIFIC CONSTANTS
# =============================================================================

# Table Layout
TABLE_ROW_HEIGHT = 22.0  # Default height per table row
TABLE_HEADER_HEIGHT = 25.0  # Height for header row
TABLE_CELL_PADDING = 4.0  # Padding within table cells
TABLE_BORDER_WIDTH = 1.0  # Default border width

# =============================================================================
# CODE-SPECIFIC CONSTANTS
# =============================================================================

# Code Block Layout
CODE_LANGUAGE_LABEL_HEIGHT = 15.0  # Height for language label
CODE_BORDER_RADIUS = 4.0  # Border radius for code blocks

# =============================================================================
# IMAGE-SPECIFIC CONSTANTS
# =============================================================================

# Image Layout
DEFAULT_IMAGE_ASPECT_RATIO = 16 / 9  # Default aspect ratio when unknown
IMAGE_MAX_HEIGHT_FRACTION = 0.8  # Max height as fraction of container

# =============================================================================
# SLIDE LAYOUT CONSTANTS
# =============================================================================

# Default Slide Dimensions (Google Slides standard)
DEFAULT_SLIDE_WIDTH = 720.0  # 10 inches at 72 DPI
DEFAULT_SLIDE_HEIGHT = 405.0  # 5.625 inches at 72 DPI (16:9 aspect ratio)

# Default Margins
# REFACTORED: All margins set to 0.0 per "Zero Default Spacing" principle.
DEFAULT_MARGIN_TOP = 0.0  # Top margin
DEFAULT_MARGIN_RIGHT = 0.0  # Right margin
DEFAULT_MARGIN_BOTTOM = 20.0  # Bottom margin
DEFAULT_MARGIN_LEFT = 0.0  # Left margin

# =============================================================================
# ALIGNMENT CONSTANTS
# =============================================================================

# Horizontal Alignment
ALIGN_LEFT = "left"
ALIGN_CENTER = "center"
ALIGN_RIGHT = "right"
ALIGN_JUSTIFY = "justify"

# Vertical Alignment
VALIGN_TOP = "top"
VALIGN_MIDDLE = "middle"
VALIGN_BOTTOM = "bottom"

# =============================================================================
# CALCULATION SAFETY CONSTANTS
# =============================================================================

# Safety Margins (to prevent calculation errors)
CALCULATION_EPSILON = 0.1  # Minimum meaningful dimension difference
MAX_ITERATIONS = 100  # Maximum layout calculation iterations
OVERFLOW_TOLERANCE = 1000.0  # Maximum allowed overflow before warning
