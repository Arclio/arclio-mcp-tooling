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
    # TextFormat and TextFormatType are not directly used in orchestration tests here
)


@pytest.fixture
def sample_slide() -> Slide:
    """Creates a sample slide for orchestration testing."""
    # Keep this simple, as the details of element generation are tested in builder tests
    return Slide(
        object_id="test_slide_001",
        elements=[],  # Elements will be added by specific orchestration tests
        layout=SlideLayout.BLANK,
        title="Sample Slide",
        placeholder_mappings={},
    )


class TestApiRequestGenerator:
    """Unit tests for the ApiRequestGenerator's orchestration role."""

    @pytest.fixture
    def generator(self) -> ApiRequestGenerator:
        return ApiRequestGenerator()

    def test_generate_slide_batch_orchestration(
        self, generator: ApiRequestGenerator, sample_slide: Slide
    ):
        """Test that generate_slide_batch calls appropriate builder methods."""
        # Populate sample_slide with a few representative elements for dispatch testing
        sample_slide.elements = [
            TextElement(element_type=ElementType.TITLE, text="Title", object_id="el_title"),
            TextElement(element_type=ElementType.TEXT, text="Body", object_id="el_body"),
            ImageElement(element_type=ElementType.IMAGE, url="test.png", object_id="el_img"),
        ]
        sample_slide.background = {"type": "color", "value": "#FFFFFF"}
        sample_slide.notes = "Test notes"
        sample_slide.speaker_notes_object_id = "notes_obj_id"

        # Mock the builder methods directly on the generator's instances
        generator.slide_builder.create_slide_request = MagicMock(
            return_value={"mock_slide_req": True}
        )
        generator.slide_builder.create_background_request = MagicMock(
            return_value={"mock_bg_req": True}
        )
        generator.slide_builder.create_notes_request = MagicMock(
            return_value=[{"mock_notes_req": True}]
        )  # Assuming it returns a list

        generator.text_builder.generate_text_element_requests = MagicMock(
            return_value=[{"mock_text_el_req": True}]
        )
        generator.media_builder.generate_image_element_requests = MagicMock(
            return_value=[{"mock_img_el_req": True}]
        )
        # Mock other builders if their elements were added to sample_slide.elements
        generator.list_builder.generate_bullet_list_element_requests = MagicMock()
        generator.list_builder.generate_list_element_requests = MagicMock()
        generator.table_builder.generate_table_element_requests = MagicMock()
        generator.code_builder.generate_code_element_requests = MagicMock()

        batch = generator.generate_slide_batch(sample_slide, "pres_id")

        assert batch["presentationId"] == "pres_id"
        generator.slide_builder.create_slide_request.assert_called_once_with(sample_slide)
        generator.slide_builder.create_background_request.assert_called_once_with(sample_slide)
        generator.slide_builder.create_notes_request.assert_called_once_with(sample_slide)

        # Check calls to element builders (via _generate_element_requests)
        assert generator.text_builder.generate_text_element_requests.call_count == 2
        generator.text_builder.generate_text_element_requests.assert_any_call(
            sample_slide.elements[0],  # Title element
            sample_slide.object_id,
            sample_slide.placeholder_mappings,
        )
        generator.text_builder.generate_text_element_requests.assert_any_call(
            sample_slide.elements[1],  # Text element
            sample_slide.object_id,
            sample_slide.placeholder_mappings,
        )
        generator.media_builder.generate_image_element_requests.assert_called_once_with(
            sample_slide.elements[2],
            sample_slide.object_id,  # No placeholders for image
        )

        # Check request list content (simplified)
        assert {"mock_slide_req": True} in batch["requests"]
        assert {"mock_bg_req": True} in batch["requests"]
        assert {"mock_notes_req": True} in batch["requests"]
        assert batch["requests"].count({"mock_text_el_req": True}) == 2
        assert {"mock_img_el_req": True} in batch["requests"]

    def test_generate_element_requests_dispatch(
        self, generator: ApiRequestGenerator, sample_slide: Slide
    ):
        """Test that _generate_element_requests dispatches to the correct builders."""
        title_el = TextElement(element_type=ElementType.TITLE, text="T", object_id="id_title")
        text_el = TextElement(element_type=ElementType.TEXT, text="P", object_id="id_text")
        list_el = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[ListItem(text="L")],
            object_id="id_list",
        )
        img_el = ImageElement(element_type=ElementType.IMAGE, url="i.png", object_id="id_img")
        code_el = CodeElement(element_type=ElementType.CODE, code="c", object_id="id_code")
        table_el = TableElement(element_type=ElementType.TABLE, headers=["H"], object_id="id_table")
        quote_el = TextElement(element_type=ElementType.QUOTE, text="Q", object_id="id_quote")
        footer_el = TextElement(element_type=ElementType.FOOTER, text="F", object_id="id_footer")
        ordered_list_el = ListElement(
            element_type=ElementType.ORDERED_LIST,
            items=[ListItem(text="O")],
            object_id="id_ordered_list",
        )

        elements_to_test = [
            title_el,
            text_el,
            list_el,
            ordered_list_el,
            img_el,
            code_el,
            table_el,
            quote_el,
            footer_el,
        ]

        # Mock all builder methods that _generate_element_requests calls
        generator.text_builder.generate_text_element_requests = MagicMock(
            return_value=[{"req_text": True}]
        )
        generator.list_builder.generate_bullet_list_element_requests = MagicMock(
            return_value=[{"req_bullet_list": True}]
        )
        generator.list_builder.generate_list_element_requests = MagicMock(
            return_value=[{"req_ordered_list": True}]
        )  # For ORDERED_LIST
        generator.media_builder.generate_image_element_requests = MagicMock(
            return_value=[{"req_img": True}]
        )
        generator.code_builder.generate_code_element_requests = MagicMock(
            return_value=[{"req_code": True}]
        )
        generator.table_builder.generate_table_element_requests = MagicMock(
            return_value=[{"req_table": True}]
        )

        for el in elements_to_test:
            # Reset object_id if it's expected to be generated by ApiRequestGenerator
            # For this test, assume they are pre-assigned for simplicity of assertion
            # or that the placeholder logic will handle it.
            # The primary check is the dispatch.
            generator._generate_element_requests(
                el, sample_slide.object_id, sample_slide.placeholder_mappings
            )

        # Asserts for calls
        generator.text_builder.generate_text_element_requests.assert_any_call(
            title_el, sample_slide.object_id, sample_slide.placeholder_mappings
        )
        generator.text_builder.generate_text_element_requests.assert_any_call(
            text_el, sample_slide.object_id, sample_slide.placeholder_mappings
        )
        generator.text_builder.generate_text_element_requests.assert_any_call(
            quote_el, sample_slide.object_id, sample_slide.placeholder_mappings
        )
        generator.text_builder.generate_text_element_requests.assert_any_call(
            footer_el, sample_slide.object_id, sample_slide.placeholder_mappings
        )

        generator.list_builder.generate_bullet_list_element_requests.assert_called_once_with(
            list_el, sample_slide.object_id
        )
        generator.list_builder.generate_list_element_requests.assert_called_once_with(
            ordered_list_el, sample_slide.object_id, "NUMBERED_DIGIT_ALPHA_ROMAN"
        )

        generator.media_builder.generate_image_element_requests.assert_called_once_with(
            img_el, sample_slide.object_id
        )
        generator.code_builder.generate_code_element_requests.assert_called_once_with(
            code_el, sample_slide.object_id
        )
        generator.table_builder.generate_table_element_requests.assert_called_once_with(
            table_el, sample_slide.object_id
        )

    def test_generate_batch_requests_empty_deck(self, generator: ApiRequestGenerator):
        deck = Deck(slides=[])
        batches = generator.generate_batch_requests(deck, "pid")
        assert len(batches) == 0

    def test_generate_batch_requests_multiple_slides(
        self, generator: ApiRequestGenerator, sample_slide: Slide
    ):
        slide1 = deepcopy(sample_slide)
        slide1.object_id = "s1"
        slide2 = deepcopy(sample_slide)
        slide2.object_id = "s2"
        deck = Deck(slides=[slide1, slide2])

        # Mock generate_slide_batch to check it's called correctly
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
