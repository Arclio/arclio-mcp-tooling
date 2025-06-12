import gc
import os
import time
from concurrent.futures import ThreadPoolExecutor

import psutil
import pytest
from markdowndeck.layout import LayoutManager
from markdowndeck.models import (
    ElementType,
    Slide,
    TextElement,
)
from markdowndeck.overflow import OverflowManager
from markdowndeck.parser import Parser


class TestOverflowStress:
    """Stress tests for extreme conditions and performance validation."""

    @pytest.fixture
    def overflow_manager(self) -> OverflowManager:
        """Create overflow manager for stress testing."""
        return OverflowManager()

    @pytest.fixture
    def layout_manager(self) -> LayoutManager:
        """Create layout manager for positioning."""
        return LayoutManager()

    def test_stress_o_01(
        self, layout_manager: LayoutManager, overflow_manager: OverflowManager
    ):
        """
        Test Case: STRESS-O-01
        Tests performance with content that creates many continuations.
        From: docs/markdowndeck/testing/TEST_CASES_STRESS.md
        """
        performance_results = []

        for scale in [10, 100, 250]:  # Reduced scale for faster test runs
            elements = [
                TextElement(
                    element_type=ElementType.TEXT,
                    text=f"This is a longer content line for stress test item {i} to ensure it takes up enough vertical space to reliably trigger the overflow manager.",
                )
                for i in range(scale)
            ]
            slide = Slide(object_id=f"scale_{scale}_slide", elements=elements)

            positioned_slide = layout_manager.calculate_positions(slide)

            start_time = time.time()
            result_slides = overflow_manager.process_slide(positioned_slide)
            end_time = time.time()

            processing_time = end_time - start_time
            performance_results.append(
                {
                    "scale": scale,
                    "time": processing_time,
                    "slides_created": len(result_slides),
                }
            )
            assert (
                processing_time < scale * 0.2
            ), "Processing time should scale reasonably."
            assert len(result_slides) > 1, "Should create multiple slides."

    def test_stress_o_02(
        self, layout_manager: LayoutManager, overflow_manager: OverflowManager
    ):
        """
        Test Case: STRESS-O-02
        Tests for memory leaks during repeated processing.
        From: docs/markdowndeck/testing/TEST_CASES_STRESS.md
        """
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        for i in range(20):  # Reduced iterations
            elements = [
                TextElement(element_type=ElementType.TEXT, text=f"Item {j}" * 20)
                for j in range(50)
            ]
            slide = Slide(object_id=f"mem_test_{i}", elements=elements)

            positioned_slide = layout_manager.calculate_positions(slide)
            result_slides = overflow_manager.process_slide(positioned_slide)

            del result_slides
            del slide
            del positioned_slide
            if i % 5 == 0:
                gc.collect()

        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory

        max_acceptable_growth = 100 * 1024 * 1024  # 100MB
        assert memory_growth < max_acceptable_growth, "Potential memory leak detected."

    def test_stress_o_03(self):
        """
        Test Case: STRESS-O-03
        Tests thread safety with concurrent processing.
        From: docs/markdowndeck/testing/TEST_CASES_STRESS.md
        """

        def process_slide_task(slide_id):
            parser = Parser()
            layout_manager = LayoutManager()
            overflow_manager = OverflowManager()

            markdown = f"# Slide {slide_id}\n" + "\n".join(
                [f"* Item {i}" for i in range(50)]
            )
            deck = parser.parse(markdown)
            positioned_slide = layout_manager.calculate_positions(deck.slides[0])
            final_slides = overflow_manager.process_slide(positioned_slide)
            return len(final_slides)

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(process_slide_task, i) for i in range(8)]
            results = [future.result() for future in futures]

        assert len(results) == 8
        assert all(
            res > 1 for res in results
        ), "All concurrent tasks should result in overflow."
