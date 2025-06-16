from unittest.mock import MagicMock, patch

import pytest
from markdowndeck.models import ElementType, ImageElement, Section, Slide, TextElement
from markdowndeck.overflow import OverflowManager


@pytest.fixture
def overflow_manager_factory():
    """A factory to create overflow managers for specific test scenarios."""

    def _create_manager():
        with patch("markdowndeck.layout.LayoutManager") as mock_lm_class:
            mock_lm_instance = MagicMock()

            def simple_recursive_relayout(slide: Slide) -> Slide:
                y_offset = 10.0
                if slide.root_section:

                    def layout_section(section, current_y):
                        section_start_y = current_y
                        section.position = (50, section_start_y)
                        for child in section.children:
                            if isinstance(child, Section):
                                current_y = layout_section(child, current_y)
                            else:
                                child.position = child.position or (50, current_y)
                                child.size = child.size or (620, 100)
                                current_y += child.size[1]
                        section.size = section.size or (
                            620,
                            current_y - section_start_y,
                        )
                        return current_y

                    layout_section(slide.root_section, y_offset)
                return slide

            mock_lm_instance.calculate_positions.side_effect = simple_recursive_relayout
            mock_lm_class.return_value = mock_lm_instance
            return OverflowManager(
                margins={"top": 50, "right": 50, "bottom": 50, "left": 50},
                slide_height=405,
            )

    return _create_manager


def _get_element_by_id(slide: Slide, element_id: str):
    return next(
        (el for el in slide.renderable_elements if el.object_id == element_id), None
    )


def _get_section_by_id(section: Section, section_id: str):
    if not section:
        return None
    if section.id == section_id:
        return section
    for child in section.children:
        if isinstance(child, Section):
            found = _get_section_by_id(child, section_id)
            if found:
                return found
    return None


class TestFillContextOverflow:
    """Tests the specialized overflow handler for slides with [fill] images."""

    def test_sibling_overflow_duplicates_context(self, overflow_manager_factory):
        """Test Case: OVERFLOW-C-08 (Sibling Overflow)"""
        manager = overflow_manager_factory()

        fill_image = ImageElement(
            element_type=ElementType.IMAGE,
            url="fill.png",
            directives={"fill": True},
            object_id="fill_img",
        )
        context_col = Section(
            id="ctx_col",
            children=[fill_image],
            directives={"width": "40%", "height": "100%"},
        )

        overflowing_text = TextElement(
            element_type=ElementType.TEXT,
            text="Long text",
            object_id="overflow_txt",
            position=(300, 50),
            size=(400, 400),
        )
        overflowing_text.split = MagicMock(
            return_value=(
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Fit",
                    object_id="fit_txt",
                    size=(400, 150),
                ),
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Overflow",
                    object_id="over_txt",
                    size=(400, 250),
                ),
            )
        )
        content_col = Section(
            id="content_col", children=[overflowing_text], directives={"width": "60%"}
        )

        row = Section(id="root_row", type="row", children=[context_col, content_col])
        slide = Slide(object_id="s1", root_section=row)

        final_slides = manager.process_slide(slide)

        assert len(final_slides) == 2, "Should create a continuation slide."
        assert _get_element_by_id(final_slides[0], "fill_img") is not None
        assert _get_element_by_id(final_slides[0], "fit_txt") is not None

        continuation_slide_arg = manager.layout_manager.calculate_positions.call_args[
            0
        ][0]
        root = continuation_slide_arg.root_section
        assert _get_section_by_id(root, "ctx_col") is not None
        assert _get_section_by_id(root, "content_col") is not None

    def test_atomic_move_on_container_overflow(self, overflow_manager_factory):
        """Test Case: OVERFLOW-C-09 (Atomic Move)"""
        manager = overflow_manager_factory()

        title = TextElement(
            element_type=ElementType.TITLE,
            text="A Title",
            object_id="title1",
            position=(50, 10),
            size=(620, 300),
        )

        fill_image = ImageElement(
            element_type=ElementType.IMAGE,
            url="fill.png",
            directives={"fill": True},
            object_id="fill_img",
        )
        context_col = Section(
            id="ctx_col",
            children=[fill_image],
            directives={"width": "40%", "height": "100%"},
        )
        content_col = Section(
            id="content_col",
            children=[TextElement(element_type=ElementType.TEXT, text="Sib")],
            directives={"width": "60%"},
        )

        row_to_move = Section(
            id="atomic_row",
            type="row",
            children=[context_col, content_col],
            position=(50, 350),
            size=(620, 200),
        )

        root = Section(id="root_sec", children=[title, row_to_move])
        slide = Slide(
            object_id="s1",
            root_section=root,
            elements=[title],
            renderable_elements=[title],
        )

        final_slides = manager.process_slide(slide)

        assert len(final_slides) == 2
        assert _get_element_by_id(final_slides[0], "title1") is not None
        assert _get_element_by_id(final_slides[0], "fill_img") is None

        continuation_slide_arg = manager.layout_manager.calculate_positions.call_args[
            0
        ][0]
        assert (
            _get_section_by_id(continuation_slide_arg.root_section, "atomic_row")
            is not None
        )

    def test_deeply_nested_sibling_overflow(self, overflow_manager_factory):
        """Validates correct context duplication with a deeply nested fill image."""
        manager = overflow_manager_factory()

        fill_image = ImageElement(
            element_type=ElementType.IMAGE,
            url="fill.png",
            directives={"fill": True},
            object_id="fill_img_deep",
        )
        nested_context_section = Section(
            id="nested_ctx", children=[fill_image], directives={"height": "100%"}
        )
        context_col = Section(
            id="ctx_col_deep",
            children=[nested_context_section],
            directives={"width": "50%"},
        )

        overflowing_text = TextElement(
            element_type=ElementType.TEXT,
            text="Long text",
            object_id="overflow_txt_deep",
            position=(300, 50),
            size=(300, 400),
        )
        overflowing_text.split = MagicMock(
            return_value=(
                TextElement(element_type=ElementType.TEXT, text="Fit", size=(300, 150)),
                TextElement(
                    element_type=ElementType.TEXT, text="Overflow", size=(300, 250)
                ),
            )
        )
        content_col = Section(
            id="content_col_deep",
            children=[overflowing_text],
            directives={"width": "50%"},
        )

        row = Section(id="deep_row", type="row", children=[context_col, content_col])
        slide = Slide(object_id="s_deep", root_section=row)

        final_slides = manager.process_slide(slide)

        assert len(final_slides) == 2

        assert _get_element_by_id(final_slides[0], "fill_img_deep") is not None

        continuation_slide = manager.layout_manager.calculate_positions.call_args[0][0]
        assert (
            _get_section_by_id(continuation_slide.root_section, "deep_row") is not None
        )
