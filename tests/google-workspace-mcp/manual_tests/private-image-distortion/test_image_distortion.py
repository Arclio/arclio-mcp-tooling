#!/usr/bin/env python3
"""
Focused test script for investigating image distortion issues in Google Slides.

This script specifically tests different image embedding approaches to identify
where distortion occurs when using Apps Script vs REST API.

Usage:
    python test_image_distortion.py
"""

import json
import logging
import os
import sys
from typing import Any, Dict, List, Tuple

# Add the package to the Python path
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "packages", "google-workspace-mcp", "src"),
)

from google_workspace_mcp.auth.gauth import get_credentials
from google_workspace_mcp.services.slides import SlidesService

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def setup_environment():
    """Setup and validate environment."""
    required_vars = [
        "GOOGLE_WORKSPACE_CLIENT_ID",
        "GOOGLE_WORKSPACE_CLIENT_SECRET",
        "GOOGLE_WORKSPACE_REFRESH_TOKEN",
    ]

    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        return False

    try:
        get_credentials()
        print("✅ Environment setup complete")
        return True
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return False


def test_image_sizing_logic():
    """Test the image sizing logic that might cause distortion."""

    print("\n🔍 Testing Image Sizing Logic")
    print("=" * 40)

    # Test cases that might cause distortion
    test_cases = [
        {
            "name": "Background image (0,0, no size)",
            "position": {"x": 0, "y": 0},
            "expected_size": (720, 540),  # Full slide dimensions
            "description": "Should use full slide dimensions",
        },
        {
            "name": "Small image with exact dimensions",
            "position": {"x": 207, "y": 63, "width": 120, "height": 40},
            "expected_size": (120, 40),
            "description": "Should use exact specified dimensions",
        },
        {
            "name": "Width-only specification",
            "position": {"x": 100, "y": 100, "width": 200},
            "expected_size": (200, 112.5),  # 16:9 aspect ratio
            "description": "Should calculate height using 16:9 ratio",
        },
        {
            "name": "Height-only specification",
            "position": {"x": 100, "y": 100, "height": 150},
            "expected_size": (266.67, 150),  # 16:9 aspect ratio
            "description": "Should calculate width using 16:9 ratio",
        },
    ]

    for i, test_case in enumerate(test_cases):
        print(f"\n--- Test Case {i+1}: {test_case['name']} ---")
        print(f"Position: {test_case['position']}")
        print(f"Expected size: {test_case['expected_size']}")
        print(f"Description: {test_case['description']}")

        # Simulate the sizing logic from the code
        pos = test_case["position"]
        pos_x = pos.get("x", 100)
        pos_y = pos.get("y", 100)
        pos_width = pos.get("width")
        pos_height = pos.get("height")

        calculated_size = None

        if pos_x == 0 and pos_y == 0 and not pos_width and not pos_height:
            calculated_size = (720, 540)
            print(
                f"✅ Background image detected - using full slide dimensions: {calculated_size}"
            )
        elif pos_width and pos_height:
            calculated_size = (pos_width, pos_height)
            print(f"✅ Exact sizing - using specified dimensions: {calculated_size}")
        elif pos_width and not pos_height:
            calculated_height = pos_width * 9 / 16
            calculated_size = (pos_width, calculated_height)
            print(f"✅ Width-only sizing - calculated height: {calculated_size}")
        elif pos_height and not pos_width:
            calculated_width = pos_height * 16 / 9
            calculated_size = (calculated_width, pos_height)
            print(f"✅ Height-only sizing - calculated width: {calculated_size}")
        else:
            calculated_size = (200, 150)
            print(f"✅ Default sizing applied: {calculated_size}")

        # Check if calculated matches expected
        if calculated_size == test_case["expected_size"]:
            print("✅ Size calculation matches expected")
        else:
            print(
                f"⚠️  Size calculation differs: expected {test_case['expected_size']}, got {calculated_size}"
            )


def test_image_request_building():
    """Test how image requests are built for different scenarios."""

    print("\n🔍 Testing Image Request Building")
    print("=" * 40)

    slides_service = SlidesService()

    test_elements = [
        {
            "name": "Private Drive Image",
            "element": {
                "type": "image",
                "content": "https://drive.google.com/file/d/1obxZHk7ioeCn-BogkIJ3aVlTyst0hICv/view?usp=drive_link",
                "position": {"x": 0, "y": 0},
            },
        },
        {
            "name": "Public Image",
            "element": {
                "type": "image",
                "content": "https://example.com/public-image.jpg",
                "position": {"x": 100, "y": 100, "width": 200, "height": 150},
            },
        },
    ]

    for i, test_case in enumerate(test_elements):
        print(f"\n--- Test Case {i+1}: {test_case['name']} ---")

        try:
            element_id = f"test_element_{i}"
            slide_id = "test_slide_id"

            result = slides_service._build_image_request_generic(
                element_id, slide_id, test_case["element"]
            )

            if result:
                if result.get("_apps_script_image"):
                    print("✅ Detected as Apps Script image (private Drive)")
                    print(f"   Drive file ID: {result.get('drive_file_id')}")
                    print(f"   Position: {result.get('position')}")
                else:
                    print("✅ Built REST API image request")
                    request = result.get("createImage", {})
                    transform = request.get("elementProperties", {}).get(
                        "transform", {}
                    )
                    size = request.get("elementProperties", {}).get("size")

                    print(f"   URL: {request.get('url')}")
                    print(f"   Transform: {transform}")
                    if size:
                        print(f"   Size: {size}")
                    else:
                        print("   Size: Not specified (natural dimensions)")
            else:
                print("❌ Failed to build image request")

        except Exception as e:
            print(f"❌ Image request building failed: {e}")


def test_unit_conversions():
    """Test unit conversion logic that might affect image sizing."""

    print("\n🔍 Testing Unit Conversions")
    print("=" * 40)

    # Test different unit scenarios
    test_cases = [
        {"unit": "PT", "value": 100, "description": "Points (default)"},
        {"unit": "EMU", "value": 100, "description": "English Metric Units"},
        {"unit": "PX", "value": 100, "description": "Pixels"},
    ]

    for test_case in test_cases:
        print(f"\n--- Testing {test_case['unit']} ---")
        print(f"Value: {test_case['value']}")
        print(f"Description: {test_case['description']}")

        # Show how this would be used in a request
        request_structure = {
            "createImage": {
                "elementProperties": {
                    "transform": {
                        "translateX": test_case["value"],
                        "translateY": test_case["value"],
                        "unit": test_case["unit"],
                    },
                    "size": {
                        "width": {
                            "magnitude": test_case["value"],
                            "unit": test_case["unit"],
                        },
                        "height": {
                            "magnitude": test_case["value"],
                            "unit": test_case["unit"],
                        },
                    },
                }
            }
        }

        print(f"Request structure: {json.dumps(request_structure, indent=2)}")


def test_apps_script_vs_rest_api():
    """Compare Apps Script vs REST API image embedding approaches."""

    print("\n🔍 Comparing Apps Script vs REST API Approaches")
    print("=" * 50)

    print("\n📋 REST API Approach:")
    print("- Uses createImage request")
    print("- Direct URL embedding")
    print("- Supports public URLs only")
    print("- Size specified in request")
    print("- Transform includes position and scale")

    print("\n📋 Apps Script Approach:")
    print("- Uses embedPrivateImage function")
    print("- Requires Drive file ID")
    print("- Handles private Drive files")
    print("- Size calculated in Apps Script")
    print("- Position passed as parameters")

    print("\n🔍 Potential Distortion Sources:")
    print("1. Unit conversion differences (PT vs EMU)")
    print("2. Size calculation logic differences")
    print("3. Aspect ratio handling")
    print("4. Coordinate system differences")
    print("5. Apps Script vs REST API implementation differences")


def main():
    """Main investigation function."""
    print("🚀 Image Distortion Investigation")
    print("=" * 50)

    if not setup_environment():
        return

    # Run all tests
    test_image_sizing_logic()
    test_image_request_building()
    test_unit_conversions()
    test_apps_script_vs_rest_api()

    print("\n🎯 Investigation Summary:")
    print("1. Check if Apps Script uses different unit conversions")
    print("2. Verify size calculation logic in Apps Script")
    print("3. Compare coordinate systems between approaches")
    print("4. Test with known good images to establish baseline")
    print("5. Check Apps Script logs for detailed error information")


if __name__ == "__main__":
    main()
