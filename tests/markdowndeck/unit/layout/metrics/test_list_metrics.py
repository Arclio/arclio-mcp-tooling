from markdowndeck.layout.metrics.list import calculate_list_element_height
from markdowndeck.models import ElementType, ListElement, ListItem


class TestListMetrics:
    """Unit tests for list element height calculation."""

    def test_calculate_list_height_empty(self):
        element = ListElement(items=[], element_type=ElementType.BULLET_LIST)
        height = calculate_list_element_height(element, 500)
        assert height >= 20  # Min height for empty list

    def test_calculate_list_height_single_item(self):
        item = ListItem(text="Simple item")
        element = ListElement(items=[item], element_type=ElementType.BULLET_LIST)
        height = calculate_list_element_height(element, 500)
        # Current implementation may return exactly 30 as the minimum height
        assert height >= 30  # Should be text height + list padding + item spacing (minus one)

    def test_calculate_list_height_multiple_items(self):
        items = [
            ListItem(text="Item 1"),
            ListItem(text="Item 2"),
            ListItem(text="Item 3"),
        ]
        element = ListElement(items=items, element_type=ElementType.ORDERED_LIST)
        height1 = calculate_list_element_height(ListElement(items=[items[0]], element_type=ElementType.ORDERED_LIST), 500)
        height3 = calculate_list_element_height(element, 500)
        assert height3 > height1  # More items should lead to more height

    def test_calculate_list_height_wrapping_text(self):
        item_short = ListItem(text="Short")
        item_long = ListItem(text="This is a very long list item that will definitely wrap several times to test height.")

        element_short = ListElement(items=[item_short], element_type=ElementType.BULLET_LIST)
        element_long = ListElement(items=[item_long], element_type=ElementType.BULLET_LIST)

        height_short = calculate_list_element_height(element_short, 200)
        height_long = calculate_list_element_height(element_long, 200)  # Same width
        assert height_long > height_short

    def test_calculate_list_height_nested_items(self):
        l3 = ListItem(text="Level 3")
        l2 = ListItem(text="Level 2", children=[l3])
        l1 = ListItem(text="Level 1", children=[l2])
        element = ListElement(items=[l1, ListItem("Another L1")], element_type=ElementType.BULLET_LIST)

        height = calculate_list_element_height(element, 500)

        # Calculate height of just the L1 items without L2/L3 nesting
        l1_simple = ListItem(text="Level 1")
        element_simple_l1s = ListElement(
            items=[l1_simple, ListItem("Another L1")],
            element_type=ElementType.BULLET_LIST,
        )
        height_simple_l1s = calculate_list_element_height(element_simple_l1s, 500)

        assert height > height_simple_l1s  # Nesting should add height

    def test_calculate_list_item_with_formatting(self):
        from markdowndeck.models import TextFormat, TextFormatType

        item_formatted = ListItem(
            text="Item with **bold** text",
            formatting=[TextFormat(start=10, end=14, format_type=TextFormatType.BOLD)],
        )
        element = ListElement(items=[item_formatted], element_type=ElementType.BULLET_LIST)
        # The height difference due to mild formatting might be negligible or absorbed by line height
        # but the test ensures it doesn't crash and uses the text_height_calculator.
        height = calculate_list_element_height(element, 500)
        assert height > 0
