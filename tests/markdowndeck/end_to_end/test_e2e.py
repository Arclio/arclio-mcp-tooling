"""
E2E tests for the markdowndeck library's public functions.

These tests validate the complete pipeline from markdown input to final output,
ensuring all components work together as specified. They use mocks for external
API calls to focus on the integrity of the generation process.
"""

from unittest.mock import MagicMock, patch

from markdowndeck import create_presentation, markdown_to_requests
from markdowndeck.models import Deck, Slide

MOCK_API_CLIENT_PATH = "markdowndeck.ApiClient"


class TestEndToEndFunctions:
    """End-to-end tests for the library's main functions."""

    @patch(MOCK_API_CLIENT_PATH)
    def test_e2e_f_01(self, mock_api_client_cls: MagicMock):
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

        # Verify the Deck object passed to the API client
        passed_deck = mock_api_client_instance.create_presentation_from_deck.call_args[
            0
        ][0]
        assert isinstance(passed_deck, Deck)
        assert passed_deck.title == "Simple E2E Test"
        assert len(passed_deck.slides) == 1

        assert result["presentationId"] == "pres_e2e_simple"

    @patch(MOCK_API_CLIENT_PATH)
    def test_e2e_f_02(self, mock_api_client_cls: MagicMock):
        """
        Test Case: E2E-F-02
        Validates the pipeline correctly handles content that causes overflow.
        From: docs/markdowndeck/testing/TEST_CASES_E2E.md
        """
        # Arrange
        mock_api_client_instance = mock_api_client_cls.return_value
        mock_api_client_instance.create_presentation_from_deck.return_value = {}

        # This content is guaranteed to overflow
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

        # The key assertion is that the overflow manager was triggered and produced multiple slides
        assert (
            len(passed_deck.slides) > 1
        ), "Overflow should have resulted in multiple slides."

        # Verify all slides in the final deck are finalized
        for slide in passed_deck.slides:
            assert isinstance(slide, Slide)
            assert slide.sections == []
            assert len(slide.renderable_elements) > 0

    def test_e2e_f_03(self):
        """
        Test Case: E2E-F-03
        Validates the `markdown_to_requests` function for complex layouts.
        From: docs/markdowndeck/testing/TEST_CASES_E2E.md
        """
        # Arrange
        markdown = """# Complex Layout
[width=1/2]
Left content
***
[width=1/2]
Right content
"""

        # Act
        result = markdown_to_requests(markdown, title="Request Gen Test")

        # Assert
        assert result["title"] == "Request Gen Test"
        assert len(result["slide_batches"]) == 1

        requests = result["slide_batches"][0]["requests"]
        assert len(requests) > 2, "Should have requests for slide and content."

        # Find the shapes created for the two columns of text
        create_shape_reqs = [r["createShape"] for r in requests if "createShape" in r]
        text_shapes = [r for r in create_shape_reqs if r.get("shapeType") == "TEXT_BOX"]

        # There will be TEXT_BOX shapes for Left Text and Right Text
        # (Title is handled via slide placeholder, not TEXT_BOX)
        assert len(text_shapes) >= 2, "Should create TEXT_BOX shapes for both columns."

        # Verify title is handled via insertText to slide placeholder
        insert_text_reqs = [r["insertText"] for r in requests if "insertText" in r]
        title_inserts = [
            r for r in insert_text_reqs if "title" in r.get("objectId", "")
        ]
        assert (
            len(title_inserts) >= 1
        ), "Should insert title text into slide placeholder."

        # Verify columns are positioned horizontally apart (a simple proxy for layout)
        # Note: This is a simplified check. A more robust check would analyze transforms precisely.
        positions = [
            s["elementProperties"]["transform"]["translateX"]
            for s in text_shapes
            if "transform" in s["elementProperties"]
        ]
        # Sort positions to reliably find left-most vs right-most
        sorted(positions)
        # Check that there's a clear difference in horizontal position, indicating columns
        # This checks that not all text boxes are just stacked vertically at the same X coordinate.
        assert (
            max(positions) - min(positions) > 100
        ), "Text boxes for columns should have different X positions."
