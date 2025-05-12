from copy import deepcopy
from typing import cast

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
    TextFormat,
    TextFormatType,
)


@pytest.fixture
def generator() -> ApiRequestGenerator:
    return ApiRequestGenerator()


@pytest.fixture
def sample_slide(request) -> Slide:
    """Creates a sample slide, optionally with specific elements based on marker."""
    slide_id = "test_slide_001"
    elements = []

    if hasattr(request, "param") and request.param:
        if request.param == "with_title":
            elements.append(
                TextElement(
                    element_type=ElementType.TITLE,
                    text="Test Title",
                    object_id="title1",
                    position=(50, 50),
                    size=(600, 50),
                )
            )
        elif request.param == "with_text_box":
            elements.append(
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Hello World",
                    object_id="text1",
                    position=(50, 120),
                    size=(600, 100),
                )
            )
        elif request.param == "with_formatted_text":
            elements.append(
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Bold Italic",
                    object_id="fmttext1",
                    position=(50, 120),
                    size=(600, 50),
                    formatting=[
                        TextFormat(start=0, end=4, format_type=TextFormatType.BOLD),
                        TextFormat(start=5, end=11, format_type=TextFormatType.ITALIC),
                    ],
                )
            )
        elif request.param == "with_bullet_list":
            elements.append(
                ListElement(
                    element_type=ElementType.BULLET_LIST,
                    object_id="list1",
                    position=(50, 120),
                    size=(600, 100),
                    items=[ListItem(text="Item 1"), ListItem(text="Item 2")],
                )
            )
        elif request.param == "with_image":
            elements.append(
                ImageElement(
                    element_type=ElementType.IMAGE,
                    url="http://example.com/img.png",
                    alt_text="Alt",
                    object_id="img1",
                    position=(50, 120),
                    size=(300, 200),
                )
            )
        elif request.param == "with_code":
            elements.append(
                CodeElement(
                    element_type=ElementType.CODE,
                    code="print('hi')",
                    language="python",
                    object_id="code1",
                    position=(50, 120),
                    size=(600, 100),
                )
            )
        elif request.param == "with_table":
            elements.append(
                TableElement(
                    element_type=ElementType.TABLE,
                    headers=["H1"],
                    rows=[["C1"]],
                    object_id="table1",
                    position=(50, 120),
                    size=(300, 100),
                )
            )

    return Slide(
        object_id=slide_id,
        elements=elements,
        layout=SlideLayout.BLANK,
        title="Sample Slide",
    )


class TestApiRequestGenerator:
    """Unit tests for the ApiRequestGenerator."""

    def test_generate_id(self, generator: ApiRequestGenerator):
        id1 = generator._generate_id("prefix")
        id2 = generator._generate_id("prefix")
        assert id1 != id2
        assert id1.startswith("prefix_")

    def test_hex_to_rgb(self, generator: ApiRequestGenerator):
        assert generator._hex_to_rgb("#FF0000") == {
            "red": 1.0,
            "green": 0.0,
            "blue": 0.0,
        }
        assert generator._hex_to_rgb("00FF00") == {
            "red": 0.0,
            "green": 1.0,
            "blue": 0.0,
        }
        assert generator._hex_to_rgb("#00F") == {
            "red": 0.0,
            "green": 0.0,
            "blue": 1.0,
        }  # Shorthand

    def test_create_slide_request(
        self, generator: ApiRequestGenerator, sample_slide: Slide
    ):
        request = generator._create_slide_request(sample_slide)
        assert "createSlide" in request
        cs_data = request["createSlide"]
        assert cs_data["objectId"] == sample_slide.object_id
        assert (
            cs_data["slideLayoutReference"]["predefinedLayout"]
            == sample_slide.layout.value
        )

    def test_create_slide_request_generates_id(self, generator: ApiRequestGenerator):
        slide = Slide(layout=SlideLayout.TITLE_ONLY)  # No object_id provided
        request = generator._create_slide_request(slide)
        assert "createSlide" in request
        assert request["createSlide"]["objectId"] is not None
        assert (
            slide.object_id == request["createSlide"]["objectId"]
        )  # Ensure slide object is updated

    def test_create_background_request_color(
        self, generator: ApiRequestGenerator, sample_slide: Slide
    ):
        sample_slide.background = {"type": "color", "value": "#ABCDEF"}
        request = generator._create_background_request(sample_slide)
        assert "updateSlideProperties" in request
        fill = request["updateSlideProperties"]["slideProperties"]["backgroundFill"]
        assert "solidFill" in fill
        assert fill["solidFill"]["color"]["opaqueColor"][
            "rgbColor"
        ] == generator._hex_to_rgb("#ABCDEF")

    def test_create_background_request_theme_color(
        self, generator: ApiRequestGenerator, sample_slide: Slide
    ):
        sample_slide.background = {"type": "color", "value": "ACCENT1"}
        request = generator._create_background_request(sample_slide)
        fill = request["updateSlideProperties"]["slideProperties"]["backgroundFill"]
        assert fill["solidFill"]["color"]["opaqueColor"]["themeColor"] == "ACCENT1"

    def test_create_background_request_image(
        self, generator: ApiRequestGenerator, sample_slide: Slide
    ):
        sample_slide.background = {"type": "image", "value": "image_placeholder_id"}
        request = generator._create_background_request(sample_slide)
        fill = request["updateSlideProperties"]["slideProperties"]["backgroundFill"]
        assert "stretchedPictureFill" in fill
        assert fill["stretchedPictureFill"]["pictureId"] == "image_placeholder_id"

    def test_create_background_request_no_background(
        self, generator: ApiRequestGenerator, sample_slide: Slide
    ):
        sample_slide.background = None
        request = generator._create_background_request(sample_slide)
        assert request == {}  # Should return an empty dict or similar non-request

    def test_create_notes_request(self, generator: ApiRequestGenerator):
        notes = "These are my notes"
        slide_with_notes = Slide(
            layout="title", notes=notes, object_id="slide123", elements=[]
        )
        request = generator._create_notes_request(slide_with_notes)
        assert "updateSlideProperties" in request
        unp_data = request["updateSlideProperties"]
        assert unp_data["objectId"] == "slide123"
        assert (
            unp_data["slideProperties"]["notesPage"]["notesProperties"][
                "speakerNotesText"
            ]
            == notes
        )
        assert unp_data["fields"] == "notesPage.notesProperties.speakerNotesText"

    @pytest.mark.parametrize("sample_slide", ["with_title"], indirect=True)
    def test_generate_text_element_requests_title(
        self, generator: ApiRequestGenerator, sample_slide: Slide
    ):
        title_element = sample_slide.elements[0]
        requests = generator._generate_text_element_requests(
            title_element, sample_slide.object_id
        )
        assert (
            len(requests) >= 2
        )  # createShape, insertText, possibly updateParagraphStyle
        assert requests[0]["createShape"]["shapeType"] == "TEXT_BOX"
        assert requests[1]["insertText"]["text"] == title_element.text
        # Check for paragraph style for title
        paragraph_style_req = next(
            (r for r in requests if "updateParagraphStyle" in r), None
        )
        assert paragraph_style_req is not None
        assert (
            paragraph_style_req["updateParagraphStyle"]["style"]["alignment"]
            == "CENTER"
        )

    @pytest.mark.parametrize("sample_slide", ["with_formatted_text"], indirect=True)
    def test_generate_text_element_requests_with_formatting(
        self, generator: ApiRequestGenerator, sample_slide: Slide
    ):
        text_element = sample_slide.elements[0]
        requests = generator._generate_text_element_requests(
            text_element, sample_slide.object_id
        )
        # Expected: createShape, insertText, updateTextStyle (bold), updateTextStyle (italic), updateParagraphStyle
        assert len(requests) == 5
        update_style_requests = [r for r in requests if "updateTextStyle" in r]
        assert len(update_style_requests) == 2
        assert any(
            r["updateTextStyle"]["style"].get("bold") for r in update_style_requests
        )
        assert any(
            r["updateTextStyle"]["style"].get("italic") for r in update_style_requests
        )

    @pytest.mark.parametrize("sample_slide", ["with_bullet_list"], indirect=True)
    def test_generate_list_element_requests(
        self, generator: ApiRequestGenerator, sample_slide: Slide
    ):
        list_element = cast(ListElement, sample_slide.elements[0])
        requests = generator._generate_list_element_requests(
            list_element, sample_slide.object_id, "BULLET_DISC_CIRCLE_SQUARE"
        )
        # createShape, insertText, createParagraphBullets
        assert len(requests) >= 3
        assert requests[0]["createShape"]["shapeType"] == "TEXT_BOX"
        assert (
            "Item 1\nItem 2" in requests[1]["insertText"]["text"]
        )  # Check combined text
        assert (
            requests[2]["createParagraphBullets"]["bulletPreset"]
            == "BULLET_DISC_CIRCLE_SQUARE"
        )

    @pytest.mark.parametrize("sample_slide", ["with_image"], indirect=True)
    def test_generate_image_element_requests(
        self, generator: ApiRequestGenerator, sample_slide: Slide
    ):
        image_element = cast(ImageElement, sample_slide.elements[0])
        requests = generator._generate_image_element_requests(
            image_element, sample_slide.object_id
        )
        assert len(requests) == 2  # createImage, updateImageProperties (for alt text)
        assert "createImage" in requests[0]
        assert requests[0]["createImage"]["url"] == image_element.url
        assert "updateImageProperties" in requests[1]
        assert (
            requests[1]["updateImageProperties"]["imageProperties"]["description"]
            == image_element.alt_text
        )

    @pytest.mark.parametrize("sample_slide", ["with_code"], indirect=True)
    def test_generate_code_element_requests(
        self, generator: ApiRequestGenerator, sample_slide: Slide
    ):
        code_element = cast(CodeElement, sample_slide.elements[0])
        requests = generator._generate_code_element_requests(
            code_element, sample_slide.object_id
        )
        # createShape, insertText, updateTextStyle (font, bg), updateShapeProperties (bg), createShape (label), insertText(label), style(label), center(label)
        assert len(requests) == 8
        assert requests[0]["createShape"]["shapeType"] == "TEXT_BOX"
        assert requests[1]["insertText"]["text"] == code_element.code
        style_req = requests[2]["updateTextStyle"]
        assert style_req["style"]["fontFamily"] == "Courier New"
        assert "backgroundColor" in style_req["style"]
        assert (
            requests[3]["updateShapeProperties"]["fields"]
            == "shapeProperties.shapeBackgroundFill.solidFill.color"
        )
        # Language label requests
        assert requests[4]["createShape"]["objectId"].endswith("_label")
        assert requests[5]["insertText"]["text"] == "python"

    @pytest.mark.parametrize("sample_slide", ["with_table"], indirect=True)
    def test_generate_table_element_requests(
        self, generator: ApiRequestGenerator, sample_slide: Slide
    ):
        table_element = cast(TableElement, sample_slide.elements[0])
        requests = generator._generate_table_element_requests(
            table_element, sample_slide.object_id
        )
        # createTable, insertText (H1), updateTextStyle (H1 bold), updateTableCellProperties (H1 fill), insertText(C1)
        assert len(requests) >= 5
        assert "createTable" in requests[0]
        assert requests[0]["createTable"]["rows"] == 2  # 1 header + 1 row
        assert requests[0]["createTable"]["columns"] == 1
        assert requests[1]["insertText"]["text"] == "H1"
        assert requests[2]["updateTextStyle"]["style"]["bold"] is True

    def test_apply_text_formatting_specific_range(self, generator: ApiRequestGenerator):
        req = generator._apply_text_formatting(
            "el1", {"bold": True}, "bold", start_index=0, end_index=5
        )
        assert req["updateTextStyle"]["textRange"] == {
            "type": "FIXED_RANGE",
            "startIndex": 0,
            "endIndex": 5,
        }

    def test_apply_text_formatting_all_range(self, generator: ApiRequestGenerator):
        req = generator._apply_text_formatting(
            "el1", {"italic": True}, "italic", range_type="ALL"
        )
        assert req["updateTextStyle"]["textRange"] == {"type": "ALL"}
        assert "startIndex" not in req["updateTextStyle"]["textRange"]

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
        batches = generator.generate_batch_requests(deck, "pid")
        assert len(batches) == 2
        assert batches[0]["requests"][0]["createSlide"]["objectId"] == "s1"
        assert batches[1]["requests"][0]["createSlide"]["objectId"] == "s2"
