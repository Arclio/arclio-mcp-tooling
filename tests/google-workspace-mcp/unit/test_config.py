"""
Unit tests for the config module.
"""

import json
import os
from unittest.mock import patch

from google_workspace_mcp.config import get_enabled_capabilities


class TestGetEnabledCapabilities:
    """Tests for the get_enabled_capabilities function."""

    def test_valid_json_array_parsing(self):
        """Test parsing of valid JSON array capabilities."""
        with patch.dict(
            os.environ,
            {"GOOGLE_WORKSPACE_ENABLED_CAPABILITIES": '["drive", "gmail", "calendar"]'},
        ):
            result = get_enabled_capabilities()
            assert result == {"drive", "gmail", "calendar"}

    def test_empty_json_array(self):
        """Test empty JSON array returns empty set."""
        with patch.dict(os.environ, {"GOOGLE_WORKSPACE_ENABLED_CAPABILITIES": "[]"}):
            result = get_enabled_capabilities()
            assert result == set()

    def test_default_empty_array_when_not_set(self):
        """Test default behavior when environment variable is not set."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_enabled_capabilities()
            assert result == set()

    def test_whitespace_handling(self):
        """Test capabilities with extra whitespace are trimmed."""
        with patch.dict(
            os.environ,
            {"GOOGLE_WORKSPACE_ENABLED_CAPABILITIES": '["  drive  ", " gmail ", "calendar"]'},
        ):
            result = get_enabled_capabilities()
            assert result == {"drive", "gmail", "calendar"}

    def test_case_normalization(self):
        """Test capabilities are normalized to lowercase."""
        with patch.dict(
            os.environ,
            {"GOOGLE_WORKSPACE_ENABLED_CAPABILITIES": '["DRIVE", "Gmail", "CaLeNdAr"]'},
        ):
            result = get_enabled_capabilities()
            assert result == {"drive", "gmail", "calendar"}

    def test_empty_string_capabilities_filtered(self):
        """Test empty or whitespace-only capability strings are filtered out."""
        with patch.dict(
            os.environ,
            {"GOOGLE_WORKSPACE_ENABLED_CAPABILITIES": '["drive", "", "  ", "gmail"]'},
        ):
            result = get_enabled_capabilities()
            assert result == {"drive", "gmail"}

    def test_invalid_json_logs_warning(self, caplog):
        """Test invalid JSON logs warning and returns empty set."""
        with patch.dict(os.environ, {"GOOGLE_WORKSPACE_ENABLED_CAPABILITIES": '["drive", "gmail"'}):  # Missing closing bracket
            result = get_enabled_capabilities()
            assert result == set()
            assert "not valid JSON" in caplog.text
            assert "Please use format like" in caplog.text

    def test_json_not_list_logs_warning(self, caplog):
        """Test JSON that's not a list logs warning and returns empty set."""
        with patch.dict(
            os.environ,
            {"GOOGLE_WORKSPACE_ENABLED_CAPABILITIES": '{"drive": true, "gmail": true}'},
        ):  # Object instead of array
            result = get_enabled_capabilities()
            assert result == set()
            assert "not a valid JSON list of strings" in caplog.text
            assert "Found type:" in caplog.text

    def test_json_list_with_non_strings_logs_warning(self, caplog):
        """Test JSON list containing non-strings logs warning and returns empty set."""
        with patch.dict(
            os.environ,
            {"GOOGLE_WORKSPACE_ENABLED_CAPABILITIES": '["drive", 123, "gmail"]'},
        ):  # Mixed types
            result = get_enabled_capabilities()
            assert result == set()
            assert "not a valid JSON list of strings" in caplog.text

    def test_empty_or_whitespace_env_var_treated_as_empty_list(self):
        """Test empty or whitespace-only environment variable is treated as empty list."""
        # Test empty string
        with patch.dict(os.environ, {"GOOGLE_WORKSPACE_ENABLED_CAPABILITIES": ""}):
            result = get_enabled_capabilities()
            assert result == set()

        # Test whitespace-only string
        with patch.dict(os.environ, {"GOOGLE_WORKSPACE_ENABLED_CAPABILITIES": "   "}):
            result = get_enabled_capabilities()
            assert result == set()

    def test_empty_capabilities_logs_warning(self, caplog):
        """Test empty capabilities logs appropriate warning."""
        with patch.dict(os.environ, {"GOOGLE_WORKSPACE_ENABLED_CAPABILITIES": "[]"}):
            result = get_enabled_capabilities()
            assert result == set()
            assert "No GOOGLE_WORKSPACE_ENABLED_CAPABILITIES specified or list is empty" in caplog.text
            assert "All tools might be disabled" in caplog.text

    def test_valid_capabilities_logs_info(self, caplog):
        """Test valid capabilities logs info message."""
        with patch.dict(os.environ, {"GOOGLE_WORKSPACE_ENABLED_CAPABILITIES": '["drive", "gmail"]'}):
            result = get_enabled_capabilities()
            assert result == {"drive", "gmail"}
            assert "Declared Google Workspace capabilities via env var" in caplog.text

    def test_duplicate_capabilities_deduplicated(self):
        """Test duplicate capabilities are deduplicated."""
        with patch.dict(
            os.environ,
            {"GOOGLE_WORKSPACE_ENABLED_CAPABILITIES": '["drive", "gmail", "drive", "calendar", "gmail"]'},
        ):
            result = get_enabled_capabilities()
            assert result == {"drive", "gmail", "calendar"}
            assert len(result) == 3  # Ensure no duplicates

    def test_complex_valid_json_array(self):
        """Test more complex but valid JSON array."""
        capabilities_json = json.dumps(["drive", "gmail", "calendar", "slides", "docs", "sheets"])
        with patch.dict(os.environ, {"GOOGLE_WORKSPACE_ENABLED_CAPABILITIES": capabilities_json}):
            result = get_enabled_capabilities()
            assert result == {"drive", "gmail", "calendar", "slides", "docs", "sheets"}

    def test_json_with_unicode_characters(self):
        """Test JSON array with Unicode characters is handled correctly."""
        with patch.dict(
            os.environ,
            {"GOOGLE_WORKSPACE_ENABLED_CAPABILITIES": '["drive", "gmail", "test-ünicöde"]'},
        ):
            result = get_enabled_capabilities()
            assert result == {"drive", "gmail", "test-ünicöde"}
