from unittest.mock import MagicMock, patch

from markdowndeck import create_presentation, markdown_to_requests
from markdowndeck.models import Deck, Slide

MOCK_API_CLIENT_PATH = "markdowndeck.ApiClient"


class TestEndToEndFunctions:
    """End-to-end tests for the library's main functions."""

    @patch(MOCK_API_CLIENT_PATH)
    def test_e2e_f_01_simple_presentation(self, mock_api_client_cls: MagicMock):
        """
        Test Case: E2E-F-01
        Validates the successful creation of a simple presentation.
        From: docs/markdowndeck/testing/TEST_CASES_E2E.md
        """
        # Arrange
        mock_api_client_instance = mock_api_client_cls.return_value
        mock_api_client_instance.create_presentation_from_deck.return_value = {
            "presentationId": "pres_e2e_simple",
            "presentationUrl": "http://slides.example.com/e2e_simple",
        }
        markdown = "# Simple Title\nThis is a test."
        credentials = MagicMock()

        # Act
        result = create_presentation(
            markdown, title="Simple E2E Test", credentials=credentials
        )

        # Assert
        mock_api_client_cls.assert_called_once_with(credentials, None)
        mock_api_client_instance.create_presentation_from_deck.assert_called_once()

        passed_deck = mock_api_client_instance.create_presentation_from_deck.call_args[
            0
        ][0]
        assert isinstance(passed_deck, Deck)
        assert passed_deck.title == "Simple E2E Test"
        assert len(passed_deck.slides) == 1
        assert result["presentationId"] == "pres_e2e_simple"

    @patch(MOCK_API_CLIENT_PATH)
    def test_e2e_f_02_overflow_handling(self, mock_api_client_cls: MagicMock):
        """
        Test Case: E2E-F-02
        Validates the pipeline correctly handles content that causes overflow.
        From: docs/markdowndeck/testing/TEST_CASES_E2E.md
        """
        # Arrange
        mock_api_client_instance = mock_api_client_cls.return_value
        mock_api_client_instance.create_presentation_from_deck.return_value = {}

        long_content = "\n".join([f"* Item {i}" for i in range(100)])
        markdown = f"# Overflow Test\n{long_content}"
        credentials = MagicMock()

        # Act
        create_presentation(
            markdown, title="Overflow E2E Test", credentials=credentials
        )

        # Assert
        mock_api_client_instance.create_presentation_from_deck.assert_called_once()
        passed_deck = mock_api_client_instance.create_presentation_from_deck.call_args[
            0
        ][0]

        assert (
            len(passed_deck.slides) > 1
        ), "Overflow should have resulted in multiple slides."
        for slide in passed_deck.slides:
            assert isinstance(slide, Slide)
            assert not slide.sections, "Finalized slides must have empty sections list"
            assert (
                slide.renderable_elements
            ), "Finalized slides must have renderable elements"

    def test_e2e_f_03_markdown_to_requests_blank_canvas(self):
        """
        Test Case: E2E-F-03
        Validates `markdown_to_requests` reflects the "Blank Canvas First" architecture.
        From: docs/markdowndeck/testing/TEST_CASES_E2E.md
        """
        # Arrange
        markdown = "# Title\nBody Text"

        # Act
        result = markdown_to_requests(markdown)

        # Assert
        requests = result["slide_batches"][0]["requests"]
        create_slide_req = next((r for r in requests if "createSlide" in r), None)
        assert create_slide_req is not None, "A createSlide request must exist."
        assert (
            create_slide_req["createSlide"]["slideLayoutReference"]["predefinedLayout"]
            == "BLANK"
        ), "All slides must be created with a BLANK layout."

        create_shape_reqs = [r for r in requests if "createShape" in r]
        assert len(create_shape_reqs) >= 2, "Shapes must be created for title and body."
        assert all(
            req["createShape"]["shapeType"] == "TEXT_BOX" for req in create_shape_reqs
        ), "All text elements should be created as TEXT_BOX shapes."

    def test_e2e_f_04_directive_to_api_validation(self):
        """
        Test Case: E2E-F-04
        Validates that visual and layout directives are correctly translated into API requests.
        From: docs/markdowndeck/testing/TEST_CASES_E2E.md
        """
        # Arrange
        markdown = """
[background=#112233][padding=20]
# Title [fontsize=40]
[gap=30]
## Subtitle [color=#FF0000]
***
[width=1/3]
### Right Column [align=right][valign=bottom]
"""
        # Act
        result = markdown_to_requests(markdown)
        requests = result["slide_batches"][0]["requests"]

        # 1. Assert slide background color
        slide_bg_req = next((r for r in requests if "updatePageProperties" in r), None)
        assert slide_bg_req is not None
        bg_color = slide_bg_req["updatePageProperties"]["pageProperties"][
            "pageBackgroundFill"
        ]["solidFill"]["color"]["rgbColor"]
        assert abs(bg_color["red"] - (0x11 / 255.0)) < 0.01

        # 2. Assert title font size
        title_shape = next(
            r
            for r in requests
            if "insertText" in r and r["insertText"]["text"] == "Title"
        )
        title_style_req = next(
            r
            for r in requests
            if "updateTextStyle" in r
            and r["updateTextStyle"]["objectId"]
            == title_shape["insertText"]["objectId"]
            and "fontSize" in r["updateTextStyle"]["style"]
        )
        assert (
            title_style_req["updateTextStyle"]["style"]["fontSize"]["magnitude"] == 40.0
        )
        assert "fontSize" in title_style_req["updateTextStyle"]["fields"]

        # 3. Assert subtitle color
        subtitle_shape = next(
            r
            for r in requests
            if "insertText" in r and r["insertText"]["text"] == "Subtitle"
        )
        subtitle_style_req = next(
            r
            for r in requests
            if "updateTextStyle" in r
            and r["updateTextStyle"]["objectId"]
            == subtitle_shape["insertText"]["objectId"]
            and "foregroundColor" in r["updateTextStyle"]["style"]
        )
        subtitle_color = subtitle_style_req["updateTextStyle"]["style"][
            "foregroundColor"
        ]["opaqueColor"]["rgbColor"]
        assert abs(subtitle_color["red"] - 1.0) < 0.01
        assert "foregroundColor" in subtitle_style_req["updateTextStyle"]["fields"]

        # 4. Assert layout directives (width, gap, align, valign)
        subtitle_create_req = next(
            r
            for r in requests
            if "createShape" in r
            and r["createShape"]["objectId"] == subtitle_shape["insertText"]["objectId"]
        )
        right_col_shape = next(
            r
            for r in requests
            if "insertText" in r and r["insertText"]["text"] == "Right Column"
        )
        right_col_create_req = next(
            r
            for r in requests
            if "createShape" in r
            and r["createShape"]["objectId"]
            == right_col_shape["insertText"]["objectId"]
        )

        # Gap check
        subtitle_bottom = (
            subtitle_create_req["createShape"]["elementProperties"]["transform"][
                "translateY"
            ]
            + subtitle_create_req["createShape"]["elementProperties"]["size"]["height"][
                "magnitude"
            ]
        )
        right_col_top = right_col_create_req["createShape"]["elementProperties"][
            "transform"
        ]["translateY"]
        assert (
            abs((right_col_top - subtitle_bottom) - 30.0) < 5.0
        ), "Gap directive not applied correctly"

        # Width check
        assert (
            abs(
                right_col_create_req["createShape"]["elementProperties"]["size"][
                    "width"
                ]["magnitude"]
                - (720.0 / 3.0)
            )
            < 5.0
        ), "Width directive not applied correctly"

        # Align check
        align_req = next(
            r
            for r in requests
            if "updateParagraphStyle" in r
            and r["updateParagraphStyle"]["objectId"]
            == right_col_shape["insertText"]["objectId"]
        )
        assert align_req["updateParagraphStyle"]["style"]["alignment"] == "END"
        assert "alignment" in align_req["updateParagraphStyle"]["fields"]

        # Valign check
        valign_req = next(
            r
            for r in requests
            if "updateShapeProperties" in r
            and r["updateShapeProperties"]["objectId"]
            == right_col_shape["insertText"]["objectId"]
        )
        assert (
            valign_req["updateShapeProperties"]["shapeProperties"]["contentAlignment"]
            == "BOTTOM"
        )
        assert "contentAlignment" in valign_req["updateShapeProperties"]["fields"]
