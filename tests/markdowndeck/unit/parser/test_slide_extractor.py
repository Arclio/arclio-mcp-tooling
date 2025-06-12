import pytest
from markdowndeck.parser.slide_extractor import SlideExtractor


@pytest.fixture
def slide_extractor() -> SlideExtractor:
    return SlideExtractor()


class TestSlideExtractorDirectives:
    def test_strips_same_line_directives_from_subtitle(
        self, slide_extractor: SlideExtractor
    ):
        """
        Test Case: PARSER-V-03 (new)
        Validates that same-line directives are correctly stripped from subtitle text,
        similar to how they are handled for titles.
        """
        # Arrange
        markdown = "## My Subtitle [fontsize=24][color=red]"

        # Act
        # We test the internal method directly to isolate the logic.
        _title, subtitle, _content, _td, subtitle_directives = (
            slide_extractor._extract_title_with_directives(markdown)
        )

        # Assert
        assert (
            subtitle == "My Subtitle"
        ), "Directive string must be stripped from subtitle text."
        assert (
            "fontsize" in subtitle_directives
        ), "Directive 'fontsize' was not parsed from subtitle."
        assert (
            subtitle_directives.get("color") == "red"
        ), "Directive 'color' was not parsed correctly from subtitle."
