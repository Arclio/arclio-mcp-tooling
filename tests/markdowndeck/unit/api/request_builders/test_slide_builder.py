import pytest
from markdowndeck.api.request_builders.base_builder import (
    BaseRequestBuilder,
)  # For _hex_to_rgb comparison
from markdowndeck.api.request_builders.slide_builder import SlideRequestBuilder
from markdowndeck.models import ElementType, Slide, SlideLayout


@pytest.fixture
def builder() -> SlideRequestBuilder:
    return SlideRequestBuilder()


@pytest.fixture
def base_builder() -> BaseRequestBuilder:  # For helper methods like _hex_to_rgb
    return BaseRequestBuilder()


@pytest.fixture
def sample_slide_model() -> Slide:
    return Slide(object_id="test_slide_001", layout=SlideLayout.BLANK, title="Sample Slide")


@pytest.fixture
def slide_with_notes_and_id() -> Slide:
    return Slide(
        object_id="slide_notes_test",
        layout=SlideLayout.TITLE_ONLY,
        notes="This is a speaker note.",
        speaker_notes_object_id="speaker_notes_shape_123",  # Crucial: ID is preset
    )


class TestSlideRequestBuilder:
    """Unit tests for the SlideRequestBuilder."""

    def test_create_slide_request(self, builder: SlideRequestBuilder, sample_slide_model: Slide):
        request = builder.create_slide_request(sample_slide_model)
        assert "createSlide" in request
        cs_data = request["createSlide"]
        assert cs_data["objectId"] == sample_slide_model.object_id
        assert cs_data["slideLayoutReference"]["predefinedLayout"] == sample_slide_model.layout.value
        assert "placeholderIdMappings" in cs_data  # Check if mappings are present
        # Further checks on placeholder_id_mappings if specific layouts are tested

    def test_create_slide_request_generates_id(self, builder: SlideRequestBuilder):
        slide = Slide(layout=SlideLayout.TITLE_ONLY)  # No object_id provided
        request = builder.create_slide_request(slide)
        assert "createSlide" in request
        assert request["createSlide"]["objectId"] is not None
        assert slide.object_id == request["createSlide"]["objectId"]  # Ensure slide object is updated

    def test_create_slide_request_with_title_body_layout_populates_mappings(self, builder: SlideRequestBuilder):
        slide = Slide(layout=SlideLayout.TITLE_AND_BODY)
        builder.create_slide_request(slide)  # This populates slide.placeholder_mappings

        assert ElementType.TITLE in slide.placeholder_mappings
        assert ElementType.TEXT in slide.placeholder_mappings  # BODY maps to TEXT
        assert slide.placeholder_mappings[ElementType.TITLE].startswith(f"{slide.object_id}_title_")
        assert slide.placeholder_mappings[ElementType.TEXT].startswith(f"{slide.object_id}_body_")

    def test_create_background_request_color_hex(
        self,
        builder: SlideRequestBuilder,
        base_builder: BaseRequestBuilder,
        sample_slide_model: Slide,
    ):
        sample_slide_model.background = {"type": "color", "value": "#ABCDEF"}
        request = builder.create_background_request(sample_slide_model)

        assert "updatePageProperties" in request
        upp_data = request["updatePageProperties"]
        assert upp_data["objectId"] == sample_slide_model.object_id
        assert "pageProperties" in upp_data
        assert "pageBackgroundFill" in upp_data["pageProperties"]

        fill = upp_data["pageProperties"]["pageBackgroundFill"]
        assert "solidFill" in fill
        assert "color" in fill["solidFill"]
        assert "rgbColor" in fill["solidFill"]["color"]
        assert fill["solidFill"]["color"]["rgbColor"] == base_builder._hex_to_rgb("#ABCDEF")
        assert upp_data["fields"] == "pageBackgroundFill.solidFill.color.rgbColor"

    def test_create_background_request_color_theme(self, builder: SlideRequestBuilder, sample_slide_model: Slide):
        sample_slide_model.background = {"type": "color", "value": "ACCENT1"}
        request = builder.create_background_request(sample_slide_model)

        assert "updatePageProperties" in request
        upp_data = request["updatePageProperties"]
        fill = upp_data["pageProperties"]["pageBackgroundFill"]
        assert "solidFill" in fill
        assert "color" in fill["solidFill"]
        assert fill["solidFill"]["color"]["themeColor"] == "ACCENT1"
        assert upp_data["fields"] == "pageBackgroundFill.solidFill.color.themeColor"

    def test_create_background_request_image(self, builder: SlideRequestBuilder, sample_slide_model: Slide):
        sample_slide_model.background = {
            "type": "image",
            "value": "http://example.com/bg.png",
        }
        request = builder.create_background_request(sample_slide_model)

        assert "updatePageProperties" in request
        upp_data = request["updatePageProperties"]
        fill = upp_data["pageProperties"]["pageBackgroundFill"]
        assert "stretchedPictureFill" in fill
        assert fill["stretchedPictureFill"]["contentUrl"] == "http://example.com/bg.png"
        assert upp_data["fields"] == "pageBackgroundFill.stretchedPictureFill.contentUrl"

    def test_create_background_request_no_background(self, builder: SlideRequestBuilder, sample_slide_model: Slide):
        sample_slide_model.background = None
        request = builder.create_background_request(sample_slide_model)
        assert request == {}

    def test_create_notes_request_with_id(self, builder: SlideRequestBuilder, slide_with_notes_and_id: Slide):
        requests = builder.create_notes_request(slide_with_notes_and_id)

        assert isinstance(requests, list)
        assert len(requests) == 2

        delete_request = requests[0]
        insert_request = requests[1]

        assert "deleteText" in delete_request
        dt_data = delete_request["deleteText"]
        assert dt_data["objectId"] == "speaker_notes_shape_123"
        assert dt_data["textRange"]["type"] == "ALL"

        assert "insertText" in insert_request
        it_data = insert_request["insertText"]
        assert it_data["objectId"] == "speaker_notes_shape_123"
        assert it_data["text"] == "This is a speaker note."
        assert it_data["insertionIndex"] == 0

    def test_create_notes_request_no_notes_content(self, builder: SlideRequestBuilder, sample_slide_model: Slide):
        sample_slide_model.notes = None  # No notes content
        sample_slide_model.speaker_notes_object_id = "notes_id_123"
        requests = builder.create_notes_request(sample_slide_model)
        assert requests == []

    def test_create_notes_request_no_speaker_notes_id(self, builder: SlideRequestBuilder, sample_slide_model: Slide):
        sample_slide_model.notes = "Some notes"
        sample_slide_model.speaker_notes_object_id = None  # ID is missing
        requests = builder.create_notes_request(sample_slide_model)
        assert requests == []
