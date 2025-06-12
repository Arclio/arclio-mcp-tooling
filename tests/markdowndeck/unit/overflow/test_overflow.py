"""
Unit tests for the OverflowManager, ensuring adherence to OVERFLOW_SPEC.md.
"""

from unittest.mock import MagicMock, patch

import pytest
from markdowndeck.models import (
    ElementType,
    Section,
    Slide,
    TextElement,
)
from markdowndeck.overflow import OverflowManager


@pytest.fixture
def positioned_slide_no_overflow() -> Slide:
    """Creates a slide that does NOT overflow."""
    root_section = Section(
        id="fitting_section",
        position=(50, 150),
        size=(620, 200),
        children=[
            TextElement(
                element_type=ElementType.TEXT,
                text="Fits",
                object_id="el1",
                position=(50, 150),
                size=(620, 50),
            )
        ],
    )
    return Slide(
        object_id="no_overflow", root_section=root_section, renderable_elements=[]
    )


@pytest.fixture
def positioned_slide_with_internal_overflow() -> Slide:
    """Creates a slide where content overflows a fixed-height section, but the section itself fits."""
    root_section = Section(
        id="internal_overflow_section",
        position=(50, 150),
        size=(620, 100),
        directives={"height": 100},
        children=[
            TextElement(
                element_type=ElementType.TEXT,
                text="Large content",
                object_id="el1",
                position=(50, 150),
                size=(620, 500),
            )
        ],
    )
    return Slide(
        object_id="internal_overflow", root_section=root_section, renderable_elements=[]
    )


@pytest.fixture
def positioned_slide_with_external_overflow() -> Slide:
    """Creates a slide where the root_section itself overflows the slide boundaries."""
    text_element = TextElement(
        element_type=ElementType.TEXT,
        text="Overflow Content\nLine2\nLine3",
        object_id="el_overflow",
        position=(50, 150),
        size=(620, 500),  # Size that causes overflow
    )
    text_element.split = lambda h: (
        TextElement(element_type=ElementType.TEXT, text="Fitted", size=(620, 20)),
        TextElement(element_type=ElementType.TEXT, text="Overflow", size=(620, 30)),
    )

    root_section = Section(
        id="overflowing_section",
        position=(50, 150),
        size=(620, 800),
        children=[text_element],
    )
    title = TextElement(
        element_type=ElementType.TITLE,
        text="Title",
        object_id="el_title",
        position=(50, 50),
        size=(620, 40),
    )
    return Slide(
        object_id="external_overflow",
        root_section=root_section,
        renderable_elements=[title],
        title="Original Title",
    )


class TestOverflowManager:
    def test_overflow_c_01(self, positioned_slide_no_overflow: Slide):
        """Test Case: OVERFLOW-C-01"""
        overflow_manager = OverflowManager()
        final_slides = overflow_manager.process_slide(positioned_slide_no_overflow)

        assert len(final_slides) == 1
        final_slide = final_slides[0]
        assert final_slide.root_section is None
        assert len(final_slide.renderable_elements) == 1
        assert final_slide.renderable_elements[0].text == "Fits"

    def test_overflow_c_02(self, positioned_slide_with_internal_overflow: Slide):
        """Test Case: OVERFLOW-C-02"""
        overflow_manager = OverflowManager()
        final_slides = overflow_manager.process_slide(
            positioned_slide_with_internal_overflow
        )

        assert len(final_slides) == 1
        assert final_slides[0].renderable_elements[0].text == "Large content"

    @patch(
        "markdowndeck.layout.LayoutManager.calculate_positions", side_effect=lambda s: s
    )
    def test_overflow_c_03_and_c_04(
        self,
        mock_calculate_positions: MagicMock,
        positioned_slide_with_external_overflow: Slide,
    ):
        """Test Cases: OVERFLOW-C-03 & C-04"""
        overflow_manager = OverflowManager()
        final_slides = overflow_manager.process_slide(
            positioned_slide_with_external_overflow
        )

        assert len(final_slides) == 2

        fitted_slide = final_slides[0]
        assert fitted_slide.renderable_elements[0].element_type == ElementType.TITLE
        assert fitted_slide.renderable_elements[1].text == "Fitted"
        assert fitted_slide.root_section is None

        mock_calculate_positions.assert_called_once()
        continuation_slide_arg = mock_calculate_positions.call_args[0][0]

        assert continuation_slide_arg.is_continuation is True
        continuation_title = continuation_slide_arg.get_title_element()
        assert continuation_title is not None
        assert "(continued)" in continuation_title.text

        continuation_root = continuation_slide_arg.root_section
        assert continuation_root is not None
        assert continuation_root.children[0].text == "Overflow"
