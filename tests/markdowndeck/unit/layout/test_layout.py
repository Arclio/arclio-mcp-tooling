"""
Unit tests for the LayoutManager, ensuring adherence to LAYOUT_SPEC.md.

Each test case directly corresponds to a specification in
`docs/markdowndeck/testing/TEST_CASES_LAYOUT.md`.
"""

import pytest
from markdowndeck.layout import LayoutManager
from markdowndeck.models import (
    ElementType,
    ImageElement,
    Section,
    Slide,
    TextElement,
)


@pytest.fixture
def layout_manager() -> LayoutManager:
    """Provides a fresh LayoutManager instance for each test."""
    return LayoutManager()


def _create_unpositioned_slide(elements=None, sections=None, object_id="test_slide"):
    """Helper to create a slide in the 'Unpositioned' state."""
    if sections is None:
        sections = []
    if elements is None:
        elements = []
    return Slide(object_id=object_id, elements=elements, sections=sections)


class TestLayoutManager:
    """Tests the functionality of the LayoutManager."""

    def test_layout_c_01(self, layout_manager: LayoutManager):
        """
        Test Case: LAYOUT-C-01
        Validates mutation from Unpositioned to Positioned state and clearing of the
        elements inventory list.
        From: docs/markdowndeck/testing/TEST_CASES_LAYOUT.md
        """
        # Arrange
        text_element = TextElement(element_type=ElementType.TEXT, text="Content")
        section = Section(id="sec1", children=[text_element])
        unpositioned_slide = _create_unpositioned_slide(
            elements=[text_element], sections=[section]
        )
        unpositioned_slide_instance_id = id(unpositioned_slide)

        # Act
        positioned_slide = layout_manager.calculate_positions(unpositioned_slide)

        # Assert
        assert (
            id(positioned_slide) == unpositioned_slide_instance_id
        ), "Should mutate the same slide instance."

        # Verify section and element have been positioned
        final_section = positioned_slide.sections[0]
        final_element = final_section.children[0]
        assert final_section.position is not None
        assert final_section.size is not None
        assert final_element.position is not None
        assert final_element.size is not None

        # Verify inventory list is cleared and renderable_elements populated with meta-elements
        assert (
            positioned_slide.elements == []
        ), "Elements inventory list must be cleared after layout."

        # Verify renderable_elements contains positioned meta-elements from LayoutManager
        # (In this test case, there are no meta-elements, so it should be empty)
        assert hasattr(
            positioned_slide, "renderable_elements"
        ), "Slide must have renderable_elements attribute"
        assert (
            positioned_slide.renderable_elements == []
        ), "No meta-elements in this test case"

    def test_layout_c_02(self, layout_manager: LayoutManager):
        """
        Test Case: LAYOUT-C-02
        Validates proactive image scaling.
        From: docs/markdowndeck/testing/TEST_CASES_LAYOUT.md
        """
        # Arrange
        image = ImageElement(element_type=ElementType.IMAGE, url="test.jpg")
        section = Section(
            id="img_sec", children=[image], directives={"width": 0.5}
        )  # 50% width
        slide = _create_unpositioned_slide(elements=[image], sections=[section])

        # Act
        positioned_slide = layout_manager.calculate_positions(slide)

        # Assert
        positioned_image = positioned_slide.sections[0].children[0]
        body_width = layout_manager.position_calculator.body_width

        assert positioned_image.size is not None, "Image must be sized."
        # Image width should be relative to its container (the section), not the whole slide
        assert positioned_image.size[0] <= (
            body_width * 0.5
        ), "Image width should fit its container section."
        assert (
            positioned_image.size[1] > 0
        ), "Image height should be calculated based on aspect ratio."

    def test_layout_c_03(self, layout_manager: LayoutManager):
        """
        Test Case: LAYOUT-C-03
        Validates interpretation of spatial directives like width and align.
        From: docs/markdowndeck/testing/TEST_CASES_LAYOUT.md
        """
        # Arrange
        text = TextElement(
            element_type=ElementType.TEXT,
            text="Centered",
            directives={"align": "center"},
        )
        section = Section(id="dir_sec", children=[text], directives={"width": 0.5})
        slide = _create_unpositioned_slide(elements=[text], sections=[section])

        # Act
        positioned_slide = layout_manager.calculate_positions(slide)

        # Assert
        positioned_section = positioned_slide.sections[0]
        positioned_element = positioned_section.children[0]

        # Check section width
        body_width = layout_manager.position_calculator.body_width
        expected_width = body_width * 0.5
        assert (
            abs(positioned_section.size[0] - expected_width) < 20
        ), "Section width should respect directive."

        # Check element alignment
        section_center = positioned_section.position[0] + positioned_section.size[0] / 2
        element_center = positioned_element.position[0] + positioned_element.size[0] / 2
        assert (
            abs(element_center - section_center) < 5
        ), "Element should be centered within its section."

    def test_layout_c_04(self, layout_manager: LayoutManager):
        """
        Test Case: LAYOUT-C-04
        Validates that user-specified section heights are respected, even with internal overflow.
        From: docs/markdowndeck/testing/TEST_CASES_LAYOUT.md
        """
        # Arrange
        # This text element's intrinsic height will be much larger than 100
        large_text = TextElement(
            element_type=ElementType.TEXT, text="Large Content " * 50
        )
        section = Section(
            id="fixed_sec", children=[large_text], directives={"height": 100}
        )
        slide = _create_unpositioned_slide(elements=[large_text], sections=[section])

        # Act
        positioned_slide = layout_manager.calculate_positions(slide)

        # Assert
        positioned_section = positioned_slide.sections[0]
        positioned_element = positioned_section.children[0]

        assert (
            abs(positioned_section.size[1] - 100) < 1
        ), "Section height must be exactly what the user specified."
        # Check that the element inside is larger than the section (internal overflow is allowed)
        assert (
            positioned_element.size[1] > positioned_section.size[1]
        ), "Internal content should be allowed to overflow."

    def test_layout_c_05(self, layout_manager: LayoutManager):
        """
        Test Case: LAYOUT-C-05
        Validates automatic creation of a root section for slides without explicit sections.
        From: docs/markdowndeck/testing/TEST_CASES_LAYOUT.md
        """
        # Arrange
        title = TextElement(element_type=ElementType.TITLE, text="Title")
        body_content = TextElement(element_type=ElementType.TEXT, text="Body Content")
        slide = _create_unpositioned_slide(
            elements=[title, body_content], sections=[]
        )  # No sections

        # Act
        positioned_slide = layout_manager.calculate_positions(slide)

        # Assert
        assert (
            len(positioned_slide.sections) == 1
        ), "A single root section should have been created."
        root_section = positioned_slide.sections[0]
        assert (
            len(root_section.children) == 1
        ), "Root section should contain the body element."
        assert root_section.children[0].text == "Body Content"
        assert root_section.position is not None, "Root section must have position."
        assert root_section.size is not None, "Root section must have size."

    def test_layout_c_06(self, layout_manager: LayoutManager):
        """
        Test Case: LAYOUT-C-06
        Validates equal space division for columns without width directives.
        From: docs/markdowndeck/testing/TEST_CASES_LAYOUT.md
        """
        # Arrange
        text1 = TextElement(element_type=ElementType.TEXT, text="Col 1")
        text2 = TextElement(element_type=ElementType.TEXT, text="Col 2")
        text3 = TextElement(element_type=ElementType.TEXT, text="Col 3")
        sections = [
            Section(id="c1", children=[text1]),
            Section(id="c2", children=[text2]),
            Section(id="c3", children=[text3]),
        ]
        slide = _create_unpositioned_slide(
            elements=[text1, text2, text3], sections=sections
        )

        # Act
        positioned_slide = layout_manager.calculate_positions(slide)

        # Assert
        positioned_sections = positioned_slide.sections
        body_width = layout_manager.position_calculator.body_width
        spacing_width = layout_manager.position_calculator.HORIZONTAL_SPACING * (
            len(sections) - 1
        )
        expected_width = (body_width - spacing_width) / 3

        for sec in positioned_sections:
            assert (
                abs(sec.size[0] - expected_width) < 1
            ), f"Section {sec.id} should have ~1/3 width."

    def test_layout_c_07(self, layout_manager: LayoutManager):
        """
        Test Case: LAYOUT-C-07
        Validates precise proportional space division with explicit directives.
        From: docs/markdowndeck/testing/TEST_CASES_LAYOUT.md
        """
        # Arrange
        text1 = TextElement(element_type=ElementType.TEXT, text="20%")
        text2 = TextElement(element_type=ElementType.TEXT, text="50%")
        text3 = TextElement(element_type=ElementType.TEXT, text="30%")
        sections = [
            Section(id="c1", children=[text1], directives={"width": 0.2}),
            Section(id="c2", children=[text2], directives={"width": 0.5}),
            Section(id="c3", children=[text3], directives={"width": 0.3}),
        ]
        slide = _create_unpositioned_slide(
            elements=[text1, text2, text3], sections=sections
        )

        # Act
        positioned_slide = layout_manager.calculate_positions(slide)

        # Assert
        positioned_sections = positioned_slide.sections
        body_width = layout_manager.position_calculator.body_width
        spacing_width = layout_manager.position_calculator.HORIZONTAL_SPACING * (
            len(sections) - 1
        )
        usable_width = body_width - spacing_width

        assert abs(positioned_sections[0].size[0] - (usable_width * 0.2)) < 1
        assert abs(positioned_sections[1].size[0] - (usable_width * 0.5)) < 1
        assert abs(positioned_sections[2].size[0] - (usable_width * 0.3)) < 1
