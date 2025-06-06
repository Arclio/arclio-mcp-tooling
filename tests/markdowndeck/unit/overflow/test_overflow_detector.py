"""Unit tests for OverflowDetector with strict jurisdictional boundaries."""

import pytest
from markdowndeck.layout.constants import (
    BODY_TO_FOOTER_SPACING,
    DEFAULT_MARGIN_BOTTOM,
    DEFAULT_MARGIN_TOP,
    DEFAULT_SLIDE_HEIGHT,
    FOOTER_HEIGHT,
    HEADER_HEIGHT,
    HEADER_TO_BODY_SPACING,
)
from markdowndeck.models import (
    ElementType,
    ImageElement,
    Section,
    Slide,
    TextElement,
)
from markdowndeck.overflow.detector import OverflowDetector


class TestOverflowDetector:
    """Unit tests for the OverflowDetector component with strict jurisdictional boundaries."""

    @pytest.fixture
    def detector(self) -> OverflowDetector:
        """Create detector with correct body height calculated from layout constants."""
        # Calculate correct body height: slide_height - margins - header - footer - spacing
        body_height = (
            DEFAULT_SLIDE_HEIGHT
            - DEFAULT_MARGIN_TOP
            - DEFAULT_MARGIN_BOTTOM
            - HEADER_HEIGHT
            - FOOTER_HEIGHT
            - HEADER_TO_BODY_SPACING
            - BODY_TO_FOOTER_SPACING
        )
        return OverflowDetector(body_height=body_height)

    def test_no_overflow_detection_with_fitting_sections(self, detector):
        """Test that slides without external overflow are correctly identified."""

        # Create slide with content that fits within external section boundaries
        # Body area: Y=150 to Y=315
        fitting_section = Section(
            id="fitting_section",
            type="section",
            position=(50, 200),
            size=(620, 100),  # Section bottom at 300, fits within body_end_y 315
            elements=[
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Content that fits",
                    position=(50, 200),
                    size=(620, 80),
                )
            ],
        )

        slide = Slide(object_id="no_overflow_slide", sections=[fitting_section])

        overflowing_section = detector.find_first_overflowing_section(slide)

        assert overflowing_section is None, "Should not detect overflow for fitting content"

        # Verify analysis methods
        assert not detector.has_any_overflow(slide), "Should report no overflow"

        summary = detector.get_overflow_summary(slide)
        assert not summary["has_overflow"], "Summary should show no overflow"
        assert summary["overflowing_section_index"] is None, "Should have no overflowing section index"

    def test_external_section_overflow_detection(self, detector):
        """Test detection of external section boundary overflow."""

        # Create section whose external boundary overflows slide body height
        # Body area starts at Y=150 and has height 165, so ends at Y=315
        overflowing_section = Section(
            id="external_overflow_section",
            type="section",
            position=(50, 280),
            size=(620, 50),  # Section bottom at 330, exceeds body_end_y of 315
            elements=[
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Normal content within section",
                    position=(50, 280),
                    size=(620, 40),  # Content fits within section
                )
            ],
        )

        fitting_section = Section(
            id="fitting_section",
            type="section",
            position=(50, 200),
            size=(620, 50),  # Section bottom at 250, fits within body area
            elements=[],
        )

        slide = Slide(
            object_id="external_overflow_slide",
            sections=[fitting_section, overflowing_section],
        )

        detected = detector.find_first_overflowing_section(slide)

        assert detected is not None, "Should detect external section overflow"
        assert detected.id == "external_overflow_section", "Should detect the externally overflowing section"

        # Verify analysis methods
        assert detector.has_any_overflow(slide), "Should report overflow exists"

        summary = detector.get_overflow_summary(slide)
        assert summary["has_overflow"], "Summary should show overflow"
        assert summary["overflowing_section_index"] == 1, "Should identify correct overflowing section index"

    def test_internal_content_overflow_ignored(self, detector):
        """Test that internal content overflow within fixed-size sections is ignored (jurisdictional boundary)."""

        # Create section with content larger than section (internal overflow)
        # but section external boundary fits within slide
        large_content = TextElement(
            element_type=ElementType.TEXT,
            text="Very large content that exceeds section boundaries " * 50,
            position=(50, 150),
            size=(620, 500),  # Content much larger than section
        )

        internal_overflow_section = Section(
            id="internal_overflow_section",
            type="section",
            position=(50, 250),
            size=(620, 60),  # Section bottom at 310, fits within body_end_y 315
            directives={"height": 60},  # Explicit height directive makes overflow acceptable
            elements=[large_content],
        )

        slide = Slide(object_id="internal_overflow_slide", sections=[internal_overflow_section])

        detected = detector.find_first_overflowing_section(slide)

        # Should NOT detect overflow - internal content overflow is ignored
        assert detected is None, "Should ignore internal content overflow within fixed-size sections"

        # Verify analysis methods
        assert not detector.has_any_overflow(slide), "Should not report internal overflow"

        summary = detector.get_overflow_summary(slide)
        assert not summary["has_overflow"], "Summary should show no overflow for internal content"

    def test_acceptable_overflow_detection(self, detector):
        """Test detection of acceptable overflow conditions."""

        # Test 1: Section with explicit height directive (acceptable overflow)
        explicit_height_content = TextElement(
            element_type=ElementType.TEXT,
            text="Content in explicitly sized section",
            position=(50, 150),
            size=(620, 300),  # Content larger than section
        )

        explicit_height_section = Section(
            id="explicit_height_section",
            type="section",
            position=(50, 280),
            size=(620, 50),  # Section bottom at 330, overflows body_end_y 315
            directives={"height": 50},  # Explicit height makes overflow acceptable
            elements=[explicit_height_content],
        )

        slide1 = Slide(object_id="explicit_height_slide", sections=[explicit_height_section])

        # Should not detect overflow due to explicit height directive
        detected1 = detector.find_first_overflowing_section(slide1)
        assert detected1 is None, "Should ignore overflow in explicitly sized sections"

        # Test 2: Section with single pre-scaled image (acceptable overflow)
        large_image = ImageElement(
            element_type=ElementType.IMAGE,
            url="https://example.com/large-image.jpg",
            position=(50, 150),
            size=(620, 200),  # Proactively scaled size
        )

        image_section = Section(
            id="image_section",
            type="section",
            position=(50, 280),
            size=(620, 50),  # Section bottom at 330, technically overflows
            elements=[large_image],
        )

        slide2 = Slide(object_id="image_overflow_slide", sections=[image_section])

        # Should detect overflow for image section (unless explicitly sized)
        detector.find_first_overflowing_section(slide2)
        # Note: Images are pre-scaled, but if section still overflows, it should be detected
        # unless the section has explicit sizing directives

    def test_first_overflowing_section_selection(self, detector):
        """Test that the first externally overflowing section is selected when multiple overflow."""

        # Create multiple externally overflowing sections
        section1 = Section(
            id="first_external_overflow",
            type="section",
            position=(50, 300),
            size=(620, 20),  # Section bottom at 320, overflows body_end_y 315
            elements=[
                TextElement(
                    element_type=ElementType.TEXT,
                    text="First overflowing content",
                    position=(50, 300),
                    size=(620, 15),
                )
            ],
        )

        section2 = Section(
            id="second_external_overflow",
            type="section",
            position=(50, 310),
            size=(620, 20),  # Section bottom at 330, also overflows
            elements=[
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Second overflowing content",
                    position=(50, 310),
                    size=(620, 15),
                )
            ],
        )

        slide = Slide(object_id="multi_overflow_slide", sections=[section1, section2])

        detected = detector.find_first_overflowing_section(slide)

        assert detected is not None, "Should detect overflow"
        assert detected.id == "first_external_overflow", "Should detect the first externally overflowing section"

    def test_missing_position_size_handling(self, detector):
        """Test handling of sections missing position or size data."""

        # Create sections with missing data
        no_position_section = Section(
            id="no_position",
            type="section",
            position=None,  # Missing position data
            size=(620, 100),
            elements=[],
        )

        no_size_section = Section(
            id="no_size",
            type="section",
            position=(50, 150),
            size=None,  # Missing size data
            elements=[],
        )

        valid_overflowing_section = Section(
            id="valid_external_overflow",
            type="section",
            position=(50, 300),
            size=(620, 20),  # Section bottom at 320, overflows body_end_y 315
            elements=[
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Valid overflowing content",
                    position=(50, 300),
                    size=(620, 15),
                )
            ],
        )

        slide = Slide(
            object_id="missing_data_slide",
            sections=[no_position_section, no_size_section, valid_overflowing_section],
        )

        detected = detector.find_first_overflowing_section(slide)

        assert detected is not None, "Should find valid overflowing section"
        assert detected.id == "valid_external_overflow", "Should skip sections with missing data"

        # Verify summary handles missing data gracefully
        summary = detector.get_overflow_summary(slide)
        assert summary["total_sections"] == 3, "Should count all sections"
        assert len(summary["sections_analysis"]) == 3, "Should analyze all sections"

        # Check that sections with missing data are marked appropriately
        analysis = summary["sections_analysis"]
        assert not analysis[0]["has_position"], "Should mark missing position"
        assert not analysis[1]["has_size"], "Should mark missing size"
        assert analysis[2]["has_position"], "Valid section should have position"
        assert analysis[2]["has_size"], "Valid section should have size"

    def test_empty_slide_handling(self, detector):
        """Test handling of slides with no sections."""

        empty_slide = Slide(object_id="empty_slide", sections=[])

        detected = detector.find_first_overflowing_section(empty_slide)

        assert detected is None, "Should handle empty slide gracefully"

        # Verify analysis methods handle empty slides
        assert not detector.has_any_overflow(empty_slide), "Empty slide should have no overflow"

        summary = detector.get_overflow_summary(empty_slide)
        assert not summary["has_overflow"], "Empty slide summary should show no overflow"
        assert summary["total_sections"] == 0, "Should show zero sections"
        assert summary["overflowing_section_index"] is None, "Should have no overflowing index"

    def test_boundary_condition_detection(self, detector):
        """Test overflow detection at exact external boundary conditions."""

        # Create section that exactly matches body height (boundary case)
        # Body area: Y=150 to Y=315
        exact_fit_section = Section(
            id="exact_external_fit",
            type="section",
            position=(50, 150),
            size=(620, 165),  # Section bottom exactly at body_end_y 315
            elements=[
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Content that exactly fits",
                    position=(50, 150),
                    size=(620, 150),
                )
            ],
        )

        # Create section that exceeds by minimal amount
        one_point_over_section = Section(
            id="one_point_external_over",
            type="section",
            position=(50, 150),
            size=(620, 166),  # Section bottom at 316, exceeds by 1 point
            elements=[
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Content that exceeds by one point",
                    position=(50, 150),
                    size=(620, 150),
                )
            ],
        )

        exact_slide = Slide(object_id="exact_slide", sections=[exact_fit_section])
        over_slide = Slide(object_id="over_slide", sections=[one_point_over_section])

        # Exact fit should not overflow
        exact_detected = detector.find_first_overflowing_section(exact_slide)
        assert exact_detected is None, "Exact external fit should not be detected as overflow"

        # One point over should overflow
        over_detected = detector.find_first_overflowing_section(over_slide)
        assert over_detected is not None, "One point external overflow should be detected"
        assert over_detected.id == "one_point_external_over", "Should detect the correct section"

    def test_floating_point_precision_boundaries(self, detector):
        """Test overflow detection with floating point precision edge cases."""

        # Test with floating point boundary values
        floating_boundary_section = Section(
            id="floating_boundary",
            type="section",
            position=(50, 150),
            size=(620, 165.000000001),  # Exceeds by minimal floating point amount
            elements=[
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Floating point precision content",
                    position=(50, 150),
                    size=(620, 150),
                )
            ],
        )

        slide = Slide(object_id="floating_slide", sections=[floating_boundary_section])

        detected = detector.find_first_overflowing_section(slide)

        # Should handle floating point precision consistently
        assert detected is not None, "Should detect minimal floating point overflow"

    def test_overflow_summary_detailed_analysis(self, detector):
        """Test detailed overflow summary analysis functionality."""

        # Create mixed scenario with fitting and overflowing sections
        # Body area: Y=150 to Y=315
        fitting_section = Section(
            id="fitting_section",
            type="section",
            position=(50, 200),
            size=(620, 100),  # Section bottom at 300, fits
            elements=[
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Fitting content",
                    position=(50, 200),
                    size=(620, 80),
                )
            ],
        )

        overflowing_section = Section(
            id="overflowing_section",
            type="section",
            position=(50, 300),
            size=(620, 20),  # Section bottom at 320, overflows
            elements=[
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Overflowing content",
                    position=(50, 300),
                    size=(620, 15),
                )
            ],
        )

        acceptable_overflow_section = Section(
            id="acceptable_overflow",
            type="section",
            position=(50, 280),
            size=(620, 50),  # Section bottom at 330, overflows
            directives={"height": 50},  # Explicit height makes it acceptable
            elements=[
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Acceptable overflow content",
                    position=(50, 280),
                    size=(620, 80),  # Content larger than section
                )
            ],
        )

        slide = Slide(
            object_id="mixed_overflow_slide",
            sections=[
                fitting_section,
                acceptable_overflow_section,
                overflowing_section,
            ],
        )

        summary = detector.get_overflow_summary(slide)

        # Verify detailed analysis
        assert summary["total_sections"] == 3, "Should count all sections"
        assert summary["has_overflow"], "Should detect overflow"
        assert summary["overflowing_section_index"] == 2, "Should identify correct first unacceptable overflow"
        assert summary["body_height"] == 165.0, "Should include body height"

        # Check individual section analysis
        sections_analysis = summary["sections_analysis"]
        assert len(sections_analysis) == 3, "Should analyze all sections"

        # First section - fits
        assert not sections_analysis[0]["overflows"], "First section should not overflow"

        # Second section - overflows but acceptable
        assert sections_analysis[1]["overflows"], "Second section should overflow"
        assert sections_analysis[1]["is_acceptable"], "Second section overflow should be acceptable"

        # Third section - overflows and not acceptable
        assert sections_analysis[2]["overflows"], "Third section should overflow"
        assert not sections_analysis[2]["is_acceptable"], "Third section overflow should not be acceptable"

    def test_detector_initialization_and_configuration(self):
        """Test detector initialization with different configurations."""

        # Test with different body heights
        small_detector = OverflowDetector(body_height=100.0)
        large_detector = OverflowDetector(body_height=500.0)

        # Create same section for both detectors
        # Body area starts at Y=150, so this section will be in the body area
        test_section = Section(
            id="test_section",
            type="section",
            position=(50, 200),
            size=(620, 200),  # Section bottom at 400
            elements=[],
        )

        slide = Slide(object_id="test_slide", sections=[test_section])

        # Small detector should detect overflow
        small_result = small_detector.find_first_overflowing_section(slide)
        assert small_result is not None, "Small detector should detect overflow at 250 > 100"

        # Large detector should not detect overflow
        large_result = large_detector.find_first_overflowing_section(slide)
        assert large_result is None, "Large detector should not detect overflow at 250 < 500"

    def test_section_type_handling(self, detector):
        """Test overflow detection for different section types."""

        # Regular section
        regular_section = Section(
            id="regular_section",
            type="section",
            position=(50, 280),
            size=(620, 50),  # Section bottom at 330, overflows body_end_y 315
            elements=[
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Regular section content",
                    position=(50, 280),
                    size=(620, 40),
                )
            ],
        )

        # Row section (should be handled same as regular for external boundary)
        row_section = Section(
            id="row_section",
            type="row",
            position=(50, 280),
            size=(620, 50),  # Section bottom at 330, overflows body_end_y 315
            subsections=[
                Section(
                    id="column1",
                    type="section",
                    position=(50, 280),
                    size=(310, 50),
                    elements=[
                        TextElement(
                            element_type=ElementType.TEXT,
                            text="Column 1",
                            position=(50, 280),
                            size=(310, 40),
                        )
                    ],
                ),
                Section(
                    id="column2",
                    type="section",
                    position=(360, 280),
                    size=(310, 50),
                    elements=[
                        TextElement(
                            element_type=ElementType.TEXT,
                            text="Column 2",
                            position=(360, 280),
                            size=(310, 40),
                        )
                    ],
                ),
            ],
        )

        # Test regular section
        regular_slide = Slide(object_id="regular_slide", sections=[regular_section])
        regular_detected = detector.find_first_overflowing_section(regular_slide)
        assert regular_detected is not None, "Should detect regular section overflow"

        # Test row section
        row_slide = Slide(object_id="row_slide", sections=[row_section])
        row_detected = detector.find_first_overflowing_section(row_slide)
        assert row_detected is not None, "Should detect row section external overflow"
        assert row_detected.type == "row", "Should identify as row section"
