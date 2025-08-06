#!/usr/bin/env python3
"""
Test script for Google Slides functionality and image distortion investigation.

This script tests the create_slide_with_elements function and investigates
image distortion issues when using Apps Script for private Drive images.

Usage:
    python test_slides_local.py

Environment Variables Required:
    GOOGLE_WORKSPACE_CLIENT_ID
    GOOGLE_WORKSPACE_CLIENT_SECRET
    GOOGLE_WORKSPACE_REFRESH_TOKEN
    GOOGLE_WORKSPACE_APPS_SCRIPT_ID (optional, for private Drive images)
"""

import json
import logging
import os
import sys
from typing import Any, Dict, List

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


def check_environment():
    """Check if required environment variables are set."""
    required_vars = [
        "GOOGLE_WORKSPACE_CLIENT_ID",
        "GOOGLE_WORKSPACE_CLIENT_SECRET",
        "GOOGLE_WORKSPACE_REFRESH_TOKEN",
    ]

    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"❌ Missing required environment variables: {missing_vars}")
        print("Please set these environment variables before running the script.")
        return False

    print("✅ All required environment variables are set")
    return True


def test_credentials():
    """Test Google authentication credentials."""
    try:
        credentials = get_credentials()
        print("✅ Google authentication credentials are valid")
        return True
    except Exception as e:
        print(f"❌ Google authentication failed: {e}")
        return False


def create_test_presentation(slides_service: SlidesService) -> str | None:
    """Create a test presentation and return its ID."""
    try:
        result = slides_service.create_presentation(
            "Test Presentation - Image Distortion Investigation"
        )
        presentation_id = result.get("presentationId")
        print(f"✅ Created test presentation: {presentation_id}")
        return presentation_id
    except Exception as e:
        print(f"❌ Failed to create presentation: {e}")
        return None


def test_create_slide_with_elements(
    slides_service: SlidesService, presentation_id: str
):
    """Test the create_slide_with_elements function with the provided data."""

    # Your test data
    slides_data = [
        {
            "layout": "BLANK",
            "background_color": "#feeef5",
            "elements": [
                {
                    "type": "image",
                    "content": "https://drive.google.com/file/d/1obxZHk7ioeCn-BogkIJ3aVlTyst0hICv/view?usp=drive_link",
                    "position": {"x": 0, "y": 0},
                },
                {
                    "type": "image",
                    "content": "https://drive.google.com/file/d/1WXUAHHk_0rRsUaze6v5lVTOKafy5JTyr/view?usp=drive_link",
                    "position": {"x": 207, "y": 63, "width": 120, "height": 40},
                },
                {
                    "type": "image",
                    "content": "https://drive.google.com/file/d/1qPb_RC1ufWn9bzy2XG784lqhbFqn7Lvt/view?usp=drive_link",
                    "position": {"x": 390, "y": 63, "width": 120, "height": 40},
                },
            ],
        }
    ]

    print("\n🔍 Testing create_slide_with_elements function...")

    for i, slide_data in enumerate(slides_data):
        print(f"\n--- Testing Slide {i+1} ---")

        try:
            # Test creating slide with elements
            result = slides_service.create_slide_with_elements(
                presentation_id=presentation_id,
                elements=slide_data.get("elements", []),
                background_color=slide_data.get("background_color"),
                create_slide=True,
                layout=slide_data.get("layout", "BLANK"),
            )

            print(f"✅ Slide creation result:")
            print(json.dumps(result, indent=2, default=str))

            # Extract slide ID for further testing
            slide_id = result.get("slideId")
            if slide_id:
                print(f"📄 Created slide ID: {slide_id}")

                # Test individual image functions to investigate distortion
                test_individual_image_functions(
                    slides_service, presentation_id, slide_id, slide_data
                )

        except Exception as e:
            print(f"❌ Failed to create slide: {e}")
            logger.exception("Slide creation failed")


def test_individual_image_functions(
    slides_service: SlidesService,
    presentation_id: str,
    slide_id: str,
    slide_data: Dict[str, Any],
):
    """Test individual image functions to investigate distortion issues."""

    print(f"\n🔍 Testing individual image functions for slide {slide_id}...")

    # Test each image element individually
    for i, element in enumerate(slide_data.get("elements", [])):
        if element.get("type") == "image":
            print(f"\n--- Testing Image {i+1} ---")
            test_single_image(slides_service, presentation_id, slide_id, element, i + 1)


def test_single_image(
    slides_service: SlidesService,
    presentation_id: str,
    slide_id: str,
    image_element: Dict[str, Any],
    image_num: int,
):
    """Test a single image element with different approaches."""

    image_url = image_element["content"]
    position = image_element["position"]

    print(f"Image URL: {image_url}")
    print(f"Position: {position}")

    # Test 1: Direct add_image function
    print(f"\n📸 Test {image_num}.1: Direct add_image function")
    try:
        result = slides_service.add_image(
            presentation_id=presentation_id,
            slide_id=slide_id,
            image_url=image_url,
            position=(position["x"], position["y"]),
            size=(
                (position.get("width"), position.get("height"))
                if position.get("width") and position.get("height")
                else None
            ),
        )
        print(f"✅ Direct add_image result: {result.get('objectId', 'No object ID')}")
    except Exception as e:
        print(f"❌ Direct add_image failed: {e}")

    # Test 2: add_image_with_unit function (PT units)
    print(f"\n📸 Test {image_num}.2: add_image_with_unit function (PT)")
    try:
        result = slides_service.add_image_with_unit(
            presentation_id=presentation_id,
            slide_id=slide_id,
            image_url=image_url,
            position=(position["x"], position["y"]),
            size=(
                (position.get("width"), position.get("height"))
                if position.get("width") and position.get("height")
                else None
            ),
            unit="PT",
        )
        print(
            f"✅ add_image_with_unit (PT) result: {result.get('objectId', 'No object ID')}"
        )
    except Exception as e:
        print(f"❌ add_image_with_unit (PT) failed: {e}")

    # Test 3: add_image_with_unit function (EMU units)
    print(f"\n📸 Test {image_num}.3: add_image_with_unit function (EMU)")
    try:
        result = slides_service.add_image_with_unit(
            presentation_id=presentation_id,
            slide_id=slide_id,
            image_url=image_url,
            position=(position["x"], position["y"]),
            size=(
                (position.get("width"), position.get("height"))
                if position.get("width") and position.get("height")
                else None
            ),
            unit="EMU",
        )
        print(
            f"✅ add_image_with_unit (EMU) result: {result.get('objectId', 'No object ID')}"
        )
    except Exception as e:
        print(f"❌ add_image_with_unit (EMU) failed: {e}")


def test_image_request_building(slides_service: SlidesService):
    """Test the image request building functions to understand distortion causes."""

    print("\n🔍 Testing image request building functions...")

    # Test data for different image scenarios
    test_cases = [
        {
            "name": "Full-size background image",
            "element": {
                "type": "image",
                "content": "https://drive.google.com/file/d/1obxZHk7ioeCn-BogkIJ3aVlTyst0hICv/view?usp=drive_link",
                "position": {"x": 0, "y": 0},
            },
        },
        {
            "name": "Small image with exact dimensions",
            "element": {
                "type": "image",
                "content": "https://drive.google.com/file/d/1WXUAHHk_0rRsUaze6v5lVTOKafy5JTyr/view?usp=drive_link",
                "position": {"x": 207, "y": 63, "width": 120, "height": 40},
            },
        },
        {
            "name": "Image with width only",
            "element": {
                "type": "image",
                "content": "https://drive.google.com/file/d/1qPb_RC1ufWn9bzy2XG784lqhbFqn7Lvt/view?usp=drive_link",
                "position": {"x": 100, "y": 100, "width": 200},
            },
        },
        {
            "name": "Image with height only",
            "element": {
                "type": "image",
                "content": "https://drive.google.com/file/d/1obxZHk7ioeCn-BogkIJ3aVlTyst0hICv/view?usp=drive_link",
                "position": {"x": 100, "y": 100, "height": 150},
            },
        },
    ]

    for i, test_case in enumerate(test_cases):
        print(f"\n--- Test Case {i+1}: {test_case['name']} ---")

        try:
            # Test _build_image_request_generic
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
                    print(
                        f"   Request structure: {json.dumps(result, indent=2, default=str)}"
                    )
            else:
                print("❌ Failed to build image request")

        except Exception as e:
            print(f"❌ Image request building failed: {e}")


def test_apps_script_image_embedding(
    slides_service: SlidesService, presentation_id: str
):
    """Test Apps Script image embedding directly."""

    print("\n🔍 Testing Apps Script image embedding...")

    # Test with a private Drive image
    drive_file_id = "1obxZHk7ioeCn-BogkIJ3aVlTyst0hICv"  # From your test data

    try:
        # Create a test slide first
        slide_result = slides_service.create_slide(presentation_id, "BLANK")
        slide_id = slide_result.get("objectId")

        if slide_id:
            print(f"📄 Created test slide: {slide_id}")

            # Test Apps Script embedding
            result = slides_service.embed_private_drive_image_via_script(
                presentation_id=presentation_id,
                slide_id=slide_id,
                drive_file_id=drive_file_id,
                position=(100, 100),
                size=(200, 150),
            )

            print(f"✅ Apps Script embedding result:")
            print(json.dumps(result, indent=2, default=str))

        else:
            print("❌ Failed to create test slide")

    except Exception as e:
        print(f"❌ Apps Script embedding failed: {e}")
        logger.exception("Apps Script embedding failed")


def main():
    """Main test function."""
    print("🚀 Starting Google Slides Test Script")
    print("=" * 50)

    # Check environment
    if not check_environment():
        return

    # Test credentials
    if not test_credentials():
        return

    try:
        # Initialize slides service
        slides_service = SlidesService()
        print("✅ Slides service initialized")

        # Create test presentation
        presentation_id = create_test_presentation(slides_service)
        if not presentation_id:
            return

        # Test image request building
        test_image_request_building(slides_service)

        # Test Apps Script embedding (if Apps Script ID is configured)
        if os.environ.get("GOOGLE_WORKSPACE_APPS_SCRIPT_ID"):
            test_apps_script_image_embedding(slides_service, presentation_id)
        else:
            print(
                "\n⚠️  Skipping Apps Script tests - GOOGLE_WORKSPACE_APPS_SCRIPT_ID not set"
            )

        # Test create_slide_with_elements
        test_create_slide_with_elements(slides_service, presentation_id)

        print(f"\n🎉 Test completed! Check presentation: {presentation_id}")
        print(
            "Open the presentation in Google Slides to see the results and investigate image distortion."
        )

    except Exception as e:
        print(f"❌ Test failed: {e}")
        logger.exception("Test failed")


if __name__ == "__main__":
    main()
