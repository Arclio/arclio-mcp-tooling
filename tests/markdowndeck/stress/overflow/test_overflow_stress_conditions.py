"""Stress and performance tests for overflow handler system."""

import gc
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from markdowndeck.models import (
    ElementType,
    Section,
    Slide,
    TableElement,
    TextElement,
)
from markdowndeck.overflow import OverflowManager
from markdowndeck.overflow.constants import MINIMUM_CONTENT_RATIO_TO_SPLIT


class TestOverflowStressConditions:
    """Stress tests for extreme conditions and performance validation."""

    @pytest.fixture
    def overflow_manager(self) -> OverflowManager:
        """Create overflow manager for stress testing."""
        return OverflowManager(
            slide_width=720,
            slide_height=405,
            margins={"top": 50, "right": 50, "bottom": 50, "left": 50},
        )

    def test_exponential_content_growth_performance(self, overflow_manager):
        """Test performance with exponentially growing content sizes."""

        performance_results = []

        for scale in [10, 100, 1000, 5000]:
            title = TextElement(
                element_type=ElementType.TITLE,
                text=f"Scale {scale} Performance Test",
                position=(50, 50),
                size=(620, 40),
            )

            # Create table with exponentially growing content
            headers = ["Column 1", "Column 2", "Column 3"]
            rows = [
                [f"Row {i} Cell {j}" for j in range(1, 4)] for i in range(1, scale + 1)
            ]

            large_table = TableElement(
                element_type=ElementType.TABLE,
                headers=headers,
                rows=rows,
                position=(50, 150),
                size=(620, scale * 2),  # Height grows with content
            )

            section = Section(
                id=f"scale_{scale}_section",
                type="section",
                position=(50, 150),
                size=(620, 200),
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
                    "time_per_slide": (
                        processing_time / len(result_slides) if result_slides else 0
                    ),
                }
            )

            # Performance should scale reasonably
            assert (
                processing_time < scale * 0.01
            ), f"Processing time {processing_time:.3f}s should scale reasonably for {scale} rows"
            assert (
                len(result_slides) >= 2
            ), f"Should create multiple slides for scale {scale}"

        # Verify performance doesn't degrade exponentially
        for i in range(1, len(performance_results)):
            prev_result = performance_results[i - 1]
            curr_result = performance_results[i]

            scale_factor = curr_result["scale"] / prev_result["scale"]
            time_factor = (
                curr_result["time"] / prev_result["time"]
                if prev_result["time"] > 0
                else 1
            )

            # Time increase should be less than quadratic relative to scale increase
            assert (
                time_factor < scale_factor**1.5
            ), f"Performance degradation too severe: {time_factor} vs {scale_factor}"

    def test_maximum_recursion_depth_handling(self, overflow_manager):
        """Test handling of maximum recursion depth scenarios."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Max Recursion Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Create extremely deep nesting that could trigger recursion limits
        content = TextElement(
            element_type=ElementType.TEXT,
            text="Deep nested content",
            position=(50, 150),
            size=(620, 50),
        )

        # Build 100 levels of nesting
        current_section = Section(
            id="level_100",
            type="section",
            position=(50, 150),
            size=(620, 200),
            elements=[content],
        )

        for level in range(99, 0, -1):
            parent = Section(
                id=f"level_{level}",
                type="section",
                position=(50, 150),
                size=(620, 200),
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
        except RecursionError:
            pytest.fail("Should not hit recursion limit with deep section nesting")

    def test_memory_leak_detection_repeated_processing(self, overflow_manager):
        """Test for memory leaks during repeated processing."""

        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Perform many iterations to detect memory leaks
        for iteration in range(50):
            title = TextElement(
                element_type=ElementType.TITLE,
                text=f"Memory Test Iteration {iteration}",
                position=(50, 50),
                size=(620, 40),
            )

            # Create large content that gets split
            large_content = TextElement(
                element_type=ElementType.TEXT,
                text="Large content for memory testing " * 100,
                position=(50, 150),
                size=(620, 500),
            )

            section = Section(
                id=f"memory_test_section_{iteration}",
                type="section",
                position=(50, 150),
                size=(620, 200),
                elements=[large_content],
            )

            slide = Slide(
                object_id=f"memory_test_slide_{iteration}",
                elements=[title, large_content],
                sections=[section],
                title=f"Memory Test Iteration {iteration}",
            )

            result_slides = overflow_manager.process_slide(slide)

            # Clear references to help detect leaks
            del result_slides
            del slide
            del section
            del large_content
            del title

            # Force garbage collection every 10 iterations
            if iteration % 10 == 0:
                gc.collect()
                current_memory = process.memory_info().rss
                memory_growth = current_memory - initial_memory

                # Memory growth should be bounded
                max_acceptable_growth = 50 * 1024 * 1024  # 50MB
                assert (
                    memory_growth < max_acceptable_growth
                ), f"Potential memory leak detected: {memory_growth} bytes after {iteration} iterations"

    def test_concurrent_processing_thread_safety(self, overflow_manager):
        """Test thread safety with concurrent overflow processing."""

        def process_slide_task(slide_id):
            """Task function for concurrent processing."""
            title = TextElement(
                element_type=ElementType.TITLE,
                text=f"Concurrent Slide {slide_id}",
                position=(50, 50),
                size=(620, 40),
            )

            content = TextElement(
                element_type=ElementType.TEXT,
                text=f"Concurrent content {slide_id} " * 50,
                position=(50, 150),
                size=(620, 300),
            )

            section = Section(
                id=f"concurrent_section_{slide_id}",
                type="section",
                position=(50, 150),
                size=(620, 200),
                elements=[content],
            )

            slide = Slide(
                object_id=f"concurrent_slide_{slide_id}",
                elements=[title, content],
                sections=[section],
                title=f"Concurrent Slide {slide_id}",
            )

            # Each thread processes its own slide
            result_slides = overflow_manager.process_slide(slide)
            return len(result_slides)

        # Test concurrent processing with multiple threads
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(process_slide_task, i) for i in range(20)]
            results = [future.result() for future in futures]

        # All tasks should complete successfully
        assert len(results) == 20, "All concurrent tasks should complete"
        assert all(
            result >= 2 for result in results
        ), "All slides should create continuations"

    def test_edge_case_boundary_arithmetic(self, overflow_manager):
        """Test arithmetic edge cases in boundary calculations."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Boundary Arithmetic Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Test with floating point precision edge cases
        precise_height = 100.333333333333  # Floating point precision test

        content = TextElement(
            element_type=ElementType.TEXT,
            text="Precise height content",
            position=(50, 150),
            size=(620, precise_height),
        )

        # Mock split to test exact arithmetic
        def precise_split(available_height):
            ratio = available_height / precise_height
            if (
                abs(ratio - MINIMUM_CONTENT_RATIO_TO_SPLIT) < 1e-10
            ):  # Floating point comparison
                # Exactly at threshold
                fitted = TextElement(
                    element_type=ElementType.TEXT,
                    text="Fitted at exact threshold",
                    size=(620, available_height),
                )
                overflowing = TextElement(
                    element_type=ElementType.TEXT,
                    text="Overflowing from exact threshold",
                    size=(620, precise_height - available_height),
                )
                return fitted, overflowing
            if ratio >= MINIMUM_CONTENT_RATIO_TO_SPLIT:
                fitted = TextElement(
                    element_type=ElementType.TEXT,
                    text="Fitted above threshold",
                    size=(620, available_height),
                )
                overflowing = TextElement(
                    element_type=ElementType.TEXT,
                    text="Overflowing above threshold",
                    size=(620, precise_height - available_height),
                )
                return fitted, overflowing
            return None, content

        content.split = precise_split

        section = Section(
            id="precise_section",
            type="section",
            position=(50, 150),
            size=(620, 200),
            elements=[content],
        )

        slide = Slide(
            object_id="precise_slide",
            elements=[title, content],
            sections=[section],
            title="Boundary Arithmetic Test",
        )

        # Test with available height exactly at threshold
        overflow_manager.body_height = 150 + (
            precise_height * MINIMUM_CONTENT_RATIO_TO_SPLIT
        )

        result_slides = overflow_manager.process_slide(slide)

        # Should handle floating point precision correctly
        assert (
            len(result_slides) >= 1
        ), "Should handle floating point precision edge cases"

    def test_massive_nested_list_stress(self, overflow_manager):
        """Test with massively nested list structures."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Massive Nested List Stress Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Create deeply nested list with many items at each level
        def create_nested_items(depth, items_per_level, current_level=0):
            if current_level >= depth:
                return []

            items = []
            for i in range(items_per_level):
                item = ListItem(
                    text=f"Level {current_level} Item {i}", level=current_level
                )
                if current_level < depth - 1:
                    item.children = create_nested_items(
                        depth, items_per_level, current_level + 1
                    )
                items.append(item)
            return items

        # Create 5 levels deep with 10 items per level = 10^5 total items
        massive_items = create_nested_items(depth=5, items_per_level=10)

        massive_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=massive_items,
            position=(50, 150),
            size=(620, 10000),  # Very large
        )

        section = Section(
            id="massive_list_section",
            type="section",
            position=(50, 150),
            size=(620, 200),
            elements=[massive_list],
        )

        slide = Slide(
            object_id="massive_list_slide",
            elements=[title, massive_list],
            sections=[section],
            title="Massive Nested List Stress Test",
        )

        start_time = time.time()
        result_slides = overflow_manager.process_slide(slide)
        end_time = time.time()

        processing_time = end_time - start_time

        # Should complete in reasonable time despite massive nesting
        assert (
            processing_time < 30.0
        ), f"Should handle massive nested list efficiently, took {processing_time:.2f}s"
        assert len(result_slides) >= 2, "Should create continuation slides"

    def test_algorithmic_complexity_validation(self, overflow_manager):
        """Validate that algorithm complexity is reasonable for various input sizes."""

        complexity_data = []

        # Test with different section counts
        section_counts = [1, 5, 10, 25, 50]

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
                content = TextElement(
                    element_type=ElementType.TEXT,
                    text=f"Section {i} content that overflows",
                    position=(50, 150 + i * 10),
                    size=(620, 100),
                )
                elements.append(content)

                section = Section(
                    id=f"complexity_section_{i}",
                    type="section",
                    position=(50, 150 + i * 10),
                    size=(620, 50),  # Smaller than content
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

        # Verify algorithmic complexity is reasonable (should be roughly linear or sub-quadratic)
        for i in range(1, len(complexity_data)):
            prev_data = complexity_data[i - 1]
            curr_data = complexity_data[i]

            section_ratio = curr_data["section_count"] / prev_data["section_count"]
            time_ratio = (
                curr_data["processing_time"] / prev_data["processing_time"]
                if prev_data["processing_time"] > 0
                else 1
            )

            # Time complexity should not exceed quadratic
            max_acceptable_ratio = section_ratio**2
            assert (
                time_ratio <= max_acceptable_ratio * 2
            ), f"Algorithmic complexity too high: time ratio {time_ratio} vs section ratio {section_ratio}"

    def test_pathological_split_scenarios(self, overflow_manager):
        """Test pathological cases where splitting behavior might be problematic."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Pathological Split Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Create element that splits into many tiny pieces
        def pathological_split(available_height):
            # Always splits into very small pieces to test iteration limits
            if available_height > 1:
                fitted = TextElement(
                    element_type=ElementType.TEXT,
                    text="Tiny fitted piece",
                    size=(620, 1),  # Always 1 point high
                )
                overflowing = TextElement(
                    element_type=ElementType.TEXT,
                    text="Remaining pathological content",
                    size=(620, 1000 - 1),  # Rest of the content
                )
                overflowing.split = pathological_split  # Recursive splitting
                return fitted, overflowing
            return None, TextElement(
                element_type=ElementType.TEXT,
                text="Final pathological content",
                size=(620, 1000),
            )

        pathological_content = TextElement(
            element_type=ElementType.TEXT,
            text="Pathological content that splits badly",
            position=(50, 150),
            size=(620, 1000),
        )
        pathological_content.split = pathological_split

        section = Section(
            id="pathological_section",
            type="section",
            position=(50, 150),
            size=(620, 200),
            elements=[pathological_content],
        )

        slide = Slide(
            object_id="pathological_slide",
            elements=[title, pathological_content],
            sections=[section],
            title="Pathological Split Test",
        )

        start_time = time.time()
        result_slides = overflow_manager.process_slide(slide)
        end_time = time.time()

        processing_time = end_time - start_time

        # Should handle pathological splitting without infinite loops
        assert (
            processing_time < 10.0
        ), f"Should handle pathological splitting efficiently, took {processing_time:.2f}s"
        assert (
            len(result_slides) < 500
        ), f"Should not create excessive slides from pathological splitting, got {len(result_slides)}"

    def test_extreme_dimension_edge_cases(self, overflow_manager):
        """Test with extreme dimension values that might cause numerical issues."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Extreme Dimensions Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Test with very large dimensions
        extreme_content = TextElement(
            element_type=ElementType.TEXT,
            text="Content with extreme dimensions",
            position=(50, 150),
            size=(620, 999999999),  # Extremely large height
        )

        extreme_section = Section(
            id="extreme_section",
            type="section",
            position=(50, 150),
            size=(620, 200),
            elements=[extreme_content],
        )

        slide = Slide(
            object_id="extreme_slide",
            elements=[title, extreme_content],
            sections=[extreme_section],
            title="Extreme Dimensions Test",
        )

        # Should handle extreme values gracefully
        result_slides = overflow_manager.process_slide(slide)

        assert len(result_slides) >= 1, "Should handle extreme dimensions gracefully"

        # Test with very small dimensions
        tiny_content = TextElement(
            element_type=ElementType.TEXT,
            text="Tiny content",
            position=(50, 150),
            size=(620, 0.001),  # Extremely small height
        )

        tiny_section = Section(
            id="tiny_section",
            type="section",
            position=(50, 150),
            size=(620, 200),
            elements=[tiny_content],
        )

        tiny_slide = Slide(
            object_id="tiny_slide",
            elements=[title, tiny_content],
            sections=[tiny_section],
            title="Tiny Dimensions Test",
        )

        result_slides = overflow_manager.process_slide(tiny_slide)

        assert len(result_slides) >= 1, "Should handle tiny dimensions gracefully"

    def test_overflow_manager_configuration_stress(self):
        """Test overflow manager with extreme configuration values."""

        # Test with extreme slide dimensions
        extreme_manager = OverflowManager(
            slide_width=10000,  # Very wide
            slide_height=50,  # Very short
            margins={"top": 10, "right": 10, "bottom": 10, "left": 10},
        )

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Extreme Config Test",
            position=(10, 10),
            size=(9980, 20),
        )

        content = TextElement(
            element_type=ElementType.TEXT,
            text="Content in extreme slide",
            position=(10, 35),
            size=(9980, 30),  # Overflows the very short slide
        )

        section = Section(
            id="extreme_config_section",
            type="section",
            position=(10, 35),
            size=(9980, 20),  # Very short available space
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

        # Test with extreme margins
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
