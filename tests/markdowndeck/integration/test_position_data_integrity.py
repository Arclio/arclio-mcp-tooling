"""Integration tests for position and size data integrity through the full pipeline."""

import pytest
from markdowndeck.layout import LayoutManager
from markdowndeck.overflow import OverflowManager
from markdowndeck.parser import Parser


class TestPositionDataIntegrity:
    """Test that position and size data are preserved through the full processing pipeline."""

    @pytest.fixture
    def layout_manager(self):
        """Create a standard layout manager."""
        return LayoutManager(
            slide_width=720,
            slide_height=405,
            margins={"top": 50, "right": 50, "bottom": 50, "left": 50},
        )

    @pytest.fixture
    def overflow_manager(self):
        """Create a standard overflow manager."""
        return OverflowManager(
            slide_width=720,
            slide_height=405,
            margins={"top": 50, "right": 50, "bottom": 50, "left": 50},
        )

    def test_no_overflow_elements_have_positions(
        self, layout_manager, overflow_manager
    ):
        """
        CRITICAL: Test that elements in the final slide have position and size data
        when there is no overflow (the most common case).

        This test verifies the fix for the bug where positioned elements from
        slide.sections were never flattened into the final slide.elements list.
        """
        # Create markdown that will fit on one slide
        markdown = """# Test Slide

This is a test paragraph with some content.

* First item
* Second item
* Third item
"""

        # Parse the markdown
        parser = Parser()
        deck = parser.parse(markdown)
        parsed_slide = deck.slides[0]  # Get the first slide

        # Verify initial state - sections have elements but main elements list is incomplete
        assert len(parsed_slide.sections) > 0
        body_elements_in_sections = sum(len(s.elements) for s in parsed_slide.sections)
        assert body_elements_in_sections > 0

        # Apply layout calculations
        positioned_slide = layout_manager.calculate_positions(parsed_slide)

        # Verify layout manager sets positions in sections
        for section in positioned_slide.sections:
            assert section.position is not None
            assert section.size is not None
            for element in section.elements:
                assert (
                    element.position is not None
                ), f"Element {element.element_type} missing position"
                assert (
                    element.size is not None
                ), f"Element {element.element_type} missing size"

        # Process through overflow manager (no overflow expected)
        final_slides = overflow_manager.process_slide(positioned_slide)

        # Should get exactly one slide back
        assert len(final_slides) == 1
        final_slide = final_slides[0]

        # CRITICAL: Verify all elements in final slide have position and size
        body_element_count = 0
        for element in final_slide.elements:
            assert (
                element.position is not None
            ), f"Final element {element.element_type} missing position"
            assert (
                element.size is not None
            ), f"Final element {element.element_type} missing size"

            # CRITICAL: Verify elements are NOT at default fallback position (100, 100)
            x, y = element.position
            assert not (x == 100 and y == 100), (
                f"Element {element.element_type} still at default position (100, 100) - "
                f"layout calculation failed or positioned data was lost"
            )

            # Verify position values are reasonable
            assert isinstance(
                x, int | float
            ), f"Position x should be numeric, got {type(x)}"
            assert isinstance(
                y, int | float
            ), f"Position y should be numeric, got {type(y)}"
            width, height = element.size
            assert isinstance(
                width, int | float
            ), f"Size width should be numeric, got {type(width)}"
            assert isinstance(
                height, int | float
            ), f"Size height should be numeric, got {type(height)}"
            assert width > 0, f"Element width should be positive, got {width}"
            assert height > 0, f"Element height should be positive, got {height}"

            # Count non-meta elements (body content)
            from markdowndeck.models import ElementType

            if element.element_type not in (
                ElementType.TITLE,
                ElementType.SUBTITLE,
                ElementType.FOOTER,
            ):
                body_element_count += 1

        # Verify we have the expected number of body elements in the final list
        assert body_element_count == body_elements_in_sections, (
            f"Expected {body_elements_in_sections} body elements in final slide, "
            f"but found {body_element_count}"
        )

    def test_overflow_elements_have_positions(self, layout_manager, overflow_manager):
        """
        Test that elements in slides with overflow still have position and size data.

        This test verifies the fix for the deepcopy bug in the overflow handling
        that was stripping position/size data.
        """
        # Create markdown that will overflow to test the overflow path
        markdown = """# Long Content Slide

This is a test paragraph with content that should cause overflow.

This is another paragraph with content.

This is a third paragraph with content.

This is a fourth paragraph with content.

This is a fifth paragraph with content.

This is a sixth paragraph with content.

This is a seventh paragraph with content.

This is an eighth paragraph with content.

This is a ninth paragraph with content.

This is a tenth paragraph with content.

This is an eleventh paragraph with content.

This is a twelfth paragraph with content that should definitely cause overflow.
"""

        # Parse and layout
        parser = Parser()
        deck = parser.parse(markdown)
        parsed_slide = deck.slides[0]  # Get the first slide
        positioned_slide = layout_manager.calculate_positions(parsed_slide)

        # Process through overflow manager (overflow expected)
        final_slides = overflow_manager.process_slide(positioned_slide)

        # Should get multiple slides due to overflow
        assert len(final_slides) > 1, "Expected overflow to create multiple slides"

        # Verify ALL slides have properly positioned elements
        for slide_idx, slide in enumerate(final_slides):
            for element_idx, element in enumerate(slide.elements):
                assert (
                    element.position is not None
                ), f"Slide {slide_idx} element {element_idx} ({element.element_type}) missing position"
                assert (
                    element.size is not None
                ), f"Slide {slide_idx} element {element_idx} ({element.element_type}) missing size"

                # CRITICAL: Verify elements are NOT at default fallback position (100, 100)
                x, y = element.position
                assert not (x == 100 and y == 100), (
                    f"Slide {slide_idx} element {element_idx} ({element.element_type}) still at default position (100, 100) - "
                    f"layout calculation failed or positioned data was lost"
                )

                # Verify position values are reasonable (not (0,0) which might indicate default)
                assert isinstance(
                    x, int | float
                ), f"Position x should be numeric, got {type(x)}"
                assert isinstance(
                    y, int | float
                ), f"Position y should be numeric, got {type(y)}"
                width, height = element.size
                assert isinstance(
                    width, int | float
                ), f"Size width should be numeric, got {type(width)}"
                assert isinstance(
                    height, int | float
                ), f"Size height should be numeric, got {type(height)}"
                assert width > 0, f"Element width should be positive, got {width}"
                assert height > 0, f"Element height should be positive, got {height}"

    def test_column_layout_position_integrity(self, layout_manager, overflow_manager):
        """
        Test position integrity with column layouts (the most complex case).

        This tests the unanimous consent overflow logic and ensures that
        columnar layouts preserve position data correctly.
        """
        markdown = """# Column Test

---

## Left Column

Content for the left column:
* Item A
* Item B
* Item C

---

## Right Column

Content for the right column:
* Item X
* Item Y
* Item Z
* Extra item that might cause overflow
* Another extra item
* Yet another item to test overflow
"""

        # Parse, layout, and process
        parser = Parser()
        deck = parser.parse(markdown)
        parsed_slide = deck.slides[0]  # Get the first slide
        positioned_slide = layout_manager.calculate_positions(parsed_slide)
        final_slides = overflow_manager.process_slide(positioned_slide)

        # Verify position data integrity regardless of overflow
        for slide_idx, slide in enumerate(final_slides):
            for element_idx, element in enumerate(slide.elements):
                assert (
                    element.position is not None
                ), f"Slide {slide_idx} element {element_idx} ({element.element_type}) missing position"
                assert (
                    element.size is not None
                ), f"Slide {slide_idx} element {element_idx} ({element.element_type}) missing size"

                # CRITICAL: Verify elements are NOT at default fallback position (100, 100)
                x, y = element.position
                assert not (x == 100 and y == 100), (
                    f"Slide {slide_idx} element {element_idx} ({element.element_type}) still at default position (100, 100) - "
                    f"layout calculation failed or positioned data was lost"
                )

                # For column layouts, verify positions make sense spatially
                assert x >= 0, f"Position x should be non-negative, got {x}"
                assert y >= 0, f"Position y should be non-negative, got {y}"

    def test_notebook_deepcopy_pattern(self, layout_manager, overflow_manager):
        """
        Test the exact pattern used in the notebook with multiple deepcopy operations.

        This test reproduces the notebook's workflow to catch position data loss
        that might be caused by deepcopy operations.
        """
        from copy import deepcopy

        # Create simple markdown (like the notebook)
        markdown = """# Simple Slide Title
[background=#e0f0ff]

This is a paragraph in the first section.
It has some **bold** and *italic* text.

---
[width=1/2][padding=10]
## Column 1
- List item 1
- List item 2

***
[width=1/2][padding=10][align=center]
## Column 2
![placeholder](https://via.placeholder.com/150/d3d3d3/000000?Text=Image)
Centered caption.

@@@
Simple Footer Text
"""

        # Parse the markdown (Stage 1)
        parser = Parser()
        parsed_deck = parser.parse(markdown, title="Test Deck")

        # Stage 2: Layout Calculation (with deepcopy like notebook)
        deck_after_layout = deepcopy(parsed_deck)  # First deepcopy
        for slide in deck_after_layout.slides:
            layout_manager.calculate_positions(slide)

        # Stage 3: Overflow Handling (with another deepcopy like notebook)
        final_deck = deepcopy(deck_after_layout)  # Second deepcopy
        all_final_slides = []
        for slide in final_deck.slides:
            processed_slides = overflow_manager.process_slide(slide)
            all_final_slides.extend(processed_slides)

        # Verify final slide has properly positioned elements
        assert len(all_final_slides) == 1
        final_slide = all_final_slides[0]

        # Check each element for proper positioning
        for element_idx, element in enumerate(final_slide.elements):
            assert (
                element.position is not None
            ), f"Element {element_idx} ({element.element_type}) missing position after deepcopy workflow"
            assert (
                element.size is not None
            ), f"Element {element_idx} ({element.element_type}) missing size after deepcopy workflow"

            # CRITICAL: This is the check that should catch the notebook issue
            x, y = element.position
            assert not (x == 100 and y == 100), (
                f"Element {element_idx} ({element.element_type}) still at default position (100, 100) - "
                f"deepcopy operations may have corrupted position data"
            )

            # Verify position values are reasonable
            assert isinstance(
                x, int | float
            ), f"Position x should be numeric, got {type(x)}"
            assert isinstance(
                y, int | float
            ), f"Position y should be numeric, got {type(y)}"
            width, height = element.size
            assert width > 0, f"Element width should be positive, got {width}"
            assert height > 0, f"Element height should be positive, got {height}"
