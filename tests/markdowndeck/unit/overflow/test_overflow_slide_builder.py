"""Unit tests for individual overflow handler components."""

import pytest
from markdowndeck.models import (
    ElementType,
    Section,
    Slide,
    TextElement,
)
from markdowndeck.models.constants import SlideLayout
from markdowndeck.overflow.constants import (
    CONTINUED_FOOTER_SUFFIX,
    CONTINUED_TITLE_SUFFIX,
)
from markdowndeck.overflow.slide_builder import SlideBuilder


class TestSlideBuilder:
    """Unit tests for the SlideBuilder component."""

    @pytest.fixture
    def original_slide(self) -> Slide:
        """Create a sample original slide for testing."""
        return Slide(
            object_id="original_slide_123",
            title="Original Slide Title",
            layout=SlideLayout.TITLE_AND_BODY,
            notes="Important speaker notes",
            background={"type": "color", "value": "#ffffff"},
            elements=[
                TextElement(
                    element_type=ElementType.TITLE, text="Original Slide Title"
                ),
                TextElement(element_type=ElementType.FOOTER, text="Page Footer"),
            ],
        )

    @pytest.fixture
    def slide_builder(self, original_slide) -> SlideBuilder:
        """Create slide builder with original slide."""
        return SlideBuilder(original_slide)

    def test_continuation_slide_id_generation(self, slide_builder):
        """Test that continuation slides get unique IDs."""

        new_sections = [Section(id="test_section", elements=[])]

        slide1 = slide_builder.create_continuation_slide(new_sections, 1)
        slide2 = slide_builder.create_continuation_slide(new_sections, 2)

        assert (
            slide1.object_id != slide2.object_id
        ), "Continuation slides should have unique IDs"
        assert (
            "original_slide_123_cont_1" in slide1.object_id
        ), "Should include original ID and sequence"
        assert (
            "original_slide_123_cont_2" in slide2.object_id
        ), "Should include original ID and sequence"

    def test_continuation_title_creation(self, slide_builder):
        """Test creation of continuation titles."""

        new_sections = [Section(id="test_section", elements=[])]

        # Test first continuation
        continuation1 = slide_builder.create_continuation_slide(new_sections, 1)

        title_elements = [
            e for e in continuation1.elements if e.element_type == ElementType.TITLE
        ]
        assert len(title_elements) == 1, "Should have one title element"

        title = title_elements[0]
        assert (
            CONTINUED_TITLE_SUFFIX in title.text
        ), "Should include continuation suffix"
        assert "Original Slide Title" in title.text, "Should preserve original title"

        # Test numbered continuation
        continuation2 = slide_builder.create_continuation_slide(new_sections, 2)

        title_elements2 = [
            e for e in continuation2.elements if e.element_type == ElementType.TITLE
        ]
        title2 = title_elements2[0]
        assert (
            "(2)" in title2.text
        ), "Should include slide number for multiple continuations"

    def test_continuation_footer_creation(self, slide_builder):
        """Test creation of continuation footers."""

        new_sections = [Section(id="test_section", elements=[])]

        continuation = slide_builder.create_continuation_slide(new_sections, 1)

        footer_elements = [
            e for e in continuation.elements if e.element_type == ElementType.FOOTER
        ]
        assert len(footer_elements) == 1, "Should have one footer element"

        footer = footer_elements[0]
        assert (
            CONTINUED_FOOTER_SUFFIX in footer.text
        ), "Should include continuation suffix"
        assert "Page Footer" in footer.text, "Should preserve original footer text"

    def test_metadata_preservation(self, slide_builder):
        """Test that slide metadata is preserved in continuations."""

        new_sections = [Section(id="test_section", elements=[])]

        continuation = slide_builder.create_continuation_slide(new_sections, 1)

        assert (
            continuation.layout == SlideLayout.TITLE_AND_BODY
        ), "Should use standard layout"
        assert continuation.notes == "Important speaker notes", "Should preserve notes"
        assert continuation.background == {
            "type": "color",
            "value": "#ffffff",
        }, "Should preserve background"

    def test_element_extraction_from_sections(self, slide_builder):
        """Test extraction of elements from sections for slide elements list."""

        # Create sections with elements
        text1 = TextElement(element_type=ElementType.TEXT, text="Section 1 text")
        text2 = TextElement(element_type=ElementType.TEXT, text="Section 2 text")

        section1 = Section(id="section1", elements=[text1])
        section2 = Section(id="section2", elements=[text2])

        continuation = slide_builder.create_continuation_slide([section1, section2], 1)

        # Should have title, footer, and section elements
        expected_elements = 2 + 2  # title + footer + 2 section elements
        assert (
            len(continuation.elements) == expected_elements
        ), f"Should have {expected_elements} elements"

        # Check that section elements are included
        text_elements = [
            e
            for e in continuation.elements
            if e.element_type == ElementType.TEXT
            and e.text in ["Section 1 text", "Section 2 text"]
        ]
        assert len(text_elements) == 2, "Should include all section elements"

    def test_nested_section_element_extraction(self, slide_builder):
        """Test extraction from nested section structures."""

        # Create nested sections
        nested_text = TextElement(element_type=ElementType.TEXT, text="Nested content")
        nested_section = Section(id="nested", elements=[nested_text])

        parent_text = TextElement(element_type=ElementType.TEXT, text="Parent content")
        parent_section = Section(
            id="parent", elements=[parent_text], subsections=[nested_section]
        )

        continuation = slide_builder.create_continuation_slide([parent_section], 1)

        # Should extract elements from both parent and nested sections
        text_elements = [
            e
            for e in continuation.elements
            if e.element_type == ElementType.TEXT
            and e.text in ["Parent content", "Nested content"]
        ]
        assert len(text_elements) == 2, "Should extract from nested sections"

    def test_original_slide_without_title(self):
        """Test slide builder with original slide that has no title."""

        original_without_title = Slide(
            object_id="no_title_slide",
            elements=[TextElement(element_type=ElementType.TEXT, text="Just content")],
        )

        builder = SlideBuilder(original_without_title)
        new_sections = [Section(id="test_section", elements=[])]

        continuation = builder.create_continuation_slide(new_sections, 1)

        # Should create generic continuation title
        title_elements = [
            e for e in continuation.elements if e.element_type == ElementType.TITLE
        ]
        assert len(title_elements) == 1, "Should create title even if original had none"

        title = title_elements[0]
        assert "Content" in title.text, "Should use generic title"
        assert (
            CONTINUED_TITLE_SUFFIX in title.text
        ), "Should include continuation suffix"

    def test_original_slide_without_footer(self):
        """Test slide builder with original slide that has no footer."""

        original_without_footer = Slide(
            object_id="no_footer_slide",
            elements=[TextElement(element_type=ElementType.TITLE, text="Title Only")],
        )

        builder = SlideBuilder(original_without_footer)
        new_sections = [Section(id="test_section", elements=[])]

        continuation = builder.create_continuation_slide(new_sections, 1)

        # Should not create footer if original had none
        footer_elements = [
            e for e in continuation.elements if e.element_type == ElementType.FOOTER
        ]
        assert (
            len(footer_elements) == 0
        ), "Should not create footer if original had none"

    def test_unique_element_ids_generation(self, slide_builder):
        """Test that elements get unique IDs to avoid conflicts."""

        text_element = TextElement(
            element_type=ElementType.TEXT, text="Test", object_id="original_id"
        )
        section = Section(id="test_section", elements=[text_element])

        continuation = slide_builder.create_continuation_slide([section], 1)

        # Find the extracted text element
        extracted_elements = [
            e
            for e in continuation.elements
            if e.element_type == ElementType.TEXT and e.text == "Test"
        ]
        assert len(extracted_elements) == 1, "Should have extracted text element"

        extracted = extracted_elements[0]
        assert extracted.object_id != "original_id", "Should generate new unique ID"
        assert extracted.object_id is not None, "Should have an ID"
