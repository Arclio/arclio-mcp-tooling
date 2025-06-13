from unittest.mock import patch

import pytest
from markdowndeck.layout import LayoutManager
from markdowndeck.models import ElementType, ImageElement, Section, Slide, TextElement


@pytest.fixture
def layout_manager() -> LayoutManager:
    return LayoutManager()


def _create_unpositioned_slide(
    elements=None, root_section=None, object_id="test_slide"
):
    if elements is None:
        elements = []
    if root_section is None and elements:
        body_elements = [
            e
            for e in elements
            if e.element_type not in (ElementType.TITLE, ElementType.FOOTER)
        ]
        root_section = Section(id="root", children=body_elements)
    return Slide(object_id=object_id, elements=elements, root_section=root_section)


class TestLayoutManager:
    """Comprehensive tests for the LayoutManager component."""

    def test_layout_c_01_state_transition(self, layout_manager: LayoutManager):
        """Test Case: LAYOUT-C-01"""
        slide = _create_unpositioned_slide(
            elements=[
                TextElement(element_type=ElementType.TITLE, text="Title"),
                TextElement(element_type=ElementType.TEXT, text="Body"),
            ]
        )
        positioned_slide = layout_manager.calculate_positions(slide)
        assert (
            positioned_slide.elements == []
        ), "Initial elements inventory must be cleared."
        assert (
            len(positioned_slide.renderable_elements) == 1
        ), "Meta-elements should be in renderable."
        assert positioned_slide.renderable_elements[0].position is not None
        assert positioned_slide.root_section is not None
        assert (
            positioned_slide.root_section.position is not None
        ), "Root section must be positioned."
        assert (
            positioned_slide.root_section.children[0].position is not None
        ), "Body element must be positioned."

    @patch("markdowndeck.api.validation.is_valid_image_url", return_value=True)
    def test_layout_c_02_proactive_image_scaling(
        self, mock_is_valid, layout_manager: LayoutManager
    ):
        """Test Case: LAYOUT-C-02"""
        image = ImageElement(
            element_type=ElementType.IMAGE, url="test.png", aspect_ratio=16 / 9
        )
        slide = _create_unpositioned_slide(elements=[image])

        positioned_slide = layout_manager.calculate_positions(slide)
        positioned_image = positioned_slide.root_section.children[0]

        assert positioned_image.size is not None
        container_width = layout_manager.position_calculator.body_width

        expected_width = container_width
        expected_height = container_width / (16 / 9)

        assert abs(positioned_image.size[0] - expected_width) < 1.0
        assert abs(positioned_image.size[1] - expected_height) < 1.0

    def test_layout_c_04_fixed_height_directive_is_respected(
        self, layout_manager: LayoutManager
    ):
        """Test Case: LAYOUT-C-04"""
        tall_element = TextElement(element_type=ElementType.TEXT, text="Line 1\n" * 10)
        section = Section(
            id="fixed_height_sec", directives={"height": 100}, children=[tall_element]
        )
        slide = _create_unpositioned_slide(
            elements=[tall_element], root_section=section
        )

        positioned_slide = layout_manager.calculate_positions(slide)

        assert positioned_slide.root_section.size is not None
        # The LayoutManager calculates the INTRINSIC height needed. The OverflowManager handles the overflow.
        assert (
            positioned_slide.root_section.size[1] > 100.0
        ), "Layout manager should calculate intrinsic height, not respect fixed height."

    @patch("markdowndeck.layout.metrics.image.is_valid_image_url", return_value=False)
    def test_layout_c_08_invalid_image_url(
        self, mock_is_valid, layout_manager: LayoutManager
    ):
        """Test Case: LAYOUT-C-08"""
        image = ImageElement(element_type=ElementType.IMAGE, url="invalid.png")
        slide = _create_unpositioned_slide(elements=[image])

        positioned_slide = layout_manager.calculate_positions(slide)
        positioned_image = positioned_slide.root_section.children[0]

        assert positioned_image.size == (0, 0), "Invalid image must have size (0, 0)."
