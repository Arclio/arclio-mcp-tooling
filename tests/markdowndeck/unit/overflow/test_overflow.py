import logging
from unittest.mock import MagicMock, patch

import pytest
from markdowndeck.models import (
    ElementType,
    ImageElement,
    Section,
    Slide,
    TableElement,
    TextElement,
)
from markdowndeck.overflow import OverflowManager


@pytest.fixture
def overflow_manager() -> OverflowManager:
    """Provides an OverflowManager with a mocked LayoutManager."""
    with patch("markdowndeck.layout.LayoutManager") as mock_lm_class:
        mock_lm_instance = MagicMock()

        def relayout(slide):
            """A simple relayout that positions elements sequentially."""
            if slide.root_section:
                y_offset = 50  # Start after top margin

                # Recursively layout sections and elements
                def layout_section(section, start_y):
                    current_y = start_y
                    section.position = (50, start_y)

                    for child in section.children:
                        if isinstance(child, Section):
                            # Recursively layout child section
                            end_y = layout_section(child, current_y)
                            current_y = end_y
                        else:
                            # Layout element
                            child.position = (50, current_y)
                            if child.size:
                                current_y += child.size[1]
                            else:
                                # Give default size if not set
                                child.size = (620, 50)
                                current_y += 50

                    # Set section size based on its children
                    section.size = (620, current_y - start_y)
                    return current_y

                layout_section(slide.root_section, y_offset)

            # Also position any meta-elements
            if hasattr(slide, "elements"):
                for element in slide.elements:
                    if element.element_type == ElementType.TITLE and not element.position:
                        element.position = (50, 10)
                        element.size = element.size or (620, 30)
                    elif element.element_type == ElementType.SUBTITLE and not element.position:
                        element.position = (50, 45)
                        element.size = element.size or (620, 25)
                    elif element.element_type == ElementType.FOOTER and not element.position:
                        element.position = (50, 375)
                        element.size = element.size or (620, 20)

            return slide

        mock_lm_instance.calculate_positions.side_effect = relayout
        mock_lm_class.return_value = mock_lm_instance

        yield OverflowManager(
            margins={"top": 50, "right": 50, "bottom": 50, "left": 50},
            slide_height=405,
        )


@pytest.fixture
def positioned_slide_with_overflow() -> Slide:
    """Creates a slide with a single overflowing text element."""
    text_element = TextElement(
        element_type=ElementType.TEXT,
        text="Overflow\nContent",
        object_id="el_overflow",
        position=(50, 50),
        size=(620, 500),  # Overflows 405 slide height
    )

    # Mock the split method to return predictable parts
    fitted_text_part = TextElement(
        element_type=ElementType.TEXT,
        text="Fitted",
        object_id="el_fitted",
        size=(620, 350),
        position=(50, 50),
    )
    overflow_text_part = TextElement(
        element_type=ElementType.TEXT,
        text="Overflowing",
        object_id="el_overflow_part",
        size=(620, 150),
    )
    text_element.split = MagicMock(return_value=(fitted_text_part, overflow_text_part))

    root_section = Section(
        id="overflowing_section",
        position=(50, 50),
        size=(620, 500),
        children=[text_element],
    )

    title = TextElement(
        element_type=ElementType.TITLE,
        text="Original Title",
        object_id="el_title",
        position=(50, 10),
        size=(620, 30),
    )

    return Slide(
        object_id="external_overflow",
        root_section=root_section,
        elements=[title],
        renderable_elements=[title],
    )


@pytest.fixture
def positioned_slide_no_overflow() -> Slide:
    """Creates a slide where content fits perfectly."""
    text_element = TextElement(
        element_type=ElementType.TEXT,
        text="Fits",
        position=(50, 50),
        size=(620, 100),
        object_id="el_fit",
    )

    root_section = Section(
        id="fitting_section",
        position=(50, 50),
        size=(620, 100),  # Fits within 405 height
        children=[text_element],
    )

    return Slide(
        object_id="no_overflow_slide",
        root_section=root_section,
        elements=[],
        renderable_elements=[],
    )


class TestOverflowManager:
    def test_overflow_c_01_no_op_path(self, overflow_manager: OverflowManager, positioned_slide_no_overflow: Slide):
        """Test Case: OVERFLOW-C-01: A slide that fits is finalized without creating continuations."""
        final_slides = overflow_manager.process_slide(positioned_slide_no_overflow)

        assert len(final_slides) == 1
        final_slide = final_slides[0]

        # Check that slide was finalized properly
        assert final_slide.root_section is None
        assert len(final_slide.renderable_elements) == 1
        assert final_slide.renderable_elements[0].object_id == "el_fit"

        # Layout manager should not be called for slides that fit
        overflow_manager.layout_manager.calculate_positions.assert_not_called()

    def test_overflow_c_02_internal_overflow_is_ignored(self, overflow_manager: OverflowManager):
        """Test Case: OVERFLOW-C-02: Internal overflow in a fixed-height section is ignored."""
        # This section's box fits on the slide (y=50, h=200 -> bottom=250),
        # but its content is taller. The detector should ignore this as the
        # section has a fixed height and its box fits.
        tall_element = TextElement(
            element_type=ElementType.TEXT,
            text="Tall content inside fixed container",
            position=(50, 50),
            size=(620, 500),  # This is taller than the container
            object_id="el_tall",
        )

        section = Section(
            id="fixed_height_sec",
            position=(50, 50),
            size=(620, 200),  # Fixed height that fits on slide
            directives={"height": 200},  # This makes it a fixed-height section
            children=[tall_element],
        )

        slide = Slide(
            object_id="internal_overflow",
            root_section=section,
            elements=[],
            renderable_elements=[],
        )

        final_slides = overflow_manager.process_slide(slide)

        # Should not split because the fixed-height section itself fits
        assert len(final_slides) == 1, "Internal overflow should be ignored and not cause a split."
        assert final_slides[0].renderable_elements[0].object_id == "el_tall"

    def test_overflow_c_03_circuit_breaker_first_strike(self, overflow_manager: OverflowManager):
        """Test Case: OVERFLOW-C-03: Verifies circuit breaker's first strike."""
        image = ImageElement(
            element_type=ElementType.IMAGE,
            url="test.png",
            alt_text="Test image",
            object_id="img1",
            position=(50, 50),
            size=(100, 500),  # Too tall for slide
        )

        root_section = Section(
            id="r1",
            position=(50, 50),
            size=(100, 500),
            children=[image],
        )

        slide = Slide(
            object_id="s1",
            root_section=root_section,
            elements=[],
            renderable_elements=[],
        )

        final_slides = overflow_manager.process_slide(slide)

        assert len(final_slides) == 2, "Should create a continuation slide"

        # Verify the image was moved to continuation slide with flag set
        continuation_slide_arg = overflow_manager.layout_manager.calculate_positions.call_args[0][0]
        assert continuation_slide_arg.is_continuation is True

        # The image should be in the continuation slide's root_section
        moved_image = continuation_slide_arg.root_section.children[0]
        assert moved_image.object_id == "img1"
        assert moved_image._overflow_moved is True

    def test_overflow_c_04_circuit_breaker_second_strike(self, overflow_manager: OverflowManager, caplog):
        """Test Case: OVERFLOW-C-04: Verifies circuit breaker's second strike."""
        # Image that has already been moved once
        image = ImageElement(
            element_type=ElementType.IMAGE,
            url="test.png",
            alt_text="Test image",
            object_id="img1",
            position=(50, 50),
            size=(100, 500),  # Still too tall
            _overflow_moved=True,  # Already moved once
        )

        root_section = Section(
            id="r1",
            position=(50, 50),
            size=(100, 500),
            children=[image],
        )

        slide = Slide(
            object_id="s1_cont",
            root_section=root_section,
            is_continuation=True,
            elements=[],
            renderable_elements=[],
        )

        with caplog.at_level(logging.ERROR):
            final_slides = overflow_manager.process_slide(slide)

        # Should not create another continuation slide
        assert len(final_slides) == 1, "Should not create another continuation slide"

        # Should log circuit breaker message
        assert "OVERFLOW CIRCUIT BREAKER" in caplog.text

        # Image should still be in the slide
        assert len(final_slides[0].renderable_elements) == 1
        assert final_slides[0].renderable_elements[0].object_id == "img1"

    def test_table_header_duplication_on_split(self, overflow_manager: OverflowManager):
        """Test Case: OVERFLOW_SPEC Rule #7: Table headers must be duplicated on split."""
        table = TableElement(
            element_type=ElementType.TABLE,
            object_id="table1",
            position=(50, 50),
            size=(400, 500),  # Too tall
            headers=["Column 1", "Column 2"],
            rows=[["Row 1 Cell 1", "Row 1 Cell 2"], ["Row 2 Cell 1", "Row 2 Cell 2"]],
            row_directives=[
                {"background": "gray"},
                {},
                {},
            ],  # Header directive and two row directives
        )

        # Mock split to return an overflowing part without headers
        fitted = TableElement(
            element_type=ElementType.TABLE,
            object_id="table1_fitted",
            headers=["Column 1", "Column 2"],
            rows=[["Row 1 Cell 1", "Row 1 Cell 2"]],
            row_directives=[{"background": "gray"}, {}],
            size=(400, 250),
        )
        overflowing = TableElement(
            element_type=ElementType.TABLE,
            object_id="table1_overflow",
            headers=[],  # No headers in the split result
            rows=[["Row 2 Cell 1", "Row 2 Cell 2"]],
            row_directives=[{}],
            size=(400, 250),
        )
        table.split = MagicMock(return_value=(fitted, overflowing))

        root_section = Section(
            id="r1",
            position=(50, 50),
            size=(400, 500),
            children=[table],
        )

        slide = Slide(
            object_id="s1",
            root_section=root_section,
            elements=[],
            renderable_elements=[],
        )

        final_slides = overflow_manager.process_slide(slide)

        assert len(final_slides) == 2, "Should create continuation slide"

        # Get the continuation slide that was passed to layout manager
        continuation_slide_arg = overflow_manager.layout_manager.calculate_positions.call_args[0][0]

        # The overflowing table should have headers duplicated
        overflowing_table_on_new_slide = continuation_slide_arg.root_section.children[0]
        assert overflowing_table_on_new_slide.headers == ["Column 1", "Column 2"]
        assert len(overflowing_table_on_new_slide.row_directives) == 2  # Header directive + 1 row
        assert overflowing_table_on_new_slide.row_directives[0] == {"background": "gray"}
