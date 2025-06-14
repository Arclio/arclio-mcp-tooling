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

    @patch("markdowndeck.layout.metrics.image.is_valid_image_url", return_value=True)
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
        # REFACTORED: The test was incorrect. The LayoutManager MUST respect an explicit height directive
        # per the "Container-First" principle. The OverflowManager handles the consequences.
        tall_element = TextElement(element_type=ElementType.TEXT, text="Line 1\n" * 10)
        section = Section(
            id="fixed_height_sec", directives={"height": 100}, children=[tall_element]
        )
        slide = _create_unpositioned_slide(
            elements=[tall_element], root_section=section
        )

        positioned_slide = layout_manager.calculate_positions(slide)

        assert positioned_slide.root_section.size is not None
        assert (
            abs(positioned_slide.root_section.size[1] - 100.0) < 1.0
        ), "Layout manager must respect fixed height directives on sections."

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

    def test_layout_c_07_percentage_resolution_algorithm(
        self, layout_manager: LayoutManager
    ):
        """NEW TEST: Test Case LAYOUT-C-07. Validates Percentage Dimension Resolution Algorithm."""
        # Arrange: Nested sections. Parent has explicit width, grandparent does not.
        inner_section = Section(id="inner", directives={"width": "50%"})
        # Parent has EXPLICIT width, so inner should be 50% of parent's width.
        parent_section_explicit = Section(
            id="parent_explicit", directives={"width": "80%"}, children=[inner_section]
        )
        # Grandparent has INFERRED width, so parent should be 80% of slide width.
        grandparent_section = Section(
            id="grandparent", children=[parent_section_explicit]
        )
        slide = _create_unpositioned_slide(root_section=grandparent_section)

        # Act
        positioned_slide = layout_manager.calculate_positions(slide)
        p_grandparent = positioned_slide.root_section
        p_parent = p_grandparent.children[0]
        p_inner = p_parent.children[0]

        # Assert
        # Parent's width is 80% of slide content width.
        expected_parent_width = layout_manager.max_content_width * 0.8
        assert (
            abs(p_parent.size[0] - expected_parent_width) < 1.0
        ), "Parent width calculation failed"

        # Inner's width is 50% of parent's resolved width.
        expected_inner_width = expected_parent_width * 0.5
        assert (
            abs(p_inner.size[0] - expected_inner_width) < 1.0
        ), "Inner width calculation failed"

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

    def test_layout_c_09_padding_directive_offsets_children(
        self, layout_manager: LayoutManager
    ):
        """
        Test Case: LAYOUT-C-09
        Spec: Verify that `padding` directive on a Section correctly offsets children.
        """
        # Arrange
        child_element = TextElement(element_type=ElementType.TEXT, text="Padded")
        section = Section(
            id="padded_sec", directives={"padding": 20}, children=[child_element]
        )
        slide = _create_unpositioned_slide(root_section=section)

        # Act
        # The root section will be positioned at (0, 0) by default in the test fixture
        positioned_slide = layout_manager.calculate_positions(slide)
        positioned_child = positioned_slide.root_section.children[0]

        # Assert
        assert positioned_child.position == (
            20,
            20,
        ), "Child position should be offset by parent padding."

    def test_principles_c_06_b_zero_default_horizontal_spacing(
        self, layout_manager: LayoutManager
    ):
        """
        Test Case: PRINCIPLES-C-06-B
        Spec: Verify that default horizontal spacing (`gap`) between columns is zero.
        """
        # Arrange
        col1 = Section(
            id="c1",
            directives={"width": "30%"},
            children=[TextElement(element_type=ElementType.TEXT, text="Col 1")],
        )
        col2 = Section(
            id="c2",
            directives={"width": "70%"},
            children=[TextElement(element_type=ElementType.TEXT, text="Col 2")],
        )
        # This row has no `gap` directive
        row = Section(id="row", type="row", children=[col1, col2])
        slide = _create_unpositioned_slide(root_section=row)

        # Act
        positioned_slide = layout_manager.calculate_positions(slide)
        p_col1, p_col2 = positioned_slide.root_section.children

        # Assert
        horizontal_gap = p_col2.position[0] - (p_col1.position[0] + p_col1.size[0])
        assert (
            abs(horizontal_gap) < 1.0
        ), "Default horizontal gap between columns should be zero."

    def test_layout_c_12_mixed_column_widths(self, layout_manager: LayoutManager):
        """NEW TEST: Validates complex column width distribution (golden case failure)."""
        # Arrange
        col_implicit = Section(
            id="c_imp",
            children=[TextElement(element_type=ElementType.TEXT, text="Implicit")],
        )
        col_proportional = Section(
            id="c_prop",
            directives={"width": "25%"},
            children=[TextElement(element_type=ElementType.TEXT, text="Prop")],
        )
        col_absolute = Section(
            id="c_abs",
            directives={"width": 150},
            children=[TextElement(element_type=ElementType.TEXT, text="Abs")],
        )

        row = Section(
            id="row",
            type="row",
            children=[col_implicit, col_proportional, col_absolute],
        )
        slide = _create_unpositioned_slide(root_section=row)

        # Act
        positioned_slide = layout_manager.calculate_positions(slide)
        p_row = positioned_slide.root_section
        p_imp, p_prop, p_abs = p_row.children

        # Assert
        # Total width = 720. No gap.
        # Absolute takes 150. Remaining = 570.
        # Proportional takes 25% of 720 = 180.
        # Implicit takes the rest: 570 - 180 = 390.
        assert abs(p_abs.size[0] - 150.0) < 1.0, "Absolute column width is incorrect"
        assert (
            abs(p_prop.size[0] - 180.0) < 1.0
        ), "Proportional column width is incorrect"
        assert abs(p_imp.size[0] - 390.0) < 1.0, "Implicit column width is incorrect"

    def test_layout_c_13_oversubscribed_column_widths_clamped(
        self, layout_manager: LayoutManager
    ):
        """NEW TEST: Validates clamping for over-subscribed columns (container clamping failure)."""
        # Arrange
        col1 = Section(
            id="c1",
            directives={"width": "60%"},
            children=[TextElement(element_type=ElementType.TEXT, text="Left")],
        )
        col2 = Section(
            id="c2",
            directives={"width": "60%"},
            children=[TextElement(element_type=ElementType.TEXT, text="Right")],
        )
        row = Section(id="row", type="row", children=[col1, col2])
        slide = _create_unpositioned_slide(root_section=row)

        # Act
        positioned_slide = layout_manager.calculate_positions(slide)
        p_col1, p_col2 = positioned_slide.root_section.children

        # Assert
        # Total requested width is 120%. Each should be scaled down to 50% of total width (720).
        expected_width = 360.0
        assert (
            abs(p_col1.size[0] - expected_width) < 1.0
        ), "Clamped width for column 1 is incorrect"
        assert (
            abs(p_col2.size[0] - expected_width) < 1.0
        ), "Clamped width for column 2 is incorrect"

    def test_layout_c_14_meta_element_directive_precedence(
        self, layout_manager: LayoutManager
    ):
        """NEW TEST: Validates correct directive precedence for meta elements."""
        # Arrange
        title = TextElement(
            element_type=ElementType.TITLE,
            text="Title",
            directives={"color": "blue"},  # From element itself
        )
        slide = _create_unpositioned_slide(elements=[title])
        slide.base_directives = {"color": "red"}  # Slide-wide base style
        slide.title_directives = {"color": "green"}  # Highest-precedence override

        # Act
        positioned_slide = layout_manager.calculate_positions(slide)
        final_title = positioned_slide.renderable_elements[0]

        # Assert
        # Per PRINCIPLES.md, precedence is: base -> element -> override
        # The final color should be 'green'.
        assert final_title.directives.get("color") == "green"
