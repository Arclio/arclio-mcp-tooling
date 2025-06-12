import pytest
from markdowndeck.layout import LayoutManager
from markdowndeck.models import ElementType, ImageElement, Section, Slide, TextElement


@pytest.fixture
def layout_manager() -> LayoutManager:
    return LayoutManager()


class TestLayoutManagerDirectives:
    def test_layout_c_07_proportional_width_division(
        self, layout_manager: LayoutManager
    ):
        """
        Test Case: LAYOUT-C-07
        Validates precise proportional width division for horizontal sections.
        """
        # Arrange
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
        # Flatten elements for initial slide inventory
        elements = [child.children[0] for child in sections]
        slide = Slide(
            object_id="proportional_slide", sections=[row_section], elements=elements
        )

        # Act
        positioned_slide = layout_manager.calculate_positions(slide)

        # Assert
        positioned_sections = positioned_slide.sections[0].children
        content_width = layout_manager.max_content_width

        assert len(positioned_sections) == 3
        assert positioned_sections[0].size is not None
        assert positioned_sections[1].size is not None
        assert positioned_sections[2].size is not None

        # Check widths with a small tolerance for floating point math
        assert abs(positioned_sections[0].size[0] - content_width * 0.2) < 0.1
        assert abs(positioned_sections[1].size[0] - content_width * 0.5) < 0.1
        assert abs(positioned_sections[2].size[0] - content_width * 0.3) < 0.1

    def test_layout_c_04_fixed_height_directive_is_respected(
        self, layout_manager: LayoutManager
    ):
        """
        Test Case: LAYOUT-C-04
        Validates that a fixed height directive on a section is respected.
        """
        # Arrange
        tall_element = TextElement(
            element_type=ElementType.TEXT,
            text="Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6",
        )
        section = Section(
            id="fixed_height_sec", directives={"height": 100}, children=[tall_element]
        )
        slide = Slide(
            object_id="fixed_height_slide", sections=[section], elements=[tall_element]
        )

        # Act
        positioned_slide = layout_manager.calculate_positions(slide)

        # Assert
        positioned_section = positioned_slide.sections[0]
        assert positioned_section.size is not None
        assert (
            positioned_section.size[1] == 100.0
        ), "The section height must be exactly what the directive specified."

    def test_layout_c_02_proactive_image_scaling(self, layout_manager: LayoutManager):
        """
        Test Case: LAYOUT-C-02
        Verify the Proactive Image Scaling rule.
        """
        # Arrange
        image = ImageElement(
            element_type=ElementType.IMAGE, url="test.png", aspect_ratio=1.6
        )  # 16:10 aspect ratio
        section = Section(id="img_sec", children=[image])
        slide = Slide(object_id="img_slide", sections=[section], elements=[image])

        # Act
        positioned_slide = layout_manager.calculate_positions(slide)

        # Assert
        positioned_image = positioned_slide.sections[0].children[0]
        assert positioned_image.size is not None

        # FIXED: Updated assertions to reflect correct scaling logic where height
        # can also be a constraint.
        # The container width is 720. The container height is 405.
        # An image with aspect ratio 1.6 scaled to width 720 would have height 450.
        # This exceeds the container height of 405.
        # Therefore, the image must be scaled to the container height instead.
        expected_height = 405.0
        expected_width = expected_height * 1.6  # 648.0

        assert abs(positioned_image.size[0] - expected_width) < 1.0
        assert abs(positioned_image.size[1] - expected_height) < 1.0
