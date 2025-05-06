import pytest
from markdowndeck.models import ElementType, SlideLayout
from markdowndeck.parser.layout_processor import LayoutProcessor


class TestLayoutProcessor:
    """Tests for the LayoutProcessor component."""

    @pytest.fixture
    def processor(self):
        """Create a layout processor for testing."""
        return LayoutProcessor()

    def test_calculate_implicit_widths(self, processor):
        """Test calculating implicit widths for horizontal sections."""
        # Two sections with one explicit width
        sections = [
            {"directives": {"width": 0.75}, "id": "section-1"},
            {"directives": {}, "id": "section-2"},
        ]

        processor._calculate_implicit_widths(sections)

        assert sections[0]["directives"]["width"] == 0.75
        assert sections[1]["directives"]["width"] == 0.25

        # Three sections with one explicit width
        sections = [
            {"directives": {"width": 0.5}, "id": "section-1"},
            {"directives": {}, "id": "section-2"},
            {"directives": {}, "id": "section-3"},
        ]

        processor._calculate_implicit_widths(sections)

        assert sections[0]["directives"]["width"] == 0.5
        assert sections[1]["directives"]["width"] == 0.25
        assert sections[2]["directives"]["width"] == 0.25

        # All sections with explicit widths
        sections = [
            {"directives": {"width": 0.3}, "id": "section-1"},
            {"directives": {"width": 0.7}, "id": "section-2"},
        ]

        processor._calculate_implicit_widths(sections)

        assert sections[0]["directives"]["width"] == 0.3
        assert sections[1]["directives"]["width"] == 0.7

        # Total explicit width exceeds 1.0 (should be handled gracefully)
        sections = [
            {"directives": {"width": 0.7}, "id": "section-1"},
            {"directives": {"width": 0.7}, "id": "section-2"},
            {"directives": {}, "id": "section-3"},
        ]

        processor._calculate_implicit_widths(sections)

        assert sections[0]["directives"]["width"] == 0.7
        assert sections[1]["directives"]["width"] == 0.7
        assert sections[2]["directives"]["width"] == 0.0

    def test_calculate_implicit_heights(self, processor):
        """Test calculating implicit heights for vertical sections."""
        # Two sections with one explicit height
        sections = [
            {
                "directives": {"height": 0.6},
                "id": "section-1",
                "content": "Short content",
            },
            {
                "directives": {},
                "id": "section-2",
                "content": "Longer content with more text",
            },
        ]

        processor._calculate_implicit_heights(sections)

        assert sections[0]["directives"]["height"] == 0.6
        assert sections[1]["directives"]["height"] == 0.4

        # All sections with explicit heights
        sections = [
            {"directives": {"height": 0.3}, "id": "section-1", "content": "Content 1"},
            {"directives": {"height": 0.7}, "id": "section-2", "content": "Content 2"},
        ]

        processor._calculate_implicit_heights(sections)

        assert sections[0]["directives"]["height"] == 0.3
        assert sections[1]["directives"]["height"] == 0.7

        # Total explicit height exceeds 1.0 (should be handled gracefully)
        sections = [
            {"directives": {"height": 0.8}, "id": "section-1", "content": "Content 1"},
            {"directives": {"height": 0.8}, "id": "section-2", "content": "Content 2"},
            {"directives": {}, "id": "section-3", "content": "Content 3"},
        ]

        processor._calculate_implicit_heights(sections)

        assert sections[0]["directives"]["height"] == 0.8
        assert sections[1]["directives"]["height"] == 0.8
        assert sections[2]["directives"]["height"] == 0.0

    def test_estimate_content_size(self, processor):
        """Test estimating content size based on content structure."""
        # Simple text
        simple_text = "This is simple text content."
        simple_size = processor._estimate_content_size(simple_text)

        # Text with list items
        list_text = "List:\n* Item 1\n* Item 2\n* Item 3"
        list_size = processor._estimate_content_size(list_text)

        # Text with code block
        code_text = "Code:\n```python\ndef hello():\n    print('Hello world')\n```"
        code_size = processor._estimate_content_size(code_text)

        # Text with table
        table_text = "Table:\n| Header 1 | Header 2 |\n|-|-|\n| Cell 1 | Cell 2 |\n| Cell 3 | Cell 4 |"
        table_size = processor._estimate_content_size(table_text)

        # Check relative sizes
        assert code_size > simple_size  # Code blocks get extra size
        assert list_size > simple_size  # Lists get extra size
        assert table_size > simple_size  # Tables get extra size

    def test_determine_layout(self, processor):
        """Test determining slide layout based on element types."""
        # Elements with just a title
        title_only_elements = [{"element_type": ElementType.TITLE}]
        title_only_layout = processor.determine_layout(title_only_elements)
        assert title_only_layout == SlideLayout.TITLE_ONLY

        # Elements with title and subtitle
        title_subtitle_elements = [
            {"element_type": ElementType.TITLE},
            {"element_type": ElementType.SUBTITLE},
        ]
        title_subtitle_layout = processor.determine_layout(title_subtitle_elements)
        assert title_subtitle_layout == SlideLayout.TITLE

        # Elements with title and image
        title_image_elements = [
            {"element_type": ElementType.TITLE},
            {"element_type": ElementType.IMAGE},
        ]
        title_image_layout = processor.determine_layout(title_image_elements)
        assert title_image_layout == SlideLayout.CAPTION_ONLY

        # Elements with title and list
        title_list_elements = [
            {"element_type": ElementType.TITLE},
            {"element_type": ElementType.BULLET_LIST},
        ]
        title_list_layout = processor.determine_layout(title_list_elements)
        assert title_list_layout == SlideLayout.TITLE_AND_BODY

        # Elements with no title
        no_title_elements = [
            {"element_type": ElementType.TEXT},
            {"element_type": ElementType.IMAGE},
        ]
        no_title_layout = processor.determine_layout(no_title_elements)
        assert no_title_layout == SlideLayout.BLANK

        # Elements with title, subtitle, and content
        complex_elements = [
            {"element_type": ElementType.TITLE},
            {"element_type": ElementType.SUBTITLE},
            {"element_type": ElementType.BULLET_LIST},
        ]
        complex_layout = processor.determine_layout(complex_elements)
        assert complex_layout == SlideLayout.TITLE_AND_BODY

    def test_calculate_section_positions(self, processor):
        """Test calculating positions for sections."""
        # Setup content area and sections
        content_area = (50, 100, 600, 300)  # left, top, width, height

        # Two vertical sections with equal height
        sections = [
            {"type": "section", "directives": {"height": 0.5}, "id": "section-1"},
            {"type": "section", "directives": {"height": 0.5}, "id": "section-2"},
        ]

        positioned_sections = processor.calculate_section_positions(
            sections, content_area
        )

        # Check positions
        assert positioned_sections[0]["position"] == (50, 100)
        assert positioned_sections[0]["size"] == (600, 150)
        assert positioned_sections[1]["position"][0] == 50
        assert positioned_sections[1]["position"][1] > 100
        assert positioned_sections[1]["size"] == (600, 150)

        # Row with two subsections
        sections = [
            {
                "type": "row",
                "directives": {"height": 1.0},
                "id": "row-1",
                "subsections": [
                    {
                        "type": "section",
                        "directives": {"width": 0.5},
                        "id": "subsection-1",
                    },
                    {
                        "type": "section",
                        "directives": {"width": 0.5},
                        "id": "subsection-2",
                    },
                ],
            },
        ]

        positioned_sections = processor.calculate_section_positions(
            sections, content_area
        )

        # Check row position
        assert positioned_sections[0]["position"] == (50, 100)
        assert positioned_sections[0]["size"] == (600, 300)

        # Check subsections
        subsections = positioned_sections[0]["subsections"]
        assert subsections[0]["position"] == (50, 100)
        assert subsections[0]["size"][0] == 300  # Half of content width
        assert subsections[1]["position"][0] > 50
        assert subsections[1]["position"][1] == 100
        assert subsections[1]["size"][0] == 300  # Half of content width
