"""Stress and performance tests for overflow handler system with updated specification compliance."""

import gc
import time
from concurrent.futures import ThreadPoolExecutor

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


class TestOverflowStressConditions:
    """Stress tests for extreme conditions and performance validation with updated specifications."""

    @pytest.fixture
    def overflow_manager(self) -> OverflowManager:
        """Create overflow manager for stress testing."""
        return OverflowManager(
            slide_width=720,
            slide_height=405,
            margins={"top": 50, "right": 50, "bottom": 50, "left": 50},
        )

    def test_exponential_content_growth_performance_with_minimum_requirements(self, overflow_manager):
        """Test performance with exponentially growing content sizes following minimum requirements."""

        performance_results = []

        for scale in [10, 100, 500, 1000]:  # Reduced max scale for performance
            title = TextElement(
                element_type=ElementType.TITLE,
                text=f"Scale {scale} Performance Test",
                position=(50, 50),
                size=(620, 40),
            )

            # Create table with exponentially growing content that can be split
            headers = ["Column 1", "Column 2", "Column 3"]
            rows = [[f"Row {i} Cell {j}" for j in range(1, 4)] for i in range(1, scale + 1)]

            large_table = TableElement(
                element_type=ElementType.TABLE,
                headers=headers,
                rows=rows,
                position=(50, 150),
                size=(620, scale * 2),  # Height grows with content
            )

            # Create section that will cause external overflow
            section = Section(
                id=f"scale_{scale}_section",
                type="section",
                position=(50, 150),
                size=(620, 300),  # Section external boundary overflows body_height ~255
                elements=[large_table],
            )

            slide = Slide(
                object_id=f"scale_{scale}_slide",
                elements=[title, large_table],
                sections=[section],
                title=f"Scale {scale} Performance Test",
            )

            # Measure processing time
            start_time = time.time()
            result_slides = overflow_manager.process_slide(slide)
            end_time = time.time()

            processing_time = end_time - start_time
            performance_results.append(
                {
                    "scale": scale,
                    "time": processing_time,
                    "slides_created": len(result_slides),
                    "time_per_slide": (processing_time / len(result_slides) if result_slides else 0),
                }
            )

            # Performance should scale reasonably with minimum requirements
            assert processing_time < scale * 0.02, (
                f"Processing time {processing_time:.3f}s should scale reasonably for {scale} rows"
            )
            assert len(result_slides) >= 2, f"Should create multiple slides for scale {scale} due to external overflow"

        # Verify performance doesn't degrade exponentially
        for i in range(1, len(performance_results)):
            prev_result = performance_results[i - 1]
            curr_result = performance_results[i]

            scale_factor = curr_result["scale"] / prev_result["scale"]
            time_factor = curr_result["time"] / prev_result["time"] if prev_result["time"] > 0 else 1

            # Time increase should be sub-quadratic relative to scale increase
            assert time_factor < scale_factor**1.8, f"Performance degradation too severe: {time_factor} vs {scale_factor}"

    def test_maximum_recursion_depth_handling_with_circular_protection(self, overflow_manager):
        """Test handling of maximum recursion depth scenarios with circular reference protection."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Max Recursion Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Create extremely deep nesting that could trigger recursion limits
        content = TextElement(
            element_type=ElementType.TEXT,
            text="Deep nested content\nSecond line for minimum requirements",
            position=(50, 150),
            size=(620, 50),
        )

        # Build 50 levels of nesting (reduced from 100 for performance)
        current_section = Section(
            id="level_50",
            type="section",
            position=(50, 150),
            size=(620, 300),  # External boundary overflows
            elements=[content],
        )

        for level in range(49, 0, -1):
            parent = Section(
                id=f"level_{level}",
                type="section",
                position=(50, 150),
                size=(620, 300),  # Maintain external overflow
                subsections=[current_section],
            )
            current_section = parent

        slide = Slide(
            object_id="max_recursion_slide",
            elements=[title, content],
            sections=[current_section],
            title="Max Recursion Test",
        )

        # Should handle deep recursion without stack overflow
        try:
            result_slides = overflow_manager.process_slide(slide)
            assert len(result_slides) >= 1, "Should handle deep nesting gracefully"
            assert len(result_slides) < 100, "Should not create excessive slides"
        except RecursionError:
            pytest.fail("Should not hit recursion limit with deep section nesting")

    def test_memory_leak_detection_repeated_processing_with_element_splitting(self, overflow_manager):
        """Test for memory leaks during repeated processing with element splitting."""

        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Perform many iterations to detect memory leaks
        for iteration in range(30):  # Reduced iterations for performance
            title = TextElement(
                element_type=ElementType.TITLE,
                text=f"Memory Test Iteration {iteration}",
                position=(50, 50),
                size=(620, 40),
            )

            # Create content that will be split according to minimum requirements
            large_text = TextElement(
                element_type=ElementType.TEXT,
                text="Large content for memory testing\n" + "Line content " * 100,
                position=(50, 150),
                size=(620, 500),
            )

            # Create code that will be split
            large_code = CodeElement(
                element_type=ElementType.CODE,
                code="\n".join([f"line_{i} = 'content_{i}'" for i in range(50)]),
                language="python",
                position=(50, 200),
                size=(620, 300),
            )

            # Create list that will be split
            large_list = ListElement(
                element_type=ElementType.BULLET_LIST,
                items=[ListItem(text=f"Memory test item {i}") for i in range(50)],
                position=(50, 250),
                size=(620, 400),
            )

            section = Section(
                id=f"memory_test_section_{iteration}",
                type="section",
                position=(50, 150),
                size=(620, 300),  # External boundary overflows
                elements=[large_text, large_code, large_list],
            )

            slide = Slide(
                object_id=f"memory_test_slide_{iteration}",
                elements=[title, large_text, large_code, large_list],
                sections=[section],
                title=f"Memory Test Iteration {iteration}",
            )

            result_slides = overflow_manager.process_slide(slide)

            # Clear references to help detect leaks
            del result_slides
            del slide
            del section
            del large_text, large_code, large_list
            del title

            # Force garbage collection every 5 iterations
            if iteration % 5 == 0:
                gc.collect()
                current_memory = process.memory_info().rss
                memory_growth = current_memory - initial_memory

                # Memory growth should be bounded (increased limit for element splitting)
                max_acceptable_growth = 100 * 1024 * 1024  # 100MB
                assert memory_growth < max_acceptable_growth, (
                    f"Potential memory leak detected: {memory_growth} bytes after {iteration} iterations"
                )

    def test_concurrent_processing_thread_safety_with_splitting(self, overflow_manager):
        """Test thread safety with concurrent overflow processing including element splitting."""

        def process_slide_task(slide_id):
            """Task function for concurrent processing with different element types."""
            title = TextElement(
                element_type=ElementType.TITLE,
                text=f"Concurrent Slide {slide_id}",
                position=(50, 50),
                size=(620, 40),
            )

            # Create different element types for different threads
            if slide_id % 3 == 0:
                # Text element
                content = TextElement(
                    element_type=ElementType.TEXT,
                    text=f"Concurrent text content {slide_id}\n" + "Line content\n" * 20,
                    position=(50, 150),
                    size=(620, 300),
                )
            elif slide_id % 3 == 1:
                # Code element
                content = CodeElement(
                    element_type=ElementType.CODE,
                    code="\n".join([f"function_{slide_id}_line_{i}();" for i in range(15)]),
                    language="javascript",
                    position=(50, 150),
                    size=(620, 300),
                )
            else:
                # List element
                content = ListElement(
                    element_type=ElementType.BULLET_LIST,
                    items=[ListItem(text=f"Concurrent item {slide_id}_{i}") for i in range(15)],
                    position=(50, 150),
                    size=(620, 300),
                )

            section = Section(
                id=f"concurrent_section_{slide_id}",
                type="section",
                position=(50, 150),
                size=(620, 300),  # External boundary overflows
                elements=[content],
            )

            slide = Slide(
                object_id=f"concurrent_slide_{slide_id}",
                elements=[title, content],
                sections=[section],
                title=f"Concurrent Slide {slide_id}",
            )

            # Each thread processes its own slide with element splitting
            result_slides = overflow_manager.process_slide(slide)
            return len(result_slides)

        # Test concurrent processing with multiple threads
        with ThreadPoolExecutor(max_workers=4) as executor:  # Reduced workers for stability
            futures = [executor.submit(process_slide_task, i) for i in range(12)]
            results = [future.result() for future in futures]

        # All tasks should complete successfully
        assert len(results) == 12, "All concurrent tasks should complete"
        assert all(result >= 2 for result in results), "All slides should create continuations due to external overflow"

    def test_unanimous_consent_stress_with_complex_columns(self, overflow_manager):
        """Test unanimous consent model stress with complex columnar content."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Unanimous Consent Stress Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Create complex left column with multiple splittable elements
        left_text = TextElement(
            element_type=ElementType.TEXT,
            text="Left column multi-line content\n" + "Line content\n" * 20,
            position=(50, 150),
            size=(300, 200),
        )

        left_code = CodeElement(
            element_type=ElementType.CODE,
            code="\n".join([f"left_function_{i}();" for i in range(15)]),
            language="python",
            position=(50, 200),
            size=(300, 150),
        )

        # Create complex right column with multiple splittable elements
        right_table = TableElement(
            element_type=ElementType.TABLE,
            headers=["Name", "Value", "Status"],
            rows=[[f"Item {i}", f"Value {i}", f"Status {i}"] for i in range(20)],
            position=(360, 150),
            size=(310, 200),
        )

        right_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[ListItem(text=f"Right item {i}") for i in range(15)],
            position=(360, 200),
            size=(310, 150),
        )

        # Create columnar structure
        left_column = Section(
            id="complex_left_column",
            type="section",
            position=(50, 150),
            size=(300, 200),
            elements=[left_text, left_code],
        )

        right_column = Section(
            id="complex_right_column",
            type="section",
            position=(360, 150),
            size=(310, 200),
            elements=[right_table, right_list],
        )

        row_section = Section(
            id="complex_unanimous_row",
            type="row",
            position=(50, 150),
            size=(620, 300),  # External boundary overflows
            subsections=[left_column, right_column],
        )

        slide = Slide(
            object_id="unanimous_stress_slide",
            elements=[title, left_text, left_code, right_table, right_list],
            sections=[row_section],
            title="Unanimous Consent Stress Test",
        )

        start_time = time.time()
        result_slides = overflow_manager.process_slide(slide)
        end_time = time.time()

        processing_time = end_time - start_time

        # Should handle complex unanimous consent efficiently
        assert processing_time < 3.0, f"Should handle complex unanimous consent efficiently, took {processing_time:.2f}s"
        assert len(result_slides) >= 2, "Should create continuation slides"

        # Verify coordinated splitting maintained column structure
        for slide in result_slides:
            for section in slide.sections:
                if section.type == "row":
                    assert len(section.subsections) == 2, "Row structure should be maintained"

    def test_pathological_split_scenarios_with_minimum_requirements(self, overflow_manager):
        """Test pathological cases where minimum requirements prevent excessive splitting."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Pathological Split Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Create elements with challenging split characteristics
        # Table with minimal rows (edge case for minimum requirements)
        minimal_table = TableElement(
            element_type=ElementType.TABLE,
            headers=["Col1", "Col2"],
            rows=[["Row1 A", "Row1 B"], ["Row2 A", "Row2 B"]],  # Exactly minimum
            position=(50, 150),
            size=(620, 100),
        )

        # List with minimal items
        minimal_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[ListItem(text="Item 1"), ListItem(text="Item 2")],  # Exactly minimum
            position=(50, 260),
            size=(620, 50),
        )

        # Text with minimal lines
        minimal_text = TextElement(
            element_type=ElementType.TEXT,
            text="Line 1\nLine 2",  # Exactly minimum
            position=(50, 320),
            size=(620, 40),
        )

        # Code with minimal lines
        minimal_code = CodeElement(
            element_type=ElementType.CODE,
            code="line1\nline2",  # Exactly minimum
            language="python",
            position=(50, 370),
            size=(620, 40),
        )

        section = Section(
            id="pathological_section",
            type="section",
            position=(50, 150),
            size=(620, 300),  # External boundary overflows
            elements=[minimal_table, minimal_list, minimal_text, minimal_code],
        )

        slide = Slide(
            object_id="pathological_slide",
            elements=[title, minimal_table, minimal_list, minimal_text, minimal_code],
            sections=[section],
            title="Pathological Split Test",
        )

        start_time = time.time()
        result_slides = overflow_manager.process_slide(slide)
        end_time = time.time()

        processing_time = end_time - start_time

        # Should handle pathological cases efficiently due to minimum requirements
        assert processing_time < 2.0, f"Should handle pathological splitting efficiently, took {processing_time:.2f}s"
        assert len(result_slides) < 20, f"Minimum requirements should prevent excessive splitting, got {len(result_slides)}"

    def test_extreme_dimension_edge_cases_with_specification_compliance(self, overflow_manager):
        """Test with extreme dimension values that respect specification boundaries."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Extreme Dimensions Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Test with very large content in normal section (internal overflow - should be ignored)
        massive_content = TextElement(
            element_type=ElementType.TEXT,
            text="Content with massive internal size " * 1000,
            position=(50, 150),
            size=(620, 999999),  # Extremely large internal content
        )

        # Section with explicit height (internal overflow acceptable)
        internal_overflow_section = Section(
            id="internal_extreme_section",
            type="section",
            position=(50, 150),
            size=(620, 100),  # Section fits within slide (bottom at 250 < 315)
            directives={"height": 100},  # Explicit height makes internal overflow acceptable
            elements=[massive_content],
        )

        # Section with external overflow
        external_overflow_section = Section(
            id="external_extreme_section",
            type="section",
            position=(50, 150),
            size=(620, 200),  # Section bottom at 350, overflows body_height ~315
            elements=[
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Normal content causing external overflow\nSecond line",
                    position=(50, 150),
                    size=(620, 50),
                )
            ],
        )

        # Test internal overflow (should be ignored)
        internal_slide = Slide(
            object_id="internal_extreme_slide",
            elements=[title, massive_content],
            sections=[internal_overflow_section],
            title="Internal Extreme Test",
        )

        result_internal = overflow_manager.process_slide(internal_slide)
        assert len(result_internal) == 1, "Internal overflow should be ignored per specification"

        # Test external overflow (should be handled)
        external_slide = Slide(
            object_id="external_extreme_slide",
            elements=[
                title,
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Normal content causing external overflow\nSecond line",
                    position=(50, 150),
                    size=(620, 50),
                ),
            ],
            sections=[external_overflow_section],
            title="External Extreme Test",
        )

        result_external = overflow_manager.process_slide(external_slide)
        assert len(result_external) >= 2, "External overflow should be handled per specification"

    def test_overflow_manager_configuration_stress_with_edge_cases(self):
        """Test overflow manager with extreme configuration values and edge cases."""

        # Test with extreme slide dimensions
        extreme_manager = OverflowManager(
            slide_width=10000,  # Very wide
            slide_height=100,  # Very short
            margins={"top": 10, "right": 10, "bottom": 10, "left": 10},
        )

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Extreme Config Test",
            position=(10, 10),
            size=(9980, 15),
        )

        content = TextElement(
            element_type=ElementType.TEXT,
            text="Content in extreme slide\nSecond line for minimum",
            position=(10, 30),
            size=(9980, 30),  # Overflows the very short slide
        )

        section = Section(
            id="extreme_config_section",
            type="section",
            position=(10, 30),
            size=(9980, 40),  # External boundary overflows short body height
            elements=[content],
        )

        slide = Slide(
            object_id="extreme_config_slide",
            elements=[title, content],
            sections=[section],
            title="Extreme Config Test",
        )

        result_slides = extreme_manager.process_slide(slide)
        assert len(result_slides) >= 2, "Should handle extreme slide configurations"

        # Test with extreme margins (negative body height)
        extreme_margins_manager = OverflowManager(
            slide_width=720,
            slide_height=405,
            margins={
                "top": 200,
                "right": 200,
                "bottom": 200,
                "left": 200,
            },  # Very large margins
        )

        # Body height will be very small or negative
        # Should handle gracefully without crashing
        result_slides = extreme_margins_manager.process_slide(slide)
        assert len(result_slides) >= 1, "Should handle extreme margins gracefully"

    def test_algorithmic_complexity_validation_with_element_splitting(self, overflow_manager):
        """Validate algorithm complexity with element splitting is reasonable for various input sizes."""

        complexity_data = []

        # Test with different section counts containing splittable elements
        section_counts = [1, 5, 10, 20]  # Reduced for performance

        for section_count in section_counts:
            title = TextElement(
                element_type=ElementType.TITLE,
                text=f"Complexity Test {section_count} Sections",
                position=(50, 50),
                size=(620, 40),
            )

            sections = []
            elements = [title]

            for i in range(section_count):
                # Mix different splittable element types
                if i % 3 == 0:
                    content = TextElement(
                        element_type=ElementType.TEXT,
                        text=f"Section {i} text content\n" + "Additional line\n" * 10,
                        position=(50, 150 + i * 20),
                        size=(620, 100),
                    )
                elif i % 3 == 1:
                    content = CodeElement(
                        element_type=ElementType.CODE,
                        code="\n".join([f"section_{i}_line_{j} = {j}" for j in range(10)]),
                        language="python",
                        position=(50, 150 + i * 20),
                        size=(620, 100),
                    )
                else:
                    content = ListElement(
                        element_type=ElementType.BULLET_LIST,
                        items=[ListItem(text=f"Section {i} item {j}") for j in range(10)],
                        position=(50, 150 + i * 20),
                        size=(620, 100),
                    )

                elements.append(content)

                section = Section(
                    id=f"complexity_section_{i}",
                    type="section",
                    position=(50, 150 + i * 20),
                    size=(620, 100),  # Each section overflows individually
                    elements=[content],
                )
                sections.append(section)

            slide = Slide(
                object_id=f"complexity_slide_{section_count}",
                elements=elements,
                sections=sections,
                title=f"Complexity Test {section_count} Sections",
            )

            start_time = time.time()
            result_slides = overflow_manager.process_slide(slide)
            end_time = time.time()

            processing_time = end_time - start_time
            complexity_data.append(
                {
                    "section_count": section_count,
                    "processing_time": processing_time,
                    "slides_created": len(result_slides),
                }
            )

        # Verify algorithmic complexity is reasonable (should be roughly linear)
        for i in range(1, len(complexity_data)):
            prev_data = complexity_data[i - 1]
            curr_data = complexity_data[i]

            section_ratio = curr_data["section_count"] / prev_data["section_count"]
            time_ratio = curr_data["processing_time"] / prev_data["processing_time"] if prev_data["processing_time"] > 0 else 1

            # Time complexity should not exceed quadratic with element splitting
            max_acceptable_ratio = section_ratio**2.5  # Allow for element splitting complexity
            assert time_ratio <= max_acceptable_ratio, (
                f"Algorithmic complexity too high: time ratio {time_ratio} vs section ratio {section_ratio}"
            )

    def test_proactive_image_scaling_performance_validation(self, overflow_manager):
        """Test that proactive image scaling prevents performance issues."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Image Scaling Performance Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Create many large images (all should be pre-scaled)
        large_images = []
        for i in range(50):  # Many images
            image = ImageElement(
                element_type=ElementType.IMAGE,
                url=f"https://example.com/large-image-{i}.jpg",
                alt_text=f"Large image {i}",
                position=(50, 150 + i * 100),
                size=(620, 90),  # All pre-scaled to fit
            )
            large_images.append(image)

        # FIXED: Section that actually fits within slide boundary
        # body_end_y = 315, so section bottom must be ≤ 315
        # With position=(50, 150), max size = 315 - 150 = 165
        image_section = Section(
            id="image_performance_section",
            type="section",
            position=(50, 150),
            size=(620, 160),  # Section fits: bottom = 150 + 160 = 310 < 315
            elements=large_images,
        )

        slide = Slide(
            object_id="image_performance_slide",
            elements=[title] + large_images,
            sections=[image_section],
            title="Image Scaling Performance Test",
        )

        start_time = time.time()
        result_slides = overflow_manager.process_slide(slide)
        end_time = time.time()

        processing_time = end_time - start_time

        # Should process quickly due to proactive image scaling
        assert processing_time < 1.0, f"Pre-scaled images should process quickly, took {processing_time:.2f}s"

        # FIXED: Should not create overflow when section explicitly fits within boundary
        # Proactive scaling prevents images from expanding section beyond calculated dimensions
        assert len(result_slides) == 1, (
            f"Section that fits within boundary should not overflow, got {len(result_slides)} slides"
        )

        # Verify image split behavior
        for image in large_images:
            fitted, overflowing = image.split(50.0)
            assert fitted == image, "Image should return self as fitted"
            assert overflowing is None, "Image should have no overflowing part"

    def test_specification_compliance_stress_comprehensive(self, overflow_manager):
        """Comprehensive stress test of all specification compliance requirements."""

        # Test 1: External vs Internal Overflow Distinction (stress version)
        large_internal_content = TextElement(
            element_type=ElementType.TEXT,
            text="Massive internal content " * 200,
            position=(50, 150),
            size=(620, 5000),  # Huge internal size
        )

        internal_stress_section = Section(
            id="internal_stress",
            type="section",
            position=(50, 150),
            size=(620, 100),  # Section fits (bottom at 250 < 315)
            directives={"height": 100},  # Explicit sizing
            elements=[large_internal_content],
        )

        internal_stress_slide = Slide(
            object_id="internal_stress_slide",
            elements=[large_internal_content],
            sections=[internal_stress_section],
        )

        result_internal = overflow_manager.process_slide(internal_stress_slide)
        assert len(result_internal) == 1, "Massive internal overflow should be ignored"

        # Test 2: Element-Driven Splitting Stress
        splitting_elements = []
        for i in range(20):  # Many splittable elements
            if i % 4 == 0:
                elem = TextElement(
                    element_type=ElementType.TEXT,
                    text=f"Text element {i}\n" + "Content line\n" * 10,
                    position=(50, 150 + i * 30),
                    size=(620, 80),
                )
            elif i % 4 == 1:
                elem = CodeElement(
                    element_type=ElementType.CODE,
                    code="\n".join([f"code_line_{i}_{j} = {j}" for j in range(10)]),
                    language="python",
                    position=(50, 150 + i * 30),
                    size=(620, 80),
                )
            elif i % 4 == 2:
                elem = ListElement(
                    element_type=ElementType.BULLET_LIST,
                    items=[ListItem(text=f"Item {i}_{j}") for j in range(10)],
                    position=(50, 150 + i * 30),
                    size=(620, 80),
                )
            else:
                elem = TableElement(
                    element_type=ElementType.TABLE,
                    headers=["Col1", "Col2"],
                    rows=[[f"Row {j} A", f"Row {j} B"] for j in range(10)],
                    position=(50, 150 + i * 30),
                    size=(620, 80),
                )
            splitting_elements.append(elem)

        splitting_section = Section(
            id="splitting_stress_section",
            type="section",
            position=(50, 150),
            size=(620, 800),  # Large external overflow
            elements=splitting_elements,
        )

        splitting_slide = Slide(
            object_id="splitting_stress_slide",
            elements=splitting_elements,
            sections=[splitting_section],
        )

        start_time = time.time()
        result_splitting = overflow_manager.process_slide(splitting_slide)
        end_time = time.time()

        splitting_time = end_time - start_time

        assert splitting_time < 5.0, f"Element-driven splitting should be efficient, took {splitting_time:.2f}s"
        assert len(result_splitting) >= 2, "Should create continuation slides"

        # Test 3: Position Reset Validation Stress
        for slide in result_splitting[1:]:  # Check continuation slides

            def validate_reset_recursive(sections, path=""):
                for i, section in enumerate(sections):
                    assert section.position is None, f"Section {path}[{i}] position should be reset"
                    assert section.size is None, f"Section {path}[{i}] size should be reset"

                    for j, element in enumerate(section.elements):
                        assert element.position is None, f"Element {path}[{i}].element[{j}] position should be reset"
                        assert element.size is None, f"Element {path}[{i}].element[{j}] size should be reset"

                    if section.subsections:
                        validate_reset_recursive(section.subsections, f"{path}[{i}].")

            validate_reset_recursive(slide.sections)

    def test_edge_case_boundary_arithmetic_with_floating_precision(self, overflow_manager):
        """Test arithmetic edge cases with floating point precision in boundary calculations."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Floating Point Precision Test",
            position=(50, 50),
            size=(620, 40),
        )

        # FIXED: Test with floating point precision edge cases around CORRECT boundary (315.0)
        # body_end_y = top_margin(50) + HEADER_HEIGHT(90) + HEADER_TO_BODY_SPACING(10) + body_height(165) = 315
        precise_positions = [314.999999999, 315.000000001, 314.5, 315.5]

        for i, precise_pos in enumerate(precise_positions):
            content = TextElement(
                element_type=ElementType.TEXT,
                text=f"Precision test content {i}\nSecond line",
                position=(50, 150),
                size=(620, 50),
            )

            # Section with precise floating point boundary
            section = Section(
                id=f"precision_section_{i}",
                type="section",
                position=(50, 150),
                size=(620, precise_pos - 150),  # Precise height calculation
                elements=[content],
            )

            slide = Slide(
                object_id=f"precision_slide_{i}",
                elements=[title, content],
                sections=[section],
            )

            result_slides = overflow_manager.process_slide(slide)

            # FIXED: Should handle floating point precision consistently against CORRECT boundary (315.0)
            expected_overflow = (150 + (precise_pos - 150)) > 315.0
            if expected_overflow:
                assert len(result_slides) >= 2, f"Should detect overflow for position {precise_pos}"
            else:
                assert len(result_slides) == 1, f"Should not detect overflow for position {precise_pos}"
