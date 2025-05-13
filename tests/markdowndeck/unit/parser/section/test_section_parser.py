import pytest
from markdowndeck.models.slide import Section
from markdowndeck.parser.section.section_parser import SectionParser


class TestSectionParser:
    """Unit tests for the SectionParser component."""

    @pytest.fixture
    def parser(self) -> SectionParser:
        return SectionParser()

    def test_parse_single_section_no_separators(self, parser: SectionParser):
        content = "This is simple content."
        sections = parser.parse_sections(content)
        assert len(sections) == 1
        assert isinstance(sections[0], Section)
        assert sections[0].type == "section"
        assert sections[0].content == content
        assert sections[0].id is not None

    def test_parse_only_vertical_sections(self, parser: SectionParser):
        content = "Content A\n---\nContent B\n---\nContent C"
        sections = parser.parse_sections(content)
        assert len(sections) == 3
        assert all(s.type == "section" for s in sections)
        assert sections[0].content == "Content A"
        assert sections[1].content == "Content B"
        assert sections[2].content == "Content C"

    def test_parse_only_horizontal_sections(self, parser: SectionParser):
        """Content with only *** should result in one 'row' section."""
        content = "Content Left\n***\nContent Right"
        sections = parser.parse_sections(content)
        assert len(sections) == 1
        assert sections[0].type == "row"
        assert len(sections[0].subsections) == 2
        assert sections[0].subsections[0].content == "Content Left"
        assert sections[0].subsections[1].content == "Content Right"
        assert (
            sections[0].content == content
        )  # Row's content is the original un-horizontally-split part

    def test_parse_mixed_vertical_and_horizontal(self, parser: SectionParser):
        content = "Top Section\n---\nLeft Col\n***\nRight Col\n---\nBottom Section"
        sections = parser.parse_sections(content)
        assert len(sections) == 3
        assert sections[0].type == "section"
        assert sections[0].content == "Top Section"

        assert sections[1].type == "row"
        assert len(sections[1].subsections) == 2
        assert sections[1].subsections[0].content == "Left Col"
        assert sections[1].subsections[1].content == "Right Col"
        assert (
            sections[1].content == "Left Col\n***\nRight Col"
        )  # Original content for this vertical part

        assert sections[2].type == "section"
        assert sections[2].content == "Bottom Section"

    def test_sections_with_code_blocks_and_separators(self, parser: SectionParser):
        content = "Intro\n```python\n# ---\n# ***\nprint('hello')\n```\n---\nConclusion"
        sections = parser.parse_sections(content)
        assert len(sections) == 2
        assert "Intro" in sections[0].content
        assert "```python\n# ---\n# ***\nprint('hello')\n```" in sections[0].content
        assert sections[1].content == "Conclusion"

    def test_empty_sections_are_filtered(self, parser: SectionParser):
        content = "A\n---\n   \n---\nB"  # Middle section is empty/whitespace
        sections = parser.parse_sections(content)
        assert len(sections) == 2
        assert sections[0].content == "A"
        assert sections[1].content == "B"

    def test_content_starting_and_ending_with_separators(self, parser: SectionParser):
        content_v = "---\nSection1\n---\nSection2\n---"
        sections_v = parser.parse_sections(content_v)
        assert len(sections_v) == 2
        assert sections_v[0].content == "Section1"
        assert sections_v[1].content == "Section2"

        content_h = "***\nCol1\n***\nCol2\n***"
        sections_h = parser.parse_sections(content_h)
        assert len(sections_h) == 1
        assert sections_h[0].type == "row"
        assert len(sections_h[0].subsections) == 2
        assert sections_h[0].subsections[0].content == "Col1"
        assert sections_h[0].subsections[1].content == "Col2"

    def test_empty_input_content(self, parser: SectionParser):
        sections = parser.parse_sections("")
        assert len(sections) == 0
        sections_ws = parser.parse_sections("   \n\t   ")
        assert len(sections_ws) == 0

    def test_content_is_only_separators(self, parser: SectionParser):
        sections_v = parser.parse_sections("---\n---\n---")
        # Current implementation creates a section for separator-only content
        assert len(sections_v) == 1
        # Current implementation preserves separator content
        assert sections_v[0].content == "---\n---\n---"

        sections_h = parser.parse_sections("***\n***")
        # Current implementation creates a section for separator-only content
        assert len(sections_h) == 1
        # Current implementation preserves separator content
        assert sections_h[0].content == "***\n***"

    def test_unique_ids_generated(self, parser: SectionParser):
        content = "A\n---\nB1\n***\nB2\n---\nC"
        sections = parser.parse_sections(content)

        # Check all top-level sections have unique IDs
        top_level_ids = {section.id for section in sections}
        assert len(top_level_ids) == 3  # All sections should have unique IDs

        # Check subsection IDs are unique too
        if sections[1].subsections:
            subsection_ids = {subsection.id for subsection in sections[1].subsections}
            assert len(subsection_ids) == len(sections[1].subsections)

            # Ensure subsection IDs don't overlap with top-level IDs
            all_ids = top_level_ids.union(subsection_ids)
            assert len(all_ids) == 3 + len(sections[1].subsections)

    def test_preservation_of_content_for_directive_parsing(self, parser: SectionParser):
        """Ensures raw content (including potential directives) is passed through."""
        content = "[dir1=val1]\nContent A\n---\n[dir2=val2]\nContent B1\n***\n[dir3=val3]\nContent B2"
        sections = parser.parse_sections(content)

        assert sections[0].content == "[dir1=val1]\nContent A"
        assert sections[1].type == "row"
        # The "content" of the row section should be the whole part between vertical separators
        assert (
            sections[1].content
            == "[dir2=val2]\nContent B1\n***\n[dir3=val3]\nContent B2"
        )
        assert sections[1].subsections[0].content == "[dir2=val2]\nContent B1"
        assert sections[1].subsections[1].content == "[dir3=val3]\nContent B2"

    def test_split_horizontal_only_with_code_block(self, parser: SectionParser):
        """Test horizontal splitting when it's the only type and contains code blocks."""
        content = "Left\n```\n*** text in code ***\n```\n***\nRight\n```\n*** more code ***\n```"
        sections = parser.parse_sections(content)
        assert len(sections) == 1
        assert sections[0].type == "row"
        assert len(sections[0].subsections) == 2
        assert (
            sections[0].subsections[0].content.strip()
            == "Left\n```\n*** text in code ***\n```"
        )
        assert (
            sections[0].subsections[1].content.strip()
            == "Right\n```\n*** more code ***\n```"
        )
