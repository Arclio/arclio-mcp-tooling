import pytest
from markdowndeck.api.request_builders.base_builder import BaseRequestBuilder
from markdowndeck.models import TextFormat, TextFormatType


class TestBaseRequestBuilder:
    """Unit tests for the BaseRequestBuilder."""

    @pytest.fixture
    def builder(self) -> BaseRequestBuilder:
        return BaseRequestBuilder()

    def test_generate_id(self, builder: BaseRequestBuilder):
        id1 = builder._generate_id("prefix")
        id2 = builder._generate_id("prefix")
        assert id1 != id2
        assert id1.startswith("prefix_")

        id3 = builder._generate_id()
        assert len(id3) == 8  # Default length without prefix

    def test_hex_to_rgb(self, builder: BaseRequestBuilder):
        assert builder._hex_to_rgb("#FF0000") == {
            "red": 1.0,
            "green": 0.0,
            "blue": 0.0,
        }
        assert builder._hex_to_rgb("00FF00") == {
            "red": 0.0,
            "green": 1.0,
            "blue": 0.0,
        }
        assert builder._hex_to_rgb("#00F") == {  # Shorthand
            "red": 0.0,
            "green": 0.0,
            "blue": 1.0,
        }
        assert builder._hex_to_rgb("ABCDEF") == {
            "red": 0xAB / 255.0,
            "green": 0xCD / 255.0,
            "blue": 0xEF / 255.0,
        }

    def test_rgb_to_color_dict(self, builder: BaseRequestBuilder):
        assert builder._rgb_to_color_dict(255, 0, 0) == {
            "rgbColor": {"red": 1.0, "green": 0.0, "blue": 0.0}
        }
        assert builder._rgb_to_color_dict(0, 128, 255) == {
            "rgbColor": {"red": 0.0, "green": 128 / 255.0, "blue": 1.0}
        }

    # Tests for _format_to_style and _format_to_fields
    # These were identified as needing updates in Phase 1.

    @pytest.mark.parametrize(
        "text_format, expected_style_dict, expected_fields_str",
        [
            (TextFormat(0, 0, TextFormatType.BOLD), {"bold": True}, "bold"),
            (TextFormat(0, 0, TextFormatType.ITALIC), {"italic": True}, "italic"),
            (
                TextFormat(0, 0, TextFormatType.UNDERLINE),
                {"underline": True},
                "underline",
            ),
            (
                TextFormat(0, 0, TextFormatType.STRIKETHROUGH),
                {"strikethrough": True},
                "strikethrough",
            ),
            (
                TextFormat(0, 0, TextFormatType.LINK, value="http://example.com"),
                {"link": {"url": "http://example.com"}},
                "link",
            ),
            (
                TextFormat(0, 0, TextFormatType.COLOR, value="#FF0000"),
                {
                    "foregroundColor": {
                        "opaqueColor": {
                            "rgbColor": {"red": 1.0, "green": 0.0, "blue": 0.0}
                        }
                    }
                },
                "foregroundColor",
            ),
            (
                TextFormat(0, 0, TextFormatType.COLOR, value="ACCENT1"),
                {"foregroundColor": {"opaqueColor": {"themeColor": "ACCENT1"}}},
                "foregroundColor",
            ),
            (
                TextFormat(0, 0, TextFormatType.BACKGROUND_COLOR, value="#00FF00"),
                {
                    "backgroundColor": {
                        "opaqueColor": {
                            "rgbColor": {"red": 0.0, "green": 1.0, "blue": 0.0}
                        }
                    }
                },
                "backgroundColor",
            ),
            (
                TextFormat(0, 0, TextFormatType.BACKGROUND_COLOR, value="BACKGROUND2"),
                {"backgroundColor": {"opaqueColor": {"themeColor": "BACKGROUND2"}}},
                "backgroundColor",
            ),
            (
                TextFormat(0, 0, TextFormatType.FONT_SIZE, value=18),
                {"fontSize": {"magnitude": 18.0, "unit": "PT"}},
                "fontSize",
            ),
            (
                TextFormat(0, 0, TextFormatType.FONT_FAMILY, value="Arial"),
                {"fontFamily": "Arial"},
                "fontFamily",
            ),
            (
                TextFormat(0, 0, TextFormatType.VERTICAL_ALIGN, value="SUPERSCRIPT"),
                {"baselineOffset": "SUPERSCRIPT"},
                "baselineOffset",
            ),
            (
                TextFormat(0, 0, TextFormatType.CODE),
                {
                    "fontFamily": "Courier New",
                    "backgroundColor": {
                        "opaqueColor": {
                            "rgbColor": {"red": 0.95, "green": 0.95, "blue": 0.95}
                        }
                    },
                },
                "fontFamily,backgroundColor",
            ),
        ],
    )
    def test_format_conversion(
        self,
        builder: BaseRequestBuilder,
        text_format: TextFormat,
        expected_style_dict: dict,
        expected_fields_str: str,
    ):
        style = builder._format_to_style(text_format)
        fields = builder._format_to_fields(text_format)
        assert style == expected_style_dict
        assert fields == expected_fields_str

    def test_apply_text_formatting_specific_range(self, builder: BaseRequestBuilder):
        req = builder._apply_text_formatting(
            "el1", {"bold": True}, "bold", start_index=0, end_index=5
        )
        assert req["updateTextStyle"]["textRange"] == {
            "type": "FIXED_RANGE",
            "startIndex": 0,
            "endIndex": 5,
        }
        assert req["updateTextStyle"]["objectId"] == "el1"
        assert req["updateTextStyle"]["style"] == {"bold": True}
        assert req["updateTextStyle"]["fields"] == "bold"

    def test_apply_text_formatting_all_range(self, builder: BaseRequestBuilder):
        req = builder._apply_text_formatting(
            "el1", {"italic": True}, "italic", range_type="ALL"
        )
        assert req["updateTextStyle"]["textRange"] == {"type": "ALL"}
        assert "startIndex" not in req["updateTextStyle"]["textRange"]

    def test_apply_text_formatting_cell_location(self, builder: BaseRequestBuilder):
        req = builder._apply_text_formatting(
            "table1",
            {"bold": True},
            "bold",
            cell_location={"rowIndex": 1, "columnIndex": 2},
            range_type="ALL",
        )
        assert req["updateTextStyle"]["cellLocation"] == {
            "rowIndex": 1,
            "columnIndex": 2,
        }
        assert req["updateTextStyle"]["textRange"] == {
            "type": "ALL"
        }  # TextRange applies within the cell
