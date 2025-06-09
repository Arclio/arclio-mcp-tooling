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

    def test_layout_c_08_vertical_split_with_row(self, layout_manager: LayoutManager):
        """
        Test Case: LAYOUT-C-08
        Validates that top-level sections split by '---' are always laid out vertically,
        even when one of them contains row sections.
        This test reproduces the layout orientation bug and should fail initially.
        """
        # Arrange - simulate parsing result of "Top Section\n---\nLeft\n***\nRight"
        top_text = TextElement(element_type=ElementType.TEXT, text="Top Section")
        left_text = TextElement(element_type=ElementType.TEXT, text="Left")
        right_text = TextElement(element_type=ElementType.TEXT, text="Right")

        # First top-level section
        top_section = Section(id="top", children=[top_text])

        # Second top-level section contains row (Left***Right)
        row_section = Section(id="row", children=[left_text, right_text], type="row")

        elements = [top_text, left_text, right_text]
        sections = [top_section, row_section]  # Two top-level sections
        slide = _create_unpositioned_slide(elements=elements, sections=sections)

        # Act
        positioned_slide = layout_manager.calculate_positions(slide)

        # Assert - top-level sections should be laid out vertically
        positioned_sections = positioned_slide.sections
        assert len(positioned_sections) == 2, "Should have two top-level sections"

        top_positioned = positioned_sections[0]
        row_positioned = positioned_sections[1]

        # The row section should be positioned BELOW the top section (vertical layout)
        assert (
            row_positioned.position[1] > top_positioned.position[1]
        ), f"Row section Y ({row_positioned.position[1]}) should be greater than top section Y ({top_positioned.position[1]}) for vertical layout"

        # The X coordinates should be approximately the same (both start at left margin)
        assert (
            abs(row_positioned.position[0] - top_positioned.position[0]) < 5
        ), f"X coordinates should be similar: top={top_positioned.position[0]}, row={row_positioned.position[0]}"

    def test_layout_p_02_proportional_columns(self, layout_manager: LayoutManager):
        """
        Test Case: LAYOUT-P-02 (Integration)
        Validates correct proportional width and intrinsic height calculation for a row section.
        This test addresses the critical bugs identified in Task 7:
        - Issue #1: Incorrect proportional width calculation
        - Issue #2: Flawed intrinsic height calculation for row sections

        Uses the actual problematic slide structure from the notebook.
        """
        # Arrange: Parse the real problematic slide from the notebook
        from markdowndeck.parser import Parser

        problematic_markdown = """# Executive Summary
[width=60%][padding=20][background=BACKGROUND2][border=2pt solid ACCENT1]
## Key Takeaways
[fontsize=18][line-spacing=1.5][color=ACCENT1]
- **Universal Standard**: MCP eliminates M×N integration complexity
- **Open Protocol**: Created by Anthropic, adopted industry-wide
***
[width=40%][background=ACCENT2][color=TEXT1][padding=15][valign=middle]
## Impact Metrics
[align=center][fontsize=20]
**85%** reduction in integration time
**3x** faster development cycles
"""

        parser = Parser()
        deck = parser.parse(problematic_markdown)
        slide = deck.slides[0]

        # Act
        positioned_slide = layout_manager.calculate_positions(slide)

        # Assert
        # Find the row section (should be the first top-level section)
        row_section = None
        for section in positioned_slide.sections:
            if section.type == "row" and len(section.children) >= 2:
                row_section = section
                break

        assert row_section is not None, "Should have a row section with 2 children"

        final_left = row_section.children[0]
        final_right = row_section.children[1]

        # Get expected dimensions
        body_width = layout_manager.position_calculator.body_width
        spacing = layout_manager.position_calculator.HORIZONTAL_SPACING
        usable_width = body_width - spacing

        expected_left_width = usable_width * 0.6
        expected_right_width = usable_width * 0.4

        # Assert widths are correct
        assert (
            abs(final_left.size[0] - expected_left_width) < 1
        ), f"Left column width is incorrect. Expected {expected_left_width}, got {final_left.size[0]}. Row size: {row_section.size}"
        assert (
            abs(final_right.size[0] - expected_right_width) < 1
        ), f"Right column width is incorrect. Expected {expected_right_width}, got {final_right.size[0]}. Row size: {row_section.size}"

        # Assert parent row height is based on tallest child
        assert (
            row_section.size[1] >= final_left.size[1]
        ), f"Row height ({row_section.size[1]}) must be at least the height of the tallest child ({final_left.size[1]})"
        assert (
            row_section.size[1] > 40
        ), f"Row height ({row_section.size[1]}) must be calculated from content, not a default value of 40"

    def test_layout_p_03_mixed_width_columns_and_intrinsic_height(
        self, layout_manager: LayoutManager
    ):
        """
        Test Case: LAYOUT-P-03 (Integration)
        Validates correct proportional and absolute width calculation, and intrinsic height for a row.
        This test directly reproduces the critical bugs from TASK_007.md.
        Spec: LAYOUT_SPEC.md, Rules #2 and #4
        """
        # Arrange: Use the problematic markdown from the Golden Test Case (Slide 3)
        from markdowndeck.parser import Parser

        problematic_markdown = """# Mixed Width Columns
This text is in the first column. It will take up the remaining space after the explicitly sized columns are accounted for.
***
[width=0.25]
This text is in the second column. It is explicitly sized to take up 25% of the available width.
***
[width=150]
This text is in the third column. It is sized to be exactly 150 points wide.
"""
        parser = Parser()
        deck = parser.parse(problematic_markdown)
        slide = deck.slides[0]

        # Act
        positioned_slide = layout_manager.calculate_positions(slide)

        # Assert
        # Find the row section (should be the first top-level section)
        row_section = next(
            (s for s in positioned_slide.sections if s.type == "row"), None
        )
        assert row_section is not None, "A 'row' type section should have been created."
        assert (
            len(row_section.children) == 3
        ), "The row section should contain three child sections (columns)."

        col1, col2, col3 = row_section.children

        # --- Assertions for Issue #1: Corrected Width Calculation ---
        body_width = layout_manager.position_calculator.body_width
        spacing = (
            layout_manager.position_calculator.HORIZONTAL_SPACING * 2
        )  # 2 gaps for 3 columns
        body_width - spacing  # Should be 620 - 20 = 600

        # Expected widths based on the CORRECTED algorithm:
        # Usable: 600. Absolute: 150.
        # Proportional (25% of total usable 600): 150.
        # Implicit (remaining): 600 - 150 - 150 = 300.
        expected_col1_width = 300.0
        expected_col2_width = 150.0
        expected_col3_width = 150.0

        assert (
            abs(col1.size[0] - expected_col1_width) < 1
        ), f"Implicit column width is incorrect. Expected ~{expected_col1_width}, got {col1.size[0]}."
        assert (
            abs(col2.size[0] - expected_col2_width) < 1
        ), f"Proportional column width is incorrect. Expected ~{expected_col2_width}, got {col2.size[0]}."
        assert (
            abs(col3.size[0] - expected_col3_width) < 1
        ), f"Absolute column width is incorrect. Expected {expected_col3_width}, got {col3.size[0]}."

        # --- Assertions for Issue #2: Flawed Intrinsic Height ---
        # The parent row's height must be at least the height of its tallest child.
        max_child_height = max(c.size[1] for c in row_section.children)
        assert (
            row_section.size[1] >= max_child_height
        ), f"Row height ({row_section.size[1]}) must be >= tallest child ({max_child_height})."
        assert (
            row_section.size[1] > 40.0
        ), f"Row height ({row_section.size[1]}) must be calculated from content, not a default of 40."
