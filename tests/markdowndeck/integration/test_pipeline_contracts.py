import pytest
from markdowndeck import markdown_to_requests
from markdowndeck.layout import LayoutManager
from markdowndeck.models import Element, ElementType, Section
from markdowndeck.overflow import OverflowManager
from markdowndeck.parser import Parser


def _find_shape_by_text(requests: list, text_substring: str) -> dict | None:
    """Finds a createShape request linked to an insertText request with specific text."""
    text_req = next(
        (
            r
            for r in requests
            if "insertText" in r and text_substring in r["insertText"]["text"]
        ),
        None,
    )
    if not text_req:
        return None

    object_id = text_req["insertText"]["objectId"]
    shape_reqs = [r for r in requests if "createShape" in r]

    return next(
        (
            r["createShape"]
            for r in shape_reqs
            if r["createShape"]["objectId"] == object_id
        ),
        None,
    )


class TestPipelineContracts:
    """Validates data integrity between pipeline stages."""

    @pytest.fixture
    def parser(self) -> Parser:
        return Parser()

    @pytest.fixture
    def layout_manager(self) -> LayoutManager:
        return LayoutManager()

    @pytest.fixture
    def overflow_manager(self) -> OverflowManager:
        return OverflowManager()

    def test_p_01_parser_to_layout_contract(self, parser: Parser):
        """
        Test Case: INTEGRATION-P-01
        Validates the Parser produces a valid "Unpositioned" slide.
        """
        # Arrange
        markdown = "# Title\n:::section\nContent\n:::"

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        # Assert: Validate the "Unpositioned" state
        assert slide.root_section is not None

        def check_unpositioned(section: Section):
            assert section.position is None, "Section position should be None"
            assert section.size is None, "Section size should be None"
            for child in section.children:
                if isinstance(child, Section):
                    check_unpositioned(child)
                elif isinstance(child, Element):
                    assert child.position is None, "Element position should be None"
                    assert child.size is None, "Element size should be None"

        check_unpositioned(slide.root_section)
        for el in slide.elements:
            assert el.position is None
            assert el.size is None

    def test_p_02_layout_to_overflow_contract_no_overflow(
        self,
        parser: Parser,
        layout_manager: LayoutManager,
        overflow_manager: OverflowManager,
    ):
        """
        Test Case: INTEGRATION-P-02
        Validates "Positioned" to "Finalized" state transition for a slide that fits.
        """
        # Arrange
        markdown = "# Title\n:::section\nContent\n:::"
        unpositioned_slide = parser.parse(markdown).slides[0]

        # Act 1: Get "Positioned" state
        positioned_slide = layout_manager.calculate_positions(unpositioned_slide)

        # Assert 1: Validate "Positioned" state
        assert positioned_slide.root_section.position is not None
        assert positioned_slide.root_section.size is not None
        assert (
            positioned_slide.root_section.children[0].children[0].position is not None
        )
        assert positioned_slide.root_section.children[0].children[0].size is not None

        # Act 2: Get "Finalized" state
        finalized_slides = overflow_manager.process_slide(positioned_slide)

        # Assert 2: Validate "Finalized" state
        assert len(finalized_slides) == 1
        final_slide = finalized_slides[0]
        assert (
            final_slide.root_section is None
        ), "Finalized slide must have root_section cleared"
        assert (
            len(final_slide.renderable_elements) > 0
        ), "Finalized slide must have renderable elements"
        for element in final_slide.renderable_elements:
            assert element.position is not None
            assert element.size is not None

    def test_p_03_overflow_produces_multiple_finalized_slides(
        self,
        parser: Parser,
        layout_manager: LayoutManager,
        overflow_manager: OverflowManager,
    ):
        """
        Test Case: INTEGRATION-P-03
        Validates an overflowing slide results in a list of multiple "Finalized" slides.
        """
        # Arrange
        long_content = "\n".join([f"* List Item {i}" for i in range(100)])
        markdown = f"# Overflow Test\n:::section\n{long_content}\n:::"
        unpositioned_slide = parser.parse(markdown).slides[0]

        # Act
        positioned_slide = layout_manager.calculate_positions(unpositioned_slide)
        finalized_slides = overflow_manager.process_slide(positioned_slide)

        # Assert
        assert len(finalized_slides) > 1, "Overflow should result in multiple slides"
        for i, slide in enumerate(finalized_slides):
            assert (
                slide.root_section is None
            ), f"Slide {i} must have root_section cleared"
            assert (
                len(slide.renderable_elements) > 0
            ), f"Slide {i} must have renderable elements"
            if i > 0:
                title_element = slide.get_title_element()
                assert title_element is not None
                assert (
                    "(continued)" in title_element.text
                ), f"Continuation slide {i} must have a continuation title"

    def test_p_04_full_pipeline_via_markdown_to_requests(self):
        """Test Case: INTEGRATION-P-04 - Full pipeline via markdown_to_requests."""
        markdown = "# E2E Test\n:::section\nContent.\n:::"
        result = markdown_to_requests(markdown, title="E2E Pipeline Test")
        requests = result["slide_batches"][0]["requests"]

        title_shape_req = _find_shape_by_text(requests, "E2E Test")
        assert (
            title_shape_req is not None
        ), "A createShape request for the title must exist."

        content_shape_req = _find_shape_by_text(requests, "Content.")
        assert (
            content_shape_req is not None
        ), "A createShape request for the content must exist."

    def test_p_05_style_directive_flow(self):
        """Test Case: INTEGRATION-P-05 - End-to-end flow of styling directives."""
        markdown = ":::section [color=#FF0000]\nRed Text\n:::"
        result = markdown_to_requests(markdown)
        requests = result["slide_batches"][0]["requests"]

        style_req = next((r for r in requests if "updateTextStyle" in r), None)
        assert style_req is not None, "An updateTextStyle request must be generated."

        color = style_req["updateTextStyle"]["style"]["foregroundColor"]["opaqueColor"][
            "rgbColor"
        ]
        assert abs(color["red"] - 1.0) < 1e-9

    def test_p_06_flexible_body_area(self):
        """Test Case: INTEGRATION-P-06 - End-to-end validation of flexible body area."""
        markdown = (
            ":::section\nBody Only\n:::\n===\n# Title\n:::section\nBody With Title\n:::"
        )
        result = markdown_to_requests(markdown)

        batch1_reqs = result["slide_batches"][0]["requests"]
        batch2_reqs = result["slide_batches"][1]["requests"]

        shape1 = _find_shape_by_text(batch1_reqs, "Body Only")
        shape2 = _find_shape_by_text(batch2_reqs, "Body With Title")
        assert shape1 is not None, "Could not find body shape in first slide."
        assert shape2 is not None, "Could not find body shape in second slide."

        shape1_y = shape1["elementProperties"]["transform"]["translateY"]
        shape2_y = shape2["elementProperties"]["transform"]["translateY"]

        assert (
            shape1_y < shape2_y
        ), "Body content should be positioned higher on a slide without a title."

    def test_p_07_gap_directive_flow(self):
        """Test Case: INTEGRATION-P-07 - End-to-end validation of the gap directive."""
        markdown = ":::section [gap=30]\nFirst Line\n\nSecond Line\n:::"
        result = markdown_to_requests(markdown)
        requests = result["slide_batches"][0]["requests"]

        shape1 = _find_shape_by_text(requests, "First Line")
        shape2 = _find_shape_by_text(requests, "Second Line")
        assert shape1 is not None, "Could not find first text shape."
        assert shape2 is not None, "Could not find second text shape."

        shape1_props = shape1["elementProperties"]
        shape2_props = shape2["elementProperties"]

        shape1_bottom = (
            shape1_props["transform"]["translateY"]
            + shape1_props["size"]["height"]["magnitude"]
        )
        shape2_top = shape2_props["transform"]["translateY"]

        actual_gap = shape2_top - shape1_bottom
        assert (
            abs(actual_gap - 30.0) < 5.0
        ), "The gap between elements must be ~30 points."

    def test_p_10_container_clamping(self):
        """Test Case: INTEGRATION-P-10 - Verify "Container-First" clamping behavior."""
        # Arrange: Two columns each want 60% of width, which is impossible.
        # REFACTORED: Use :::row and :::column for layout.
        markdown = ":::row\n:::column [width=60%]\n:::section\nLeft\n:::\n:::\n:::column [width=60%]\n:::section\nRight\n:::\n:::\n:::"

        # Act
        result = markdown_to_requests(markdown)
        requests = result["slide_batches"][0]["requests"]

        # Assert
        left_shape = _find_shape_by_text(requests, "Left")
        right_shape = _find_shape_by_text(requests, "Right")
        assert left_shape is not None, "Could not find left column shape."
        assert right_shape is not None, "Could not find right column shape."

        # Each should be clamped to 50% of the available width (720pts).
        expected_width = 360.0
        left_width = left_shape["elementProperties"]["size"]["width"]["magnitude"]
        right_width = right_shape["elementProperties"]["size"]["width"]["magnitude"]

        assert (
            abs(left_width - expected_width) < 1.0
        ), "Left column width was not clamped correctly."
        assert (
            abs(right_width - expected_width) < 1.0
        ), "Right column width was not clamped correctly."

    def test_p_11_invalid_image_url_e2e(self):
        """Test Case: INTEGRATION-P-11 - End-to-end handling of an invalid image URL."""
        # Arrange
        markdown = ":::section\n![alt](http://localhost/invalid.png) [width=100][height=100]\n:::"

        # Act
        result = markdown_to_requests(markdown)
        requests = result["slide_batches"][0]["requests"]

        # Assert
        # FIXED: The system now correctly substitutes a placeholder. The test must verify this behavior.
        image_req = next((r for r in requests if "createImage" in r), None)
        assert (
            image_req is not None
        ), "A createImage request for the placeholder should have been generated."
        assert (
            "placehold.co" in image_req["createImage"]["url"]
        ), "The image URL should be a placeholder from placehold.co."

    def test_p_12_directive_precedence(self):
        """Test Case: INTEGRATION-P-12 - Verify directive precedence for meta-elements."""
        # Arrange: Section-level directive is red, title's same-line directive is blue.
        # REFACTORED: Base directives are now used for slide-wide styling.
        markdown = "[color=red]\n# Title [color=blue]\n:::section\nBody\n:::"

        # Act
        result = markdown_to_requests(markdown)
        requests = result["slide_batches"][0]["requests"]

        # Assert
        title_shape = _find_shape_by_text(requests, "Title")
        assert title_shape is not None, "Could not find title shape."
        title_id = title_shape["objectId"]
        style_req = next(
            (
                r
                for r in requests
                if "updateTextStyle" in r
                and r["updateTextStyle"]["objectId"] == title_id
            ),
            None,
        )
        assert style_req is not None, "Could not find style request for title."

        color = style_req["updateTextStyle"]["style"]["foregroundColor"]["opaqueColor"][
            "rgbColor"
        ]
        assert abs(color["red"]) < 1e-9, "Title color red component should be 0."
        assert abs(color["green"]) < 1e-9, "Title color green component should be 0."
        assert (
            abs(color["blue"] - 1.0) < 1e-9
        ), "Title color blue component should be 1.0."

    def test_p_13_image_in_bounded_column_no_overflow(
        self,
        parser: Parser,
        layout_manager: LayoutManager,
        overflow_manager: OverflowManager,
    ):
        """
        Test Case: INTEGRATION-P-13 (Custom)
        Validates that an image, when placed in a column with a defined width,
        is correctly scaled by the LayoutManager and does NOT trigger the
        OverflowManager, preventing an infinite loop.
        """
        # Arrange
        # REFACTORED: Use :::row/column and add mandatory image dimension directives.
        markdown = """
# Image in a Column

:::row
:::column [width=50%]
:::section
![Test Image](https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800&h=1200) [width=100%][height=600]
:::
:::
:::column [width=50%]
:::section
Some text content in the other column.
:::
:::
:::
"""
        # This image is tall and would cause overflow if not scaled correctly
        # within its 50% width container.

        unpositioned_slide = parser.parse(markdown).slides[0]

        # Act
        positioned_slide = layout_manager.calculate_positions(unpositioned_slide)
        finalized_slides = overflow_manager.process_slide(positioned_slide)

        # Assert
        assert (
            len(finalized_slides) == 1
        ), "An image scaled within its container should not cause an overflow."
        final_slide = finalized_slides[0]
        image_element = next(
            (
                el
                for el in final_slide.renderable_elements
                if el.element_type == ElementType.IMAGE
            ),
            None,
        )
        assert image_element is not None, "Image element should be in the final slide."
        assert (
            image_element.size[1] < overflow_manager.slide_height
        ), "Image height must be scaled to be less than the slide height."

    def test_p_14_image_and_text_in_column_no_overflow(
        self,
        parser: Parser,
        layout_manager: LayoutManager,
        overflow_manager: OverflowManager,
    ):
        """
        Test Case: INTEGRATION-P-14 (Custom)
        Validates that an image stacked with text inside a column is correctly
        scaled and laid out by the LayoutManager, preventing a false overflow trigger.
        """
        # Arrange
        markdown = """
# Image in a Column

:::row
:::column [width=50%]
:::section
![Test Image](https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800&h=1200) [width=100%][height=600]
A short line of text below the image.
:::
:::
:::column [width=50%]
:::section
Some text content in the other column.
:::
:::
:::
"""
        unpositioned_slide = parser.parse(markdown).slides[0]

        # Act
        positioned_slide = layout_manager.calculate_positions(unpositioned_slide)
        finalized_slides = overflow_manager.process_slide(positioned_slide)

        # Assert
        assert (
            len(finalized_slides) == 1
        ), "A correctly scaled image and text in a column should not cause an overflow."
        final_slide = finalized_slides[0]

        image_element = next(
            (
                el
                for el in final_slide.renderable_elements
                if el.element_type == ElementType.IMAGE
            ),
            None,
        )
        assert image_element is not None, "Image element should be in the final slide."
        assert (
            image_element.size[1] < overflow_manager.slide_height
        ), "Image height must be scaled to be less than the slide height."

        text_element = next(
            (
                el
                for el in final_slide.renderable_elements
                if el.element_type == ElementType.TEXT and "A short line" in el.text
            ),
            None,
        )
        assert text_element is not None, "Text element should be present below image."

        image_bottom = image_element.position[1] + image_element.size[1]
        text_top = text_element.position[1]
        assert text_top >= image_bottom, "Text must be positioned below the image."

    def test_p_15_image_fill_with_sibling_overflow(self):
        """
        Test Case: INTEGRATION-P-15 - Specialized overflow handling for slides with [fill] context.
        """
        long_text = " ".join([f"Word {i}" for i in range(200)])
        # FIXED: Added explicit width and height to the section containing the [fill] image.
        # This satisfies the new, simpler validation logic.
        markdown = f"""
# Fill Context Test

:::row
:::column [width=40%][height=100%]
:::section [width=100%][height=100%]
![Fill Image](https://images.unsplash.com/photo-1521737711867-e3b97375f902?w=500) [fill]
:::
:::
:::column [width=60%]
:::section
{long_text}
:::
:::
:::
"""
        result = markdown_to_requests(markdown)
        slide_batches = result["slide_batches"]

        assert (
            len(slide_batches) == 2
        ), "Specialized fill overflow should create exactly 2 slides"

        slide1_requests = slide_batches[0]["requests"]
        slide1_image = next((r for r in slide1_requests if "createImage" in r), None)
        slide1_text = next(
            (
                r
                for r in slide1_requests
                if "insertText" in r and "Word" in r["insertText"]["text"]
            ),
            None,
        )

        assert slide1_image is not None, "First slide must contain the [fill] image"
        assert (
            slide1_text is not None
        ), "First slide must contain some of the text content"

        slide2_requests = slide_batches[1]["requests"]
        slide2_image = next((r for r in slide2_requests if "createImage" in r), None)
        slide2_text = next(
            (
                r
                for r in slide2_requests
                if "insertText" in r and "Word" in r["insertText"]["text"]
            ),
            None,
        )

        assert (
            slide2_image is not None
        ), "Second slide must contain the duplicated [fill] image context"
        assert (
            slide2_text is not None
        ), "Second slide must contain the overflowing text content"

        assert slide1_image["createImage"]["url"] == slide2_image["createImage"]["url"]
        slide1_text_content = slide1_text["insertText"]["text"]
        slide2_text_content = slide2_text["insertText"]["text"]
        assert slide1_text_content != slide2_text_content

    def test_p_16_heading_style_and_color_directive_flow(self):
        """
        Test Case: INTEGRATION-P-16
        Validates that both font size from a heading level and a color
        directive are correctly translated into a single updateTextStyle API request.
        """
        # Arrange: A heading with a color directive.
        markdown = ":::section\n## My Blue H2 Heading [color=blue]\n:::"

        # Act
        result = markdown_to_requests(markdown)
        requests = result["slide_batches"][0]["requests"]

        # Find the text element's ID
        shape = _find_shape_by_text(requests, "My Blue H2 Heading")
        assert shape is not None, "Could not find the shape for the heading."
        object_id = shape["objectId"]

        # Find the text style request for this object
        style_req = next(
            (
                r["updateTextStyle"]
                for r in requests
                if "updateTextStyle" in r
                and r["updateTextStyle"]["objectId"] == object_id
            ),
            None,
        )

        # Assert
        assert style_req is not None, "An updateTextStyle request must be generated."

        style = style_req["style"]
        fields = style_req["fields"]

        # 1. Assert Font Size (from H2)
        from markdowndeck.layout.constants import H2_FONT_SIZE

        assert "fontSize" in style, "Style dictionary must contain fontSize."
        assert (
            style["fontSize"]["magnitude"] == H2_FONT_SIZE
        ), f"Font size should be {H2_FONT_SIZE} for an H2."
        assert "fontSize" in fields, "Fields mask must include fontSize."

        # 2. Assert Color (from directive)
        assert (
            "foregroundColor" in style
        ), "Style dictionary must contain foregroundColor."
        color = style["foregroundColor"]["opaqueColor"]["rgbColor"]
        assert abs(color["blue"] - 1.0) < 0.01, "Text color should be blue."
        assert "foregroundColor" in fields, "Fields mask must include foregroundColor."

    def test_p_18_inline_and_block_styling_flow(self):
        """
        Test Case: INTEGRATION-P-18
        Validates that both standard inline markdown formatting (bold, italic) and
        block-level directives (color) are correctly parsed and applied.
        """
        # Arrange
        markdown = ":::section [color=blue]\nThis is **bold** and *italic*.\n:::"

        # Act
        result = markdown_to_requests(markdown)
        requests = result["slide_batches"][0]["requests"]

        # Find the text element's ID
        shape = _find_shape_by_text(requests, "This is bold and italic.")
        assert shape is not None, "Could not find the shape for the text element."
        object_id = shape["objectId"]

        # Find all style requests for this object
        style_requests = [
            r["updateTextStyle"]
            for r in requests
            if "updateTextStyle" in r and r["updateTextStyle"]["objectId"] == object_id
        ]

        assert (
            len(style_requests) >= 2
        ), "Expected at least two styling requests (one for block, one for inline)."

        # 1. Assert Block-Level Color (applied to the whole range)
        block_style_req = next(
            (r for r in style_requests if r["textRange"]["type"] == "ALL"), None
        )
        assert block_style_req is not None, "Block-level style request is missing."
        color = block_style_req["style"]["foregroundColor"]["opaqueColor"]["rgbColor"]
        assert abs(color["blue"] - 1.0) < 0.01, "Block color should be blue."

        # 2. Assert Inline Bold Formatting (applied to a fixed range)
        bold_req = next((r for r in style_requests if r["style"].get("bold")), None)
        assert bold_req is not None, "Bold style request is missing."
        assert bold_req["textRange"]["type"] == "FIXED_RANGE"
        assert bold_req["textRange"]["startIndex"] == 8
        assert bold_req["textRange"]["endIndex"] == 12

        # 3. Assert Inline Italic Formatting (applied to a fixed range)
        italic_req = next((r for r in style_requests if r["style"].get("italic")), None)
        assert italic_req is not None, "Italic style request is missing."
        assert italic_req["textRange"]["type"] == "FIXED_RANGE"
        assert italic_req["textRange"]["startIndex"] == 17
        assert italic_req["textRange"]["endIndex"] == 23
