from copy import deepcopy
from unittest.mock import MagicMock

import pytest
from markdowndeck.api.api_generator import ApiRequestGenerator
from markdowndeck.models import (
    CodeElement,
    Deck,
    ElementType,
    ImageElement,
    ListElement,
    ListItem,
    Slide,
    SlideLayout,
    TableElement,
    TextElement,
)


@pytest.fixture
def sample_slide() -> Slide:
    """Creates a sample slide for orchestration testing."""
    return Slide(
        object_id="test_slide_001",
        elements=[],
        layout=SlideLayout.BLANK,
        title="Sample Slide",
        placeholder_mappings={},
    )


class TestApiRequestGenerator:
    """Unit tests for the ApiRequestGenerator's orchestration role."""

    @pytest.fixture
    def generator(self) -> ApiRequestGenerator:
        return ApiRequestGenerator()

    def test_generate_slide_batch_orchestration(self, generator: ApiRequestGenerator, sample_slide: Slide):
        """Test that generate_slide_batch calls appropriate builder methods."""
        sample_slide.elements = [
            TextElement(element_type=ElementType.TITLE, text="Title", object_id="el_title"),
            TextElement(element_type=ElementType.TEXT, text="Body", object_id="el_body"),
            ImageElement(element_type=ElementType.IMAGE, url="test.png", object_id="el_img"),
        ]
        sample_slide.background = {"type": "color", "value": "#FFFFFF"}
        sample_slide.notes = "Test notes"
        sample_slide.speaker_notes_object_id = "notes_obj_id"

        generator.slide_builder.create_slide_request = MagicMock(return_value={"mock_slide_req": True})
        generator.slide_builder.create_background_request = MagicMock(return_value={"mock_bg_req": True})
        generator.slide_builder.create_notes_request = MagicMock(return_value=[{"mock_notes_req": True}])

        generator.text_builder.generate_text_element_requests = MagicMock(return_value=[{"mock_text_el_req": True}])
        generator.media_builder.generate_image_element_requests = MagicMock(return_value=[{"mock_img_el_req": True}])

        batch = generator.generate_slide_batch(sample_slide, "pres_id")

        assert batch["presentationId"] == "pres_id"
        generator.slide_builder.create_slide_request.assert_called_once_with(sample_slide)
        generator.slide_builder.create_background_request.assert_called_once_with(sample_slide)
        generator.slide_builder.create_notes_request.assert_called_once_with(sample_slide)

        assert generator.text_builder.generate_text_element_requests.call_count == 2
        generator.media_builder.generate_image_element_requests.assert_called_once_with(
            sample_slide.elements[2],
            sample_slide.object_id,
        )

        assert {"mock_slide_req": True} in batch["requests"]
        assert {"mock_bg_req": True} in batch["requests"]
        assert {"mock_notes_req": True} in batch["requests"]
        assert batch["requests"].count({"mock_text_el_req": True}) == 2
        assert {"mock_img_el_req": True} in batch["requests"]

    def test_subheading_and_list_combination(self, generator: ApiRequestGenerator, sample_slide: Slide):
        """Test that a subheading followed by a related list are combined."""
        subheading = TextElement(
            element_type=ElementType.TEXT,
            text="My List Title",
            object_id="el_subheading",
            related_to_next=True,
        )
        list_el = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[ListItem(text="Item 1")],
            object_id="el_list",
            related_to_prev=True,
        )
        # Simulate a themed layout where TEXT maps to a placeholder
        sample_slide.placeholder_mappings = {ElementType.TEXT: "body_placeholder_id"}
        sample_slide.elements = [subheading, list_el]

        # Mock the list builder
        generator.list_builder.generate_bullet_list_element_requests = MagicMock(return_value=[{"mock_combined_req": True}])
        generator.text_builder.generate_text_element_requests = MagicMock()

        generator.generate_slide_batch(sample_slide, "pres_id")

        # The subheading should NOT be processed by the text builder
        generator.text_builder.generate_text_element_requests.assert_not_called()

        # The list builder should be called with the subheading data
        generator.list_builder.generate_bullet_list_element_requests.assert_called_once()
        call_args = generator.list_builder.generate_bullet_list_element_requests.call_args
        assert call_args.args[0] == list_el  # The list element
        subheading_data = call_args.kwargs.get("subheading_data")
        assert subheading_data is not None
        assert subheading_data["text"] == "My List Title"
        assert subheading_data["placeholder_id"] == "body_placeholder_id"

    def test_generate_element_requests_dispatch(self, generator: ApiRequestGenerator, sample_slide: Slide):
        """Test that _generate_element_requests dispatches to the correct builders."""
        elements_to_test = [
            TextElement(element_type=ElementType.TITLE, text="T", object_id="id_title"),
            TextElement(element_type=ElementType.TEXT, text="P", object_id="id_text"),
            ListElement(
                element_type=ElementType.BULLET_LIST,
                items=[ListItem(text="L")],
                object_id="id_list",
            ),
            ListElement(
                element_type=ElementType.ORDERED_LIST,
                items=[ListItem(text="O")],
                object_id="id_ordered_list",
            ),
            ImageElement(element_type=ElementType.IMAGE, url="i.png", object_id="id_img"),
            CodeElement(element_type=ElementType.CODE, code="c", object_id="id_code"),
            TableElement(element_type=ElementType.TABLE, headers=["H"], object_id="id_table"),
            TextElement(element_type=ElementType.QUOTE, text="Q", object_id="id_quote"),
            TextElement(element_type=ElementType.FOOTER, text="F", object_id="id_footer"),
        ]

        generator.text_builder.generate_text_element_requests = MagicMock()
        generator.list_builder.generate_bullet_list_element_requests = MagicMock()
        generator.list_builder.generate_list_element_requests = MagicMock()
        generator.media_builder.generate_image_element_requests = MagicMock()
        generator.code_builder.generate_code_element_requests = MagicMock()
        generator.table_builder.generate_table_element_requests = MagicMock()

        for el in elements_to_test:
            generator._generate_element_requests(el, sample_slide.object_id, sample_slide.placeholder_mappings)

        assert generator.text_builder.generate_text_element_requests.call_count == 4
        generator.list_builder.generate_bullet_list_element_requests.assert_called_once()
        generator.list_builder.generate_list_element_requests.assert_called_once()
        generator.media_builder.generate_image_element_requests.assert_called_once()
        generator.code_builder.generate_code_element_requests.assert_called_once()
        generator.table_builder.generate_table_element_requests.assert_called_once()

    def test_generate_batch_requests_empty_deck(self, generator: ApiRequestGenerator):
        deck = Deck(slides=[])
        batches = generator.generate_batch_requests(deck, "pid")
        assert len(batches) == 0

    def test_generate_batch_requests_multiple_slides(self, generator: ApiRequestGenerator, sample_slide: Slide):
        slide1 = deepcopy(sample_slide)
        slide1.object_id = "s1"
        slide2 = deepcopy(sample_slide)
        slide2.object_id = "s2"
        deck = Deck(slides=[slide1, slide2])

        generator.generate_slide_batch = MagicMock(
            side_effect=lambda s, p_id: {
                "presentationId": p_id,
                "requests": [{"createSlide": {"objectId": s.object_id}}],
            }
        )

        batches = generator.generate_batch_requests(deck, "pid")

        assert len(batches) == 2
        generator.generate_slide_batch.assert_any_call(slide1, "pid")
        generator.generate_slide_batch.assert_any_call(slide2, "pid")
        assert batches[0]["requests"][0]["createSlide"]["objectId"] == "s1"
        assert batches[1]["requests"][0]["createSlide"]["objectId"] == "s2"
