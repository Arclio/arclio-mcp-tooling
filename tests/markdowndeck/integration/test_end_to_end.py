from unittest.mock import MagicMock, patch

import pytest
from markdowndeck import create_presentation, get_themes, markdown_to_requests
from markdowndeck.api.api_generator import (
    ApiRequestGenerator,
)  # For type hinting if needed
from markdowndeck.api.request_builders.base_builder import BaseRequestBuilder
from markdowndeck.models import (
    Deck,
    ElementType,
    Slide,
    SlideLayout,
    TextElement,
)

MOCK_API_CLIENT_PATH = "markdowndeck.ApiClient"


class TestEndToEnd:
    """
    Integration tests for the markdown_to_requests function and mocked top-level functions.
    These tests verify the pipeline from Markdown input to API request structure.
    """

    # --- Tests for markdown_to_requests ---
    # (Existing tests for markdown_to_requests remain unchanged from your provided file)

    def test_markdown_to_requests_simple_slide(self):
        markdown = """
# Simple Title
This is a paragraph.
* Item 1
* Item 2

"""
        result = markdown_to_requests(markdown, title="Simple Test")

        assert result["title"] == "Simple Test"
        assert "slide_batches" in result
        assert len(result["slide_batches"]) == 1

        batch = result["slide_batches"][0]
        assert batch["presentationId"] == "PLACEHOLDER_PRESENTATION_ID"
        assert "requests" in batch
        requests = batch["requests"]
        assert len(requests) >= 4

        create_slide_req = next((r for r in requests if "createSlide" in r), None)
        assert create_slide_req is not None
        assert (
            create_slide_req["createSlide"]["slideLayoutReference"]["predefinedLayout"]
            is not None
        )

        title_shape_req = next(
            (r for r in requests if "createShape" in r),
            None,
        )
        assert title_shape_req is not None, "No shape requests found"

        insert_text_reqs = [r for r in requests if "insertText" in r]
        assert len(insert_text_reqs) > 0, "No insert text requests found"

        bullet_text_found = any(
            "Item 1" in req["insertText"]["text"]
            and "Item 2" in req["insertText"]["text"]
            for req in insert_text_reqs
        )
        assert bullet_text_found, "Bullet list items not found in inserted text"

        list_bullets_req = next(
            (r for r in requests if "createParagraphBullets" in r), None
        )
        assert list_bullets_req is not None, "No createParagraphBullets request found"

    def test_markdown_to_requests_complex_layout_slide(self):
        markdown = """
# Complex Slide
[background=#112233]
[width=1/2]
## Left Column
This is the left part.
```python
print("Hello Left")
````

---

[width=1/2]

## Right Column

This is the right part.

@@@
My Complex Footer
"""
        result = markdown_to_requests(markdown, title="Complex Test")
        assert result["title"] == "Complex Test"
        assert len(result["slide_batches"]) == 1
        requests = result["slide_batches"][0]["requests"]

        bg_req = next(
            (r for r in requests if "updatePageProperties" in r),
            None,
        )
        assert bg_req is not None
        assert (
            "pageBackgroundFill.solidFill.color.rgbColor"
            in bg_req["updatePageProperties"]["fields"]
        )
        assert bg_req["updatePageProperties"]["pageProperties"]["pageBackgroundFill"][
            "solidFill"
        ]["color"]["rgbColor"] == BaseRequestBuilder()._hex_to_rgb("#112233")

        all_texts = [r["insertText"]["text"] for r in requests if "insertText" in r]
        assert "My Complex Footer" in " ".join(all_texts)

        code_texts = [
            r["insertText"]["text"]
            for r in requests
            if "insertText" in r and 'print("Hello Left")' in r["insertText"]["text"]
        ]
        assert len(code_texts) > 0

        left_col_texts = [
            r["insertText"]["text"]
            for r in requests
            if "insertText" in r and "Left Column" in r["insertText"]["text"]
        ]
        assert len(left_col_texts) > 0
        right_col_texts = [
            r["insertText"]["text"]
            for r in requests
            if "insertText" in r and "Right Column" in r["insertText"]["text"]
        ]
        assert len(right_col_texts) > 0

    @pytest.fixture
    def deck_with_notes(self):
        test_slide = Slide(
            object_id="slide1",
            layout=SlideLayout.TITLE,
            notes="These are my notes",
            speaker_notes_object_id="fixed_notes_id_for_test",
            elements=[
                TextElement(
                    element_type=ElementType.TITLE,
                    text="Test Slide Title",
                    object_id="title1",
                )
            ],
        )
        return Deck(title="Test Deck with Notes", slides=[test_slide])

    def test_notes_included_in_api_requests(self, deck_with_notes):
        api_generator = ApiRequestGenerator()
        batches = api_generator.generate_batch_requests(
            deck_with_notes, "presentation_id"
        )
        assert len(batches) == 1
        all_requests = batches[0]["requests"]
        expected_notes_id = "fixed_notes_id_for_test"

        delete_notes_req = next(
            (
                r
                for r in all_requests
                if "deleteText" in r
                and r["deleteText"]["objectId"] == expected_notes_id
            ),
            None,
        )
        insert_notes_req = next(
            (
                r
                for r in all_requests
                if "insertText" in r
                and r["insertText"]["objectId"] == expected_notes_id
            ),
            None,
        )
        assert delete_notes_req is not None
        assert insert_notes_req is not None
        assert insert_notes_req["insertText"]["text"] == "These are my notes"

    # --- Fixed Skipped Tests ---
    @patch("markdowndeck.Parser")
    @patch("markdowndeck.LayoutManager")
    @patch(MOCK_API_CLIENT_PATH)  # Corrected patch path
    def test_create_presentation_orchestration(
        self,
        MockApiClient: MagicMock,
        MockLayoutManager: MagicMock,
        MockParser: MagicMock,
    ):
        mock_parser_instance = MockParser.return_value
        mock_deck = Deck(title="Test Deck", slides=[Slide(object_id="s1")])
        mock_parser_instance.parse.return_value = mock_deck

        mock_layout_instance = MockLayoutManager.return_value
        # Assume calculate_positions returns the deck with potentially modified slides
        mock_layout_instance.calculate_positions.side_effect = lambda slide: slide

        mock_api_client_instance = MockApiClient.return_value
        mock_api_client_instance.create_presentation_from_deck.return_value = {
            "presentationId": "pres_id_123",
            "presentationUrl": "http://slides.example.com/pres_id_123",
            "title": "Test Deck",
            "slideCount": 1,
        }

        markdown_input = "# Test Slide\nContent"
        title_input = "My Orchestrated Presentation"
        theme_id_input = "THEME_ID_XYZ"
        mock_credentials = MagicMock(name="MockCredentials")

        result = create_presentation(
            markdown=markdown_input,
            title=title_input,
            credentials=mock_credentials,
            theme_id=theme_id_input,
        )

        MockParser.assert_called_once_with()
        mock_parser_instance.parse.assert_called_once_with(
            markdown_input, title_input, theme_id_input
        )

        MockLayoutManager.assert_called_once_with()
        # Check if calculate_positions was called for each slide in the parsed deck
        assert mock_layout_instance.calculate_positions.call_count == len(
            mock_deck.slides
        )
        if mock_deck.slides:
            mock_layout_instance.calculate_positions.assert_any_call(
                mock_deck.slides[0]
            )

        MockApiClient.assert_called_once_with(
            mock_credentials, None
        )  # service is None by default
        # The deck passed to create_presentation_from_deck might have been modified by layout_manager
        # So we check the mock_deck that was returned by parser, assuming layout_manager works in place or returns modified
        # For simplicity, assume mock_deck (as returned by parser) is what's passed if calculate_positions returns identity
        # A more robust check would capture the argument passed to create_presentation_from_deck
        passed_deck_to_api = (
            mock_api_client_instance.create_presentation_from_deck.call_args[0][0]
        )
        assert passed_deck_to_api.title == "Test Deck"  # From mock_deck
        assert passed_deck_to_api.slides == mock_deck.slides

        assert result["presentationId"] == "pres_id_123"
        assert result["title"] == "Test Deck"

    @patch(MOCK_API_CLIENT_PATH)  # Corrected patch path
    def test_get_themes_calls_api_client(self, MockApiClient: MagicMock):
        mock_api_client_instance = MockApiClient.return_value
        expected_themes = [{"id": "THEME_1", "name": "Simple Light"}]
        mock_api_client_instance.get_available_themes.return_value = expected_themes
        mock_credentials = MagicMock(name="MockCredentials")

        themes = get_themes(credentials=mock_credentials)

        MockApiClient.assert_called_once_with(
            mock_credentials, None
        )  # service is None by default
        mock_api_client_instance.get_available_themes.assert_called_once_with()
        assert themes == expected_themes
