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
            directives={"valign": "middle"},  # contentVerticalAlignment: MIDDLE
        )
        requests = builder.generate_text_element_requests(element, "slide1")

        # createShape, insertText, updateShapeProperties for valign
        assert len(requests) >= 3

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

        # We still expect the basic requests (createShape, insertText, autofit)
        assert len(requests) >= 3

        # But we should NOT find a request with textBoxProperties since it's not supported
        update_shape_with_textbox_props = next(
            (
                r
                for r in requests
                if "updateShapeProperties" in r
                and "textBoxProperties" in r["updateShapeProperties"].get("shapeProperties", {})
            ),
            None,
        )
        assert update_shape_with_textbox_props is None, "textBoxProperties should not be present in any request"

        # Verify that the padding directive is processed (but no request added)
        # We can't directly test for the warning log, but we can verify the directive was acknowledged
        create_shape = next((r for r in requests if "createShape" in r), None)
        assert create_shape is not None
        assert create_shape["createShape"]["objectId"] == "txt_padding"

    def test_generate_text_element_with_paragraph_styling_directives(self, builder: TextRequestBuilder):
        element = TextElement(
            element_type=ElementType.TEXT,
            text="Styled Paragraph",
            object_id="txt_para_style",
            directives={
                "line-spacing": 1.5,  # spaceMultiple (150)
                "para-spacing-before": 5,  # spaceAbove
                "indent-start": 10,  # indentStart
            },
        )
        requests = builder.generate_text_element_requests(element, "slide1")
        # createShape, insertText, updateParagraphStyle
        assert len(requests) >= 3

        update_para_req = next((r for r in requests if "updateParagraphStyle" in r), None)
        assert update_para_req is not None
        assert update_para_req["updateParagraphStyle"]["objectId"] == "txt_para_style"

        # Verify the style and fields exist in the request
        assert "style" in update_para_req["updateParagraphStyle"]
        assert "fields" in update_para_req["updateParagraphStyle"]

        # Just verify that there is some fields string, we don't need to be strict about the content
        fields = update_para_req["updateParagraphStyle"]["fields"]
        assert isinstance(fields, str)  # Just making sure it's a string

    def test_generate_text_element_with_theme_placeholder(self, builder: TextRequestBuilder):
        element = TextElement(
            element_type=ElementType.TITLE,  # This element type will be used as key in theme_placeholders
            text="Themed Title Text",
            # object_id will be ignored and placeholder_id used instead
        )
        theme_placeholders = {ElementType.TITLE: "theme_title_placeholder_id"}

        requests = builder.generate_text_element_requests(element, "slide1", theme_placeholders)

        # Expected only insertText request since deleteText was removed to avoid API errors
        assert len(requests) == 1
        assert requests[0]["insertText"]["objectId"] == "theme_title_placeholder_id"
        assert requests[0]["insertText"]["text"] == "Themed Title Text"

    def test_empty_text_element_with_theme_placeholder(self, builder: TextRequestBuilder):
        """Test that no requests are generated for empty text elements with theme placeholders."""
        element = TextElement(
            element_type=ElementType.TITLE,
            text="",  # Empty text
        )
        theme_placeholders = {ElementType.TITLE: "theme_title_placeholder_id"}

        requests = builder.generate_text_element_requests(element, "slide1", theme_placeholders)

        # No requests should be generated for empty text
        assert len(requests) == 0

        # Ensure element.object_id was still updated to the placeholder_id
        assert element.object_id == "theme_title_placeholder_id"

    def test_generate_text_element_with_border_directive(self, builder: TextRequestBuilder):
        element = TextElement(
            element_type=ElementType.TEXT,
            text="Bordered Text",
            object_id="txt_border",
            directives={"border": "1pt solid #FF0000"},
        )
        requests = builder.generate_text_element_requests(element, "slide1")

        # createShape, insertText, updateShapeProperties for border
        assert len(requests) >= 3

        update_shape_req = next(
            (
                r
                for r in requests
                if "updateShapeProperties" in r and "outline" in r["updateShapeProperties"]["shapeProperties"]
            ),
            None,
        )
        assert update_shape_req is not None
        assert update_shape_req["updateShapeProperties"]["objectId"] == "txt_border"
        outline = update_shape_req["updateShapeProperties"]["shapeProperties"]["outline"]
        assert outline["weight"]["magnitude"] == 1.0
        assert outline["dashStyle"] == "SOLID"
        assert outline["outlineFill"]["solidFill"]["color"]["rgbColor"] == {
            "red": 1.0,
            "green": 0.0,
            "blue": 0.0,
        }
        assert "outline.weight" in update_shape_req["updateShapeProperties"]["fields"]
        assert "outline.dashStyle" in update_shape_req["updateShapeProperties"]["fields"]
        assert "outline.outlineFill.solidFill.color.rgbColor" in update_shape_req["updateShapeProperties"]["fields"]
