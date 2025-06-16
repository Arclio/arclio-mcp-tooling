"""
Test file for unit conversion functionality.
"""

import os
import sys

# Add the package to the path
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "../packages/google-workspace-mcp/src")
)

from google_workspace_mcp.utils.unit_conversion import (
    convert_template_zone_coordinates,
    convert_template_zones,
    emu_to_pt,
    pt_to_emu,
)


def test_emu_to_pt_conversion():
    """Test EMU to PT conversion."""
    # 1 point = 12,700 EMU
    assert emu_to_pt(12700) == 1.0
    assert emu_to_pt(25400) == 2.0
    assert emu_to_pt(914400) == 72.0  # 1 inch in points
    print("✅ EMU to PT conversion tests passed")


def test_pt_to_emu_conversion():
    """Test PT to EMU conversion."""
    # 1 point = 12,700 EMU
    assert pt_to_emu(1.0) == 12700
    assert pt_to_emu(2.0) == 25400
    assert pt_to_emu(72.0) == 914400  # 1 inch in EMU
    print("✅ PT to EMU conversion tests passed")


def test_convert_template_zone_coordinates():
    """Test template zone coordinate conversion."""
    # Sample zone data in EMU
    zone_data = {
        "zone_name": "test_zone",
        "x_emu": 25400,  # 2 PT
        "y_emu": 38100,  # 3 PT
        "width_emu": 127000,  # 10 PT
        "height_emu": 254000,  # 20 PT
    }

    # Convert to PT
    converted = convert_template_zone_coordinates(zone_data, "PT")

    assert converted["x_pt"] == 2.0
    assert converted["y_pt"] == 3.0
    assert converted["width_pt"] == 10.0
    assert converted["height_pt"] == 20.0

    # Original EMU values should still be present
    assert converted["x_emu"] == 25400
    assert converted["y_emu"] == 38100

    print("✅ Template zone coordinate conversion tests passed")


def test_template_zones_structure():
    """Test conversion of nested template zones structure."""
    # Sample template zones data
    template_zones = {
        "zones": {
            "zone1": {
                "zone_name": "zone1",
                "x_emu": 12700,  # 1 PT
                "y_emu": 25400,  # 2 PT
                "width_emu": 63500,  # 5 PT
                "height_emu": 127000,  # 10 PT
            },
            "zone2": {
                "zone_name": "zone2",
                "x_emu": 38100,  # 3 PT
                "y_emu": 50800,  # 4 PT
                "width_emu": 76200,  # 6 PT
                "height_emu": 152400,  # 12 PT
            },
        }
    }

    # Convert to PT
    converted = convert_template_zones(template_zones, "PT")

    # Check structure is preserved
    assert "zones" in converted
    assert "zone1" in converted["zones"]
    assert "zone2" in converted["zones"]

    # Check zone1 conversion
    zone1 = converted["zones"]["zone1"]
    assert zone1["x_pt"] == 1.0
    assert zone1["y_pt"] == 2.0
    assert zone1["width_pt"] == 5.0
    assert zone1["height_pt"] == 10.0

    # Check zone2 conversion
    zone2 = converted["zones"]["zone2"]
    assert zone2["x_pt"] == 3.0
    assert zone2["y_pt"] == 4.0
    assert zone2["width_pt"] == 6.0
    assert zone2["height_pt"] == 12.0

    print("✅ Template zones structure conversion tests passed")


if __name__ == "__main__":
    print("Running unit conversion tests...")
    test_emu_to_pt_conversion()
    test_pt_to_emu_conversion()
    test_convert_template_zone_coordinates()
    test_template_zones_structure()
    print("\n🎉 All unit conversion tests passed!")
