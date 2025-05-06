import pytest
from markdowndeck.api_generator import ApiRequestGenerator
from markdowndeck.layout import LayoutManager
from markdowndeck.models import ElementType
from markdowndeck.parser import Parser


class TestIntegration:
    """Integration tests for the complete parser-layout-api generation pipeline."""

    @pytest.fixture
    def parser(self):
        """Create a parser for testing."""
        return Parser()

    @pytest.fixture
    def layout_manager(self):
        """Create a layout manager for testing."""
        return LayoutManager()

    @pytest.fixture
    def api_generator(self):
        """Create an API request generator for testing."""
        return ApiRequestGenerator()

    def test_simple_presentation(self, parser, layout_manager, api_generator):
        """Test creating a simple presentation with the full pipeline."""
        markdown = """
        # Simple Presentation

        This is a simple slide with some text.

        * Bullet 1
        * Bullet 2

        ===

        # Second Slide

        More content here.
        """

        # Step 1: Parse markdown into a deck
        deck = parser.parse(markdown, "Test Presentation")

        # Verify basic deck structure
        assert len(deck.slides) == 2
        assert deck.title == "Test Presentation"

        # Verify first slide
        assert deck.slides[0].elements[0].element_type == ElementType.TITLE
        assert deck.slides[0].elements[0].text == "Simple Presentation"

        # Step 2: Calculate layout positions
        for i, slide in enumerate(deck.slides):
            deck.slides[i] = layout_manager.calculate_positions(slide)

        # Verify layout positions were calculated
        for slide in deck.slides:
            for element in slide.elements:
                assert hasattr(element, "position")
                assert hasattr(element, "size")

        # Step 3: Generate API requests
        presentation_id = "test_presentation_id"
        batches = api_generator.generate_batch_requests(deck, presentation_id)

        # Verify API requests
        assert len(batches) == 2  # One batch per slide

        # Each batch should have a create slide request as the first request
        for batch in batches:
            assert batch["presentationId"] == presentation_id
            assert len(batch["requests"]) > 0
            assert "createSlide" in batch["requests"][0]

    def test_complex_layout(self, parser, layout_manager, api_generator):
        """Test creating a presentation with complex layout."""
        markdown = """
        # Complex Layout

        [width=2/3][align=center]
        Main content area with some important information.

        * Feature 1
        * Feature 2

        ***

        [width=1/3][background=#f5f5f5]
        ## Sidebar

        Supporting information here.

        ===

        # Vertical Layout

        [height=30%]
        Top section content.

        ---

        [height=70%]
        Bottom section with more detailed information.

        ```python
        def example():
            return "This is a code example"
        ```
        """

        # Step 1: Parse markdown into a deck
        deck = parser.parse(markdown, "Complex Layout Test")

        # Verify basic deck structure
        assert len(deck.slides) == 2
        assert deck.title == "Complex Layout Test"

        # Verify first slide has sections
        assert len(deck.slides[0].sections) > 0
        assert deck.slides[0].sections[0]["type"] == "row"
        assert len(deck.slides[0].sections[0]["subsections"]) == 2

        # Verify section directives
        assert (
            deck.slides[0].sections[0]["subsections"][0]["directives"]["width"] == 2 / 3
        )
        assert (
            deck.slides[0].sections[0]["subsections"][0]["directives"]["align"]
            == "center"
        )
        assert (
            deck.slides[0].sections[0]["subsections"][1]["directives"]["width"] == 1 / 3
        )

        # Verify second slide vertical sections
        assert len(deck.slides[1].sections) == 2
        assert deck.slides[1].sections[0]["directives"]["height"] == 0.3
        assert deck.slides[1].sections[1]["directives"]["height"] == 0.7

        # Step 2: Calculate layout positions
        updated_slides = []
        for _i, slide in enumerate(deck.slides):
            result = layout_manager.calculate_positions(slide)
            # Handle both single slide and list of slides results
            if isinstance(result, list):
                updated_slides.extend(result)
            else:
                updated_slides.append(result)

        # Replace the deck's slides with the updated ones
        deck.slides = updated_slides

        # Step 3: Generate API requests
        presentation_id = "test_presentation_id"
        batches = api_generator.generate_batch_requests(deck, presentation_id)

        # Verify API requests
        assert len(batches) >= 2  # At least one batch per slide

        # Check that complex layout elements are included in the requests
        for batch in batches:
            for request in batch["requests"]:
                if "createShape" in request:
                    # Check that element positioning is reflected in the API request
                    assert "transform" in request["createShape"]["elementProperties"]
                    assert (
                        "translateX"
                        in request["createShape"]["elementProperties"]["transform"]
                    )
                    assert (
                        "translateY"
                        in request["createShape"]["elementProperties"]["transform"]
                    )

    def test_slide_with_notes_and_footer(self, parser, layout_manager, api_generator):
        """Test creating a slide with speaker notes and footer."""
        markdown = """
        # Slide With Notes and Footer

        Main content.

        <!-- notes: These are speaker notes for the presenter -->

        @@@

        This is the slide footer
        """

        # Step 1: Parse markdown into a deck
        deck = parser.parse(markdown, "Notes and Footer Test")

        # Verify basic deck structure
        assert len(deck.slides) == 1

        # Verify notes were extracted
        assert deck.slides[0].notes == "These are speaker notes for the presenter"

        # Verify footer was extracted
        assert deck.slides[0].footer == "This is the slide footer"

        # Find footer element
        footer_element = None
        for element in deck.slides[0].elements:
            if element.element_type == ElementType.FOOTER:
                footer_element = element
                break

        assert footer_element is not None
        assert footer_element.text == "This is the slide footer"

        # Step 2: Calculate layout positions
        deck.slides[0] = layout_manager.calculate_positions(deck.slides[0])

        # Verify footer is positioned at the bottom
        assert footer_element.position[1] > 300  # Y position should be near bottom

        # Step 3: Generate API requests
        presentation_id = "test_presentation_id"
        batches = api_generator.generate_batch_requests(deck, presentation_id)

        # Verify speaker notes request is included
        speaker_notes_request = None
        for request in batches[0]["requests"]:
            if "updateSpeakerNotesProperties" in request:
                speaker_notes_request = request
                break

        assert speaker_notes_request is not None
        assert (
            speaker_notes_request["updateSpeakerNotesProperties"][
                "speakerNotesProperties"
            ]["speakerNotesText"]
            == "These are speaker notes for the presenter"
        )

    def test_overflow_handling(self, parser, layout_manager, api_generator):
        """Test handling of content that overflows a slide."""
        # Create a slide with lots of content that will overflow
        markdown = """
        # Overflow Test

        ## First Section

        * Item 1
        * Item 2
        * Item 3

        ## Second Section

        * Item A
        * Item B
        * Item C

        ## Third Section

        * Item X
        * Item Y
        * Item Z

        ## Fourth Section

        Additional content that should cause overflow.

        ## Fifth Section

        Even more content that definitely won't fit.
        """

        # Step 1: Parse markdown into a deck
        deck = parser.parse(markdown, "Overflow Test")

        # Step 2: Calculate layout positions with overflow handling
        original_slide = deck.slides[0]
        processed_slide = layout_manager.calculate_positions(original_slide)

        # Check if overflow was detected and handled
        if isinstance(processed_slide, list):
            # Multiple slides were created to handle overflow
            assert len(processed_slide) > 1

            # Verify first slide has the original title
            assert processed_slide[0].elements[0].element_type == ElementType.TITLE
            assert processed_slide[0].elements[0].text == "Overflow Test"

            # Verify continuation slide has a title with "(cont.)"
            assert processed_slide[1].elements[0].element_type == ElementType.TITLE
            assert "(cont.)" in processed_slide[1].elements[0].text

            # Update the deck with the overflow-handled slides
            deck.slides = processed_slide

        # Step 3: Generate API requests
        presentation_id = "test_presentation_id"
        batches = api_generator.generate_batch_requests(deck, presentation_id)

        # Verify correct number of batches were created
        assert len(batches) >= 1
