import pytest
from markdowndeck.api.request_builders import ListRequestBuilder
from markdowndeck.models import ElementType, ListElement, ListItem
from markdowndeck.parser.content.element_factory import ElementFactory


@pytest.fixture
def list_builder() -> ListRequestBuilder:
    return ListRequestBuilder(element_factory=ElementFactory())


class TestListBuilderNesting:
    def test_api_c_17_nested_list_generates_indentation_requests(
        self, list_builder: ListRequestBuilder
    ):
        """
        Test Case: API-C-17
        Validates that a nested list generates 'updateParagraphStyle' requests
        with 'indentStart' to create visual nesting in Google Slides.
        """
        # Arrange
        nested_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[
                ListItem(text="Level 1"),
                ListItem(text="Level 1, Item 2", children=[ListItem(text="Level 2")]),
            ],
            object_id="nested_list_test",
            position=(100, 100),
            size=(400, 200),
        )

        # Act
        requests = list_builder.generate_bullet_list_element_requests(
            nested_list, "slide_id"
        )

        # Assert
        indent_requests = [
            req
            for req in requests
            if "updateParagraphStyle" in req
            and "indentStart" in req["updateParagraphStyle"].get("fields", "")
        ]

        assert (
            len(indent_requests) > 0
        ), "Should generate at least one request to set indentation for the nested item."

        nested_item_request = next(
            (
                req
                for req in indent_requests
                if req["updateParagraphStyle"]["style"]["indentStart"]["magnitude"] > 0
            ),
            None,
        )

        assert (
            nested_item_request is not None
        ), "A request to indent the Level 2 item must exist."

        style = nested_item_request["updateParagraphStyle"]["style"]
        assert "indentStart" in style
        assert "indentFirstLine" in style
        assert style["indentStart"]["magnitude"] > 0
        assert style["indentFirstLine"]["magnitude"] > 0
