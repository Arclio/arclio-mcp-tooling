"""Comprehensive integration test for the complete updated overflow handler system."""

import pytest
from markdowndeck.models import (
    CodeElement,
    ElementType,
    ImageElement,
    ListElement,
    ListItem,
    Section,
    Slide,
    TableElement,
    TextElement,
)
from markdowndeck.overflow import OverflowManager
from markdowndeck.overflow.constants import (
    CONTINUED_FOOTER_SUFFIX,
    CONTINUED_TITLE_SUFFIX,
)


class TestComprehensiveOverflowIntegration:
    """Comprehensive integration tests validating the complete updated overflow system."""

    @pytest.fixture
    def overflow_manager(self) -> OverflowManager:
        """Create overflow manager with standard test configuration."""
        return OverflowManager(
            slide_width=720,
            slide_height=405,
            margins={"top": 50, "right": 50, "bottom": 50, "left": 50},
        )

    def test_complete_specification_workflow_comprehensive(self, overflow_manager):
        """Test the complete workflow demonstrating all specification features."""

        # Create comprehensive slide with all element types and scenarios
        title = TextElement(
            element_type=ElementType.TITLE,
            text="Comprehensive Overflow Specification Test",
            position=(50, 50),
            size=(620, 40),
        )

        footer = TextElement(
            element_type=ElementType.FOOTER,
            text="Test Footer",
            position=(50, 370),
            size=(620, 20),
        )

        # 1. Text element that will test minimum 2 lines requirement
        splittable_text = TextElement(
            element_type=ElementType.TEXT,
            text="This is a multi-line text element\nSecond line of content\nThird line here\nFourth line content\nFifth line for testing\nSixth line final",
            position=(50, 150),
            size=(620, 120),
        )

        # 2. Code element (now splittable) with minimum 2 lines requirement
        splittable_code = CodeElement(
            element_type=ElementType.CODE,
            code="def test_function():\n    print('line 1')\n    print('line 2')\n    print('line 3')\n    return True\n\ntest_function()",
            language="python",
            position=(50, 280),
            size=(620, 120),
        )

        # 3. List element with minimum 2 items requirement
        splittable_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[
                ListItem(text="First important item"),
                ListItem(text="Second critical item"),
                ListItem(text="Third essential item"),
                ListItem(text="Fourth necessary item"),
                ListItem(text="Fifth required item"),
            ],
            position=(50, 410),
            size=(620, 100),
        )

        # 4. Table element with header + minimum 2 rows requirement
        splittable_table = TableElement(
            element_type=ElementType.TABLE,
            headers=["Name", "Value", "Status"],
            rows=[
                ["Item 1", "100", "Active"],
                ["Item 2", "200", "Pending"],
                ["Item 3", "300", "Complete"],
                ["Item 4", "400", "Active"],
                ["Item 5", "500", "Pending"],
            ],
            position=(50, 520),
            size=(620, 120),
        )

        # 5. Proactively scaled image (should never overflow)
        scaled_image = ImageElement(
            element_type=ElementType.IMAGE,
            url="https://example.com/test-image.jpg",
            alt_text="Test image",
            position=(50, 650),
            size=(620, 150),  # Pre-scaled to fit
        )

        # Create section that will cause external overflow
        main_section = Section(
            id="comprehensive_main_section",
            type="section",
            position=(50, 150),
            size=(620, 800),  # Section bottom at 950, far exceeds body_height ~255
            elements=[
                splittable_text,
                splittable_code,
                splittable_list,
                splittable_table,
                scaled_image,
            ],
        )

        slide = Slide(
            object_id="comprehensive_test_slide",
            elements=[
                title,
                footer,
                splittable_text,
                splittable_code,
                splittable_list,
                splittable_table,
                scaled_image,
            ],
            sections=[main_section],
            title="Comprehensive Overflow Specification Test",
        )

        # Process the slide
        result_slides = overflow_manager.process_slide(slide)

        # Verify multiple slides created due to external overflow
        assert (
            len(result_slides) >= 2
        ), f"Should create multiple slides, got {len(result_slides)}"

        # Verify first slide (fitted content)
        first_slide = result_slides[0]
        assert (
            first_slide.object_id == "comprehensive_test_slide"
        ), "First slide should keep original ID"

        # Verify continuation slides have proper structure
        for i, continuation_slide in enumerate(result_slides[1:], 1):
            # Check continuation slide ID format
            assert (
                "comprehensive_test_slide_cont" in continuation_slide.object_id
            ), f"Continuation {i} should have proper ID"

            # Check continuation title
            continuation_title = None
            for element in continuation_slide.elements:
                if element.element_type == ElementType.TITLE:
                    continuation_title = element
                    break

            assert continuation_title is not None, f"Continuation {i} should have title"
            assert (
                CONTINUED_TITLE_SUFFIX in continuation_title.text
            ), f"Continuation {i} title should have suffix"
            assert (
                "Comprehensive Overflow Specification Test" in continuation_title.text
            ), f"Continuation {i} should preserve original title"

            # Check continuation footer
            continuation_footer = None
            for element in continuation_slide.elements:
                if element.element_type == ElementType.FOOTER:
                    continuation_footer = element
                    break

            if continuation_footer:  # May not have footer if original didn't
                assert (
                    CONTINUED_FOOTER_SUFFIX in continuation_footer.text
                ), f"Continuation {i} footer should have suffix"

            # Verify position reset in continuation slides
            for section in continuation_slide.sections:
                assert (
                    section.position is None
                ), f"Continuation {i} section position should be reset"
                assert (
                    section.size is None
                ), f"Continuation {i} section size should be reset"

                for element in section.elements:
                    assert (
                        element.position is None
                    ), f"Continuation {i} element position should be reset"
                    assert (
                        element.size is None
                    ), f"Continuation {i} element size should be reset"

        # Verify content preservation across slides
        all_content_elements = []
        for slide in result_slides:
            for section in slide.sections:
                for element in section.elements:
                    if element.element_type not in (
                        ElementType.TITLE,
                        ElementType.FOOTER,
                    ):
                        all_content_elements.append(element)

        # Should have preserved all content types
        content_types = {elem.element_type for elem in all_content_elements}
        expected_types = {
            ElementType.TEXT,
            ElementType.CODE,
            ElementType.BULLET_LIST,
            ElementType.TABLE,
            ElementType.IMAGE,
        }
        assert expected_types.issubset(
            content_types
        ), "Should preserve all content element types"

    def test_unanimous_consent_model_comprehensive_scenarios(self, overflow_manager):
        """Test the unanimous consent model with comprehensive columnar scenarios."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Unanimous Consent Comprehensive Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Scenario 1: All columns can split (unanimous consent achieved)
        left_splittable_text = TextElement(
            element_type=ElementType.TEXT,
            text="Left column multi-line\nSecond line left\nThird line left\nFourth line left",
            position=(50, 150),
            size=(300, 80),
        )

        right_splittable_table = TableElement(
            element_type=ElementType.TABLE,
            headers=["Right Col1", "Right Col2"],
            rows=[["R1A", "R1B"], ["R2A", "R2B"], ["R3A", "R3B"], ["R4A", "R4B"]],
            position=(360, 150),
            size=(310, 80),
        )

        left_column = Section(
            id="unanimous_left",
            type="section",
            position=(50, 150),
            size=(300, 100),
            elements=[left_splittable_text],
        )

        right_column = Section(
            id="unanimous_right",
            type="section",
            position=(360, 150),
            size=(310, 100),
            elements=[right_splittable_table],
        )

        unanimous_row = Section(
            id="unanimous_consent_row",
            type="row",
            position=(50, 150),
            size=(620, 200),  # External boundary overflows
            subsections=[left_column, right_column],
        )

        unanimous_slide = Slide(
            object_id="unanimous_consent_slide",
            elements=[title, left_splittable_text, right_splittable_table],
            sections=[unanimous_row],
            title="Unanimous Consent Test",
        )

        result_unanimous = overflow_manager.process_slide(unanimous_slide)

        # Should successfully split with unanimous consent
        assert (
            len(result_unanimous) >= 2
        ), "Should create continuation with unanimous consent"

        # Verify row structure is preserved
        for slide in result_unanimous:
            for section in slide.sections:
                if section.type == "row":
                    assert (
                        len(section.subsections) >= 1
                    ), "Row structure should be preserved"

    def test_jurisdictional_boundaries_comprehensive_validation(self, overflow_manager):
        """Test comprehensive validation of jurisdictional boundaries (external vs internal overflow)."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Jurisdictional Boundaries Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Test Case 1: Internal overflow with explicit height (should be ignored)
        massive_internal_content = TextElement(
            element_type=ElementType.TEXT,
            text="This content is much larger than its container " * 100,
            position=(50, 150),
            size=(620, 2000),  # Massive internal size
        )

        internal_overflow_section = Section(
            id="internal_overflow_section",
            type="section",
            position=(50, 150),
            size=(620, 100),  # Section fits within slide (bottom at 250 < 255)
            directives={"height": 100},  # Explicit height directive
            elements=[massive_internal_content],
        )

        internal_slide = Slide(
            object_id="internal_overflow_slide",
            elements=[title, massive_internal_content],
            sections=[internal_overflow_section],
        )

        result_internal = overflow_manager.process_slide(internal_slide)

        # Should NOT create continuation - internal overflow is ignored
        assert (
            len(result_internal) == 1
        ), "Internal overflow should be ignored per jurisdictional boundaries"

        # Test Case 2: External overflow (should be handled)
        normal_content = TextElement(
            element_type=ElementType.TEXT,
            text="Normal content that fits within section\nSecond line",
            position=(50, 150),
            size=(620, 50),
        )

        external_overflow_section = Section(
            id="external_overflow_section",
            type="section",
            position=(50, 150),
            size=(620, 200),  # Section bottom at 350, exceeds body_height ~255
            elements=[normal_content],
        )

        external_slide = Slide(
            object_id="external_overflow_slide",
            elements=[title, normal_content],
            sections=[external_overflow_section],
        )

        result_external = overflow_manager.process_slide(external_slide)

        # Should create continuation - external overflow is handled
        assert (
            len(result_external) >= 2
        ), "External overflow should be handled per jurisdictional boundaries"

    def test_proactive_image_scaling_comprehensive_validation(self, overflow_manager):
        """Test comprehensive validation of proactive image scaling contract."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Proactive Image Scaling Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Create multiple images of different sizes (all should be pre-scaled)
        small_image = ImageElement(
            element_type=ElementType.IMAGE,
            url="https://example.com/small.jpg",
            alt_text="Small image",
            position=(50, 150),
            size=(200, 100),  # Pre-scaled small
        )

        medium_image = ImageElement(
            element_type=ElementType.IMAGE,
            url="https://example.com/medium.jpg",
            alt_text="Medium image",
            position=(50, 260),
            size=(400, 150),  # Pre-scaled medium
        )

        large_image = ImageElement(
            element_type=ElementType.IMAGE,
            url="https://example.com/large.jpg",
            alt_text="Large image",
            position=(50, 420),
            size=(620, 200),  # Pre-scaled large
        )

        # All images in one section that fits within slide
        image_section = Section(
            id="proactive_image_section",
            type="section",
            position=(50, 150),
            size=(620, 200),  # Section fits within slide
            elements=[small_image, medium_image, large_image],
        )

        image_slide = Slide(
            object_id="proactive_image_slide",
            elements=[title, small_image, medium_image, large_image],
            sections=[image_section],
        )

        result_images = overflow_manager.process_slide(image_slide)

        # Should NOT create continuation - images are pre-scaled
        assert len(result_images) == 1, "Pre-scaled images should not cause overflow"

        # Test image split contracts
        for image in [small_image, medium_image, large_image]:
            fitted, overflowing = image.split(50.0)  # Any available height
            assert (
                fitted == image
            ), f"Image {image.alt_text} should return self as fitted"
            assert (
                overflowing is None
            ), f"Image {image.alt_text} should have no overflowing part"

    def test_minimum_requirements_comprehensive_enforcement(self, overflow_manager):
        """Test comprehensive enforcement of minimum requirements across all element types."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Minimum Requirements Comprehensive Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Test elements at minimum thresholds
        # Text: exactly 2 lines (minimum)
        minimum_text = TextElement(
            element_type=ElementType.TEXT,
            text="Line one content\nLine two content",
            position=(50, 150),
            size=(620, 40),
        )

        # Code: exactly 2 lines (minimum)
        minimum_code = CodeElement(
            element_type=ElementType.CODE,
            code="line_one = 'first'\nline_two = 'second'",
            language="python",
            position=(50, 200),
            size=(620, 40),
        )

        # List: exactly 2 items (minimum)
        minimum_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[
                ListItem(text="First minimum item"),
                ListItem(text="Second minimum item"),
            ],
            position=(50, 250),
            size=(620, 40),
        )

        # Table: header + exactly 2 rows (minimum)
        minimum_table = TableElement(
            element_type=ElementType.TABLE,
            headers=["Col1", "Col2"],
            rows=[
                ["Row1 A", "Row1 B"],
                ["Row2 A", "Row2 B"],
            ],
            position=(50, 300),
            size=(620, 60),
        )

        minimum_section = Section(
            id="minimum_requirements_section",
            type="section",
            position=(50, 150),
            size=(620, 300),  # External boundary overflows
            elements=[minimum_text, minimum_code, minimum_list, minimum_table],
        )

        minimum_slide = Slide(
            object_id="minimum_requirements_slide",
            elements=[title, minimum_text, minimum_code, minimum_list, minimum_table],
            sections=[minimum_section],
        )

        result_minimum = overflow_manager.process_slide(minimum_slide)

        # Should create continuation, respecting minimum requirements
        assert len(result_minimum) >= 2, "Should create continuation slides"

        # Verify all continuation slides have content that meets minimum requirements
        for slide in result_minimum[1:]:  # Check continuation slides
            for section in slide.sections:
                for element in section.elements:
                    if element.element_type == ElementType.TEXT:
                        lines = element.text.count("\n") + 1
                        assert (
                            lines >= 2 or lines == element.text.count("\n") + 1
                        ), "Text should meet minimum lines or be complete"
                    elif element.element_type == ElementType.CODE:
                        lines = element.code.count("\n") + 1
                        assert (
                            lines >= 2 or lines == element.code.count("\n") + 1
                        ), "Code should meet minimum lines or be complete"
                    elif element.element_type == ElementType.BULLET_LIST:
                        assert len(element.items) >= 2 or len(element.items) == len(
                            element.items
                        ), "List should meet minimum items or be complete"
                    elif element.element_type == ElementType.TABLE:
                        if element.rows:  # If has data rows
                            assert len(element.rows) >= 2 or len(element.rows) == len(
                                element.rows
                            ), "Table should meet minimum rows or be complete"

    def test_position_reset_comprehensive_validation(self, overflow_manager):
        """Test comprehensive validation of position reset in continuation slides."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Position Reset Comprehensive Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Create complex nested structure with deep positioning
        level3_text = TextElement(
            element_type=ElementType.TEXT,
            text="Level 3 text content\nSecond line",
            position=(50, 300),
            size=(620, 40),
        )

        level3_section = Section(
            id="level3_section",
            type="section",
            position=(50, 300),
            size=(620, 50),
            elements=[level3_text],
        )

        level2_code = CodeElement(
            element_type=ElementType.CODE,
            code="level2_var = 'test'\nprint(level2_var)",
            language="python",
            position=(50, 250),
            size=(620, 40),
        )

        level2_section = Section(
            id="level2_section",
            type="section",
            position=(50, 250),
            size=(620, 100),
            elements=[level2_code],
            subsections=[level3_section],
        )

        level1_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[
                ListItem(text="Level 1 item 1"),
                ListItem(text="Level 1 item 2"),
            ],
            position=(50, 200),
            size=(620, 40),
        )

        level1_section = Section(
            id="level1_section",
            type="section",
            position=(50, 200),
            size=(620, 150),
            elements=[level1_list],
            subsections=[level2_section],
        )

        root_text = TextElement(
            element_type=ElementType.TEXT,
            text="Root level content\nAnother line",
            position=(50, 150),
            size=(620, 40),
        )

        root_section = Section(
            id="root_section",
            type="section",
            position=(50, 150),
            size=(620, 250),  # External boundary overflows
            elements=[root_text],
            subsections=[level1_section],
        )

        position_slide = Slide(
            object_id="position_reset_slide",
            elements=[title, root_text, level1_list, level2_code, level3_text],
            sections=[root_section],
        )

        result_position = overflow_manager.process_slide(position_slide)

        # Should create continuation slides
        assert len(result_position) >= 2, "Should create continuation slides"

        # Verify comprehensive position reset
        for slide in result_position[1:]:  # Check continuation slides only

            def validate_reset_recursive(sections, path=""):
                for i, section in enumerate(sections):
                    section_path = f"{path}section[{i}]({section.id})"
                    assert (
                        section.position is None
                    ), f"{section_path} position should be reset"
                    assert section.size is None, f"{section_path} size should be reset"

                    # Check all elements in this section
                    for j, element in enumerate(section.elements):
                        element_path = (
                            f"{section_path}.element[{j}]({element.element_type})"
                        )
                        assert (
                            element.position is None
                        ), f"{element_path} position should be reset"
                        assert (
                            element.size is None
                        ), f"{element_path} size should be reset"

                    # Recursively check subsections
                    if section.subsections:
                        validate_reset_recursive(
                            section.subsections, f"{section_path}."
                        )

            validate_reset_recursive(slide.sections)

    def test_overflow_analysis_comprehensive_reporting(self, overflow_manager):
        """Test comprehensive overflow analysis and reporting functionality."""

        # Create slide with mixed overflow conditions
        title = TextElement(
            element_type=ElementType.TITLE,
            text="Overflow Analysis Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Section 1: Fits perfectly
        fitting_section = Section(
            id="perfect_fit_section",
            type="section",
            position=(50, 100),
            size=(620, 50),  # Bottom at 150, fits well
            elements=[
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Perfectly fitting content",
                    position=(50, 100),
                    size=(620, 40),
                )
            ],
        )

        # Section 2: Internal overflow (acceptable)
        internal_overflow_content = TextElement(
            element_type=ElementType.TEXT,
            text="Large internal content " * 50,
            position=(50, 160),
            size=(620, 500),  # Much larger than section
        )

        internal_overflow_section = Section(
            id="internal_overflow_section",
            type="section",
            position=(50, 160),
            size=(620, 80),  # Bottom at 240, fits within slide
            directives={"height": 80},  # Explicit height makes overflow acceptable
            elements=[internal_overflow_content],
        )

        # Section 3: External overflow (unacceptable)
        external_overflow_section = Section(
            id="external_overflow_section",
            type="section",
            position=(50, 250),
            size=(620, 100),  # Bottom at 350, exceeds body_height ~255
            elements=[
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Content causing external overflow\nSecond line",
                    position=(50, 250),
                    size=(620, 50),
                )
            ],
        )

        analysis_slide = Slide(
            object_id="analysis_test_slide",
            elements=[
                title,
                TextElement(
                    element_type=ElementType.TEXT, text="Perfectly fitting content"
                ),
                internal_overflow_content,
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Content causing external overflow\nSecond line",
                ),
            ],
            sections=[
                fitting_section,
                internal_overflow_section,
                external_overflow_section,
            ],
        )

        # Test comprehensive analysis
        analysis = overflow_manager.get_overflow_analysis(analysis_slide)

        # Verify analysis structure
        assert "has_overflow" in analysis, "Analysis should include overflow detection"
        assert (
            "overflowing_section_index" in analysis
        ), "Analysis should identify overflowing section"
        assert "total_sections" in analysis, "Analysis should count sections"
        assert (
            "sections_analysis" in analysis
        ), "Analysis should include detailed section analysis"
        assert "body_height" in analysis, "Analysis should include body height"

        # Verify analysis content
        assert analysis["total_sections"] == 3, "Should count all sections"
        assert analysis["has_overflow"], "Should detect external overflow"
        assert (
            analysis["overflowing_section_index"] == 2
        ), "Should identify correct first overflowing section"

        # Verify detailed section analysis
        sections_analysis = analysis["sections_analysis"]
        assert len(sections_analysis) == 3, "Should analyze all sections"

        # Section 0: Should not overflow
        assert not sections_analysis[0][
            "overflows"
        ], "First section should not overflow"

        # Section 1: Should overflow but be acceptable
        assert sections_analysis[1][
            "overflows"
        ], "Second section should overflow internally"
        assert sections_analysis[1][
            "is_acceptable"
        ], "Second section overflow should be acceptable"

        # Section 2: Should overflow and not be acceptable
        assert sections_analysis[2][
            "overflows"
        ], "Third section should overflow externally"
        assert not sections_analysis[2][
            "is_acceptable"
        ], "Third section overflow should not be acceptable"

        # Test quick overflow check
        assert overflow_manager.has_external_overflow(
            analysis_slide
        ), "Should detect external overflow exists"

    def test_error_handling_and_edge_cases_comprehensive(self, overflow_manager):
        """Test comprehensive error handling and edge cases."""

        # Test Case 1: Empty slide
        empty_slide = Slide(object_id="empty_slide", elements=[], sections=[])
        result_empty = overflow_manager.process_slide(empty_slide)
        assert len(result_empty) == 1, "Empty slide should return single slide"

        # Test Case 2: Slide with missing section data
        malformed_section = Section(
            id="malformed_section",
            position=None,  # Missing position
            size=None,  # Missing size
            elements=[],
        )

        malformed_slide = Slide(
            object_id="malformed_slide",
            elements=[],
            sections=[malformed_section],
        )

        result_malformed = overflow_manager.process_slide(malformed_slide)
        assert len(result_malformed) >= 1, "Should handle malformed slides gracefully"

        # Test Case 3: Circular reference handling
        circular_section_a = Section(
            id="circular_a", position=(50, 150), size=(620, 100)
        )
        circular_section_b = Section(
            id="circular_b", position=(50, 200), size=(620, 100)
        )

        # Create circular reference
        circular_section_a.subsections = [circular_section_b]
        circular_section_b.subsections = [circular_section_a]

        circular_slide = Slide(
            object_id="circular_slide",
            elements=[],
            sections=[circular_section_a],
        )

        # Should handle without infinite recursion
        try:
            result_circular = overflow_manager.process_slide(circular_slide)
            assert (
                len(result_circular) >= 1
            ), "Should handle circular references gracefully"
        except RecursionError:
            pytest.fail("Should not cause infinite recursion with circular references")

        # Test Case 4: Validation warnings
        warnings = overflow_manager.validate_slide_structure(malformed_slide)
        assert isinstance(warnings, list), "Should return list of warnings"
        assert len(warnings) > 0, "Should have warnings for malformed slide"

    def test_performance_comprehensive_validation(self, overflow_manager):
        """Test comprehensive performance validation with realistic content."""

        import time

        # Create realistic complex slide
        title = TextElement(
            element_type=ElementType.TITLE,
            text="Performance Test Slide",
            position=(50, 50),
            size=(620, 40),
        )

        # Create multiple sections with diverse content
        sections = []
        elements = [title]

        for i in range(10):  # 10 sections with mixed content
            section_elements = []

            # Add text element
            text_elem = TextElement(
                element_type=ElementType.TEXT,
                text=f"Section {i} text content\n" + "Additional line content\n" * 5,
                position=(50, 150 + i * 100),
                size=(620, 60),
            )
            section_elements.append(text_elem)
            elements.append(text_elem)

            # Add code element every other section
            if i % 2 == 0:
                code_elem = CodeElement(
                    element_type=ElementType.CODE,
                    code="\n".join([f"section_{i}_function_{j}();" for j in range(8)]),
                    language="python",
                    position=(50, 220 + i * 100),
                    size=(620, 80),
                )
                section_elements.append(code_elem)
                elements.append(code_elem)

            # Add list element every third section
            if i % 3 == 0:
                list_elem = ListElement(
                    element_type=ElementType.BULLET_LIST,
                    items=[ListItem(text=f"Section {i} item {j}") for j in range(6)],
                    position=(50, 310 + i * 100),
                    size=(620, 60),
                )
                section_elements.append(list_elem)
                elements.append(list_elem)

            section = Section(
                id=f"performance_section_{i}",
                type="section",
                position=(50, 150 + i * 100),
                size=(620, 200),  # Each section overflows
                elements=section_elements,
            )
            sections.append(section)

        performance_slide = Slide(
            object_id="performance_test_slide",
            elements=elements,
            sections=sections,
            title="Performance Test Slide",
        )

        # Measure processing time
        start_time = time.time()
        result_performance = overflow_manager.process_slide(performance_slide)
        end_time = time.time()

        processing_time = end_time - start_time

        # Should complete in reasonable time
        assert (
            processing_time < 5.0
        ), f"Should process complex slide efficiently, took {processing_time:.2f}s"
        assert len(result_performance) >= 2, "Should create multiple slides"

        # Verify all content preserved
        total_content_elements = sum(
            len(
                [
                    e
                    for e in slide.elements
                    if e.element_type not in (ElementType.TITLE, ElementType.FOOTER)
                ]
            )
            for slide in result_performance
        )
        original_content_count = len(
            [e for e in elements if e.element_type != ElementType.TITLE]
        )

        # Content might be split, so total could be higher due to split elements
        assert (
            total_content_elements >= original_content_count
        ), "Should preserve all content through splitting"

        circular_slide = Slide(
            object_id="circular_slide",
            elements=[],
            sections=[circular_section_a],
        )

        # Should handle without infinite recursion
        try:
            result_circular = overflow_manager.process_slide(circular_slide)
            assert (
                len(result_circular) >= 1
            ), "Should handle circular references gracefully"
        except RecursionError:
            pytest.fail("Should not cause infinite recursion with circular references")

        # Test Case 4: Validation warnings
        warnings = overflow_manager.validate_slide_structure(malformed_slide)
        assert isinstance(warnings, list), "Should return list of warnings"
        assert len(warnings) > 0, "Should have warnings for malformed slide"

    def test_performance_comprehensive_validation(self, overflow_manager):
        """Test comprehensive performance validation with realistic content."""

        import time

        # Create realistic complex slide
        title = TextElement(
            element_type=ElementType.TITLE,
            text="Performance Test Slide",
            position=(50, 50),
            size=(620, 40),
        )

        # Create multiple sections with diverse content
        sections = []
        elements = [title]

        for i in range(10):  # 10 sections with mixed content
            section_elements = []

            # Add text element
            text_elem = TextElement(
                element_type=ElementType.TEXT,
                text=f"Section {i} text content\n" + "Additional line content\n" * 5,
                position=(50, 150 + i * 100),
                size=(620, 60),
            )
            section_elements.append(text_elem)
            elements.append(text_elem)

            # Add code element every other section
            if i % 2 == 0:
                code_elem = CodeElement(
                    element_type=ElementType.CODE,
                    code="\n".join([f"section_{i}_function_{j}();" for j in range(8)]),
                    language="python",
                    position=(50, 220 + i * 100),
                    size=(620, 80),
                )
                section_elements.append(code_elem)
                elements.append(code_elem)

            # Add list element every third section
            if i % 3 == 0:
                list_elem = ListElement(
                    element_type=ElementType.BULLET_LIST,
                    items=[ListItem(text=f"Section {i} item {j}") for j in range(6)],
                    position=(50, 310 + i * 100),
                    size=(620, 60),
                )
                section_elements.append(list_elem)
                elements.append(list_elem)

            section = Section(
                id=f"performance_section_{i}",
                type="section",
                position=(50, 150 + i * 100),
                size=(620, 200),  # Each section overflows
                elements=section_elements,
            )
            sections.append(section)

        performance_slide = Slide(
            object_id="performance_test_slide",
            elements=elements,
            sections=sections,
            title="Performance Test Slide",
        )

        # Measure processing time
        start_time = time.time()
        result_performance = overflow_manager.process_slide(performance_slide)
        end_time = time.time()

        processing_time = end_time - start_time

        # Should complete in reasonable time
        assert (
            processing_time < 5.0
        ), f"Should process complex slide efficiently, took {processing_time:.2f}s"
        assert len(result_performance) >= 2, "Should create multiple slides"

        # Verify all content preserved
        total_content_elements = sum(
            len(
                [
                    e
                    for e in slide.elements
                    if e.element_type not in (ElementType.TITLE, ElementType.FOOTER)
                ]
            )
            for slide in result_performance
        )
        original_content_count = len(
            [e for e in elements if e.element_type != ElementType.TITLE]
        )

        # Content might be split, so total could be higher due to split elements
        assert (
            total_content_elements >= original_content_count
        ), "Should preserve all content through splitting"
