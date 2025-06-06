#!/usr/bin/env python3

"""
Simple test script to verify the overflow infinite loop fix.
"""

import sys

# Add the markdowndeck package to the path
sys.path.insert(0, "packages/markdowndeck/src")

from markdowndeck.models import ElementType, Slide, TextElement
from markdowndeck.models.slide import Section
from markdowndeck.overflow.manager import OverflowManager


def test_overflow_fix():
    """Test that overflow no longer creates infinite loops."""

    print("Testing overflow fix...")

    # Create reasonable test content that will overflow
    title = TextElement(
        element_type=ElementType.TITLE,
        text="Test Title",
        position=(50, 50),
        size=(620, 40),
        object_id="title_1",
    )

    # Create text that will overflow modestly (around 140pt with width 620)
    overflow_text = TextElement(
        element_type=ElementType.TEXT,
        text="Content that will need to overflow to the next slide. "
        * 12,  # ~140pt height
        position=(50, 150),
        size=(620, 140),
        object_id="overflow_text",
    )

    # Create section that's smaller than the text content to force overflow
    section = Section(
        id="test_section",
        type="section",
        position=(50, 150),
        size=(620, 100),  # Smaller than text height to force overflow
        elements=[overflow_text],
    )

    slide = Slide(
        object_id="overflow_test_slide",
        elements=[title, overflow_text],
        sections=[section],
        title="Test Title",
    )

    # Create overflow manager with dimensions that force overflow
    manager = OverflowManager(
        slide_width=720,
        slide_height=405,
        margins={"top": 50, "right": 50, "bottom": 50, "left": 50},
    )

    print(f"Manager body height: {manager.body_height}pt")
    print("Text element height: 140pt (should overflow)")

    try:
        result_slides = manager.process_slide(slide)
        print(f"SUCCESS: Created {len(result_slides)} slides")

        for i, result_slide in enumerate(result_slides):
            print(f"  Slide {i+1}: {result_slide.object_id}")
            print(f"    - {len(result_slide.sections)} sections")
            print(f"    - {len(result_slide.elements)} elements")

            # Check text content in continuation slides
            for element in result_slide.elements:
                if (
                    hasattr(element, "text")
                    and element.element_type == ElementType.TEXT
                ):
                    text_preview = (
                        element.text[:50] + "..."
                        if len(element.text) > 50
                        else element.text
                    )
                    print(f'    - Text: "{text_preview}" (length: {len(element.text)})')

        if len(result_slides) <= 3:
            print("✅ PASS: Reasonable number of slides created")
            return True
        print(f"❌ FAIL: Too many slides created ({len(result_slides)})")
        return False

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_overflow_fix()
    sys.exit(0 if success else 1)
