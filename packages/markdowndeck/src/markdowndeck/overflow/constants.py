"""Configuration constants for the MarkdownDeck overflow handler system."""

# The suffix to add to the titles of continuation slides.
CONTINUED_TITLE_SUFFIX = "(continued)"

# The suffix to add to the footers of continuation slides.
CONTINUED_FOOTER_SUFFIX = "(cont.)"

# The suffix to add to the title of a list or table that is split across slides.
CONTINUED_ELEMENT_TITLE_SUFFIX = "(continued)"

# Default slide dimensions for overflow calculations
DEFAULT_SLIDE_WIDTH = 720.0
DEFAULT_SLIDE_HEIGHT = 405.0
DEFAULT_MARGINS = {"top": 50, "right": 50, "bottom": 50, "left": 50}

# Zone heights matching layout calculator constants
HEADER_HEIGHT = 90.0
FOOTER_HEIGHT = 30.0
