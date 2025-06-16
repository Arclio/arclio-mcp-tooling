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
) -> tuple[float, float, list[dict]]:
    """
    Calculate the bounding box (width, height) for the given text and return line metrics.
    """
    if not text.strip():
        return (0.0, font_size * 1.2, [])

    font = _get_font(font_size, font_family)

    if "\n" in text or max_width is not None:
        return _calculate_wrapped_text_bbox(
            text, font, max_width, line_height_multiplier
        )
    try:
        bbox = font.getbbox(text)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        height = max(height, font_size)
        line_metrics = [{"start": 0, "end": len(text), "height": height}]
        return (float(width), float(height), line_metrics)
    except Exception as e:
        logger.warning(f"Font bbox calculation failed, using estimation: {e}")
        width, height = _estimate_text_size(text, font_size)
        line_metrics = [{"start": 0, "end": len(text), "height": height}]
        return (width, height, line_metrics)


def _estimate_text_size(text: str, font_size: float) -> tuple[float, float]:
    """Fallback text size estimation when font metrics fail."""
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
) -> tuple[float, float, list[dict]]:
    """
    Calculate bbox for wrapped text and generate detailed line metrics.
    """
    paragraphs = text.split("\n")
    all_lines = []
    line_metrics = []
    current_char_index = 0

    try:
        ascent, descent = font.getmetrics()
        base_line_height = float(ascent + abs(descent))
    except Exception:
        base_line_height = font.size * 1.2
    proper_line_height = base_line_height * line_height_multiplier

    for p_idx, paragraph in enumerate(paragraphs):
        if not paragraph:
            all_lines.append("")
            line_metrics.append(
                {
                    "start": current_char_index,
                    "end": current_char_index,
                    "height": proper_line_height,
                }
            )
        else:
            if max_width is not None:
                wrapped_lines = _wrap_text_to_lines(paragraph, font, max_width)
                all_lines.extend(wrapped_lines)
                line_start_index_in_paragraph = 0
                for line in wrapped_lines:
                    line_len = len(line)
                    line_metrics.append(
                        {
                            "start": current_char_index + line_start_index_in_paragraph,
                            "end": current_char_index
                            + line_start_index_in_paragraph
                            + line_len,
                            "height": proper_line_height,
                        }
                    )
                    line_start_index_in_paragraph += len(line.rstrip())
            else:
                all_lines.append(paragraph)
                line_len = len(paragraph)
                line_metrics.append(
                    {
                        "start": current_char_index,
                        "end": current_char_index + line_len,
                        "height": proper_line_height,
                    }
                )

        current_char_index += len(paragraph)
        if p_idx < len(paragraphs) - 1:
            current_char_index += 1

    if not all_lines:
        return (0.0, font.size * 1.2, [])

    max_line_width = 0.0
    for line in all_lines:
        if line:
            try:
                bbox = font.getbbox(line)
                line_width = bbox[2] - bbox[0]
            except Exception:
                line_width = len(line) * font.size * 0.6
            max_line_width = max(max_line_width, line_width)

    total_height = len(all_lines) * proper_line_height

    return (float(max_line_width), float(total_height), line_metrics)


def _wrap_text_to_lines(
    text: str, font: ImageFont.FreeTypeFont, max_width: float
) -> list[str]:
    """Wrap text into lines that fit within max_width."""
    words = text.split()
    if not words:
        return [""]

    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()
        try:
            bbox = font.getbbox(test_line)
            test_width = bbox[2] - bbox[0]
        except Exception:
            test_width = len(test_line) * font.size * 0.6

        if test_width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
            try:
                word_bbox = font.getbbox(word)
                word_width = word_bbox[2] - word_bbox[0]
                if word_width > max_width:
                    avg_char_width = word_width / len(word)
                    split_idx = int(max_width / avg_char_width)
                    lines.append(word[:split_idx])
                    current_line = word[split_idx:]
            except Exception:
                pass

    if current_line:
        lines.append(current_line)
    return lines if lines else [""]


def get_font_metrics(
    font_size: float, font_family: str | None = None
) -> dict[str, float]:
    """Get detailed font metrics for layout calculations."""
    font = _get_font(font_size, font_family)
    try:
        ascent, descent = font.getmetrics()
        descent = abs(descent)
    except (AttributeError, Exception):
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
