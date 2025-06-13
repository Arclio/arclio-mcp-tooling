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
        TextElement(element_type=ElementType.TEXT, text="Fitted", size=(620, 20)),
        TextElement(element_type=ElementType.TEXT, text="Overflow", size=(620, 30)),
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


class TestOverflowManager:
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
