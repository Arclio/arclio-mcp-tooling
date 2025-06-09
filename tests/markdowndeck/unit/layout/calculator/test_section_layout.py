from markdowndeck.layout.calculator.base import PositionCalculator
from markdowndeck.layout.calculator.section_layout import (
    _position_elements_within_section,
)
from markdowndeck.models import ElementType, TextElement
from markdowndeck.models.slide import Section


class TestSectionLayoutHeightBug:
    def test_section_layout_v_01_height_allocation_consistency(self):
        """
        Test Case: SECTION-LAYOUT-V-01
        Exposes the bug where section calculates correct total height but then
        allocates wrong content area for element positioning.

        This reproduces the exact issue from TASK_007:
        - Section calculates total height (e.g., 102.8pt)
        - But content area allocation uses this as available space instead of needed space
        """
        # Arrange: Create a section with a long text element that needs significant height
        long_text = "This is the first section with a very long paragraph that contains multiple sentences and should require significant vertical space when rendered. This content block should demonstrate the height calculation issue where the section calculates one height but allocates a different content area."

        text_element = TextElement(
            element_type=ElementType.TEXT, text=long_text, object_id="text_element_test"
        )

        section = Section(
            id="test_section",
            type="section",
            children=[text_element],
            directives={},
            position=(70.0, 170.0),  # From TASK_007 evidence
            size=(580.0, 102.8),  # Section calculated total height: 102.8pt
        )

        # Create calculator
        calculator = PositionCalculator()

        # Act: Position elements within the section
        _position_elements_within_section(calculator, section)

        # Assert: The positioned element should fit within the section's calculated height
        positioned_element = section.children[0]

        # The element should have been positioned
        assert (
            positioned_element.position is not None
        ), "Element should have been positioned"
        assert positioned_element.size is not None, "Element should have been sized"

        element_width, element_height = positioned_element.size
        element_x, element_y = positioned_element.position

        # Calculate where the element ends
        element_bottom = element_y + element_height
        section_bottom = section.position[1] + section.size[1]

        # CRITICAL: The element should fit within the section's calculated height
        # This test will FAIL if the bug exists, proving the height allocation inconsistency
        assert element_bottom <= section_bottom + 1.0, (
            f"Element extends beyond section boundary! "
            f"Element bottom: {element_bottom:.1f}, Section bottom: {section_bottom:.1f}. "
            f"This proves the height allocation bug where section calculates {section.size[1]:.1f}pt "
            f"but allocates insufficient content area for element positioning."
        )
