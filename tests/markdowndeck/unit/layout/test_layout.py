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
    # If no root_section is provided but elements exist, create a default one.
    if root_section is None and elements:
        body_elements = [
            e
            for e in elements
            if e.element_type not in (ElementType.TITLE, ElementType.FOOTER)
        ]
        root_section = Section(id="root", children=body_elements)

    return Slide(object_id=object_id, elements=elements, root_section=root_section)


class TestLayoutManager:
    def test_layout_c_07_proportional_width_division(
        self, layout_manager: LayoutManager
    ):
        """Test Case: LAYOUT-C-07"""
        sections = [
            Section(
                id="sec1",
                directives={"width": 0.2},
                children=[TextElement(element_type=ElementType.TEXT, text="Col 1")],
            ),
            Section(
                id="sec2",
                directives={"width": 0.5},
                children=[TextElement(element_type=ElementType.TEXT, text="Col 2")],
            ),
            Section(
                id="sec3",
                directives={"width": 0.3},
                children=[TextElement(element_type=ElementType.TEXT, text="Col 3")],
            ),
        ]
        row_section = Section(id="root_row", type="row", children=sections)
        elements = [child.children[0] for child in sections]
        slide = _create_unpositioned_slide(elements=elements, root_section=row_section)

        positioned_slide = layout_manager.calculate_positions(slide)

        positioned_sections = positioned_slide.root_section.children
        content_width = layout_manager.max_content_width

        assert len(positioned_sections) == 3
        assert abs(positioned_sections[0].size[0] - content_width * 0.2) < 1.0
        assert abs(positioned_sections[1].size[0] - content_width * 0.5) < 1.0
        assert abs(positioned_sections[2].size[0] - content_width * 0.3) < 1.0

    def test_layout_c_04_fixed_height_directive_is_respected(
        self, layout_manager: LayoutManager
    ):
        """Test Case: LAYOUT-C-04"""
        tall_element = TextElement(element_type=ElementType.TEXT, text="Line 1\n" * 6)
        section = Section(
            id="fixed_height_sec", directives={"height": 100}, children=[tall_element]
        )
        slide = _create_unpositioned_slide(
            elements=[tall_element], root_section=section
        )

        positioned_slide = layout_manager.calculate_positions(slide)
        positioned_section = positioned_slide.root_section

        assert positioned_section.size is not None
        assert positioned_section.size[1] == 100.0

    def test_layout_c_02_proactive_image_scaling(self, layout_manager: LayoutManager):
        """Test Case: LAYOUT-C-02"""
        image = ImageElement(
            element_type=ElementType.IMAGE, url="test.png", aspect_ratio=1.6
        )
        section = Section(id="img_sec", children=[image])
        slide = _create_unpositioned_slide(elements=[image], root_section=section)

        positioned_slide = layout_manager.calculate_positions(slide)
        positioned_image = positioned_slide.root_section.children[0]

        assert positioned_image.size is not None
        expected_width = layout_manager.max_content_width
        expected_height = expected_width / 1.6

        assert abs(positioned_image.size[0] - expected_width) < 1.0
        assert abs(positioned_image.size[1] - expected_height) < 1.0

    def test_layout_c_09_gap_directive(self, layout_manager: LayoutManager):
        """Test Case: LAYOUT-C-06"""
        elements = [
            TextElement(element_type=ElementType.TEXT, text="El 1"),
            TextElement(element_type=ElementType.TEXT, text="El 2"),
        ]
        section = Section(id="root", children=elements, directives={"gap": 20})
        slide = _create_unpositioned_slide(elements=elements, root_section=section)

        positioned_slide = layout_manager.calculate_positions(slide)
        el1, el2 = positioned_slide.root_section.children

        expected_gap = 20.0
        actual_gap = el2.position[1] - (el1.position[1] + el1.size[1])
        assert abs(actual_gap - expected_gap) < 1.0
