import gc
import os
import time
from concurrent.futures import ThreadPoolExecutor

import psutil
from markdowndeck.layout import LayoutManager
from markdowndeck.models.slide import Slide
from markdowndeck.overflow import OverflowManager
from markdowndeck.parser import Parser


class TestOverflowStress:
    """Stress tests for extreme conditions and performance validation."""

    def _create_overflowing_slide(self, num_items: int) -> Slide:
        parser = Parser()
        layout_manager = LayoutManager()
        long_content = "\n".join([f"* List Item {i}" for i in range(num_items)])
        markdown = f"# Overflow Test\n{long_content}"
        unpositioned_slide = parser.parse(markdown).slides[0]
        return layout_manager.calculate_positions(unpositioned_slide)

    def test_stress_o_01(self):
        """Test Case: STRESS-O-01 - Tests performance with content that creates many continuations."""
        overflow_manager = OverflowManager()

        positioned_slide = self._create_overflowing_slide(250)

        start_time = time.time()
        result_slides = overflow_manager.process_slide(positioned_slide)
        end_time = time.time()

        processing_time = end_time - start_time
        print(f"Overflow processing for {len(result_slides)} slides took {processing_time:.4f} seconds.")

        assert processing_time < 5.0, "Overflow processing should be performant."
        assert len(result_slides) > 10, "Should create many continuation slides."

    def test_stress_o_02(self):
        """Test Case: STRESS-O-02 - Tests for memory leaks during repeated processing."""
        process = psutil.Process(os.getpid())
        gc.collect()
        initial_memory = process.memory_info().rss

        for i in range(15):
            overflow_manager = OverflowManager()
            positioned_slide = self._create_overflowing_slide(50)
            _ = overflow_manager.process_slide(positioned_slide)
            if i % 5 == 0:
                gc.collect()

        gc.collect()
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory

        print(f"Memory growth after 15 overflow cycles: {memory_growth / 1024 / 1024:.2f} MB")
        max_acceptable_growth = 50 * 1024 * 1024  # 50MB
        assert memory_growth < max_acceptable_growth, "Potential memory leak detected."

    def test_stress_o_03(self):
        """Test Case: STRESS-O-03 - Tests thread safety with concurrent processing."""

        def process_slide_task(slide_id: int):
            parser = Parser()
            layout_manager = LayoutManager()
            overflow_manager = OverflowManager()
            markdown = f"# Slide {slide_id}\n" + "\n".join([f"* Item {i}" for i in range(50)])
            deck = parser.parse(markdown)
            positioned_slide = layout_manager.calculate_positions(deck.slides[0])
            final_slides = overflow_manager.process_slide(positioned_slide)
            return len(final_slides)

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(process_slide_task, i) for i in range(8)]
            results = [future.result() for future in futures]

        assert len(results) == 8
        assert all(res > 1 for res in results), "All concurrent tasks should result in overflow."
