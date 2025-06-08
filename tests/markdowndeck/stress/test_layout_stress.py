"""Stress tests for the unified layout calculator."""

import time

import pytest
from markdowndeck.layout import LayoutManager
from markdowndeck.models import (
    ElementType,
    Section,
    Slide,
    TextElement,
)


class TestLayoutCalculatorStress:
    """Stress tests for the LayoutManager and its components."""

    @pytest.fixture(scope="class")
    def layout_manager(self) -> LayoutManager:
        """Provides a class-scoped LayoutManager instance."""
        return LayoutManager()

    def test_stress_l_01(self, layout_manager: LayoutManager):
        """
        Test Case: STRESS-L-01
        Tests layout calculation with a very large number of elements.
        From: docs/markdowndeck/testing/TEST_CASES_STRESS.md
        """
        num_elements = 500
        elements = [
            TextElement(
                element_type=ElementType.TEXT,
                text=f"Element {i}",
                object_id=f"el_{i}",
            )
            for i in range(num_elements)
        ]
        slide = Slide(object_id="massive_elements_slide", elements=elements)

        start_time = time.time()
        result_slide = layout_manager.calculate_positions(slide)
        end_time = time.time()

        processing_time = end_time - start_time
        print(
            f"Layout with {num_elements} elements took {processing_time:.4f} seconds."
        )

        assert processing_time < 5.0, "Layout for many elements should be performant."
        assert len(result_slide.sections) == 1, "Should create a single root section."

        # After layout, all elements are in sections.children
        root_section_elements = [
            child
            for child in result_slide.sections[0].children
            if not hasattr(child, "children")
        ]
        assert (
            len(root_section_elements) == num_elements
        ), "All elements should be in the root section."
        for el in root_section_elements:
            assert el.position is not None
            assert el.size is not None

    def test_stress_l_02(self, layout_manager: LayoutManager):
        """
        Test Case: STRESS-L-02
        Tests layout calculation with deeply nested section structures.
        From: docs/markdowndeck/testing/TEST_CASES_STRESS.md
        """
        depth = 25
        content_element = TextElement(
            element_type=ElementType.TEXT, text="Deep Content", object_id="deep_content"
        )

        # Build a deeply nested structure
        deepest_section = Section(id=f"sec_{depth}", children=[content_element])
        current_section = deepest_section
        for i in range(depth - 1, 0, -1):
            parent_section = Section(
                id=f"sec_{i}", type="section", children=[current_section]
            )
            current_section = parent_section

        slide = Slide(
            object_id="deep_nest_slide",
            elements=[content_element],
            sections=[current_section],
        )

        start_time = time.time()
        # This should complete without a RecursionError
        result_slide = layout_manager.calculate_positions(slide)
        end_time = time.time()

        processing_time = end_time - start_time
        print(
            f"Layout with {depth} nested sections took {processing_time:.4f} seconds."
        )

        assert processing_time < 2.0, "Deeply nested layout should be performant."

        # Verify the structure is still there and positioned
        final_section = result_slide.sections[0]
        for _ in range(depth - 1):
            child_sections = [
                child for child in final_section.children if hasattr(child, "children")
            ]
            assert len(child_sections) == 1
            final_section = child_sections[0]
            assert final_section.position is not None
            assert final_section.size is not None

        final_elements = [
            child for child in final_section.children if not hasattr(child, "children")
        ]
        assert len(final_elements) == 1
        assert final_elements[0].object_id == "deep_content"
