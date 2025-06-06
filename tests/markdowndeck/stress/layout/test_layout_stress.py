"""Stress tests for the unified layout calculator."""

import time

import pytest
from markdowndeck.layout import LayoutManager
from markdowndeck.models import (
    ElementType,
    ListElement,
    ListItem,
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

    def test_layout_with_massive_element_count(self, layout_manager: LayoutManager):
        """Tests layout calculation with a very large number of elements on a single slide."""
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
        print(f"Layout with {num_elements} elements took {processing_time:.4f} seconds.")

        assert processing_time < 5.0, "Layout for many elements should be performant."
        assert len(result_slide.sections) == 1, "Should create a single root section."
        assert len(result_slide.sections[0].elements) == num_elements, "All elements should be in the root section."
        for el in result_slide.sections[0].elements:
            assert el.position is not None
            assert el.size is not None

    def test_layout_with_deeply_nested_sections(self, layout_manager: LayoutManager):
        """Tests layout calculation with deeply nested section structures."""
        depth = 25
        content_element = TextElement(element_type=ElementType.TEXT, text="Deep Content", object_id="deep_content")

        # Build a deeply nested structure
        deepest_section = Section(id=f"sec_{depth}", elements=[content_element])
        current_section = deepest_section
        for i in range(depth - 1, 0, -1):
            parent_section = Section(id=f"sec_{i}", type="section", subsections=[current_section])
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
        print(f"Layout with {depth} nested sections took {processing_time:.4f} seconds.")

        assert processing_time < 2.0, "Deeply nested layout should be performant."

        # Verify the structure is still there and positioned
        final_section = result_slide.sections[0]
        for _ in range(depth - 1):
            assert len(final_section.subsections) == 1
            final_section = final_section.subsections[0]
            assert final_section.position is not None
            assert final_section.size is not None

        assert len(final_section.elements) == 1
        assert final_section.elements[0].object_id == "deep_content"

    def test_layout_with_huge_element_content(self, layout_manager: LayoutManager):
        """Tests layout calculation for elements with massive content strings."""
        # 1 million characters
        huge_text_content = "This is a very long word. " * 100_000
        huge_text_element = TextElement(
            element_type=ElementType.TEXT,
            text=huge_text_content,
            object_id="huge_text",
        )

        huge_list_items = [ListItem(text="Long list item " * 20) for _ in range(200)]
        huge_list_element = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=huge_list_items,
            object_id="huge_list",
        )

        slide = Slide(
            object_id="huge_content_slide",
            elements=[huge_text_element, huge_list_element],
        )

        start_time = time.time()
        result_slide = layout_manager.calculate_positions(slide)
        end_time = time.time()

        processing_time = end_time - start_time
        print(f"Layout with huge content took {processing_time:.4f} seconds.")

        assert processing_time < 5.0, "Layout for huge content should be performant."

        positioned_text = next(el for el in result_slide.sections[0].elements if el.object_id == "huge_text")
        positioned_list = next(el for el in result_slide.sections[0].elements if el.object_id == "huge_list")

        # The height should be very large, indicating the content was fully measured
        assert positioned_text.size[1] > 5000, "Height of huge text should be very large."
        assert positioned_list.size[1] > 2000, "Height of huge list should be very large."
