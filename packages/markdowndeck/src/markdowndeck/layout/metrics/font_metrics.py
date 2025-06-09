"""Font metrics utilities using Pillow for accurate text measurement."""

import logging
from pathlib import Path

from PIL import ImageFont

logger = logging.getLogger(__name__)

# Cache for loaded fonts to avoid repeated file I/O
_font_cache: dict[tuple[str, float], ImageFont.FreeTypeFont] = {}

# Default system fonts to try if specific font family is not available
DEFAULT_FONTS = [
    # macOS fonts
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Times.ttc",
    "/Library/Fonts/Arial.ttf",
    # Linux fonts
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    # Windows fonts (if running on Windows with fonts available)
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/times.ttf",
]


def _get_font(
    font_size: float, font_family: str | None = None
) -> ImageFont.FreeTypeFont:
    """
    Load and cache a font for the given size and family.

    Args:
        font_size: Font size in points (minimum 1.0)
        font_family: Font family name (optional)

    Returns:
        PIL FreeTypeFont object
    """
    # Ensure minimum font size to avoid division by zero
    font_size = max(1.0, font_size)

    cache_key = (font_family or "default", font_size)

    if cache_key in _font_cache:
        return _font_cache[cache_key]

    font = None

    # If font_family is specified, try to find it in system fonts
    if font_family:
        # This is a simplified approach - in production you'd want to use
        # a proper font discovery mechanism
        for font_path in DEFAULT_FONTS:
            if Path(font_path).exists():
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    logger.debug(f"Loaded font {font_path} at size {font_size}")
                    break
                except OSError:
                    continue

    # Fall back to default font if specific font not found
    if font is None:
        try:
            # Try system default fonts
            for font_path in DEFAULT_FONTS:
                if Path(font_path).exists():
                    try:
                        font = ImageFont.truetype(font_path, font_size)
                        logger.debug(
                            f"Using fallback font {font_path} at size {font_size}"
                        )
                        break
                    except OSError:
                        continue
        except Exception:
            pass

    # Final fallback to PIL's default font
    if font is None:
        try:
            font = ImageFont.load_default(font_size)
            logger.debug(f"Using PIL default font at size {font_size}")
        except Exception:
            # Create a minimal default if all else fails
            font = ImageFont.load_default()
            logger.warning("Could not load any fonts, using minimal default")

    _font_cache[cache_key] = font
    return font


def calculate_text_bbox(
    text: str,
    font_size: float,
    font_family: str | None = None,
    max_width: float | None = None,
    line_height_multiplier: float = 1.0,
) -> tuple[float, float]:
    """
    Calculate the bounding box (width, height) for the given text.

    Args:
        text: Text to measure
        font_size: Font size in points
        font_family: Font family (optional)
        max_width: Maximum width for line wrapping (optional)
        line_height_multiplier: Typography-specific line height multiplier

    Returns:
        Tuple of (width, height) in points
    """
    if not text.strip():
        # Return minimal dimensions for empty text
        return (0.0, font_size * 1.2)

    font = _get_font(font_size, font_family)

    # Check if text contains newlines - if so, we need multi-line handling
    # even without a width constraint
    if "\n" in text or max_width is not None:
        # Multi-line measurement with or without wrapping
        return _calculate_wrapped_text_bbox(
            text, font, max_width, line_height_multiplier
        )

    # Single line measurement only for text without newlines
    try:
        bbox = font.getbbox(text)
        width = bbox[2] - bbox[0]  # right - left
        height = bbox[3] - bbox[1]  # bottom - top

        # Ensure minimum height is font size
        height = max(height, font_size)

        return (float(width), float(height))
    except Exception as e:
        logger.warning(f"Font bbox calculation failed, using estimation: {e}")
        # Fallback calculation
        return _estimate_text_size(text, font_size)


def _estimate_text_size(text: str, font_size: float) -> tuple[float, float]:
    """
    Fallback text size estimation when font metrics fail.

    Args:
        text: Text to measure
        font_size: Font size in points

    Returns:
        Tuple of (width, height) in points
    """
    # Rough estimation: average character width is ~0.6 * font_size
    char_width = font_size * 0.6
    line_height = font_size * 1.2

    lines = text.split("\n")
    max_line_width = max((len(line) * char_width for line in lines), default=0)
    total_height = len(lines) * line_height

    return (float(max_line_width), float(total_height))


def _calculate_wrapped_text_bbox(
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: float | None,
    line_height_multiplier: float = 1.0,
) -> tuple[float, float]:
    """
    Calculate bbox for text that may wrap across multiple lines.

    Args:
        text: Text to measure
        font: PIL font object
        max_width: Maximum width before wrapping (None for no wrapping)

    Returns:
        Tuple of (width, height) in points
    """
    # Handle explicit newlines first
    paragraphs = text.split("\n")
    all_lines = []

    for paragraph in paragraphs:
        if not paragraph.strip():
            # Empty line
            all_lines.append("")
        else:
            if max_width is not None:
                # Wrap this paragraph
                wrapped_lines = _wrap_text_to_lines(paragraph, font, max_width)
                all_lines.extend(wrapped_lines)
            else:
                # No wrapping, just add the paragraph as-is
                all_lines.append(paragraph)

    if not all_lines:
        return (0.0, font.size * 1.2)

    # Calculate total width (max of all line widths) and height
    max_line_width = 0.0

    # Get proper font metrics for accurate line height calculation
    try:
        ascent, descent = font.getmetrics()
        # This gives us the proper line height that accounts for ascenders and descenders
        base_line_height = float(ascent + abs(descent))
    except (AttributeError, Exception):
        # Fallback: use font size with reasonable spacing
        base_line_height = font.size * 1.2

    # Apply typography-specific line height multiplier
    proper_line_height = base_line_height * line_height_multiplier

    for line in all_lines:
        if line.strip():  # Non-empty line
            try:
                bbox = font.getbbox(line)
                line_width = bbox[2] - bbox[0]
            except Exception:
                # Fallback for problematic lines
                line_width = len(line) * font.size * 0.6

            max_line_width = max(max_line_width, line_width)

    # Total height is number of lines times the proper line height
    # This now correctly accounts for spacing between lines
    total_height = len(all_lines) * proper_line_height

    return (float(max_line_width), float(total_height))


def _wrap_text_to_lines(
    text: str, font: ImageFont.FreeTypeFont, max_width: float
) -> list[str]:
    """
    Wrap text into lines that fit within max_width.

    Args:
        text: Text to wrap
        font: PIL font object
        max_width: Maximum width per line

    Returns:
        List of lines
    """
    words = text.split()
    if not words:
        return [""]

    lines = []
    current_line = ""

    for word in words:
        # Test if adding this word would exceed max width
        test_line = f"{current_line} {word}".strip()

        try:
            bbox = font.getbbox(test_line)
            test_width = bbox[2] - bbox[0]
        except Exception:
            # Fallback calculation
            test_width = len(test_line) * font.size * 0.6

        if test_width <= max_width or not current_line:
            # Word fits, or it's the first word (must fit even if too long)
            current_line = test_line
        else:
            # Word doesn't fit, start new line
            if current_line:
                lines.append(current_line)
            current_line = word

    # Add the last line
    if current_line:
        lines.append(current_line)

    return lines if lines else [""]


def get_font_metrics(
    font_size: float, font_family: str | None = None
) -> dict[str, float]:
    """
    Get detailed font metrics for layout calculations.

    Args:
        font_size: Font size in points
        font_family: Font family (optional)

    Returns:
        Dictionary with font metrics including ascent, descent, line_height
    """
    font = _get_font(font_size, font_family)

    try:
        ascent, descent = font.getmetrics()
        # Ensure descent is positive (PIL returns it as negative)
        descent = abs(descent)
    except (AttributeError, Exception):
        # Fallback for older PIL versions or bitmap fonts
        ascent = font_size * 0.8
        descent = font_size * 0.2

    return {
        "ascent": float(ascent),
        "descent": float(descent),
        "line_height": float(ascent + descent),
        "font_size": font_size,
    }


def clear_font_cache():
    """Clear the font cache to free memory."""
    global _font_cache
    _font_cache.clear()
    logger.debug("Font cache cleared")
