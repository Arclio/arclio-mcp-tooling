"""
Integration tests for Google Slides API.

These tests require valid Google API credentials and will make actual API calls.
They should be run cautiously to avoid unwanted side effects on real accounts.
"""

import contextlib
import os
import uuid

import pytest
from arclio_mcp_gsuite.services.slides import SlidesService

# Skip integration tests if environment flag is not set
pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION_TESTS", "0") != "1",
    reason="Integration tests are disabled. Set RUN_INTEGRATION_TESTS=1 to enable.",
)


class TestSlidesIntegration:
    """Integration tests for Google Slides API."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up the SlidesService for each test."""
        # Check if credentials are available
        for var in ["GSUITE_CLIENT_ID", "GSUITE_CLIENT_SECRET", "GSUITE_REFRESH_TOKEN"]:
            if not os.environ.get(var):
                pytest.skip(f"Environment variable {var} not set")

        self.service = SlidesService()

        # Generate a unique identifier for test resources
        self.test_id = f"test-{uuid.uuid4().hex[:8]}"

        # Create a test presentation to use for all tests
        self.presentation_id = None

    def teardown_method(self):
        """Clean up any created presentations."""
        # Delete test presentation if it exists
        if hasattr(self, "presentation_id") and self.presentation_id:
            with contextlib.suppress(Exception):
                # Note: Slides API doesn't have a direct delete method
                # In a real implementation, we could use the Drive API to delete presentations
                pass

    def test_presentation_creation_integration(self):
        """Test creating a presentation with the actual API."""
        presentation_title = f"Test Presentation {self.test_id}"

        # Create the presentation
        presentation = self.service.create_presentation(presentation_title)

        # Store ID for potential cleanup
        self.presentation_id = presentation.get("presentationId")

        # Verify creation succeeded
        assert isinstance(presentation, dict)
        assert "presentationId" in presentation
        assert presentation["title"] == presentation_title

    def test_slides_lifecycle_integration(self):
        """
        Test the complete lifecycle of slides: create presentation, add slide,
        add content, retrieve slides.
        """
        try:
            # 1. Create a test presentation
            presentation_title = f"Slide Lifecycle Test {self.test_id}"
            presentation = self.service.create_presentation(presentation_title)

            self.presentation_id = presentation.get("presentationId")
            assert self.presentation_id, "Presentation creation did not return an ID"

            # 2. Add a slide with TITLE_AND_BODY layout
            slide_result = self.service.create_slide(
                presentation_id=self.presentation_id, layout="TITLE_AND_BODY"
            )

            assert "slideId" in slide_result, "Slide creation did not return a slide ID"
            slide_id = slide_result["slideId"]

            # 3. Add text to the slide
            title_text = f"Integration Test Slide {self.test_id}"
            text_result = self.service.add_text(
                presentation_id=self.presentation_id,
                slide_id=slide_id,
                text=title_text,
                position=(100, 50),
                size=(400, 100),
            )

            assert text_result.get("result") == "success", "Text addition failed"

            # 4. Get slides and verify our content is there
            slides = self.service.get_slides(self.presentation_id)

            assert isinstance(slides, list), "get_slides did not return a list"
            assert len(slides) >= 1, "No slides found in the presentation"

            # Find our slide
            test_slide = None
            for slide in slides:
                if slide["id"] == slide_id:
                    test_slide = slide
                    break

            assert test_slide is not None, "Created slide not found in retrieved slides"

            # Check if our text is in any of the elements
            text_found = False
            for element in test_slide.get("elements", []):
                if element.get("type") == "text" and self.test_id in element.get("content", ""):
                    text_found = True
                    break

            assert text_found, "Added text not found in the slide elements"

        finally:
            # Note: As mentioned above, to properly delete presentations,
            # we would need to use the Drive API's delete file method
            pass
