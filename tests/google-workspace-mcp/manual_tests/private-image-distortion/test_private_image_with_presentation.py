#!/usr/bin/env python3
"""
Simple test script to test with a specific presentation ID.

Usage:
    python test_with_presentation.py PRESENTATION_ID

Example:
    python test_with_presentation.py 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms
"""

import json
import logging
import os
import sys
from typing import Any, Dict

presentation_id = "1cOTwsmXRwXoeCJJ1C9AwNhHRhqZB5KtzLbfq9Em6Rts"

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


def test_with_presentation(presentation_id: str):
    """Test the create_slide_with_elements function with a specific presentation."""

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
                # {
                #     "type": "image",
                #     "content": "https://drive.google.com/file/d/1WXUAHHk_0rRsUaze6v5lVTOKafy5JTyr/view?usp=drive_link",
                #     "position": {"x": 207, "y": 63, "width": 120, "height": 40},
                # },
                # {
                #     "type": "image",
                #     "content": "https://drive.google.com/file/d/1qPb_RC1ufWn9bzy2XG784lqhbFqn7Lvt/view?usp=drive_link",
                #     "position": {"x": 390, "y": 63, "width": 120, "height": 40},
                # },
            ],
        }
    ]

    print(f"🚀 Testing with presentation ID: {presentation_id}")
    print("=" * 60)

    try:
        # Initialize slides service
        slides_service = SlidesService()
        print("✅ Slides service initialized")

        # Test create_slide_with_elements
        for i, slide_data in enumerate(slides_data):
            print(f"\n--- Creating Slide {i+1} ---")

            result = slides_service.create_slide_with_elements(
                presentation_id=presentation_id,
                elements=slide_data.get("elements", []),
                background_color=slide_data.get("background_color"),
                create_slide=True,
                layout=slide_data.get("layout", "BLANK"),
            )

            print("✅ Slide creation result:")
            print(json.dumps(result, indent=2, default=str))

        print(f"\n🎉 Test completed! Check presentation: {presentation_id}")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        logger.exception("Test failed")

def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python test_with_presentation.py PRESENTATION_ID")
        print(
            "Example: python test_with_presentation.py 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
        )
        return

    presentation_id = sys.argv[1]

    # Check environment
    required_vars = [
        "GOOGLE_WORKSPACE_CLIENT_ID",
        "GOOGLE_WORKSPACE_CLIENT_SECRET",
        "GOOGLE_WORKSPACE_REFRESH_TOKEN",
    ]

    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        return

    try:
        get_credentials()
        print("✅ Authentication successful")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return

    test_with_presentation(presentation_id=presentation_id)


if __name__ == "__main__":
    main()
