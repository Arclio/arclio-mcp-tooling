"""Unit tests for the unified content-aware base position calculator."""

import pytest
from markdowndeck.layout.calculator.base import PositionCalculator
from markdowndeck.layout.constants import (
    BODY_TO_FOOTER_SPACING,
    DEFAULT_MARGIN_BOTTOM,
    DEFAULT_MARGIN_LEFT,
    DEFAULT_MARGIN_RIGHT,
    DEFAULT_MARGIN_TOP,
    DEFAULT_SLIDE_HEIGHT,
    DEFAULT_SLIDE_WIDTH,
    FOOTER_HEIGHT,
    HEADER_HEIGHT,
    HEADER_TO_BODY_SPACING,
)
from markdowndeck.models import (
    CodeElement,
    ElementType,
    ListElement,
    ListItem,
    Section,
    Slide,
    TextElement,
)


class TestBasePositionCalculator:
    """Unit tests for the base position calculator functionality."""

    @pytest.fixture
    def default_margins(self) -> dict[str, float]:
        return {
            "top": DEFAULT_MARGIN_TOP,
            "right": DEFAULT_MARGIN_RIGHT,
            "bottom": DEFAULT_MARGIN_BOTTOM,
            "left": DEFAULT_MARGIN_LEFT,
        }

    @pytest.fixture
    def calculator(self, default_margins: dict[str, float]) -> PositionCalculator:
        return PositionCalculator(
            slide_width=DEFAULT_SLIDE_WIDTH,
            slide_height=DEFAULT_SLIDE_HEIGHT,
            margins=default_margins,
        )

    def test_slide_zone_calculation_with_clear_spacing(
        self, calculator: PositionCalculator
    ):
        """Test that slide zones are calculated with clear spacing between them."""

        # Verify basic dimensions
        assert calculator.slide_width == DEFAULT_SLIDE_WIDTH
        assert calculator.slide_height == DEFAULT_SLIDE_HEIGHT

        # Verify content area calculation
        expected_content_width = (
            DEFAULT_SLIDE_WIDTH - DEFAULT_MARGIN_LEFT - DEFAULT_MARGIN_RIGHT
        )
        expected_content_height = (
            DEFAULT_SLIDE_HEIGHT - DEFAULT_MARGIN_TOP - DEFAULT_MARGIN_BOTTOM
        )

        assert calculator.max_content_width == expected_content_width
        assert calculator.max_content_height == expected_content_height

        # Verify header zone
        assert calculator.header_top == DEFAULT_MARGIN_TOP
        assert calculator.header_left == DEFAULT_MARGIN_LEFT
        assert calculator.header_width == expected_content_width
        assert calculator.header_height == HEADER_HEIGHT

        # Verify body zone with clear spacing
        expected_body_top = (
            calculator.header_top + HEADER_HEIGHT + HEADER_TO_BODY_SPACING
        )
        assert calculator.body_top == expected_body_top
        assert calculator.body_left == DEFAULT_MARGIN_LEFT
        assert calculator.body_width == expected_content_width

        # Verify footer zone
        expected_footer_top = (
            DEFAULT_SLIDE_HEIGHT - DEFAULT_MARGIN_BOTTOM - FOOTER_HEIGHT
        )
        assert calculator.footer_top == expected_footer_top
        assert calculator.footer_height == FOOTER_HEIGHT

        # Verify body height calculation (space between body start and footer with spacing)
        expected_body_bottom = expected_footer_top - BODY_TO_FOOTER_SPACING
        expected_body_height = expected_body_bottom - expected_body_top
        assert calculator.body_height == expected_body_height

        # Verify zones don't overlap
        assert calculator.header_top + HEADER_HEIGHT < calculator.body_top
        assert calculator.body_top + calculator.body_height < calculator.footer_top

    def test_universal_section_model_root_section_creation(
        self, calculator: PositionCalculator
    ):
        """Test that the Universal Section Model creates root sections for slides without explicit sections."""

        title = TextElement(element_type=ElementType.TITLE, text="Universal Model Test")

        # Create elements with different content characteristics
        short_para = TextElement(
            element_type=ElementType.TEXT,
            text="Short paragraph.",
            object_id="short_para",
        )

        long_para = TextElement(
            element_type=ElementType.TEXT,
            text="This is a much longer paragraph that will require significantly more vertical space due to line wrapping and content length. "
            * 2,
            object_id="long_para",
        )

        bullet_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[
                ListItem(text="First bullet point"),
                ListItem(text="Second bullet point with more content"),
                ListItem(text="Third bullet point"),
            ],
            object_id="bullet_list",
        )

        footer = TextElement(element_type=ElementType.FOOTER, text="Test Footer")

        # Create slide WITHOUT explicit sections - should trigger root section creation
        slide = Slide(
            object_id="universal_model_test_slide",
            elements=[title, short_para, long_para, bullet_list, footer],
            sections=[],  # Explicitly empty sections
        )

        result_slide = calculator.calculate_positions(slide)

        # Verify that a root section was created
        assert (
            len(result_slide.sections) == 1
        ), "Should have created exactly one root section"

        root_section = result_slide.sections[0]
        assert root_section.id == "root", "Root section should have ID 'root'"

        # Verify that body elements are in the root section
        expected_body_elements = [
            e
            for e in slide.elements
            if e.element_type
            not in (ElementType.TITLE, ElementType.SUBTITLE, ElementType.FOOTER)
        ]
        assert len(root_section.elements) == len(
            expected_body_elements
        ), f"Root section should contain {len(expected_body_elements)} body elements"

        # Verify root section is positioned in body zone
        body_zone = calculator.get_body_zone_area()
        assert root_section.position == (
            body_zone[0],
            body_zone[1],
        ), "Root section should be positioned at body zone origin"
        assert root_section.size == (
            body_zone[2],
            body_zone[3],
        ), "Root section should span the entire body zone"

        # Verify all elements have positions and sizes
        for element in result_slide.elements:
            assert (
                element.position is not None
            ), f"Element {getattr(element, 'object_id', 'unknown')} not positioned"
            assert (
                element.size is not None
            ), f"Element {getattr(element, 'object_id', 'unknown')} not sized"

        # Get positioned elements from root section
        positioned_short = next(
            e for e in root_section.elements if e.object_id == "short_para"
        )
        positioned_long = next(
            e for e in root_section.elements if e.object_id == "long_para"
        )
        positioned_list = next(
            e for e in root_section.elements if e.object_id == "bullet_list"
        )

        # Verify content-aware sizing
        assert (
            positioned_long.size[1] > positioned_short.size[1]
        ), "Longer paragraph should be taller than shorter paragraph"

        assert (
            positioned_list.size[1] > positioned_short.size[1]
        ), "List should be taller than short paragraph"

        # Verify header and footer elements are still positioned in their zones
        positioned_title = next(
            e for e in result_slide.elements if e.element_type == ElementType.TITLE
        )
        positioned_footer = next(
            e for e in result_slide.elements if e.element_type == ElementType.FOOTER
        )

        assert (
            positioned_title.position[1] >= calculator.header_top
        ), "Title should be in header zone"
        assert (
            positioned_title.position[1] < calculator.body_top
        ), "Title should be within header zone"

        assert (
            positioned_footer.position[1] >= calculator.footer_top
        ), "Footer should be in footer zone"

    def test_universal_section_model_preserves_explicit_sections(
        self, calculator: PositionCalculator
    ):
        """Test that explicit sections are preserved and not replaced with root section."""

        title = TextElement(
            element_type=ElementType.TITLE, text="Explicit Sections Test"
        )

        text1 = TextElement(
            element_type=ElementType.TEXT, text="Left content", object_id="left_text"
        )
        text2 = TextElement(
            element_type=ElementType.TEXT, text="Right content", object_id="right_text"
        )

        # Create explicit sections with width directives
        left_section = Section(
            id="left_section_70",
            type="section",
            directives={"width": 0.7},
            elements=[text1],
        )

        right_section = Section(
            id="right_section_30",
            type="section",
            directives={"width": 0.3},
            elements=[text2],
        )

        slide = Slide(
            object_id="explicit_sections_slide",
            elements=[title, text1, text2],
            sections=[left_section, right_section],
        )

        result_slide = calculator.calculate_positions(slide)

        # Verify explicit sections are preserved (not replaced with root section)
        assert len(result_slide.sections) == 2, "Should preserve explicit sections"

        sections = result_slide.sections
        left_sec = sections[0]
        right_sec = sections[1]

        # Verify section IDs are preserved
        assert left_sec.id == "left_section_70"
        assert right_sec.id == "right_section_30"

        assert left_sec.position is not None
        assert left_sec.size is not None
        assert right_sec.position is not None
        assert right_sec.size is not None

        # Verify predictable division - sections should get approximately their specified proportions
        body_width = calculator.body_width

        # Due to spacing, exact percentages may vary slightly
        assert (
            abs(left_sec.size[0] / body_width - 0.7) < 0.1
        ), f"Left section should be ~70% width, got {left_sec.size[0] / body_width:.2f}"
        assert (
            abs(right_sec.size[0] / body_width - 0.3) < 0.1
        ), f"Right section should be ~30% width, got {right_sec.size[0] / body_width:.2f}"

        # Verify horizontal arrangement (width directives trigger horizontal layout)
        assert (
            left_sec.position[0] < right_sec.position[0]
        ), "Left section should be to left of right section"

        # Verify both sections start at same Y coordinate (horizontal layout)
        assert (
            abs(left_sec.position[1] - right_sec.position[1]) < 1
        ), "Sections should be at same Y level"

        # Verify elements are positioned within their sections
        left_element = left_sec.elements[0]
        right_element = right_sec.elements[0]

        assert (
            left_element.position[0] >= left_sec.position[0]
        ), "Left element should be within left section"
        assert (
            right_element.position[0] >= right_sec.position[0]
        ), "Right element should be within right section"

    def test_empty_slide_universal_model(self, calculator: PositionCalculator):
        """Test that empty slides create empty root sections without errors."""

        empty_slide = Slide(object_id="empty_slide", elements=[], sections=[])
        result_slide = calculator.calculate_positions(empty_slide)

        # Should create a root section even for empty slides
        assert (
            len(result_slide.sections) == 1
        ), "Should create root section for empty slide"

        root_section = result_slide.sections[0]
        assert root_section.id == "root"
        assert len(root_section.elements) == 0, "Root section should be empty"

        # Should not raise any exceptions
        assert result_slide.object_id == "empty_slide"

    def test_slide_with_only_header_and_footer_universal_model(
        self, calculator: PositionCalculator
    ):
        """Test slide with only header and footer elements creates empty root section."""

        title = TextElement(element_type=ElementType.TITLE, text="Only Title")
        footer = TextElement(element_type=ElementType.FOOTER, text="Only Footer")

        slide = Slide(
            object_id="header_footer_only_slide", elements=[title, footer], sections=[]
        )

        result_slide = calculator.calculate_positions(slide)

        # Should create empty root section since no body elements exist
        assert len(result_slide.sections) == 1, "Should create root section"
        root_section = result_slide.sections[0]
        assert (
            len(root_section.elements) == 0
        ), "Root section should be empty (no body elements)"

        # Both header/footer elements should be positioned
        positioned_title = next(
            e for e in result_slide.elements if e.element_type == ElementType.TITLE
        )
        positioned_footer = next(
            e for e in result_slide.elements if e.element_type == ElementType.FOOTER
        )

        assert positioned_title.position is not None
        assert positioned_title.size is not None
        assert positioned_footer.position is not None
        assert positioned_footer.size is not None

        # Title should be in header zone
        assert positioned_title.position[1] >= calculator.header_top
        assert positioned_title.position[1] < calculator.body_top

        # Footer should be in footer zone
        assert positioned_footer.position[1] >= calculator.footer_top

    def test_element_width_calculation_with_directives(
        self, calculator: PositionCalculator
    ):
        """Test element width calculation respects directives and defaults."""

        container_width = 400.0

        # Element with no directive - should use default for type
        text_element = TextElement(element_type=ElementType.TEXT, text="Test text")
        text_width = calculator._calculate_element_width(text_element, container_width)

        # Text elements default to full width
        assert (
            abs(text_width - container_width) < 1
        ), "Text should default to full container width"

        # Element with percentage directive
        narrow_element = TextElement(
            element_type=ElementType.TEXT,
            text="Narrow text",
            directives={"width": 0.5},  # 50% width
        )
        narrow_width = calculator._calculate_element_width(
            narrow_element, container_width
        )

        expected_narrow_width = container_width * 0.5
        assert (
            abs(narrow_width - expected_narrow_width) < 1
        ), f"Element should be 50% width: expected {expected_narrow_width}, got {narrow_width}"

        # Element with absolute directive
        fixed_element = TextElement(
            element_type=ElementType.TEXT,
            text="Fixed width text",
            directives={"width": 200},  # 200 points
        )
        fixed_width = calculator._calculate_element_width(
            fixed_element, container_width
        )

        assert (
            abs(fixed_width - 200) < 1
        ), "Element should have specified absolute width"

        # Element with absolute directive larger than container (should be clamped)
        oversized_element = TextElement(
            element_type=ElementType.TEXT,
            text="Oversized text",
            directives={"width": 500},  # Larger than container
        )
        oversized_width = calculator._calculate_element_width(
            oversized_element, container_width
        )

        assert (
            abs(oversized_width - container_width) < 1
        ), "Oversized width directive should be clamped to container width"

    def test_body_elements_identification_universal_model(
        self, calculator: PositionCalculator
    ):
        """Test that body elements are correctly identified for root section creation."""

        title = TextElement(element_type=ElementType.TITLE, text="Title")
        subtitle = TextElement(element_type=ElementType.SUBTITLE, text="Subtitle")
        text1 = TextElement(element_type=ElementType.TEXT, text="Body text 1")
        text2 = TextElement(element_type=ElementType.TEXT, text="Body text 2")
        code_block = CodeElement(element_type=ElementType.CODE, code="print('hello')")
        footer = TextElement(element_type=ElementType.FOOTER, text="Footer")

        slide = Slide(
            object_id="body_identification_slide",
            elements=[title, subtitle, text1, text2, code_block, footer],
        )

        body_elements = calculator.get_body_elements(slide)

        # Should only include text1, text2, and code_block
        assert (
            len(body_elements) == 3
        ), f"Should have 3 body elements, got {len(body_elements)}"

        body_types = [e.element_type for e in body_elements]
        expected_types = [ElementType.TEXT, ElementType.TEXT, ElementType.CODE]

        assert (
            body_types == expected_types
        ), "Body elements should be text and code only"

        # Verify header and footer elements are excluded
        assert not any(e.element_type == ElementType.TITLE for e in body_elements)
        assert not any(e.element_type == ElementType.SUBTITLE for e in body_elements)
        assert not any(e.element_type == ElementType.FOOTER for e in body_elements)

        # Test that these body elements end up in root section
        result_slide = calculator.calculate_positions(slide)
        root_section = result_slide.sections[0]

        assert (
            len(root_section.elements) == 3
        ), "Root section should contain all body elements"

    def test_custom_slide_dimensions_and_margins(self):
        """Test calculator with custom slide dimensions and margins."""

        custom_width = 800.0
        custom_height = 600.0
        custom_margins = {"top": 40, "right": 30, "bottom": 40, "left": 30}

        calculator = PositionCalculator(
            slide_width=custom_width, slide_height=custom_height, margins=custom_margins
        )

        # Verify custom dimensions are used
        assert calculator.slide_width == custom_width
        assert calculator.slide_height == custom_height
        assert calculator.margins == custom_margins

        # Verify derived calculations use custom values
        expected_content_width = (
            custom_width - custom_margins["left"] - custom_margins["right"]
        )
        expected_content_height = (
            custom_height - custom_margins["top"] - custom_margins["bottom"]
        )

        assert calculator.max_content_width == expected_content_width
        assert calculator.max_content_height == expected_content_height

        # Verify zones use custom margins
        assert calculator.header_top == custom_margins["top"]
        assert calculator.header_left == custom_margins["left"]
        assert calculator.body_left == custom_margins["left"]

        # Verify footer calculation with custom dimensions
        expected_footer_top = custom_height - custom_margins["bottom"] - FOOTER_HEIGHT
        assert calculator.footer_top == expected_footer_top

        # Test that universal model works with custom dimensions
        text_elem = TextElement(element_type=ElementType.TEXT, text="Test content")
        slide = Slide(object_id="custom_dims_slide", elements=[text_elem])

        result_slide = calculator.calculate_positions(slide)

        # Should create root section with custom body zone dimensions
        root_section = result_slide.sections[0]
        expected_body_width = expected_content_width
        assert (
            abs(root_section.size[0] - expected_body_width) < 1
        ), "Root section should use custom body width"

    def test_header_footer_positioning_universal_model(
        self, calculator: PositionCalculator
    ):
        """Test that header and footer positioning works correctly in universal model."""

        title = TextElement(
            element_type=ElementType.TITLE, text="Test Title", object_id="title"
        )
        subtitle = TextElement(
            element_type=ElementType.SUBTITLE,
            text="Test Subtitle",
            object_id="subtitle",
        )
        footer = TextElement(
            element_type=ElementType.FOOTER, text="Test Footer", object_id="footer"
        )

        # Add some body content too
        body_text = TextElement(
            element_type=ElementType.TEXT, text="Body content", object_id="body"
        )

        slide = Slide(
            object_id="header_footer_test_slide",
            elements=[title, subtitle, body_text, footer],
        )

        result_slide = calculator.calculate_positions(slide)

        # Find header/footer elements in slide elements (not in sections)
        positioned_title = next(
            e for e in result_slide.elements if e.object_id == "title"
        )
        positioned_subtitle = next(
            e for e in result_slide.elements if e.object_id == "subtitle"
        )
        positioned_footer = next(
            e for e in result_slide.elements if e.object_id == "footer"
        )

        # Verify header elements are in header zone
        assert (
            positioned_title.position[1] >= calculator.header_top
        ), "Title should be at or below header top"
        assert (
            positioned_title.position[1] < calculator.body_top
        ), "Title should be above body zone"

        assert (
            positioned_subtitle.position[1] >= calculator.header_top
        ), "Subtitle should be at or below header top"
        assert (
            positioned_subtitle.position[1] < calculator.body_top
        ), "Subtitle should be above body zone"

        # Subtitle should be below title
        assert (
            positioned_subtitle.position[1] > positioned_title.position[1]
        ), "Subtitle should be positioned below title"

        # Verify footer is in footer zone
        assert (
            positioned_footer.position[1] >= calculator.footer_top
        ), "Footer should be in footer zone"

        # Verify body element ended up in root section
        root_section = result_slide.sections[0]
        assert (
            len(root_section.elements) == 1
        ), "Root section should contain body element"
        body_element = root_section.elements[0]
        assert (
            body_element.object_id == "body"
        ), "Body element should be in root section"

    def test_horizontal_alignment_inheritance_universal_model(
        self, calculator: PositionCalculator
    ):
        """Test that horizontal alignment works correctly in the universal section model."""

        title = TextElement(element_type=ElementType.TITLE, text="Alignment Test")

        # Create elements with different alignments
        left_text = TextElement(
            element_type=ElementType.TEXT,
            text="Left aligned text",
            directives={"align": "left"},
            object_id="left_aligned",
        )

        center_text = TextElement(
            element_type=ElementType.TEXT,
            text="Center aligned text",
            directives={"align": "center"},
            object_id="center_aligned",
        )

        right_text = TextElement(
            element_type=ElementType.TEXT,
            text="Right aligned text",
            directives={"align": "right"},
            object_id="right_aligned",
        )

        slide = Slide(
            object_id="alignment_test_slide",
            elements=[title, left_text, center_text, right_text],
        )

        result_slide = calculator.calculate_positions(slide)

        # Elements should be in root section
        root_section = result_slide.sections[0]

        # Extract positioned elements from root section
        pos_left = next(
            e for e in root_section.elements if e.object_id == "left_aligned"
        )
        pos_center = next(
            e for e in root_section.elements if e.object_id == "center_aligned"
        )
        pos_right = next(
            e for e in root_section.elements if e.object_id == "right_aligned"
        )

        body_left = calculator.body_left
        body_width = calculator.body_width
        body_right = body_left + body_width

        # Verify alignments within root section
        # Left alignment
        assert (
            abs(pos_left.position[0] - body_left) < 5
        ), f"Left-aligned element should be at body left: expected {body_left}, got {pos_left.position[0]}"

        # Center alignment
        element_center = pos_center.position[0] + pos_center.size[0] / 2
        body_center = body_left + body_width / 2
        assert (
            abs(element_center - body_center) < 10
        ), f"Center-aligned element should be centered in body: expected {body_center}, got {element_center}"

        # Right alignment
        element_right = pos_right.position[0] + pos_right.size[0]
        assert (
            abs(element_right - body_right) < 5
        ), f"Right-aligned element should end at body right: expected {body_right}, got {element_right}"

    def test_ensure_section_based_layout_method(self, calculator: PositionCalculator):
        """Test the _ensure_section_based_layout method directly."""

        # Test 1: Slide with no sections should get root section
        title = TextElement(element_type=ElementType.TITLE, text="Test")
        body_text = TextElement(
            element_type=ElementType.TEXT, text="Body", object_id="body"
        )

        slide_no_sections = Slide(
            object_id="no_sections", elements=[title, body_text], sections=[]
        )

        sections = calculator._ensure_section_based_layout(slide_no_sections)

        assert len(sections) == 1, "Should create one root section"
        root_section = sections[0]
        assert root_section.id == "root"
        assert (
            len(root_section.elements) == 1
        ), "Root section should contain body element"
        assert root_section.elements[0].object_id == "body"

        # Test 2: Slide with existing sections should preserve them
        existing_section = Section(id="existing", type="section", elements=[body_text])

        slide_with_sections = Slide(
            object_id="with_sections",
            elements=[title, body_text],
            sections=[existing_section],
        )

        sections = calculator._ensure_section_based_layout(slide_with_sections)

        assert len(sections) == 1, "Should preserve existing section"
        assert sections[0].id == "existing", "Should preserve section ID"
        assert sections[0] is existing_section, "Should return the same section object"

        # Test 3: Slide with only header/footer elements
        slide_header_footer_only = Slide(
            object_id="header_footer_only",
            elements=[
                title,
                TextElement(element_type=ElementType.FOOTER, text="Footer"),
            ],
            sections=[],
        )

        sections = calculator._ensure_section_based_layout(slide_header_footer_only)

        assert (
            len(sections) == 1
        ), "Should create root section even with no body elements"
        root_section = sections[0]
        assert len(root_section.elements) == 0, "Root section should be empty"
