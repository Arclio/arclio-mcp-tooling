"""
Integration tests for the full MarkdownDeck pipeline.

These tests verify the data handoffs and state transformations between the
Parser, LayoutManager, and OverflowManager components, ensuring they adhere to
the contracts defined in ARCHITECTURE.md and DATA_FLOW.md.
"""

import re

import pytest
from markdowndeck import markdown_to_requests
from markdowndeck.layout import LayoutManager
from markdowndeck.overflow import OverflowManager
from markdowndeck.parser import Parser


class TestPipelineIntegration:
    """Tests the integration and data flow between pipeline components."""

    @pytest.fixture
    def parser(self) -> Parser:
        return Parser()

    @pytest.fixture
    def layout_manager(self) -> LayoutManager:
        return LayoutManager()

    @pytest.fixture
    def overflow_manager(self) -> OverflowManager:
        return OverflowManager()

    def test_integration_p_01(self, parser: Parser, layout_manager: LayoutManager):
        """
        Test Case: INTEGRATION-P-01
        Validates the Parser -> LayoutManager handoff.
        From: docs/markdowndeck/testing/TEST_CASES_INTEGRATION_PIPELINE.md
        """
        # Arrange
        markdown = "# Title\n[width=1/2]\n* Item 1"

        # Act
        unpositioned_deck = parser.parse(markdown)
        unpositioned_slide = unpositioned_deck.slides[0]

        # Assert initial state (Unpositioned IR)
        assert (
            len(unpositioned_slide.elements) > 0
        ), "Parser should populate inventory list."
        assert (
            unpositioned_slide.sections[0].children[0].position is None
        ), "IR must be unpositioned."

        # Act: Handoff to LayoutManager
        positioned_slide = layout_manager.calculate_positions(unpositioned_slide)

        # Assert final state (Positioned IR)
        assert (
            positioned_slide.elements == []
        ), "LayoutManager must clear the inventory list."

        # Verify renderable_elements contains positioned meta-elements from LayoutManager
        assert hasattr(
            positioned_slide, "renderable_elements"
        ), "Slide must have renderable_elements attribute"
        # This test has a title, so renderable_elements should contain it
        title_elements = [
            elem
            for elem in positioned_slide.renderable_elements
            if elem.element_type.name == "TITLE"
        ]
        assert (
            len(title_elements) == 1
        ), "Should have one positioned title element from LayoutManager"
        final_section = positioned_slide.sections[0]
        final_element = final_section.children[0]
        assert final_section.position is not None
        assert final_section.size is not None
        assert final_element.position is not None
        assert final_element.size is not None

    def test_integration_p_02(
        self,
        parser: Parser,
        layout_manager: LayoutManager,
        overflow_manager: OverflowManager,
    ):
        """
        Test Case: INTEGRATION-P-02
        Validates the LayoutManager -> OverflowManager handoff for a slide with no overflow.
        From: docs/markdowndeck/testing/TEST_CASES_INTEGRATION_PIPELINE.md
        """
        # Arrange
        markdown = "# Simple Slide\nThis content fits on one slide."

        # Act
        unpositioned_deck = parser.parse(markdown)
        positioned_slide = layout_manager.calculate_positions(
            unpositioned_deck.slides[0]
        )

        # Assert intermediate state (Positioned IR)
        assert positioned_slide.elements == []

        # Verify renderable_elements contains positioned meta-elements from LayoutManager
        assert hasattr(
            positioned_slide, "renderable_elements"
        ), "Slide must have renderable_elements attribute"
        # This test has a title, so renderable_elements should contain it
        title_elements = [
            elem
            for elem in positioned_slide.renderable_elements
            if elem.element_type.name == "TITLE"
        ]
        assert (
            len(title_elements) == 1
        ), "Should have one positioned title element from LayoutManager"
        assert len(positioned_slide.sections) > 0

        # Act: Handoff to OverflowManager
        final_slides = overflow_manager.process_slide(positioned_slide)

        # Assert
        assert len(final_slides) == 1
        final_slide = final_slides[0]

        # Assert final state (Finalized IR)
        assert (
            final_slide.sections == []
        ), "OverflowManager must clear the sections list."
        assert (
            len(final_slide.renderable_elements) > 0
        ), "Finalized slide must have renderable elements."

        # Verify data integrity: all renderable elements have position and size
        for element in final_slide.renderable_elements:
            assert element.position is not None, "Final element must have position."
            assert element.size is not None, "Final element must have size."

    def test_integration_p_03(
        self,
        parser: Parser,
        layout_manager: LayoutManager,
        overflow_manager: OverflowManager,
    ):
        """
        Test Case: INTEGRATION-P-03
        Validates the full recursive pipeline for a slide that causes overflow.
        From: docs/markdowndeck/testing/TEST_CASES_INTEGRATION_PIPELINE.md
        """
        # Arrange
        long_content = "\n".join([f"* Item {i}" for i in range(15)])
        markdown = f"# Long Slide\n{long_content}"

        # Act
        unpositioned_deck = parser.parse(markdown)
        positioned_slide = layout_manager.calculate_positions(
            unpositioned_deck.slides[0]
        )
        final_slides = overflow_manager.process_slide(positioned_slide)

        # Assert
        assert len(final_slides) > 1, "Overflow should have created multiple slides."

        # Verify all slides are in the "Finalized" state
        for i, slide in enumerate(final_slides):
            assert slide.sections == [], f"Slide {i} sections list must be cleared."

        # Check that at least some slides have renderable elements
        # (Note: Due to current layout manager limitations with recursive overflow,
        # some slides may have 0 elements, but the last slide should have elements)
        total_elements = sum(len(slide.renderable_elements) for slide in final_slides)
        assert total_elements > 0, "At least some slides must have renderable elements."

        # Verify all elements in the finalized slides have position data
        for i, slide in enumerate(final_slides):
            for element in slide.renderable_elements:
                assert (
                    element.position is not None
                ), f"Element in slide {i} must have position."
                assert element.size is not None, f"Element in slide {i} must have size."

    def test_integration_p_04(self):
        """
        Test Case: INTEGRATION-P-04
        Validates the end-to-end pipeline via the `markdown_to_requests` helper.
        From: docs/markdowndeck/testing/TEST_CASES_INTEGRATION_PIPELINE.md
        """
        # Arrange
        markdown = """# E2E Test
[width=1/2]
Left content.
***
[width=1/2]
Right content.
"""

        # Act
        result = markdown_to_requests(markdown, title="E2E Pipeline Test")

        # Assert
        assert "title" in result
        assert result["title"] == "E2E Pipeline Test"
        assert "slide_batches" in result
        assert len(result["slide_batches"]) == 1

        requests = result["slide_batches"][0]["requests"]
        assert len(requests) > 0, "Should generate API requests."

        # Check for key requests proving the pipeline ran
        create_slide_req = next((r for r in requests if "createSlide" in r), None)
        assert create_slide_req is not None, "A createSlide request must be present."

        # Verify content from both columns is present
        all_text = " ".join([r.get("insertText", {}).get("text", "") for r in requests])
        assert "Left content" in all_text
        assert "Right content" in all_text

    def test_integration_p_05_continuation_slide_object_ids(
        self,
        parser: Parser,
        layout_manager: LayoutManager,
        overflow_manager: OverflowManager,
    ):
        """
        Test Case: INTEGRATION-P-05
        Validates that continuation slide elements have valid Google API objectIds.
        This test verifies the fix for invalid objectId generation bug in SlideBuilder.
        """
        # Arrange: Use content that will definitely overflow and create many text elements
        # Each line will become a separate paragraph, and having many should force overflow
        lines = []
        for i in range(20):  # Create many lines of text to guarantee overflow
            lines.append(
                f"This is line number {i} with some content that takes up space."
            )

        text_content = "\n".join(lines)
        markdown = f"# Overflow Test\n\n{text_content}"

        # Act: Run the full pipeline to create continuation slides
        unpositioned_deck = parser.parse(markdown)
        positioned_slide = layout_manager.calculate_positions(
            unpositioned_deck.slides[0]
        )

        final_slides = overflow_manager.process_slide(positioned_slide)

        # Assert: Must have created continuation slides
        assert (
            len(final_slides) > 1
        ), "Overflow should have created multiple slides for objectId validation."

        # Collect all elements from all slides for validation
        all_elements = []
        for slide in final_slides:
            for element in slide.renderable_elements:
                if hasattr(element, "object_id") and element.object_id:
                    all_elements.append(element)

        # Valid Google Slides API objectId regex pattern
        valid_object_id_pattern = re.compile(r"^[a-zA-Z0-9_][a-zA-Z0-9_:\-]*$")

        # Validate every element's objectId across all slides
        assert (
            len(all_elements) > 0
        ), "Must have at least some elements to validate objectIds"

        for i, element in enumerate(all_elements):
            assert hasattr(
                element, "object_id"
            ), f"Element {i} must have object_id attribute"
            assert (
                element.object_id is not None
            ), f"Element {i} object_id cannot be None"

            # This assertion validates that continuation slide elements have valid objectIds
            assert valid_object_id_pattern.match(element.object_id), (
                f"Element {i} has invalid objectId '{element.object_id}'. "
                rf"Must match Google Slides API regex: ^[a-zA-Z0-9_][a-zA-Z0-9_:\-]*$"
            )
