"""Unit tests for individual overflow handler components."""

import pytest
from markdowndeck.models import (
    Section,
    Slide,
)
from markdowndeck.overflow.detector import OverflowDetector


class TestOverflowDetector:
    """Unit tests for the OverflowDetector component."""

    @pytest.fixture
    def detector(self) -> OverflowDetector:
        """Create detector with standard body height."""
        return OverflowDetector(body_height=255.0)  # 405 - 90 - 30 - 30 (margins)

    def test_no_overflow_detection(self, detector):
        """Test that slides without overflow are correctly identified."""

        # Create slide with content that fits
        fitting_section = Section(
            id="fitting_section",
            type="section",
            position=(50, 150),
            size=(620, 100),  # Fits within body height
            elements=[],
        )

        slide = Slide(object_id="no_overflow_slide", sections=[fitting_section])

        overflowing_section = detector.find_first_overflowing_section(slide)

        assert (
            overflowing_section is None
        ), "Should not detect overflow for fitting content"

    def test_simple_overflow_detection(self, detector):
        """Test detection of basic overflow condition."""

        # Create section that overflows
        overflowing_section = Section(
            id="overflow_section",
            type="section",
            position=(50, 150),
            size=(620, 200),  # Bottom at 350, exceeds body_height of 255
            elements=[],
        )

        fitting_section = Section(
            id="fitting_section",
            type="section",
            position=(50, 100),
            size=(620, 50),  # Bottom at 150, fits
            elements=[],
        )

        slide = Slide(
            object_id="overflow_slide", sections=[fitting_section, overflowing_section]
        )

        detected = detector.find_first_overflowing_section(slide)

        assert detected is not None, "Should detect overflow"
        assert (
            detected.id == "overflow_section"
        ), "Should detect the overflowing section"

    def test_first_overflowing_section_selection(self, detector):
        """Test that the first overflowing section is selected when multiple overflow."""

        # Create multiple overflowing sections
        section1 = Section(
            id="first_overflow",
            type="section",
            position=(50, 200),
            size=(620, 100),  # Bottom at 300, overflows
            elements=[],
        )

        section2 = Section(
            id="second_overflow",
            type="section",
            position=(50, 250),
            size=(620, 100),  # Bottom at 350, also overflows
            elements=[],
        )

        slide = Slide(object_id="multi_overflow_slide", sections=[section1, section2])

        detected = detector.find_first_overflowing_section(slide)

        assert detected is not None, "Should detect overflow"
        assert (
            detected.id == "first_overflow"
        ), "Should detect the first overflowing section"

    def test_missing_position_size_handling(self, detector):
        """Test handling of sections missing position or size data."""

        # Create sections with missing data
        no_position_section = Section(
            id="no_position",
            type="section",
            position=None,
            size=(620, 100),
            elements=[],
        )

        no_size_section = Section(
            id="no_size", type="section", position=(50, 150), size=None, elements=[]
        )

        valid_overflowing_section = Section(
            id="valid_overflow",
            type="section",
            position=(50, 200),
            size=(620, 100),  # Overflows
            elements=[],
        )

        slide = Slide(
            object_id="missing_data_slide",
            sections=[no_position_section, no_size_section, valid_overflowing_section],
        )

        detected = detector.find_first_overflowing_section(slide)

        assert detected is not None, "Should find valid overflowing section"
        assert detected.id == "valid_overflow", "Should skip sections with missing data"

    def test_empty_slide_handling(self, detector):
        """Test handling of slides with no sections."""

        empty_slide = Slide(object_id="empty_slide", sections=[])

        detected = detector.find_first_overflowing_section(empty_slide)

        assert detected is None, "Should handle empty slide gracefully"

    def test_boundary_condition_detection(self, detector):
        """Test overflow detection at exact boundaries."""

        # Create section that exactly matches body height
        exact_fit_section = Section(
            id="exact_fit",
            type="section",
            position=(50, 0),
            size=(620, 255),  # Exactly matches body_height
            elements=[],
        )

        # Create section that exceeds by 1 point
        one_point_over_section = Section(
            id="one_point_over",
            type="section",
            position=(50, 0),
            size=(620, 256),  # Exceeds by 1 point
            elements=[],
        )

        exact_slide = Slide(object_id="exact_slide", sections=[exact_fit_section])
        over_slide = Slide(object_id="over_slide", sections=[one_point_over_section])

        # Exact fit should not overflow
        exact_detected = detector.find_first_overflowing_section(exact_slide)
        assert exact_detected is None, "Exact fit should not be detected as overflow"

        # One point over should overflow
        over_detected = detector.find_first_overflowing_section(over_slide)
        assert (
            over_detected is not None
        ), "One point over should be detected as overflow"
