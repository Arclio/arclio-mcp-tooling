import pytest
from markdowndeck import markdown_to_requests
from markdowndeck.layout import LayoutManager
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

    @pytest.fixture(scope="class")
    def parser(self) -> Parser:
        return Parser()

    @pytest.fixture(scope="class")
    def layout_manager(self) -> LayoutManager:
        return LayoutManager()

    @pytest.fixture(scope="class")
    def overflow_manager(self) -> OverflowManager:
        return OverflowManager()

    def test_p_01_parser_to_layout_contract(self, parser: Parser):
        """
        Test Case: INTEGRATION-P-01
        Validates the Parser produces a valid "Unpositioned" slide.
        From: docs/markdowndeck/testing/TEST_CASES_INTEGRATION_PIPELINE.md
        """
        # Arrange
        markdown = "# Title\nContent"

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        # Assert: Validate the "Unpositioned" state
        assert slide.sections is not None
        assert len(slide.sections) > 0

        def check_unpositioned(sections):
            for section in sections:
                assert section.position is None, "Section position should be None"
                assert section.size is None, "Section size should be None"
                for child in section.children:
                    if not hasattr(child, "children"):  # Is an Element
                        assert child.position is None, "Element position should be None"
                        assert child.size is None, "Element size should be None"
                    else:  # Is a Section
                        check_unpositioned([child])

        check_unpositioned(slide.sections)

    def test_p_02_layout_to_overflow_contract_no_overflow(
        self,
        parser: Parser,
        layout_manager: LayoutManager,
        overflow_manager: OverflowManager,
    ):
        """
        Test Case: INTEGRATION-P-02
        Validates the "Positioned" to "Finalized" state transition for a slide that fits.
        From: docs/markdowndeck/testing/TEST_CASES_INTEGRATION_PIPELINE.md
        """
        # Arrange
        markdown = "# Title\nContent"
        unpositioned_slide = parser.parse(markdown).slides[0]

        # Act 1: Get "Positioned" state
        positioned_slide = layout_manager.calculate_positions(unpositioned_slide)

        # Assert 1: Validate "Positioned" state
        assert positioned_slide.sections[0].position is not None
        assert positioned_slide.sections[0].size is not None
        assert positioned_slide.sections[0].children[0].position is not None
        assert positioned_slide.sections[0].children[0].size is not None

        # Act 2: Get "Finalized" state
        finalized_slides = overflow_manager.process_slide(positioned_slide)

        # Assert 2: Validate "Finalized" state
        assert len(finalized_slides) == 1
        final_slide = finalized_slides[0]
        assert (
            final_slide.sections == []
        ), "Finalized slide must have empty sections list"
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
        Validates that an overflowing slide results in a list of multiple "Finalized" slides.
        From: docs/markdowndeck/testing/TEST_CASES_INTEGRATION_PIPELINE.md
        """
        # Arrange: Create markdown guaranteed to overflow
        long_content = "\n".join([f"* List Item {i}" for i in range(100)])
        markdown = f"# Overflow Test\n{long_content}"
        unpositioned_slide = parser.parse(markdown).slides[0]

        # Act
        positioned_slide = layout_manager.calculate_positions(unpositioned_slide)
        finalized_slides = overflow_manager.process_slide(positioned_slide)

        # Assert
        assert len(finalized_slides) > 1, "Overflow should result in multiple slides"

        # Verify all resulting slides are in the "Finalized" state
        for i, slide in enumerate(finalized_slides):
            assert slide.sections == [], f"Slide {i} must have empty sections list"
            assert (
                len(slide.renderable_elements) > 0
            ), f"Slide {i} must have renderable elements"
            if i > 0:
                assert (
                    "(continued)" in slide.title
                ), f"Continuation slide {i} must have a continuation title"

    def test_p_04_full_pipeline_via_markdown_to_requests(self):
        """Test Case: INTEGRATION-P-04 - Full pipeline via markdown_to_requests."""
        markdown = "# E2E Test\nContent."
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
        markdown = "[color=#FF0000]\nRed Text"
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
        markdown = "Body Only\n===\n# Title\nBody With Title"
        result = markdown_to_requests(markdown)

        batch1_reqs = result["slide_batches"][0]["requests"]
        batch2_reqs = result["slide_batches"][1]["requests"]

        shape1 = _find_shape_by_text(batch1_reqs, "Body Only")
        shape2 = _find_shape_by_text(batch2_reqs, "Body With Title")
        assert shape1 and shape2, "Could not find body shapes in both slides."

        shape1_y = shape1["elementProperties"]["transform"]["translateY"]
        shape2_y = shape2["elementProperties"]["transform"]["translateY"]

        assert (
            shape1_y < shape2_y
        ), "Body content should be positioned higher on a slide without a title."

    def test_p_07_gap_directive_flow(self):
        """Test Case: INTEGRATION-P-07 - End-to-end validation of the gap directive."""
        markdown = "[gap=30]\nFirst Line\n\nSecond Line"
        result = markdown_to_requests(markdown)
        requests = result["slide_batches"][0]["requests"]

        shape1 = _find_shape_by_text(requests, "First Line")
        shape2 = _find_shape_by_text(requests, "Second Line")
        assert shape1 and shape2, "Could not find text shapes."

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
