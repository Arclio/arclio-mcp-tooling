"""
Overflow handling for MarkdownDeck slides with strict jurisdictional boundaries.

This package provides intelligent overflow detection and handling for slides
where content exceeds slide boundaries. It operates independently of the
layout calculator, taking positioned slides as input and producing optimally
distributed content across multiple slides.

Per the specification: The Overflow Handler's logic is triggered ONLY when a
section's external bounding box overflows the slide's available height. It
MUST IGNORE internal content overflow within sections that have user-defined,
fixed sizes.

Architecture:
- OverflowManager: Main orchestrator with strict jurisdictional boundaries
- OverflowDetector: Analyzes positioned slides for external overflow only
- OverflowHandlers: Implements unanimous consent model for coordinated splitting
- SlideBuilder: Creates continuation slides with proper position reset

Key Principles:
1. Strict Jurisdictional Boundary: Only external section overflow triggers handling
2. Element-Driven Splitting: All splitting decisions delegated to element models
3. Unanimous Consent: Row sections require all columns to consent to split
4. Minimum Requirements: Elements enforce minimum content requirements for splits
5. Structure Preservation: Layout structure maintained across continuation slides

Usage:
    from markdowndeck.overflow import OverflowManager

    # Create overflow manager with strict boundaries
    overflow_manager = OverflowManager()

    # Process positioned slide from layout calculator
    positioned_slide = layout_manager.calculate_positions(slide)
    final_slides = overflow_manager.process_slide(positioned_slide)
"""

import logging

from markdowndeck.overflow.detector import OverflowDetector
from markdowndeck.overflow.handlers import StandardOverflowHandler
from markdowndeck.overflow.manager import OverflowManager
from markdowndeck.overflow.slide_builder import SlideBuilder

logger = logging.getLogger(__name__)

# Public API exports
__all__ = [
    "OverflowManager",
    "OverflowDetector",
    "StandardOverflowHandler",
    "SlideBuilder",
    "create_overflow_manager",
    "process_positioned_slide",
    "validate_slide_for_overflow",
    "get_overflow_analysis",
]


def create_overflow_manager(
    slide_width: float = 720,
    slide_height: float = 405,
    margins: dict[str, float] = None,
) -> OverflowManager:
    """
    Create a configured overflow manager with strict jurisdictional boundaries.

    The created manager will only process external section overflow and ignore
    internal content overflow within user-defined, fixed-size sections.

    Args:
        slide_width: Width of slides in points
        slide_height: Height of slides in points
        margins: Slide margins (top, right, bottom, left)

    Returns:
        Configured OverflowManager instance with strict boundaries

    Example:
        >>> manager = create_overflow_manager()
        >>> slides = manager.process_slide(positioned_slide)
    """
    return OverflowManager(
        slide_width=slide_width,
        slide_height=slide_height,
        margins=margins,
    )


def process_positioned_slide(
    positioned_slide,
    slide_width: float = 720,
    slide_height: float = 405,
    margins: dict[str, float] = None,
) -> list:
    """
    Convenience function to process a single positioned slide with strict jurisdictional boundaries.

    This function applies the specification's overflow handling algorithm:
    1. Detect external section overflow only
    2. Apply unanimous consent model for row sections
    3. Delegate splitting decisions to elements with minimum requirements
    4. Create continuation slides with proper position reset

    Args:
        positioned_slide: Slide with positioned elements from layout calculator
        slide_width: Width of slides in points
        slide_height: Height of slides in points
        margins: Slide margins

    Returns:
        List of slides with content properly distributed

    Example:
        >>> from markdowndeck.layout import LayoutManager
        >>> from markdowndeck.overflow import process_positioned_slide
        >>>
        >>> layout_manager = LayoutManager()
        >>> positioned_slide = layout_manager.calculate_positions(slide)
        >>> final_slides = process_positioned_slide(positioned_slide)
    """
    manager = create_overflow_manager(
        slide_width=slide_width,
        slide_height=slide_height,
        margins=margins,
    )

    return manager.process_slide(positioned_slide)


def validate_slide_for_overflow(
    slide,
    slide_width: float = 720,
    slide_height: float = 405,
    margins: dict[str, float] = None,
) -> dict:
    """
    Validate a slide's structure for overflow processing compliance.

    This function checks that the slide is properly structured for the
    overflow handling system and identifies potential issues.

    Args:
        slide: The slide to validate
        slide_width: Width of slides in points
        slide_height: Height of slides in points
        margins: Slide margins

    Returns:
        Dictionary with validation results including warnings and recommendations

    Example:
        >>> validation = validate_slide_for_overflow(slide)
        >>> if validation['warnings']:
        ...     print("Slide validation warnings:", validation['warnings'])
    """
    manager = create_overflow_manager(
        slide_width=slide_width,
        slide_height=slide_height,
        margins=margins,
    )

    validation_result = {
        "is_valid": True,
        "warnings": [],
        "recommendations": [],
        "structure_analysis": {},
        "overflow_analysis": {},
    }

    # Validate slide structure
    structure_warnings = manager.validate_slide_structure(slide)
    validation_result["warnings"].extend(structure_warnings)

    # Get overflow analysis
    try:
        overflow_analysis = manager.get_overflow_analysis(slide)
        validation_result["overflow_analysis"] = overflow_analysis

        if overflow_analysis.get("has_overflow"):
            validation_result["recommendations"].append(
                "Slide has external overflow that will be processed by overflow handler"
            )
    except Exception as e:
        validation_result["warnings"].append(f"Could not analyze overflow: {e}")

    # Analyze structure
    validation_result["structure_analysis"] = {
        "has_sections": hasattr(slide, "sections") and bool(slide.sections),
        "element_count": len(slide.elements) if hasattr(slide, "elements") else 0,
        "section_count": (len(slide.sections) if hasattr(slide, "sections") and slide.sections else 0),
    }

    # Check for circular references
    if hasattr(slide, "sections") and slide.sections:
        try:
            has_circular = manager._has_circular_references(slide.sections[0], set())
            if has_circular:
                validation_result["warnings"].append("Slide has circular section references")
                validation_result["is_valid"] = False
        except Exception:
            pass  # Skip if structure checking fails

    validation_result["is_valid"] = len([w for w in validation_result["warnings"] if "circular" in w.lower()]) == 0

    return validation_result


def get_overflow_analysis(
    slide,
    slide_width: float = 720,
    slide_height: float = 405,
    margins: dict[str, float] = None,
) -> dict:
    """
    Get detailed overflow analysis for a slide.

    This function provides comprehensive analysis of overflow conditions
    in the slide, focusing on external section overflow per the specification.

    Args:
        slide: The slide to analyze
        slide_width: Width of slides in points
        slide_height: Height of slides in points
        margins: Slide margins

    Returns:
        Dictionary with detailed overflow analysis

    Example:
        >>> analysis = get_overflow_analysis(positioned_slide)
        >>> print(f"Has overflow: {analysis['has_overflow']}")
        >>> if analysis['overflowing_section_index'] is not None:
        ...     print(f"First overflowing section: {analysis['overflowing_section_index']}")
    """
    manager = create_overflow_manager(
        slide_width=slide_width,
        slide_height=slide_height,
        margins=margins,
    )

    return manager.get_overflow_analysis(slide)


# Configuration defaults with specification compliance
DEFAULT_SLIDE_WIDTH = 720
DEFAULT_SLIDE_HEIGHT = 405
DEFAULT_MARGINS = {"top": 50, "right": 50, "bottom": 50, "left": 50}

# Specification constants
SPECIFICATION_VERSION = "1.0"
SUPPORTED_SPLITTING_ELEMENTS = [
    "TextElement",
    "ListElement",
    "TableElement",
    "CodeElement",  # Now splittable per specification
]
ATOMIC_ELEMENTS = ["ImageElement"]  # Proactively scaled, so effectively atomic

logger.debug(f"MarkdownDeck overflow package initialized with specification v{SPECIFICATION_VERSION}")


def get_specification_info() -> dict:
    """
    Get information about the overflow handling specification implemented.

    Returns:
        Dictionary with specification details
    """
    return {
        "version": SPECIFICATION_VERSION,
        "supported_splitting_elements": SUPPORTED_SPLITTING_ELEMENTS,
        "atomic_elements": ATOMIC_ELEMENTS,
        "key_principles": [
            "Strict Jurisdictional Boundary",
            "Element-Driven Splitting",
            "Unanimous Consent Model",
            "Minimum Requirements Contract",
            "Structure Preservation",
        ],
        "minimum_requirements": {
            "TableElement": "Header + 2 data rows",
            "ListElement": "2 items",
            "TextElement": "2 lines",
            "CodeElement": "2 lines of code",
        },
    }
