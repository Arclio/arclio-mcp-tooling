import logging
from typing import cast

from markdowndeck.api.validation import is_valid_image_url
from markdowndeck.layout.constants import (
    DEFAULT_IMAGE_ASPECT_RATIO,
    MIN_IMAGE_HEIGHT,
)
from markdowndeck.models import ImageElement
from markdowndeck.models.slide import Section

logger = logging.getLogger(__name__)

_image_dimensions_cache = {}


def calculate_image_element_height(
    element: ImageElement | dict,
    available_width: float,
    available_height: float = 0,
) -> float:
    """
    Calculate the height needed for an image element with proactive scaling.
    This is a wrapper around calculate_image_display_size for compatibility.
    """
    _width, height = calculate_image_display_size(
        element, available_width, available_height
    )
    return height


def calculate_image_display_size(
    element: ImageElement | dict,
    available_width: float,
    available_height: float = 0,
    parent_section: "Section" = None,
) -> tuple[float, float]:
    """
    Calculate the display size for an image element with comprehensive proactive scaling.
    This is the single source of truth for URL validation and graceful failure.
    """
    image_element = (
        cast(ImageElement, element)
        if isinstance(element, ImageElement)
        else ImageElement(**element)
    )

    if not is_valid_image_url(image_element.url):
        from markdowndeck.api.placeholder import create_placeholder_image_url

        logger.warning(
            f"Image URL failed validation: {image_element.url}. Substituting with a placeholder URL."
        )
        width_directive = image_element.directives.get("width", 300)
        height_directive = image_element.directives.get("height", 200)

        image_element.url = create_placeholder_image_url(
            400, 300, f"Invalid Image\n{width_directive} x {height_directive}"
        )

    if hasattr(image_element, "directives") and image_element.directives:
        directives = image_element.directives
        has_fill = directives.get("fill", False)
        has_width = "width" in directives
        has_height = "height" in directives

        if has_fill and not (has_width and has_height):
            if hasattr(image_element, "size") and image_element.size:
                return image_element.size

            temp_width = available_width
            temp_height = (
                available_height if available_height > 0 else available_width * 9 / 16
            )
            image_element.size = (temp_width, temp_height)
            return temp_width, temp_height

    aspect_ratio = _get_image_aspect_ratio(image_element)
    if aspect_ratio <= 0:
        aspect_ratio = DEFAULT_IMAGE_ASPECT_RATIO

    # FIXED: The element's preferred size (from directives) must be constrained by the actual available space.
    target_width, target_height = _apply_element_size_directives(
        image_element, available_width, available_height
    )
    final_width, final_height = _calculate_dual_constraint_size(
        target_width, target_height, aspect_ratio
    )

    if final_height < MIN_IMAGE_HEIGHT and final_width > 0:
        final_height = MIN_IMAGE_HEIGHT
        final_width = final_height * aspect_ratio

    image_element.size = (final_width, final_height)

    logger.debug(
        f"Image proactively scaled: url={getattr(image_element, 'url', '')[:50]}..., "
        f"aspect_ratio={aspect_ratio:.2f}, "
        f"available=({available_width:.1f}×{available_height:.1f}), "
        f"final=({final_width:.1f}×{final_height:.1f})"
    )

    return final_width, final_height


def _get_image_aspect_ratio(element: ImageElement) -> float:
    """
    Get the aspect ratio (width/height) of an image.
    """
    if element.aspect_ratio and element.aspect_ratio > 0:
        return element.aspect_ratio

    url = getattr(element, "url", "")
    if not url:
        return DEFAULT_IMAGE_ASPECT_RATIO

    if url in _image_dimensions_cache:
        return _image_dimensions_cache[url]

    logger.debug(
        f"Using default aspect ratio {DEFAULT_IMAGE_ASPECT_RATIO:.2f} for image: {url[:50]}..."
    )
    _image_dimensions_cache[url] = DEFAULT_IMAGE_ASPECT_RATIO
    return DEFAULT_IMAGE_ASPECT_RATIO


def _apply_element_size_directives(
    element: ImageElement, available_width: float, available_height: float
) -> tuple[float, float]:
    """
    Apply element-specific width/height directives to determine target dimensions.
    """
    target_width = available_width
    target_height = available_height if available_height > 0 else float("inf")

    if hasattr(element, "directives") and element.directives:
        directives = element.directives

        if "width" in directives:
            width_directive = directives["width"]
            try:
                if isinstance(width_directive, str) and "%" in width_directive:
                    percentage = float(width_directive.strip("%")) / 100.0
                    target_width = available_width * percentage
                elif isinstance(width_directive, float) and 0 < width_directive <= 1:
                    target_width = available_width * width_directive
                elif isinstance(width_directive, int | float) and width_directive > 1:
                    target_width = min(float(width_directive), available_width)
            except (ValueError, TypeError):
                logger.warning(f"Invalid width directive on image: {width_directive}")

        if "height" in directives:
            height_directive = directives["height"]
            try:
                # Calculate the height specified by the directive
                calculated_directive_height = float("inf")
                if isinstance(height_directive, str) and "%" in height_directive:
                    if available_height > 0:
                        percentage = float(height_directive.strip("%")) / 100.0
                        calculated_directive_height = available_height * percentage
                elif isinstance(height_directive, float) and 0 < height_directive <= 1:
                    if available_height > 0:
                        calculated_directive_height = (
                            available_height * height_directive
                        )
                elif isinstance(height_directive, int | float) and height_directive > 1:
                    calculated_directive_height = float(height_directive)

                # The final target height is the minimum of the directive's preference
                # and the container's actual available height.
                if target_height != float("inf"):
                    target_height = min(target_height, calculated_directive_height)
                else:
                    target_height = calculated_directive_height

            except (ValueError, TypeError):
                logger.warning(f"Invalid height directive on image: {height_directive}")

    return target_width, target_height


def _calculate_dual_constraint_size(
    target_width: float, target_height: float, aspect_ratio: float
) -> tuple[float, float]:
    """
    Calculate final image size respecting both width and height constraints.
    """
    if target_height == float("inf") or target_height <= 0:
        final_width = target_width
        final_height = target_width / aspect_ratio
        return final_width, final_height

    width_constrained_height = target_width / aspect_ratio
    height_constrained_width = target_height * aspect_ratio

    if width_constrained_height <= target_height:
        final_width = target_width
        final_height = width_constrained_height
    else:
        final_width = height_constrained_width
        final_height = target_height

    logger.debug(
        f"Dual-constraint scaling: target=({target_width:.1f}×{target_height:.1f}), "
        f"aspect_ratio={aspect_ratio:.2f}, final=({final_width:.1f}×{final_height:.1f})"
    )

    return final_width, final_height
