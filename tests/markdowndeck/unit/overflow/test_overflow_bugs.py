from unittest.mock import MagicMock, patch

import pytest
from markdowndeck.models import (
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
def overflow_manager() -> OverflowManager:
    """Provides an OverflowManager with a mocked LayoutManager that does simple re-layout."""
    with patch("markdowndeck.layout.LayoutManager") as mock_lm_class:
        mock_lm_instance = MagicMock()

        def relayout(slide):
            y_offset = 50.0
            if slide.root_section:
                for child in slide.root_section.children:
                    child.position = (50, y_offset)
                    y_offset += child.size[1] if child.size else 100
            return slide

        mock_lm_instance.calculate_positions.side_effect = relayout
        mock_lm_class.return_value = mock_lm_instance
        yield OverflowManager(
            margins={"top": 50, "right": 50, "bottom": 50, "left": 50},
            slide_height=405,
        )


class TestOverflowBugReproduction:
    """Tests designed to fail, exposing known bugs in overflow handling."""

    def test_bug_long_text_split_but_not_moved_to_new_slide(
        self, overflow_manager: OverflowManager
    ):
        """
        Test Case: OVERFLOW-BUG-01
        Description: Exposes the bug where a long text element is split, but the overflowing
                     part is rendered on the same slide instead of a new one.
        Expected to Fail: Yes. The assertion `len(final_slides) == 2` will fail.
        """
        # Arrange: A text element that is too tall for the slide
        text_element = TextElement(
            element_type=ElementType.TEXT,
            text="This is very long text" * 50,
            object_id="long_text_1",
            position=(50, 50),
            size=(620, 800),  # Taller than slide height 405
        )

        # Mock the split method to ensure it returns two distinct parts
        # FIXED: Added element_type to constructors.
        fitted_part = TextElement(
            element_type=ElementType.TEXT, text="Fitted part", size=(620, 300)
        )
        overflow_part = TextElement(
            element_type=ElementType.TEXT, text="Overflowing part", size=(620, 500)
        )
        text_element.split = MagicMock(return_value=(fitted_part, overflow_part))

        root_section = Section(
            id="r1", position=(50, 50), size=(620, 800), children=[text_element]
        )
        slide = Slide(object_id="s1", root_section=root_section)

        # Act
        final_slides = overflow_manager.process_slide(slide)

        # Assert
        assert (
            len(final_slides) > 1
        ), "The overflowing text should have been moved to a new, second slide."

    def test_bug_list_overflows_and_is_not_split(
        self, overflow_manager: OverflowManager
    ):
        """
        Test Case: OVERFLOW-BUG-02
        Description: Exposes the bug where a long list overflows the slide but is not split.
        Expected to Fail: Yes. The assertion `len(final_slides) > 1` will fail.
        """
        # Arrange: A list element that is too tall for the slide
        items = [ListItem(text=f"Item {i}") for i in range(50)]
        list_element = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=items,
            object_id="long_list_1",
            position=(50, 50),
            size=(620, 1000),  # Very tall
        )

        root_section = Section(
            id="r1", position=(50, 50), size=(620, 1000), children=[list_element]
        )
        slide = Slide(object_id="s1", root_section=root_section)

        # Act
        final_slides = overflow_manager.process_slide(slide)

        # Assert
        assert (
            len(final_slides) > 1
        ), "The overflowing list should have been split across multiple slides."

    def test_bug_table_overflows_and_is_not_split(
        self, overflow_manager: OverflowManager
    ):
        """
        Test Case: OVERFLOW-BUG-03
        Description: Exposes the bug where a tall table overflows the slide but is not split.
        Expected to Fail: Yes. The assertion `len(final_slides) > 1` will fail.
        """
        # Arrange: A table element that is too tall for the slide
        rows = [[f"R{i}C1", f"R{i}C2"] for i in range(30)]
        table_element = TableElement(
            element_type=ElementType.TABLE,
            headers=["H1", "H2"],
            rows=rows,
            object_id="long_table_1",
            position=(50, 50),
            size=(620, 900),  # Very tall
        )

        root_section = Section(
            id="r1", position=(50, 50), size=(620, 900), children=[table_element]
        )
        slide = Slide(object_id="s1", root_section=root_section)

        # Act
        final_slides = overflow_manager.process_slide(slide)

        # Assert
        assert (
            len(final_slides) > 1
        ), "The overflowing table should have been split across multiple slides."
