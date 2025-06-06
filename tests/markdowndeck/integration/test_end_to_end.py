from unittest.mock import MagicMock, patch

import pytest
from markdowndeck import create_presentation, get_themes, markdown_to_requests
from markdowndeck.api.api_generator import ApiRequestGenerator
from markdowndeck.models import (
    Deck,
    ElementType,
    Slide,
    SlideLayout,
    TextElement,
)

# Correct paths for mocking components in the markdowndeck module namespace
MOCK_API_CLIENT_PATH = "markdowndeck.ApiClient"
MOCK_PARSER_PATH = "markdowndeck.Parser"
MOCK_LAYOUT_MANAGER_PATH = "markdowndeck.LayoutManager"
MOCK_OVERFLOW_MANAGER_PATH = "markdowndeck.OverflowManager"
MOCK_GET_THEMES_API_CLIENT_PATH = "markdowndeck.ApiClient"


class TestEndToEnd:
    """
    Integration tests for the markdown_to_requests function and mocked top-level functions.
    These tests verify the pipeline from Markdown input to API request structure.
    """

    # --- Tests for markdown_to_requests ---
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
        assert len(requests) >= 4  # createSlide, text, bullets, etc.

        create_slide_req = next((r for r in requests if "createSlide" in r), None)
        assert create_slide_req is not None
        assert create_slide_req["createSlide"]["slideLayoutReference"]["predefinedLayout"] is not None

        insert_text_reqs = [r for r in requests if "insertText" in r]
        assert len(insert_text_reqs) > 0, "No insert text requests found"

        # Check for title and list items in the inserted text
        all_text = " ".join(req["insertText"]["text"] for req in insert_text_reqs)
        assert "Simple Title" in all_text
        assert "Item 1" in all_text
        assert "Item 2" in all_text

        list_bullets_req = next((r for r in requests if "createParagraphBullets" in r), None)
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
```

---

[width=1/2]

## Right Column
This is the right part.

@@@
My Complex Footer
"""
        from markdowndeck.api.request_builders.base_builder import BaseRequestBuilder

        result = markdown_to_requests(markdown, title="Complex Test")
        assert result["title"] == "Complex Test"
        assert len(result["slide_batches"]) == 1
        requests = result["slide_batches"][0]["requests"]

        bg_req = next(
            (r for r in requests if "updatePageProperties" in r),
            None,
        )
        assert bg_req is not None
        assert "pageBackgroundFill.solidFill.color" in bg_req["updatePageProperties"]["fields"]
        assert bg_req["updatePageProperties"]["pageProperties"]["pageBackgroundFill"]["solidFill"]["color"][
            "rgbColor"
        ] == BaseRequestBuilder()._hex_to_rgb("#112233")

        all_texts = " ".join([r["insertText"]["text"] for r in requests if "insertText" in r])
        assert "My Complex Footer" in all_texts

        code_texts = [
            r["insertText"]["text"] for r in requests if "insertText" in r and 'print("Hello Left")' in r["insertText"]["text"]
        ]
        assert len(code_texts) > 0

        left_col_texts = [
            r["insertText"]["text"] for r in requests if "insertText" in r and "Left Column" in r["insertText"]["text"]
        ]
        assert len(left_col_texts) > 0
        right_col_texts = [
            r["insertText"]["text"] for r in requests if "insertText" in r and "Right Column" in r["insertText"]["text"]
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
        batches = api_generator.generate_batch_requests(deck_with_notes, "presentation_id")
        assert len(batches) == 1
        all_requests = batches[0]["requests"]
        expected_notes_id = "fixed_notes_id_for_test"

        delete_notes_req = next(
            (r for r in all_requests if "deleteText" in r and r["deleteText"]["objectId"] == expected_notes_id),
            None,
        )
        insert_notes_req = next(
            (r for r in all_requests if "insertText" in r and r["insertText"]["objectId"] == expected_notes_id),
            None,
        )
        assert delete_notes_req is not None, "deleteText request for notes shape not found."
        assert insert_notes_req is not None, "insertText request for notes shape not found."
        assert insert_notes_req["insertText"]["text"] == "These are my notes"

    # --- Tests for create_presentation and get_themes ---
    @patch(MOCK_API_CLIENT_PATH)
    @patch(MOCK_OVERFLOW_MANAGER_PATH)
    @patch(MOCK_LAYOUT_MANAGER_PATH)
    @patch(MOCK_PARSER_PATH)
    def test_create_presentation_orchestration(
        self,
        mock_parser: MagicMock,
        mock_layout_manager: MagicMock,
        mock_overflow_manager: MagicMock,
        mock_api_client: MagicMock,
    ):
        # 1. Setup Mocks
        mock_parser_instance = mock_parser.return_value
        # The parsed deck has one slide, which will be passed to layout/overflow
        mock_slide = Slide(object_id="s1")
        mock_deck = Deck(title="Test Deck", slides=[mock_slide])
        mock_parser_instance.parse.return_value = mock_deck

        # LayoutManager simply returns the slide it was given
        mock_layout_instance = mock_layout_manager.return_value
        mock_layout_instance.calculate_positions.side_effect = lambda slide: slide

        # OverflowManager returns a list containing the slide it was given
        mock_overflow_instance = mock_overflow_manager.return_value
        mock_overflow_instance.process_slide.side_effect = lambda slide: [slide]

        # ApiClient returns the final result
        mock_api_client_instance = mock_api_client.return_value
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

        # 2. Call the function
        result = create_presentation(
            markdown=markdown_input,
            title=title_input,
            credentials=mock_credentials,
            theme_id=theme_id_input,
        )

        # 3. Assert the orchestration flow
        mock_parser.assert_called_once_with()
        mock_parser_instance.parse.assert_called_once_with(markdown_input, title_input, theme_id_input)

        mock_layout_manager.assert_called_once_with()
        mock_layout_instance.calculate_positions.assert_called_once_with(mock_slide)

        mock_overflow_manager.assert_called_once_with()
        mock_overflow_instance.process_slide.assert_called_once_with(mock_slide)

        mock_api_client.assert_called_once_with(mock_credentials, None)
        passed_deck_to_api = mock_api_client_instance.create_presentation_from_deck.call_args[0][0]
        assert passed_deck_to_api.title == "Test Deck"
        assert passed_deck_to_api.slides == [mock_slide]

        # 4. Assert the final result
        assert result["presentationId"] == "pres_id_123"
        assert result["title"] == "Test Deck"

    @patch(MOCK_GET_THEMES_API_CLIENT_PATH)
    def test_get_themes_calls_api_client(self, mock_api_client: MagicMock):
        mock_api_client_instance = mock_api_client.return_value
        expected_themes = [{"id": "THEME_1", "name": "Simple Light"}]
        mock_api_client_instance.get_available_themes.return_value = expected_themes
        mock_credentials = MagicMock(name="MockCredentials")

        themes = get_themes(credentials=mock_credentials)

        mock_api_client.assert_called_once_with(mock_credentials, None)
        mock_api_client_instance.get_available_themes.assert_called_once_with()
        assert themes == expected_themes
