from unittest.mock import MagicMock, patch

from markdowndeck import create_presentation, markdown_to_requests
from markdowndeck.models import Deck, Slide

MOCK_API_CLIENT_PATH = "markdowndeck.ApiClient"


def _find_request_by_id(
    requests: list, object_id: str, request_type: str
) -> dict | None:
    """Finds a specific type of request targeting a given objectId."""
    key_map = {
        "createShape": "createShape",
        "updateTextStyle": "updateTextStyle",
        "updateShapeProperties": "updateShapeProperties",
        "updateParagraphStyle": "updateParagraphStyle",
        "insertText": "insertText",
        "updatePageProperties": "updatePageProperties",
    }
    request_key = key_map.get(request_type)
    if not request_key:
        return None

    return next(
        (
            r
            for r in requests
            if request_key in r and r[request_key].get("objectId") == object_id
        ),
        None,
    )


def _get_shape_id_by_text(requests: list, text_substring: str) -> str | None:
    """Finds the objectId of a shape containing the given text."""
    text_req = next(
        (
            r
            for r in requests
            if "insertText" in r and text_substring in r["insertText"]["text"]
        ),
        None,
    )
    return text_req["insertText"]["objectId"] if text_req else None


def _find_shape_properties_with_background(
    requests: list, object_id: str
) -> dict | None:
    """Finds the updateShapeProperties request that contains shapeBackgroundFill for the given objectId."""
    return next(
        (
            r
            for r in requests
            if "updateShapeProperties" in r
            and r["updateShapeProperties"].get("objectId") == object_id
            and "shapeBackgroundFill"
            in r["updateShapeProperties"].get("shapeProperties", {})
        ),
        None,
    )


def _find_shape_properties_with_content_alignment(
    requests: list, object_id: str
) -> dict | None:
    """Finds the updateShapeProperties request that contains contentAlignment for the given objectId."""
    return next(
        (
            r
            for r in requests
            if "updateShapeProperties" in r
            and r["updateShapeProperties"].get("objectId") == object_id
            and "contentAlignment"
            in r["updateShapeProperties"].get("shapeProperties", {})
        ),
        None,
    )


class TestEndToEndFunctions:
    """End-to-end tests for the library's main functions."""

    @patch(MOCK_API_CLIENT_PATH)
    def test_e2e_f_01_simple_presentation(self, mock_api_client_cls: MagicMock):
        """Test Case: E2E-F-01 - Validates successful creation of a simple presentation."""
        # Arrange
        mock_api_instance = mock_api_client_cls.return_value
        mock_api_instance.create_presentation_from_deck.return_value = {
            "presentationId": "pres_e2e_simple",
            "presentationUrl": "http://slides.example.com/e2e_simple",
        }
        markdown = "# Simple Title\n:::section\nThis is a test.\n:::"
        credentials = MagicMock()
        credentials.universe_domain = "googleapis.com"

        # Act
        result = create_presentation(
            markdown, title="Simple E2E Test", credentials=credentials
        )

        # Assert
        mock_api_client_cls.assert_called_once_with(credentials, None)
        mock_api_instance.create_presentation_from_deck.assert_called_once()
        passed_deck = mock_api_instance.create_presentation_from_deck.call_args[0][0]
        assert isinstance(passed_deck, Deck)
        assert passed_deck.title == "Simple E2E Test"
        assert len(passed_deck.slides) == 1
        assert result["presentationId"] == "pres_e2e_simple"

    @patch(MOCK_API_CLIENT_PATH)
    def test_e2e_f_02_overflow_handling(self, mock_api_client_cls: MagicMock):
        """Test Case: E2E-F-02 - Validates the pipeline correctly handles content that causes overflow."""
        # Arrange
        mock_api_instance = mock_api_client_cls.return_value
        long_content = "\n".join([f"* Item {i}" for i in range(100)])
        markdown = f"# Overflow Test\n:::section\n{long_content}\n:::"
        credentials = MagicMock()
        credentials.universe_domain = "googleapis.com"

        # Act
        create_presentation(
            markdown, title="Overflow E2E Test", credentials=credentials
        )

        # Assert
        mock_api_instance.create_presentation_from_deck.assert_called_once()
        passed_deck = mock_api_instance.create_presentation_from_deck.call_args[0][0]
        assert (
            len(passed_deck.slides) > 1
        ), "Overflow should have resulted in multiple slides."
        for slide in passed_deck.slides:
            assert isinstance(slide, Slide)
            assert (
                slide.root_section is None
            ), "Finalized slides must have root_section cleared"
            assert (
                slide.renderable_elements
            ), "Finalized slides must have renderable elements"

    def test_e2e_f_03_markdown_to_requests_blank_canvas(self):
        """Test Case: E2E-F-03 - Validates `markdown_to_requests` reflects the 'Blank Canvas First' architecture."""
        # Arrange
        markdown = "# Title\n:::section\nBody Text\n:::"

        # Act
        result = markdown_to_requests(markdown)

        # Assert
        requests = result["slide_batches"][0]["requests"]
        create_slide_req = next((r for r in requests if "createSlide" in r), None)
        assert create_slide_req is not None
        assert (
            create_slide_req["createSlide"]["slideLayoutReference"]["predefinedLayout"]
            == "BLANK"
        )

        create_shape_reqs = [r for r in requests if "createShape" in r]
        assert len(create_shape_reqs) >= 2
        assert all(
            req["createShape"]["shapeType"] == "TEXT_BOX" for req in create_shape_reqs
        )

    def test_e2e_f_04_directive_to_api_validation(self):
        """Test Case: E2E-F-04 - Validates that visual and layout directives are correctly translated into API requests."""
        # Arrange
        # FIXED: Wrapped column content in :::section blocks to be grammatically valid.
        markdown = """
# Title [fontsize=40]

:::row [background=#112233][padding=20][gap=30]
:::column
:::section
## Subtitle [color=#FF0000]
:::
:::
:::column [width=1/3][valign=bottom]
:::section
### Right Column [align=right]
:::
:::
:::
"""
        # Act
        result = markdown_to_requests(markdown)
        requests = result["slide_batches"][0]["requests"]

        # 1. Assert title font size
        title_id = _get_shape_id_by_text(requests, "Title")
        title_style_req = _find_request_by_id(requests, title_id, "updateTextStyle")
        assert (
            title_style_req["updateTextStyle"]["style"]["fontSize"]["magnitude"] == 40.0
        )

        # 2. Assert Subtitle/Right Column section properties (background, width, gap)
        subtitle_id = _get_shape_id_by_text(requests, "Subtitle")
        right_col_id = _get_shape_id_by_text(requests, "Right Column")

        # Background should be on the shape containing the subtitle, inherited from the row.
        subtitle_shape_props = _find_shape_properties_with_background(
            requests, subtitle_id
        )
        assert (
            subtitle_shape_props is not None
        ), "Background directive from row was not applied to child element."
        bg_color = subtitle_shape_props["updateShapeProperties"]["shapeProperties"][
            "shapeBackgroundFill"
        ]["solidFill"]["color"]["rgbColor"]
        assert abs(bg_color["red"] - (0x11 / 255.0)) < 0.01

        # Color on subtitle text
        subtitle_text_style = _find_request_by_id(
            requests, subtitle_id, "updateTextStyle"
        )
        subtitle_color = subtitle_text_style["updateTextStyle"]["style"][
            "foregroundColor"
        ]["opaqueColor"]["rgbColor"]
        assert abs(subtitle_color["red"] - 1.0) < 0.01

        # Width on right column shape
        right_col_create_req = _find_request_by_id(
            requests, right_col_id, "createShape"
        )
        assert (
            abs(
                right_col_create_req["createShape"]["elementProperties"]["size"][
                    "width"
                ]["magnitude"]
                - (720.0 / 3.0)
            )
            < 30.0
        )

        # Valign and Align on right column
        right_col_shape_props = _find_shape_properties_with_content_alignment(
            requests, right_col_id
        )
        assert (
            right_col_shape_props["updateShapeProperties"]["shapeProperties"][
                "contentAlignment"
            ]
            == "BOTTOM"
        )
        right_col_para_style = _find_request_by_id(
            requests, right_col_id, "updateParagraphStyle"
        )
        assert (
            right_col_para_style["updateParagraphStyle"]["style"]["alignment"] == "END"
        )

        # Gap check between subtitle and right column is complex due to row layout.
        # This is better tested in an integration test focused solely on gap.
