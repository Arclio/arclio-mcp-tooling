from unittest.mock import MagicMock, patch

import pytest
from markdowndeck.models import (
    ElementType,
    ImageElement,
    Section,
    Slide,
)
from markdowndeck.overflow import OverflowManager


# MARKER: Test setup to isolate the OverflowManager
@pytest.fixture
def overflow_manager() -> OverflowManager:
    """
    Provides an OverflowManager with a mocked LayoutManager.
    The mock relayout is crucial because after the first split, the OverflowManager
    sends the new continuation slide back to the LayoutManager.
    """
    with patch("markdowndeck.layout.LayoutManager") as mock_lm_class:
        mock_lm_instance = MagicMock()

        # This simple mock relayout function assigns a position to any element
        # in the continuation slide's root section, which is necessary for the
        # next loop of overflow detection.
        def relayout_continuation(slide: Slide) -> Slide:
            if slide.root_section:
                y_offset = 50.0  # Start after a virtual top margin
                for child in slide.root_section.children:
                    if not child.position:
                        child.position = (50, y_offset)
                    if not child.size:
                        child.size = (620, 100)  # Give it a default size
                    y_offset += child.size[1]
            return slide

        mock_lm_instance.calculate_positions.side_effect = relayout_continuation
        mock_lm_class.return_value = mock_lm_instance

        # Instantiate the OverflowManager with the mocked LayoutManager
        yield OverflowManager(
            margins={"top": 50, "right": 50, "bottom": 50, "left": 50},
            slide_height=405,
        )


class TestOverflowBugReproduction:
    """Tests designed to fail, exposing known bugs in overflow handling."""

    def test_bug_image_split_is_not_called(self, overflow_manager: OverflowManager):
        """
        Test Case: OVERFLOW-BUG-04 (Custom ID)
        Description: This test replicates the fatal `NotImplementedError` from the logs.
                     It creates a slide where an ImageElement is the first item to overflow.
                     The OverflowManager, per spec, should identify it as unsplittable and
                     move it atomically to a new slide without calling .split().
        Expected to Fail: YES. This test will crash with `NotImplementedError` with the current code.
        """
        # Arrange: An image element positioned to overflow the slide height (405pt).
        image = ImageElement(
            element_type=ElementType.IMAGE,
            url="https://images.unsplash.com/photo-1521737711867-e3b97375f902",
            alt_text="A test image that overflows",
            object_id="overflowing_image_1",
            position=(50, 100),
            size=(600, 350),  # Position (100) + Height (350) = 450, which > 405.
            directives={"width": 600, "height": 350},
        )

        root_section = Section(
            id="r1", position=(50, 50), size=(620, 450), children=[image]
        )
        slide = Slide(object_id="s1_image_overflow", root_section=root_section)

        # Act & Assert
        # With the bug present, this call will raise NotImplementedError.
        # The fix will prevent the error, and the assertions below will pass.
        try:
            final_slides = overflow_manager.process_slide(slide)

            # These assertions will only be reached after the bug is fixed.
            assert (
                len(final_slides) == 2
            ), "An overflowing image should create a continuation slide."
            assert (
                len(final_slides[0].renderable_elements) == 0
            ), "Original slide should have no body elements left."

            # Check that the continuation slide was sent for re-layout
            overflow_manager.layout_manager.calculate_positions.assert_called_once()
            continuation_slide = (
                overflow_manager.layout_manager.calculate_positions.call_args[0][0]
            )
            assert continuation_slide.is_continuation is True
            assert len(continuation_slide.root_section.children) == 1
            assert (
                continuation_slide.root_section.children[0].object_id
                == "overflowing_image_1"
            )

        except NotImplementedError:
            pytest.fail(
                "BUG CONFIRMED: OverflowManager tried to call .split() on an ImageElement, violating OVERFLOW_SPEC.md Rule #2."
            )
