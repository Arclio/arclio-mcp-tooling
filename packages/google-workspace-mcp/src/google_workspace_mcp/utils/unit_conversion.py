"""
Unit conversion utilities for Google Slides API.

This module provides functions to convert between different units used in Google Slides:
- EMU (English Metric Units): 1 inch = 914,400 EMU, 1 point = 12,700 EMU
- PT (Points): 1 inch = 72 PT
- Inches
"""

import logging
from typing import Any, Dict, Union

logger = logging.getLogger(__name__)

# Conversion constants based on Google Slides API documentation
EMU_PER_INCH = 914400
EMU_PER_POINT = 12700
POINTS_PER_INCH = 72


def emu_to_pt(emu: Union[int, float]) -> float:
    """
    Convert EMU (English Metric Units) to Points.

    Args:
        emu: Value in EMU units

    Returns:
        Value in Points
    """
    return float(emu) / EMU_PER_POINT


def pt_to_emu(points: Union[int, float]) -> int:
    """
    Convert Points to EMU (English Metric Units).

    Args:
        points: Value in Points

    Returns:
        Value in EMU units
    """
    return int(float(points) * EMU_PER_POINT)


def emu_to_inches(emu: Union[int, float]) -> float:
    """
    Convert EMU (English Metric Units) to inches.

    Args:
        emu: Value in EMU units

    Returns:
        Value in inches
    """
    return float(emu) / EMU_PER_INCH


def inches_to_emu(inches: Union[int, float]) -> int:
    """
    Convert inches to EMU (English Metric Units).

    Args:
        inches: Value in inches

    Returns:
        Value in EMU units
    """
    return int(float(inches) * EMU_PER_INCH)


def pt_to_inches(points: Union[int, float]) -> float:
    """
    Convert Points to inches.

    Args:
        points: Value in Points

    Returns:
        Value in inches
    """
    return float(points) / POINTS_PER_INCH


def inches_to_pt(inches: Union[int, float]) -> float:
    """
    Convert inches to Points.

    Args:
        inches: Value in inches

    Returns:
        Value in Points
    """
    return float(inches) * POINTS_PER_INCH


def convert_template_zone_coordinates(
    zone_data: Dict[str, Any], target_unit: str = "PT"
) -> Dict[str, Any]:
    """
    Convert template zone coordinates from EMU to specified target unit.

    Args:
        zone_data: Dictionary containing zone information with EMU coordinates
        target_unit: Target unit ("PT", "EMU", or "INCHES")

    Returns:
        Dictionary with additional coordinates in target unit
    """
    if target_unit not in ["PT", "EMU", "INCHES"]:
        raise ValueError("target_unit must be 'PT', 'EMU', or 'INCHES'")

    # Create a copy to avoid modifying the original
    converted_zone = zone_data.copy()

    # Get EMU coordinates (these should always be present)
    x_emu = zone_data.get("x_emu", 0)
    y_emu = zone_data.get("y_emu", 0)
    width_emu = zone_data.get("width_emu", 0)
    height_emu = zone_data.get("height_emu", 0)

    if target_unit == "PT":
        converted_zone.update(
            {
                "x_pt": emu_to_pt(x_emu),
                "y_pt": emu_to_pt(y_emu),
                "width_pt": emu_to_pt(width_emu),
                "height_pt": emu_to_pt(height_emu),
            }
        )
    elif target_unit == "INCHES":
        converted_zone.update(
            {
                "x_inches": emu_to_inches(x_emu),
                "y_inches": emu_to_inches(y_emu),
                "width_inches": emu_to_inches(width_emu),
                "height_inches": emu_to_inches(height_emu),
            }
        )
    # For EMU, coordinates are already present

    return converted_zone


def convert_template_zones(
    template_zones: Dict[str, Any], target_unit: str = "PT"
) -> Dict[str, Any]:
    """
    Convert all template zones coordinates to specified target unit.

    Args:
        template_zones: Dictionary containing template zones data
        target_unit: Target unit ("PT", "EMU", or "INCHES")

    Returns:
        Dictionary with converted template zones
    """
    if not template_zones:
        raise ValueError("template_zones cannot be empty")

    converted_zones = {}

    # Handle both nested structure (from extract_template_zones_only)
    # and flat structure (single slide zones)
    if "slides_analyzed" in template_zones:
        # Nested structure from extract_template_zones_only
        converted_zones = template_zones.copy()
        converted_zones["slides_analyzed"] = []

        for slide_data in template_zones["slides_analyzed"]:
            converted_slide = slide_data.copy()
            if "template_zones" in slide_data:
                converted_slide["template_zones"] = {}
                for zone_name, zone_data in slide_data["template_zones"].items():
                    converted_slide["template_zones"][zone_name] = (
                        convert_template_zone_coordinates(zone_data, target_unit)
                    )
            converted_zones["slides_analyzed"].append(converted_slide)

    elif "zones" in template_zones:
        # Single slide structure from extract_template_zones_by_text
        converted_zones = template_zones.copy()
        converted_zones["zones"] = {}

        for zone_name, zone_data in template_zones["zones"].items():
            converted_zones["zones"][zone_name] = convert_template_zone_coordinates(
                zone_data, target_unit
            )
    else:
        # Direct zones dictionary
        for zone_name, zone_data in template_zones.items():
            converted_zones[zone_name] = convert_template_zone_coordinates(
                zone_data, target_unit
            )

    logger.info(
        f"Converted {len(template_zones)} template zones to {target_unit} coordinates"
    )
    return converted_zones
