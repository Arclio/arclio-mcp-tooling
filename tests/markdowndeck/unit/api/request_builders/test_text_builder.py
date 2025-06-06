import pytest
from markdowndeck.api.request_builders.text_builder import TextRequestBuilder
from markdowndeck.models import (
    ElementType,
    TextElement,
)


@pytest.fixture
def builder() -> TextRequestBuilder:
    return TextRequestBuilder()


class TestTextRequestBuilderDirectivesAndTheme:
    def test_generate_text_element_with_valign_directive(self, builder: TextRequestBuilder):
        element = TextElement(
            element_type=ElementType.TEXT,
            text="Vertically Aligned",
            object_id="txt_valign",
            directives={"valign": "middle"},
        )
        requests = builder.generate_text_element_requests(element, "slide1")

        update_shape_req = next(
            (
                r
                for r in requests
                if "updateShapeProperties" in r and "contentAlignment" in r["updateShapeProperties"]["fields"]
            ),
            None,
        )
        assert update_shape_req is not None
        assert update_shape_req["updateShapeProperties"]["objectId"] == "txt_valign"
        assert update_shape_req["updateShapeProperties"]["shapeProperties"]["contentAlignment"] == "MIDDLE"

    def test_generate_text_element_with_padding_directive(self, builder: TextRequestBuilder):
        element = TextElement(
            element_type=ElementType.TEXT,
            text="Padded Text",
            object_id="txt_padding",
            directives={"padding": 10},
        )
        requests = builder.generate_text_element_requests(element, "slide1")

        update_shape_with_textbox_props = next(
            (
                r
                for r in requests
                if "updateShapeProperties" in r
                and "textBoxProperties" in r["updateShapeProperties"].get("shapeProperties", {})
            ),
            None,
        )
        assert update_shape_with_textbox_props is None, (
            "textBoxProperties should not be present as it's not supported by the REST API"
        )

    def test_generate_text_element_with_paragraph_styling_directives(self, builder: TextRequestBuilder):
        element = TextElement(
            element_type=ElementType.TEXT,
            text="Styled Paragraph",
            object_id="txt_para_style",
            directives={
                "line-spacing": 1.5,
                "para-spacing-before": 5,
                "indent-start": 10,
            },
        )
        requests = builder.generate_text_element_requests(element, "slide1")

        # Find the paragraph style request that contains the directive-based styling
        # (not the alignment-based request which may have default values)
        update_para_req = next(
            (
                r
                for r in requests
                if "updateParagraphStyle" in r
                and "spaceAbove" in r["updateParagraphStyle"]["style"]
                and r["updateParagraphStyle"]["style"]["spaceAbove"]["magnitude"] > 0
            ),
            None,
        )
        assert update_para_req is not None, "Should find paragraph style request with directive-based spacing"
        style = update_para_req["updateParagraphStyle"]["style"]
        fields = update_para_req["updateParagraphStyle"]["fields"].split(",")

        assert style["lineSpacing"] == 1.5
        assert "lineSpacing" in fields
        assert style["spaceAbove"]["magnitude"] == 5.0
        assert "spaceAbove" in fields
        assert style["indentStart"]["magnitude"] == 10.0
        assert "indentStart" in fields

    def test_generate_text_element_with_theme_placeholder(self, builder: TextRequestBuilder):
        element = TextElement(
            element_type=ElementType.TITLE,
            text="Themed Title Text",
        )
        theme_placeholders = {ElementType.TITLE: "theme_title_placeholder_id"}

        requests = builder.generate_text_element_requests(element, "slide1", theme_placeholders)

        # A themed element should first delete existing text, then insert new text.
        assert len(requests) >= 1, "Should generate at least one request"

        # Check for insertText request (it might be the only one if no other styling)
        insert_req = next((r for r in requests if "insertText" in r), None)
        assert insert_req is not None
        assert insert_req["insertText"]["objectId"] == "theme_title_placeholder_id"
        assert insert_req["insertText"]["text"] == "Themed Title Text"

    def test_empty_text_element_with_theme_placeholder(self, builder: TextRequestBuilder):
        """Test that no requests are generated for empty text elements with theme placeholders."""
        element = TextElement(
            element_type=ElementType.TITLE,
            text="",  # Empty text
        )
        theme_placeholders = {ElementType.TITLE: "theme_title_placeholder_id"}

        requests = builder.generate_text_element_requests(element, "slide1", theme_placeholders)

        # No requests should be generated for empty text
        assert len(requests) == 0, "No requests should be generated for an empty text element"

        # Ensure element.object_id was still updated to the placeholder_id for reference
        assert element.object_id == "theme_title_placeholder_id"

    def test_generate_text_element_with_border_directive(self, builder: TextRequestBuilder):
        element = TextElement(
            element_type=ElementType.TEXT,
            text="Bordered Text",
            object_id="txt_border",
            directives={"border": "1pt solid #FF0000"},
        )
        requests = builder.generate_text_element_requests(element, "slide1")

        update_shape_req = next(
            (
                r
                for r in requests
                if "updateShapeProperties" in r and "outline" in r["updateShapeProperties"]["shapeProperties"]
            ),
            None,
        )
        assert update_shape_req is not None
        outline = update_shape_req["updateShapeProperties"]["shapeProperties"]["outline"]
        assert outline["weight"]["magnitude"] == 1.0
        assert outline["dashStyle"] == "SOLID"
        assert outline["outlineFill"]["solidFill"]["color"]["rgbColor"] == {
            "red": 1.0,
            "green": 0.0,
            "blue": 0.0,
        }

        # Check the fields mask for correctness
        fields = update_shape_req["updateShapeProperties"]["fields"].split(",")
        assert "outline.weight" in fields
        assert "outline.dashStyle" in fields
        assert "outline.outlineFill.solidFill.color" in fields  # Correct path to Color object
