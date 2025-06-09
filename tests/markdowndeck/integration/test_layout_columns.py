"""
Integration tests for layout manager column calculations.

These tests validate that the layout manager correctly calculates
column widths according to the LAYOUT_SPEC.md specifications.
"""

from markdowndeck.layout import LayoutManager
from markdowndeck.parser import Parser


def test_layout_v_01_mixed_width_column_calculation():
    """
    Test Case: LAYOUT-V-01 (Violation)
    Validates correct space distribution for mixed-width columns.

    Spec: LAYOUT_SPEC.md, Rule #4 - Directive Interpretation
    """
    # Arrange: Based on slide_2 from the Golden Case
    parser = Parser()
    layout_manager = LayoutManager()

    markdown = """Left content (implicit)
***
[width=25%]
Middle content (proportional)
***
[width=150]
Right content (absolute)"""

    # Correct calculations based on layout constants:
    # Slide width = 720, margins = 50*2 = 100, spacing = 2*10 = 20.
    # Content area = 720 - 100 = 620
    # Available width = 620 - 20 = 600
    # Absolute width = 150.
    # Proportional width (25% of available) = 0.25 * 600 = 150.
    # Implicit width gets the rest = 600 - 150 - 150 = 300.
    # Expected widths: [300, 150, 150]

    # Act
    deck = parser.parse(markdown)
    slide = deck.slides[0]
    layout_manager.calculate_positions(slide)

    # Find the row section (should be the root section containing columns)
    row_section = slide.sections[0]
    assert len(row_section.children) == 3, "Should have 3 columns"

    left_col, mid_col, right_col = row_section.children

    # Assert
    assert (
        abs(left_col.size[0] - 300.0) < 1e-9
    ), f"Left column width should be 300, got {left_col.size[0]}"
    assert (
        abs(mid_col.size[0] - 150.0) < 1e-9
    ), f"Middle column width should be 150, got {mid_col.size[0]}"
    assert (
        abs(right_col.size[0] - 150.0) < 1e-9
    ), f"Right column width should be 150, got {right_col.size[0]}"


def test_layout_v_01_simple_proportional_width():
    """
    Test Case: LAYOUT-V-01b (Additional case)
    Validates proportional width calculation with simpler case.

    Spec: LAYOUT_SPEC.md, Rule #4 - Directive Interpretation
    """
    # Arrange
    parser = Parser()
    layout_manager = LayoutManager()

    markdown = """[width=50%]
Left half
***
[width=50%]
Right half"""

    # Act
    deck = parser.parse(markdown)
    slide = deck.slides[0]
    layout_manager.calculate_positions(slide)

    # Find the row section
    row_section = slide.sections[0]
    assert len(row_section.children) == 2, "Should have 2 columns"

    left_col, right_col = row_section.children

    # Assert - each should get 50% of available width
    # Content area = 620, spacing = 10, available = 610, each gets 305
    expected_width = 305.0  # (620 - 10) * 0.5 = 305
    assert (
        abs(left_col.size[0] - expected_width) < 1e-9
    ), f"Left column width should be {expected_width}, got {left_col.size[0]}"
    assert (
        abs(right_col.size[0] - expected_width) < 1e-9
    ), f"Right column width should be {expected_width}, got {right_col.size[0]}"
