"""Comprehensive tests for the overflow handling system."""

import pytest
from markdowndeck.models import ElementType, ListElement, ListItem, Slide, TextElement
from markdowndeck.overflow import (
    OverflowDetector,
    OverflowManager,
    OverflowStrategy,
    SlideBuilder,
    StandardOverflowHandler,
)
from markdowndeck.overflow.models import ContentGroup, OverflowType


class TestOverflowDetector:
    """Test overflow detection functionality."""

    @pytest.fixture
    def detector(self):
        return OverflowDetector(slide_width=720, slide_height=405)

    @pytest.fixture
    def slide_no_overflow(self):
        """Create a slide with content that fits."""
        title = TextElement(
            element_type=ElementType.TITLE,
            text="Test Title",
            position=(50, 70),
            size=(620, 40),
        )
        text = TextElement(
            element_type=ElementType.TEXT,
            text="Content that fits",
            position=(50, 150),
            size=(620, 50),
        )
        return Slide(object_id="no_overflow_slide", elements=[title, text])

    @pytest.fixture
    def slide_with_overflow(self):
        """Create a slide with content that overflows."""
        title = TextElement(
            element_type=ElementType.TITLE,
            text="Test Title",
            position=(50, 70),
            size=(620, 40),
        )
        # Element that extends beyond slide boundary
        overflowing_text = TextElement(
            element_type=ElementType.TEXT,
            text="Content that overflows",
            position=(50, 350),  # Near bottom
            size=(620, 100),  # Extends beyond slide
        )
        return Slide(object_id="overflow_slide", elements=[title, overflowing_text])

    def test_no_overflow_detection(self, detector, slide_no_overflow):
        """Test that slides without overflow are correctly identified."""
        result = detector.detect_overflow(slide_no_overflow)

        assert not result.has_overflow
        assert len(result.overflow_elements) == 0
        assert result.overflow_amount == 0.0
        assert "No overflow" in result.summary

    def test_overflow_detection(self, detector, slide_with_overflow):
        """Test that slides with overflow are correctly identified."""
        result = detector.detect_overflow(slide_with_overflow)

        assert result.has_overflow
        assert len(result.overflow_elements) == 1
        assert result.overflow_amount > 0
        assert result.overflow_elements[0].overflow_type == OverflowType.VERTICAL

    def test_content_group_analysis(self, detector):
        """Test content grouping functionality."""
        # Create slide with related elements
        text1 = TextElement(
            element_type=ElementType.TEXT,
            text="Header text",
            position=(50, 150),
            size=(620, 30),
        )
        text1.related_to_next = True

        list_elem = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[ListItem(text="Item 1")],
            position=(50, 190),
            size=(620, 50),
        )
        list_elem.related_to_prev = True

        slide = Slide(object_id="grouped_slide", elements=[text1, list_elem])

        groups = detector.analyze_content_groups(slide)

        assert len(groups) == 1  # Should be grouped together
        assert len(groups[0].elements) == 2
        assert groups[0].group_type == "header_with_content"

    def test_empty_slide(self, detector):
        """Test handling of empty slides."""
        empty_slide = Slide(object_id="empty", elements=[])
        result = detector.detect_overflow(empty_slide)

        assert not result.has_overflow
        assert "No body elements" in result.summary


class TestStandardOverflowHandler:
    """Test the standard overflow handling strategy."""

    @pytest.fixture
    def handler(self):
        return StandardOverflowHandler(slide_width=720, slide_height=405)

    @pytest.fixture
    def overflowing_slide(self):
        """Create a slide that definitely needs overflow handling."""
        elements = []

        # Title
        title = TextElement(
            element_type=ElementType.TITLE,
            text="Overflowing Slide",
            position=(50, 70),
            size=(620, 40),
        )
        elements.append(title)

        # Many text elements that will overflow
        y_pos = 150
        for i in range(10):
            text = TextElement(
                element_type=ElementType.TEXT,
                text=f"Text element {i + 1} with content",
                position=(50, y_pos),
                size=(620, 50),
            )
            elements.append(text)
            y_pos += 60  # This will go beyond slide boundaries

        # Footer
        footer = TextElement(
            element_type=ElementType.FOOTER,
            text="Footer",
            position=(50, 375),
            size=(620, 30),
        )
        elements.append(footer)

        return Slide(object_id="overflow_test", elements=elements)

    def test_overflow_handling_creates_multiple_slides(self, handler, overflowing_slide):
        """Test that overflow handling creates multiple slides."""
        # Create mock overflow info
        overflow_info = type(
            "obj",
            (object,),
            {"has_overflow": True, "overflow_elements": [], "summary": "Test overflow"},
        )()

        result_slides = handler.handle_overflow(overflowing_slide, overflow_info)

        assert len(result_slides) > 1
        assert all(isinstance(slide, Slide) for slide in result_slides)

    def test_first_slide_keeps_original_title(self, handler, overflowing_slide):
        """Test that first slide keeps the original title."""
        overflow_info = type(
            "obj",
            (object,),
            {"has_overflow": True, "overflow_elements": [], "summary": "Test overflow"},
        )()

        result_slides = handler.handle_overflow(overflowing_slide, overflow_info)

        # First slide should have original title
        first_slide = result_slides[0]
        assert first_slide.object_id == overflowing_slide.object_id
        assert first_slide.title == overflowing_slide.title

    def test_continuation_slides_have_modified_titles(self, handler, overflowing_slide):
        """Test that continuation slides have appropriate titles."""
        overflow_info = type(
            "obj",
            (object,),
            {"has_overflow": True, "overflow_elements": [], "summary": "Test overflow"},
        )()

        result_slides = handler.handle_overflow(overflowing_slide, overflow_info)

        if len(result_slides) > 1:
            # Continuation slides should have modified titles and IDs
            for i, slide in enumerate(result_slides[1:], 1):
                assert "(cont.)" in slide.title
                assert f"_cont_{i}" in slide.object_id


class TestSlideBuilder:
    """Test slide building functionality."""

    @pytest.fixture
    def builder(self):
        return SlideBuilder(slide_width=720, slide_height=405)

    @pytest.fixture
    def original_slide(self):
        title = TextElement(
            element_type=ElementType.TITLE,
            text="Original Title",
            position=(50, 70),
            size=(620, 40),
        )
        footer = TextElement(
            element_type=ElementType.FOOTER,
            text="Original Footer",
            position=(50, 375),
            size=(620, 30),
        )
        return Slide(object_id="original", elements=[title, footer], title="Original Title")

    @pytest.fixture
    def content_groups(self):
        text = TextElement(
            element_type=ElementType.TEXT,
            text="Content for new slide",
            position=(50, 150),
            size=(620, 50),
        )
        return [ContentGroup(elements=[text], total_height=50, group_type="single")]

    def test_create_first_slide(self, builder, original_slide, content_groups):
        """Test creating first slide preserves original properties."""
        first_slide = builder.create_first_slide(original_slide, content_groups)

        assert first_slide.object_id == original_slide.object_id
        assert first_slide.title == original_slide.title
        assert len(first_slide.elements) > 0  # Should have copied elements

    def test_create_continuation_slide(self, builder, original_slide, content_groups):
        """Test creating continuation slide with proper modifications."""
        cont_slide = builder.create_continuation_slide(original_slide, content_groups, 1)

        assert "_cont_1" in cont_slide.object_id
        assert "(cont.)" in cont_slide.title
        assert len(cont_slide.elements) > 0

    def test_element_id_generation(self, builder):
        """Test that element IDs are properly generated."""
        id1 = builder._generate_element_id(ElementType.TEXT)
        id2 = builder._generate_element_id(ElementType.TEXT)

        assert id1 != id2  # Should be unique
        assert "text_" in id1
        assert "text_" in id2


class TestOverflowManager:
    """Test the main overflow manager orchestrator."""

    @pytest.fixture
    def manager(self):
        return OverflowManager(strategy=OverflowStrategy.STANDARD)

    @pytest.fixture
    def simple_slide(self):
        """Create a simple slide that fits on one slide."""
        title = TextElement(
            element_type=ElementType.TITLE,
            text="Simple Title",
            position=(50, 70),
            size=(620, 40),
        )
        text = TextElement(
            element_type=ElementType.TEXT,
            text="Simple content",
            position=(50, 150),
            size=(620, 50),
        )
        return Slide(object_id="simple", elements=[title, text])

    def test_no_overflow_returns_original_slide(self, manager, simple_slide):
        """Test that slides without overflow return unchanged."""
        result = manager.process_slide(simple_slide)

        assert len(result) == 1
        assert result[0].object_id == simple_slide.object_id

    def test_strategy_switching(self, manager):
        """Test that overflow strategy can be changed."""

        manager.set_strategy(OverflowStrategy.STANDARD)
        assert manager.current_strategy == OverflowStrategy.STANDARD

        # Test invalid strategy
        with pytest.raises(ValueError):
            manager.set_strategy("invalid_strategy")

    def test_overflow_summary(self, manager, simple_slide):
        """Test overflow analysis without handling."""
        summary = manager.get_overflow_summary(simple_slide)

        assert isinstance(summary, dict)
        assert "has_overflow" in summary
        assert summary["has_overflow"] is False  # Simple slide should not overflow

    def test_custom_handler_registration(self, manager):
        """Test that custom handlers can be registered."""

        # Create a mock custom handler
        class MockHandler:
            def handle_overflow(self, slide, overflow_info):
                return [slide]  # Just return original slide

        custom_handler = MockHandler()
        custom_strategy = OverflowStrategy.CUSTOM

        manager.add_custom_handler(custom_strategy, custom_handler)
        assert custom_strategy in manager.handlers


class TestOverflowIntegration:
    """Integration tests for the complete overflow system."""

    def test_complete_overflow_workflow(self):
        """Test the complete workflow from detection to handling."""
        # Create a slide with definite overflow
        elements = []

        # Title
        title = TextElement(
            element_type=ElementType.TITLE,
            text="Integration Test",
            position=(50, 70),
            size=(620, 40),
        )
        elements.append(title)

        # Content that will overflow
        y_pos = 150
        for i in range(15):  # Lots of content
            text = TextElement(
                element_type=ElementType.TEXT,
                text=f"Content line {i + 1} with substantial text",
                position=(50, y_pos),
                size=(620, 30),
            )
            elements.append(text)
            y_pos += 35

        slide = Slide(object_id="integration_test", elements=elements)

        # Process through complete system
        manager = OverflowManager()
        result_slides = manager.process_slide(slide)

        # Verify results
        assert len(result_slides) > 1  # Should create multiple slides
        assert all(isinstance(s, Slide) for s in result_slides)
        assert result_slides[0].object_id == slide.object_id  # First slide keeps ID

        # All slides should have some content
        for slide in result_slides:
            content_elements = [e for e in slide.elements if e.element_type not in (ElementType.TITLE, ElementType.FOOTER)]
            assert len(content_elements) > 0

    def test_edge_case_empty_slide(self):
        """Test handling of edge case: empty slide."""
        empty_slide = Slide(object_id="empty", elements=[])

        manager = OverflowManager()
        result = manager.process_slide(empty_slide)

        assert len(result) == 1
        assert result[0].object_id == empty_slide.object_id

    def test_edge_case_single_huge_element(self):
        """Test handling of a single element that's too big for any slide."""
        huge_text = TextElement(
            element_type=ElementType.TEXT,
            text="Huge content",
            position=(50, 150),
            size=(620, 500),  # Bigger than slide can handle
        )

        slide = Slide(object_id="huge_element", elements=[huge_text])

        manager = OverflowManager()
        result = manager.process_slide(slide)

        # Should still work, even if element is oversized
        assert len(result) >= 1
        assert isinstance(result[0], Slide)
