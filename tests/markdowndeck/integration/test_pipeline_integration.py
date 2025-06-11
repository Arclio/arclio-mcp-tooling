"""
Integration tests for the full MarkdownDeck pipeline.
"""

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
    return next(
        (
            r
            for r in requests
            if "createShape" in r and r["createShape"]["objectId"] == object_id
        ),
        None,
    )


class TestPipelineIntegration:
    @pytest.fixture
    def parser(self) -> Parser:
        return Parser()

    @pytest.fixture
    def layout_manager(self) -> LayoutManager:
        return LayoutManager()

    @pytest.fixture
    def overflow_manager(self) -> OverflowManager:
        return OverflowManager()

    def test_integration_p_04(self):
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

    def test_integration_p_06_style_directive_flow(self):
        """Test Case: INTEGRATION-P-06 - End-to-end flow of styling directives."""
        markdown = "[color=#FF0000]\nRed Text"
        result = markdown_to_requests(markdown)
        requests = result["slide_batches"][0]["requests"]

        style_req = next((r for r in requests if "updateTextStyle" in r), None)
        assert style_req is not None, "An updateTextStyle request must be generated."

        color = style_req["updateTextStyle"]["style"]["foregroundColor"]["opaqueColor"][
            "rgbColor"
        ]
        assert abs(color["red"] - 1.0) < 1e-9

    def test_integration_p_07_flexible_body_area(self):
        """Test Case: INTEGRATION-P-07 - End-to-end validation of flexible body area."""
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

    def test_integration_p_08_gap_directive_flow(self):
        """Test Case: INTEGRATION-P-08 - End-to-end validation of the gap directive."""
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
            abs(actual_gap - 30.0) < 1.0
        ), "The gap between elements must be ~30 points."
