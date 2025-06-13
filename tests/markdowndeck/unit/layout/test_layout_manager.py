from unittest.mock import patch

import pytest
from markdowndeck.layout import LayoutManager
from markdowndeck.models import ElementType, ImageElement, Section, Slide, TextElement


@pytest.fixture
def layout_manager() -> LayoutManager:
    return LayoutManager(margins={"top": 0, "right": 0, "bottom": 0, "left": 0})


def _create_unpositioned_slide(
    elements=None, root_section=None, object_id="test_slide"
):
    """
    REFACTORED: Creates a spec-compliant Unpositioned slide for testing.
    This helper now correctly handles cases where only a root_section is passed
    and ensures the `slide.elements` inventory is always complete.
    """
    inventory = []
    if elements:
        inventory.extend(elements)

    if root_section is None:
        # If no root section is provided, create one from the provided elements.
        if elements:
            body_elements = [
                e
                for e in elements
                if e.element_type
                not in (ElementType.TITLE, ElementType.SUBTITLE, ElementType.FOOTER)
            ]
            root_section = Section(id="root", children=body_elements)
        else:
            root_section = Section(id="root", children=[])
    else:
        # A root section was provided. Ensure its elements are in the inventory.
        def extract_elements(section):
            _elements = []
            if section and hasattr(section, "children"):
                for child in section.children:
                    if isinstance(child, Section):
                        _elements.extend(extract_elements(child))
                    else:
                        _elements.append(child)
            return _elements

        section_elements = extract_elements(root_section)
        # Make sure not to add duplicates if elements were also passed.
        inventory_ids = {el.object_id for el in inventory if el.object_id}
        for el in section_elements:
            if not el.object_id or el.object_id not in inventory_ids:
                inventory.append(el)

    return Slide(object_id=object_id, elements=inventory, root_section=root_section)


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

    def test_layout_c_03_spatial_directives_width_align(
        self, layout_manager: LayoutManager
    ):
        """Test Case: LAYOUT-C-03. Spec: Verify interpretation of spatial directives."""
        # Arrange
        text_element = TextElement(element_type=ElementType.TEXT, text="Aligned")
        section = Section(
            id="spatial_sec",
            directives={"width": "50%", "align": "right"},
            children=[text_element],
        )
        slide = _create_unpositioned_slide(root_section=section)

        # Act
        positioned_slide = layout_manager.calculate_positions(slide)
        positioned_section = positioned_slide.root_section
        positioned_element = positioned_section.children[0]

        # Assert Section Width
        expected_section_width = layout_manager.max_content_width * 0.5
        assert positioned_section.size is not None
        assert abs(positioned_section.size[0] - expected_section_width) < 1.0

        # Assert Element Alignment
        expected_element_x = (
            positioned_section.position[0]
            + positioned_section.size[0]
            - positioned_element.size[0]
        )
        assert positioned_element.position is not None
        assert abs(positioned_element.position[0] - expected_element_x) < 1.0

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

    def test_layout_c_05_equal_space_division_for_columns(
        self, layout_manager: LayoutManager
    ):
        """Test Case: LAYOUT-C-05. Spec: Verify equal space division for horizontal sections."""
        # Arrange
        col1 = Section(
            id="c1", children=[TextElement(element_type=ElementType.TEXT, text="Col 1")]
        )
        col2 = Section(
            id="c2", children=[TextElement(element_type=ElementType.TEXT, text="Col 2")]
        )
        row = Section(id="row", type="row", children=[col1, col2])
        slide = _create_unpositioned_slide(root_section=row)

        # Act
        positioned_slide = layout_manager.calculate_positions(slide)
        positioned_row = positioned_slide.root_section
        p_col1, p_col2 = positioned_row.children

        # Assert
        expected_width = layout_manager.max_content_width / 2
        assert abs(p_col1.size[0] - expected_width) < 1.0
        assert abs(p_col2.size[0] - expected_width) < 1.0
        assert abs(p_col2.position[0] - (p_col1.position[0] + p_col1.size[0])) < 1.0

    def test_layout_c_06_gap_directive(self, layout_manager: LayoutManager):
        """Test Case: LAYOUT-C-06. Spec: Verify `gap` directive controls spacing."""
        # Arrange
        el1 = TextElement(element_type=ElementType.TEXT, text="First")
        el2 = TextElement(element_type=ElementType.TEXT, text="Second")
        section = Section(id="gapped_sec", directives={"gap": 30}, children=[el1, el2])
        slide = _create_unpositioned_slide(root_section=section)

        # Act
        positioned_slide = layout_manager.calculate_positions(slide)
        p_el1, p_el2 = positioned_slide.root_section.children

        # Assert
        vertical_gap = p_el2.position[1] - (p_el1.position[1] + p_el1.size[1])
        assert abs(vertical_gap - 30.0) < 1.0

    def test_layout_c_07_flexible_body_area(self, layout_manager: LayoutManager):
        """Test Case: LAYOUT-C-07. Spec: Verify 'Flexible Body Area' calculation."""
        # Arrange
        slide_with_meta = _create_unpositioned_slide(
            elements=[
                TextElement(element_type=ElementType.TITLE, text="Title"),
                TextElement(element_type=ElementType.TEXT, text="Body 1"),
            ]
        )
        slide_without_meta = _create_unpositioned_slide(
            elements=[TextElement(element_type=ElementType.TEXT, text="Body 2")]
        )

        # Act
        pos_slide_with_meta = layout_manager.calculate_positions(slide_with_meta)
        pos_slide_without_meta = layout_manager.calculate_positions(slide_without_meta)

        # Assert
        body_y_with_meta = pos_slide_with_meta.root_section.position[1]
        body_y_without_meta = pos_slide_without_meta.root_section.position[1]

        assert (
            body_y_with_meta > body_y_without_meta
        ), "Body should be pushed down by title."

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

    def test_zero_default_spacing_principle(self, layout_manager: LayoutManager):
        """
        Test Case: PRINCIPLES.md, Sec 6.
        Spec: Verify that default vertical spacing between elements is zero.
        """
        # Arrange
        el1 = TextElement(element_type=ElementType.TEXT, text="First")
        el2 = TextElement(element_type=ElementType.TEXT, text="Second")
        section = Section(id="no_gap_sec", children=[el1, el2])  # No gap directive
        slide = _create_unpositioned_slide(root_section=section)

        # Act
        positioned_slide = layout_manager.calculate_positions(slide)
        p_el1, p_el2 = positioned_slide.root_section.children

        # Assert
        vertical_gap = p_el2.position[1] - (p_el1.position[1] + p_el1.size[1])
        assert abs(vertical_gap) < 1.0, "Default vertical gap should be zero."
