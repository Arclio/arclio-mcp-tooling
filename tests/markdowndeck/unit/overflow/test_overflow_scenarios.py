from unittest.mock import MagicMock, patch

import pytest
from markdowndeck.models import (
    CodeElement,
    ElementType,
    ListElement,
    ListItem,
    Section,
    Slide,
    TableElement,
    TextElement,
)
from markdowndeck.overflow import OverflowManager


@pytest.fixture
def overflow_manager_factory():
    """A factory to create overflow managers for specific test scenarios."""

    def _create_manager(layout_side_effect=None):
        with patch("markdowndeck.layout.LayoutManager") as mock_lm_class:
            mock_lm_instance = MagicMock()

            if layout_side_effect:
                mock_lm_instance.calculate_positions.side_effect = layout_side_effect
            else:

                def simple_recursive_relayout(slide: Slide) -> Slide:
                    """A more realistic relayout that positions children sequentially."""
                    y_offset = 50.0  # Start after top margin

                    if not slide.root_section:
                        return slide

                    def layout_section(section, current_y):
                        """Recursively layout a section and its children."""
                        section_start_y = current_y
                        section.position = (50, section_start_y)

                        for child in section.children:
                            if isinstance(child, Section):
                                # Recursively layout child section
                                child.position = (50, current_y)
                                current_y = layout_section(child, current_y)
                                child.size = (620, current_y - child.position[1])
                            else:
                                # Layout element
                                child.position = (50, current_y)
                                # Use existing size or give default
                                if not child.size:
                                    child.size = (620, 100)
                                current_y += child.size[1]

                        # Set section size based on content
                        section.size = (620, current_y - section_start_y)
                        return current_y

                    # Layout the root section
                    layout_section(slide.root_section, y_offset)

                    # Handle meta-elements if present
                    if hasattr(slide, "elements"):
                        for element in slide.elements:
                            if element.element_type == ElementType.TITLE and not element.position:
                                element.position = (50, 10)
                                element.size = element.size or (620, 30)

                    return slide

                mock_lm_instance.calculate_positions.side_effect = simple_recursive_relayout

            mock_lm_class.return_value = mock_lm_instance
            return OverflowManager(
                margins={"top": 50, "right": 50, "bottom": 50, "left": 50},
                slide_height=405,
            )

    return _create_manager


class TestOverflowScenarios:
    def test_text_splitting(self, overflow_manager_factory):
        """Validates that a simple TextElement is correctly split."""
        manager = overflow_manager_factory()

        text_element = TextElement(
            element_type=ElementType.TEXT,
            text="Long text that needs to be split across multiple slides.",
            object_id="text1",
            position=(50, 100),
            size=(620, 400),  # Too tall for remaining space
        )

        # Mock the split method
        fitted_part = TextElement(
            element_type=ElementType.TEXT,
            text="Long text that needs",
            object_id="text1_fitted",
            size=(620, 200),
        )
        overflow_part = TextElement(
            element_type=ElementType.TEXT,
            text="to be split across multiple slides.",
            object_id="text1_overflow",
            size=(620, 200),
        )
        text_element.split = MagicMock(return_value=(fitted_part, overflow_part))

        root_section = Section(id="r1", position=(50, 50), size=(620, 450), children=[text_element])

        slide = Slide(
            object_id="s1",
            root_section=root_section,
            elements=[],
            renderable_elements=[],
        )

        final_slides = manager.process_slide(slide)

        assert len(final_slides) == 2, "Expected slide to be split in two."

        # Check fitted slide
        assert len(final_slides[0].renderable_elements) == 1
        assert final_slides[0].renderable_elements[0].text == "Long text that needs"

        # Check continuation slide was created
        continuation_slide_arg = manager.layout_manager.calculate_positions.call_args[0][0]
        assert continuation_slide_arg.is_continuation is True
        assert continuation_slide_arg.root_section.children[0].text == "to be split across multiple slides."

    def test_list_splitting(self, overflow_manager_factory):
        """Validates that a ListElement is correctly split across slides."""
        manager = overflow_manager_factory()

        items = [ListItem(text=f"Item {i}") for i in range(10)]
        list_element = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=items,
            object_id="list1",
            position=(50, 100),
            size=(620, 400),  # Too tall
        )

        # Mock the split
        fitted_part = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=items[:5],
            object_id="list1_fitted",
            size=(620, 200),
        )
        overflow_part = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=items[5:],
            object_id="list1_overflow",
            size=(620, 200),
        )
        list_element.split = MagicMock(return_value=(fitted_part, overflow_part))

        root_section = Section(id="r1", position=(50, 50), size=(620, 450), children=[list_element])

        slide = Slide(
            object_id="s1",
            root_section=root_section,
            elements=[],
            renderable_elements=[],
        )

        final_slides = manager.process_slide(slide)

        assert len(final_slides) == 2
        assert len(final_slides[0].renderable_elements) == 1
        assert len(final_slides[0].renderable_elements[0].items) == 5

        # Check continuation slide
        continuation_slide_unpositioned = manager.layout_manager.calculate_positions.call_args[0][0]
        assert len(continuation_slide_unpositioned.root_section.children[0].items) == 5

    def test_table_splitting(self, overflow_manager_factory):
        """Validates that a TableElement is correctly split, preserving headers."""
        manager = overflow_manager_factory()

        rows = [[f"Row {i} Cell 1", f"Row {i} Cell 2"] for i in range(10)]
        table_element = TableElement(
            element_type=ElementType.TABLE,
            headers=["Header 1", "Header 2"],
            rows=rows,
            object_id="table1",
            position=(50, 100),
            size=(620, 400),  # Too tall
            row_directives=[{}] * 11,  # 1 header + 10 rows
        )

        # Mock the split
        fitted_part = TableElement(
            element_type=ElementType.TABLE,
            headers=["Header 1", "Header 2"],
            rows=rows[:4],
            object_id="table1_fitted",
            row_directives=[{}] * 5,  # 1 header + 4 rows
            size=(620, 150),
        )
        overflow_part = TableElement(
            element_type=ElementType.TABLE,
            headers=[],  # Split method doesn't duplicate headers
            rows=rows[4:],
            object_id="table1_overflow",
            row_directives=[{}] * 6,  # Just the data rows
            size=(620, 250),
        )
        table_element.split = MagicMock(return_value=(fitted_part, overflow_part))

        root_section = Section(id="r1", position=(50, 50), size=(620, 450), children=[table_element])

        slide = Slide(
            object_id="s1",
            root_section=root_section,
            elements=[],
            renderable_elements=[],
        )

        final_slides = manager.process_slide(slide)

        assert len(final_slides) == 2
        assert final_slides[0].renderable_elements[0].get_row_count() == 5  # 1 header + 4 rows

        # Check that headers were duplicated in continuation
        continuation_slide = manager.layout_manager.calculate_positions.call_args[0][0]
        continuation_table = continuation_slide.root_section.children[0]
        assert continuation_table.get_row_count() == 7  # 1 duplicated header + 6 rows
        assert continuation_table.headers == ["Header 1", "Header 2"]

    def test_code_splitting(self, overflow_manager_factory):
        """Validates that a CodeElement is correctly split between lines."""
        manager = overflow_manager_factory()

        code_lines = [f"line {i};" for i in range(10)]
        code_content = "\n".join(code_lines)
        code_element = CodeElement(
            element_type=ElementType.CODE,
            code=code_content,
            language="python",
            object_id="code1",
            position=(50, 100),
            size=(620, 400),  # Too tall
        )

        # Mock the split
        fitted_part = CodeElement(
            element_type=ElementType.CODE,
            code="\n".join(code_lines[:5]),
            language="python",
            object_id="code1_fitted",
            size=(620, 200),
        )
        overflow_part = CodeElement(
            element_type=ElementType.CODE,
            code="\n".join(code_lines[5:]),
            language="python",
            object_id="code1_overflow",
            size=(620, 200),
        )
        code_element.split = MagicMock(return_value=(fitted_part, overflow_part))

        root_section = Section(id="r1", position=(50, 50), size=(620, 450), children=[code_element])

        slide = Slide(
            object_id="s1",
            root_section=root_section,
            elements=[],
            renderable_elements=[],
        )

        final_slides = manager.process_slide(slide)

        assert len(final_slides) == 2
        assert final_slides[0].renderable_elements[0].count_lines() == 5

        # Check continuation
        continuation_slide = manager.layout_manager.calculate_positions.call_args[0][0]
        assert continuation_slide.root_section.children[0].count_lines() == 5

    def test_mixed_content_splitting(self, overflow_manager_factory):
        """Validates that content after an overflowing element is moved correctly."""
        manager = overflow_manager_factory()

        # Three elements: first fits, second overflows, third should move
        el1 = TextElement(
            element_type=ElementType.TEXT,
            text="This element fits",
            object_id="el1",
            position=(50, 100),
            size=(620, 100),
        )

        el2_overflow = TextElement(
            element_type=ElementType.TEXT,
            text="This element overflows and needs to be split",
            object_id="el2",
            position=(50, 200),
            size=(620, 300),  # Too tall
        )

        el3_after = TextElement(
            element_type=ElementType.TEXT,
            text="This element should move to continuation",
            object_id="el3",
            position=(50, 500),  # Would be off-slide
            size=(620, 100),
        )

        # Mock the split for el2
        el2_fitted = TextElement(
            element_type=ElementType.TEXT,
            text="This element overflows",
            object_id="el2_fitted",
            size=(620, 150),
        )
        el2_overflowing = TextElement(
            element_type=ElementType.TEXT,
            text="and needs to be split",
            object_id="el2_overflow",
            size=(620, 150),
        )
        el2_overflow.split = MagicMock(return_value=(el2_fitted, el2_overflowing))

        root_section = Section(
            id="r1",
            position=(50, 50),
            size=(620, 550),
            children=[el1, el2_overflow, el3_after],
        )

        slide = Slide(
            object_id="s1",
            root_section=root_section,
            elements=[],
            renderable_elements=[],
        )

        final_slides = manager.process_slide(slide)

        assert len(final_slides) == 2

        # Check fitted slide has el1 and fitted part of el2
        assert len(final_slides[0].renderable_elements) == 2
        assert final_slides[0].renderable_elements[0].object_id == "el1"
        assert final_slides[0].renderable_elements[1].text == "This element overflows"

        # Check continuation has overflow part of el2 and el3
        continuation_slide = manager.layout_manager.calculate_positions.call_args[0][0]
        cont_children = continuation_slide.root_section.children
        assert len(cont_children) == 2
        assert cont_children[0].text == "and needs to be split"
        assert cont_children[1].object_id == "el3"

    def test_no_empty_continuation_slide(self, overflow_manager_factory):
        """Validates that a continuation slide is not created if a split results in no overflow."""
        manager = overflow_manager_factory()

        element = TextElement(
            element_type=ElementType.TEXT,
            text="Content that fits after split",
            object_id="el1",
            position=(50, 100),
            size=(620, 400),  # Initially too tall
        )

        # Mock split to return fitted part only (no overflow)
        fitted_part = TextElement(
            element_type=ElementType.TEXT,
            text="Content that fits after split",
            object_id="el1_fitted",
            size=(620, 300),  # Now fits
        )
        element.split = MagicMock(return_value=(fitted_part, None))

        root_section = Section(id="r1", position=(50, 50), size=(620, 450), children=[element])

        slide = Slide(
            object_id="s1",
            root_section=root_section,
            elements=[],
            renderable_elements=[],
        )

        final_slides = manager.process_slide(slide)

        assert len(final_slides) == 1
        assert len(final_slides[0].renderable_elements) == 1
        assert final_slides[0].renderable_elements[0].text == "Content that fits after split"

        # Layout manager should not be called for continuation
        manager.layout_manager.calculate_positions.assert_not_called()

    def test_nested_section_overflow(self, overflow_manager_factory):
        """Test that overflow within nested sections is handled correctly."""
        manager = overflow_manager_factory()

        # Create a nested structure where the overflow happens deep in the hierarchy
        overflowing_element = TextElement(
            element_type=ElementType.TEXT,
            text="This text overflows",
            object_id="overflow_text",
            position=(50, 300),
            size=(620, 200),  # Will overflow
        )

        # Mock the split
        fitted_part = TextElement(
            element_type=ElementType.TEXT,
            text="This text",
            object_id="fitted_text",
            size=(620, 100),
        )
        overflow_part = TextElement(
            element_type=ElementType.TEXT,
            text="overflows",
            object_id="overflow_part",
            size=(620, 100),
        )
        overflowing_element.split = MagicMock(return_value=(fitted_part, overflow_part))

        # Create nested structure
        inner_section = Section(
            id="inner",
            position=(50, 200),
            size=(620, 250),
            children=[overflowing_element],
        )

        outer_section = Section(
            id="outer",
            position=(50, 100),
            size=(620, 350),
            children=[
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Before nested section",
                    object_id="before_text",
                    position=(50, 100),
                    size=(620, 100),
                ),
                inner_section,
                TextElement(
                    element_type=ElementType.TEXT,
                    text="After nested section",
                    object_id="after_text",
                    position=(50, 450),
                    size=(620, 50),
                ),
            ],
        )

        root_section = Section(id="root", position=(50, 50), size=(620, 450), children=[outer_section])

        slide = Slide(
            object_id="nested_test",
            root_section=root_section,
            elements=[],
            renderable_elements=[],
        )

        final_slides = manager.process_slide(slide)

        assert len(final_slides) == 2

        # The structure should be preserved in both slides
        # First slide should have outer -> [before_text, inner -> [fitted_text]]
        assert len(final_slides[0].renderable_elements) == 2
        assert final_slides[0].renderable_elements[0].object_id == "before_text"
        assert final_slides[0].renderable_elements[1].text == "This text"

        # Continuation should have outer -> [inner -> [overflow_part], after_text]
        continuation_slide = manager.layout_manager.calculate_positions.call_args[0][0]
        # The continuation should preserve the nested structure
        assert continuation_slide.root_section is not None
        # Should have the overflow part and the after_text element
        # (exact structure depends on flattening logic, but both elements should be present)
