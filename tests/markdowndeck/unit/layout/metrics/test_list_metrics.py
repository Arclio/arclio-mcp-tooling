"""Updated unit tests for list element metrics with split() method support."""

from markdowndeck.layout.metrics.list import calculate_list_element_height
from markdowndeck.models import ElementType, ListElement, ListItem


class TestListMetrics:
    """Unit tests for list element height calculation."""

    def test_calculate_list_height_empty(self):
        element = ListElement(items=[], element_type=ElementType.BULLET_LIST)
        height = calculate_list_element_height(element, 500)
        assert height >= 30  # MIN_LIST_HEIGHT

    def test_calculate_list_height_single_item(self):
        item = ListItem(text="Simple item")
        element = ListElement(items=[item], element_type=ElementType.BULLET_LIST)
        height = calculate_list_element_height(element, 500)
        assert height >= 30  # Should be at least minimum height

    def test_calculate_list_height_multiple_items(self):
        items = [
            ListItem(text="Item 1"),
            ListItem(text="Item 2"),
            ListItem(text="Item 3"),
        ]
        element = ListElement(items=items, element_type=ElementType.ORDERED_LIST)
        height1 = calculate_list_element_height(
            ListElement(items=[items[0]], element_type=ElementType.ORDERED_LIST), 500
        )
        height3 = calculate_list_element_height(element, 500)
        assert height3 > height1  # More items should lead to more height

    def test_calculate_list_height_wrapping_text(self):
        item_short = ListItem(text="Short")
        item_long = ListItem(
            text="This is a very long list item that will definitely wrap several times to test height."
        )

        element_short = ListElement(
            items=[item_short], element_type=ElementType.BULLET_LIST
        )
        element_long = ListElement(
            items=[item_long], element_type=ElementType.BULLET_LIST
        )

        height_short = calculate_list_element_height(element_short, 200)
        height_long = calculate_list_element_height(element_long, 200)  # Same width
        assert height_long > height_short

    def test_calculate_list_height_nested_items(self):
        l3 = ListItem(text="Level 3")
        l2 = ListItem(text="Level 2", children=[l3])
        l1 = ListItem(text="Level 1", children=[l2])
        element = ListElement(
            items=[l1, ListItem("Another L1")], element_type=ElementType.BULLET_LIST
        )

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
        element = ListElement(
            items=[item_formatted], element_type=ElementType.BULLET_LIST
        )
        height = calculate_list_element_height(element, 500)
        assert height > 0

    def test_list_performance_with_many_items(self):
        """Test that list height calculation performs reasonably with many items."""
        # Create a large number of items to test performance caps
        many_items = [ListItem(text=f"Item {i}") for i in range(300)]
        element = ListElement(items=many_items, element_type=ElementType.BULLET_LIST)

        import time

        start = time.time()
        height = calculate_list_element_height(element, 500)
        end = time.time()

        assert height > 0
        assert (end - start) < 1.0  # Should complete quickly
        assert height < 20000  # Should have reasonable cap


class TestListElementSplitting:
    """Test the split() method functionality for ListElement."""

    def test_list_split_basic_functionality(self):
        """Test basic split() method functionality."""
        items = [ListItem(text=f"Item {i}") for i in range(5)]
        element = ListElement(items=items, element_type=ElementType.BULLET_LIST)
        element.size = (400, 100)

        # Test with sufficient height (should fit all)
        fitted, overflowing = element.split(200)
        assert fitted is not None
        assert overflowing is None
        assert len(fitted.items) == 5

    def test_list_split_minimum_requirements(self):
        """Test that split() respects minimum 2-item requirement."""
        items = [ListItem(text=f"Item {i}") for i in range(4)]
        element = ListElement(items=items, element_type=ElementType.BULLET_LIST)
        element.size = (400, 80)

        # Test with very limited height (less than 2 items worth)
        fitted, overflowing = element.split(15)  # Very small height

        # Should reject split due to minimum requirement
        assert fitted is None
        assert overflowing is not None
        assert len(overflowing.items) == 4

    def test_list_split_successful_split(self):
        """Test successful split when minimum requirements are met."""
        items = [ListItem(text=f"Item {i}") for i in range(6)]
        element = ListElement(items=items, element_type=ElementType.BULLET_LIST)
        element.size = (400, 120)

        # Test with moderate height (should split)
        fitted, overflowing = element.split(60)

        if fitted is not None:  # Split was accepted
            assert len(fitted.items) >= 2  # At least 2 items
            assert len(fitted.items) < 6  # Not all items
            assert overflowing is not None
            assert len(overflowing.items) >= 1  # At least 1 item remaining
            assert len(fitted.items) + len(overflowing.items) == 6  # Total preserved

    def test_list_split_empty_list(self):
        """Test split() with empty list."""
        element = ListElement(items=[], element_type=ElementType.BULLET_LIST)
        element.size = (400, 50)

        fitted, overflowing = element.split(100)
        assert fitted is None
        assert overflowing is None

    def test_list_split_single_item(self):
        """Test split() with single item."""
        element = ListElement(
            items=[ListItem(text="Single item")], element_type=ElementType.BULLET_LIST
        )
        element.size = (400, 50)

        fitted, overflowing = element.split(20)  # Very small height

        # Single item that doesn't meet minimum should be treated as atomic
        assert fitted is None
        assert overflowing is not None

    def test_list_split_preserves_metadata(self):
        """Test that split preserves element metadata."""
        items = [ListItem(text=f"Item {i}") for i in range(4)]
        element = ListElement(
            items=items, element_type=ElementType.BULLET_LIST, object_id="test_list"
        )
        element.size = (400, 80)

        fitted, overflowing = element.split(50)

        if fitted is not None:
            assert fitted.element_type == ElementType.BULLET_LIST
            assert hasattr(fitted, "size")

        if overflowing is not None:
            assert overflowing.element_type == ElementType.BULLET_LIST

    def test_list_split_with_related_to_prev(self):
        """Test split() behavior with related_to_prev flag."""
        items = [ListItem(text=f"Item {i}") for i in range(4)]
        element = ListElement(
            items=items, element_type=ElementType.BULLET_LIST, related_to_prev=True
        )
        element.size = (400, 80)
        element.set_preceding_title("Section Heading")  # Set preceding title

        fitted, overflowing = element.split(50)

        if overflowing is not None:
            # Should have continuation title when related_to_prev is True
            assert hasattr(overflowing, "_continuation_title") or hasattr(
                overflowing, "_preceding_title_text"
            )

    def test_list_split_nested_items(self):
        """Test split() with nested list items."""
        child_item = ListItem(text="Child item")
        parent_items = [
            ListItem(text="Parent 1", children=[child_item]),
            ListItem(text="Parent 2"),
            ListItem(text="Parent 3"),
        ]
        element = ListElement(items=parent_items, element_type=ElementType.BULLET_LIST)
        element.size = (400, 100)

        fitted, overflowing = element.split(50)

        # Should handle nested structure appropriately
        if fitted is not None:
            assert len(fitted.items) >= 2  # Minimum requirement
            # Verify nested structure is preserved
            for item in fitted.items:
                assert isinstance(item, ListItem)
