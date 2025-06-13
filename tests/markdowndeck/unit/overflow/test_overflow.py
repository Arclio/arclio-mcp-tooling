"""
Unit tests for the OverflowManager, ensuring adherence to OVERFLOW_SPEC.md.
"""

from unittest.mock import MagicMock, patch

import pytest
from markdowndeck.models import (
    ElementType,
    ImageElement,
    Section,
    Slide,
    TextElement,
)
from markdowndeck.overflow import OverflowManager


@pytest.fixture
def overflow_manager() -> OverflowManager:
    """Provides an OverflowManager with a mocked LayoutManager."""
    with patch("markdowndeck.layout.LayoutManager") as mock_lm_class:
        mock_lm_instance = MagicMock()
        mock_lm_instance.calculate_positions.side_effect = lambda s: s
        mock_lm_class.return_value = mock_lm_instance
        yield OverflowManager(margins={"top": 0, "right": 0, "bottom": 0, "left": 0})


@pytest.fixture
def positioned_slide_with_external_overflow() -> Slide:
    """Creates a slide where the root_section itself overflows."""
    text_element = TextElement(
        element_type=ElementType.TEXT,
        text="Overflow\nContent",
        object_id="el_overflow",
        position=(50, 50),
        size=(620, 500),
    )
    text_element.split = lambda h: (
        TextElement(
            element_type=ElementType.TEXT,
            text="Fitted",
            size=(620, 20),
            object_id="el_fitted",
        ),
        TextElement(
            element_type=ElementType.TEXT,
            text="Overflow",
            size=(620, 30),
            object_id="el_overflow_part",
        ),
    )
    root_section = Section(
        id="overflowing_section",
        position=(50, 50),
        size=(620, 800),
        children=[text_element],
    )
    # FIXED: The title must be created as an element and passed in the elements list.
    title = TextElement(
        element_type=ElementType.TITLE,
        text="Original Title",
        object_id="el_title",
        position=(50, 10),
        size=(620, 30),
    )
    return Slide(
        object_id="external_overflow",
        root_section=root_section,
        elements=[title],
        renderable_elements=[title],
    )


@pytest.fixture
def positioned_slide_no_overflow() -> Slide:
    """Creates a slide where content fits perfectly."""
    root_section = Section(
        id="fitting_section",
        position=(0, 0),
        size=(720, 300),  # Fits within 405 height
        children=[
            TextElement(
                element_type=ElementType.TEXT,
                text="Fits",
                position=(0, 0),
                size=(720, 100),
                object_id="el_fit",
            )
        ],
    )
    return Slide(object_id="no_overflow_slide", root_section=root_section)


class TestOverflowManager:
    def test_overflow_c_01_no_op_path(
        self,
        overflow_manager: OverflowManager,
        positioned_slide_no_overflow: Slide,
    ):
        """
        Test Case: OVERFLOW-C-01.
        Spec: A slide that fits is finalized without creating continuations.
        """
        # Act
        final_slides = overflow_manager.process_slide(positioned_slide_no_overflow)

        # Assert
        assert len(final_slides) == 1, "Should not create continuation slides."
        final_slide = final_slides[0]
        assert (
            final_slide.root_section is None
        ), "Finalized slide must have root_section cleared."
        assert (
            len(final_slide.renderable_elements) == 1
        ), "Renderable elements should be populated."
        assert final_slide.renderable_elements[0].object_id == "el_fit"
        overflow_manager.layout_manager.calculate_positions.assert_not_called()

    def test_overflow_c_02_internal_overflow_is_ignored(
        self, overflow_manager: OverflowManager
    ):
        """
        Test Case: OVERFLOW-C-02.
        Spec: Internal overflow in a fixed-height section is ignored if the section box fits.
        """
        # This test is expected to fail with the current implementation. See verification report.
        # Arrange: Section's external box fits, but its children would overflow if not clipped.
        section = Section(
            id="fixed_height_sec",
            position=(0, 0),
            size=(720, 200),  # This box fits.
            directives={"height": 200},
            children=[
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Tall content",
                    position=(0, 0),
                    size=(720, 500),
                    object_id="el_tall",
                )
            ],
        )
        slide = Slide(object_id="internal_overflow", root_section=section)

        # Act
        final_slides = overflow_manager.process_slide(slide)

        # Assert
        assert (
            len(final_slides) == 1
        ), "Internal overflow should be ignored and not cause a split."
        assert final_slides[0].renderable_elements[0].object_id == "el_tall"

    def test_overflow_c_03_and_c_04(
        self,
        overflow_manager: OverflowManager,
        positioned_slide_with_external_overflow: Slide,
    ):
        """Test Cases: OVERFLOW-C-03 & C-04"""
        final_slides = overflow_manager.process_slide(
            positioned_slide_with_external_overflow
        )
        assert len(final_slides) == 2

        fitted_slide = final_slides[0]
        assert fitted_slide.renderable_elements[0].element_type == ElementType.TITLE
        assert fitted_slide.renderable_elements[1].text == "Fitted"

        overflow_manager.layout_manager.calculate_positions.assert_called_once()
        continuation_slide_arg = (
            overflow_manager.layout_manager.calculate_positions.call_args[0][0]
        )
        assert continuation_slide_arg.is_continuation is True
        assert "(continued)" in continuation_slide_arg.get_title_element().text
        assert continuation_slide_arg.root_section.children[0].text == "Overflow"

    def test_overflow_c_05_no_empty_continuation_slides(
        self, overflow_manager: OverflowManager
    ):
        """
        Test Case: OVERFLOW-C-05.
        Spec: Verify that empty continuation slides are NOT created.
        """
        # Arrange: A text element whose split returns (self, None)
        text_element = TextElement(
            element_type=ElementType.TEXT,
            text="Content",
            object_id="el_full_fit",
            position=(50, 50),
            size=(620, 500),  # This causes an overflow
        )
        text_element.split = lambda h: (
            text_element,
            None,
        )  # Mocks a split where everything fits
        root_section = Section(
            id="sec_full_fit", position=(0, 0), size=(720, 800), children=[text_element]
        )
        slide = Slide(object_id="full_fit_slide", root_section=root_section)

        # Act
        final_slides = overflow_manager.process_slide(slide)

        # Assert
        assert len(final_slides) == 1, "Should not create an empty continuation slide."
        assert final_slides[0].renderable_elements[0].object_id == "el_full_fit"

    def test_integration_p_09_problematic_directives_not_propagated(
        self, overflow_manager: OverflowManager
    ):
        """Test Case: INTEGRATION-P-09"""
        overflowing_section = Section(
            id="s1",
            position=(50, 50),
            size=(620, 800),
            directives={"height": 800},
            children=[
                TextElement(
                    element_type=ElementType.TEXT,
                    text="A\nB\nC",
                    position=(50, 50),
                    size=(620, 800),
                )
            ],
        )
        overflowing_section.children[0].split = lambda h: (
            TextElement(element_type=ElementType.TEXT, text="A", size=(620, 100)),
            TextElement(element_type=ElementType.TEXT, text="B\nC", size=(620, 700)),
        )
        slide = Slide(object_id="directive_overflow", root_section=overflowing_section)

        final_slides = overflow_manager.process_slide(slide)

        assert len(final_slides) == 2, "Slide should have been split."
        continuation_slide_arg = (
            overflow_manager.layout_manager.calculate_positions.call_args[0][0]
        )
        assert (
            "height" not in continuation_slide_arg.root_section.directives
        ), "Problematic [height] directive must not be propagated."

    def test_overflow_spec_rule_2_atomic_element_handling(
        self, overflow_manager: OverflowManager
    ):
        """
        Test Case: OVERFLOW_SPEC.md, Rule #2.
        Spec: Verify OverflowHandler moves unsplittable elements atomically without calling split().
        """
        # Arrange
        # This image will cause an overflow
        image_element = ImageElement(
            element_type=ElementType.IMAGE,
            url="valid.png",
            object_id="atomic_image",
            position=(0, 0),
            size=(720, 500),  # Taller than slide height of 405
        )
        # Mock the split method to ensure it's not called
        image_element.split = MagicMock()

        root_section = Section(
            id="atomic_sec", position=(0, 0), size=(720, 500), children=[image_element]
        )
        slide = Slide(object_id="atomic_overflow", root_section=root_section)

        # Act
        final_slides = overflow_manager.process_slide(slide)

        # Assert
        assert len(final_slides) == 2, "Overflow should create a continuation slide."
        image_element.split.assert_not_called(), "split() must not be called on an ImageElement."

        # The image should be on the continuation slide
        assert (
            len(final_slides[0].renderable_elements) == 0
        ), "Fitted slide should have no body elements."

        continuation_slide_arg = (
            overflow_manager.layout_manager.calculate_positions.call_args[0][0]
        )
        assert len(continuation_slide_arg.root_section.children) == 1
        assert (
            continuation_slide_arg.root_section.children[0].object_id == "atomic_image"
        )
