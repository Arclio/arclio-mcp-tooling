"""
E2E tests for the markdowndeck Command-Line Interface.

These tests validate the CLI entry point, argument parsing, and its orchestration
of the main library functions.
"""

from unittest.mock import MagicMock, patch

import pytest
from markdowndeck.cli import main as cli_main

MOCK_GET_CREDENTIALS_PATH = "markdowndeck.cli.get_credentials"
MOCK_CREATE_PRESENTATION_PATH = "markdowndeck.cli.create_presentation"
MOCK_GET_THEMES_PATH = "markdowndeck.cli.get_themes"


@pytest.fixture
def mock_creds(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Fixture that mocks the get_credentials function to return credentials."""
    mock = MagicMock()
    get_creds_mock = MagicMock(return_value=mock)
    monkeypatch.setattr(MOCK_GET_CREDENTIALS_PATH, get_creds_mock)
    return get_creds_mock


@pytest.fixture
def mock_create_presentation(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mocks the create_presentation function."""
    mock = MagicMock(
        return_value={
            "presentationId": "cli_pres_id_123",
            "presentationUrl": "https://slides.example.com/cli_pres_id_123",
            "title": "CLI Test Presentation",
            "slideCount": 2,
        }
    )
    monkeypatch.setattr(MOCK_CREATE_PRESENTATION_PATH, mock)
    return mock


@pytest.fixture
def mock_get_themes(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mocks the get_themes function."""
    mock = MagicMock(return_value=[{"id": "THEME_CLI", "name": "CLI Test Theme"}])
    monkeypatch.setattr(MOCK_GET_THEMES_PATH, mock)
    return mock


class TestCliEndToEnd:
    """End-to-end tests for the markdowndeck CLI."""

    def run_cli(
        self,
        monkeypatch: pytest.MonkeyPatch,
        args: list[str],
        input_data: str | None = None,
    ):
        """Helper to run the CLI's main function with mocked sys.argv and I/O."""
        full_args = ["markdowndeck"] + args
        monkeypatch.setattr("sys.argv", full_args)
        if input_data:
            monkeypatch.setattr("sys.stdin", MagicMock(read=lambda: input_data))

    def test_e2e_c_01(
        self, tmp_path, mock_creds, mock_create_presentation, monkeypatch, capsys
    ):
        """
        Test Case: E2E-C-01
        Validates the CLI can create a presentation from a file.
        From: docs/markdowndeck/testing/TEST_CASES_E2E.md
        """
        # Arrange
        md_file = tmp_path / "test.md"
        md_content = "# Test\nContent."
        md_file.write_text(md_content)

        # Act
        self.run_cli(monkeypatch, ["create", str(md_file), "--title", "File Test"])
        cli_main()

        # Assert
        mock_creds.assert_called_once()
        mock_create_presentation.assert_called_once_with(
            markdown=md_content,
            title="File Test",
            credentials=mock_creds.return_value,
            theme_id=None,
        )
        captured = capsys.readouterr()
        assert "ID: cli_pres_id_123" in captured.out
        assert "URL: https://slides.example.com/cli_pres_id_123" in captured.out

    def test_e2e_c_02(self, mock_creds, mock_get_themes, monkeypatch, capsys):
        """
        Test Case: E2E-C-02
        Validates the CLI 'themes' command.
        From: docs/markdowndeck/testing/TEST_CASES_E2E.md
        """
        # Arrange & Act
        self.run_cli(monkeypatch, ["themes"])
        cli_main()

        # Assert
        mock_creds.assert_called_once()
        mock_get_themes.assert_called_once_with(credentials=mock_creds.return_value)
        captured = capsys.readouterr()
        assert "CLI Test Theme (ID: THEME_CLI)" in captured.out

    def test_cli_create_from_stdin(
        self, mock_creds, mock_create_presentation, monkeypatch, capsys
    ):
        """Validates the CLI can create a presentation from stdin."""
        # Arrange
        md_content = "# Stdin\nInput."

        # Act
        self.run_cli(monkeypatch, ["create", "-"], input_data=md_content)
        cli_main()

        # Assert
        mock_creds.assert_called_once()
        mock_create_presentation.assert_called_once_with(
            markdown=md_content,
            title="Markdown Presentation",  # Default title
            credentials=mock_creds.return_value,
            theme_id=None,
        )
        captured = capsys.readouterr()
        assert "Title: CLI Test Presentation" in captured.out

    @patch("logging.getLogger")
    def test_cli_verbose_flag(
        self,
        mock_get_logger,
        tmp_path,
        mock_creds,
        mock_create_presentation,
        monkeypatch,
    ):
        """Validates that the --verbose flag sets the logging level to DEBUG."""
        # Arrange
        md_file = tmp_path / "verbose.md"
        md_file.write_text("# Verbose")
        mock_root_logger = MagicMock()
        mock_get_logger.return_value = mock_root_logger

        # Act
        self.run_cli(monkeypatch, ["--verbose", "create", str(md_file)])
        cli_main()

        # Assert
        mock_root_logger.setLevel.assert_called_with(
            pytest.importorskip("logging").DEBUG
        )
