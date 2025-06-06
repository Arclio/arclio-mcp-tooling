"""
Fixtures and configuration specific to the markdowndeck test suite.
"""

import pytest
from markdowndeck.api.api_generator import ApiRequestGenerator
from markdowndeck.layout import LayoutManager
from markdowndeck.overflow import OverflowManager
from markdowndeck.parser import Parser


@pytest.fixture(scope="session")
def parser() -> Parser:
    """Provides a session-scoped Parser instance."""
    return Parser()


@pytest.fixture(scope="session")
def layout_manager() -> LayoutManager:
    """Provides a session-scoped LayoutManager instance."""
    return LayoutManager()


@pytest.fixture(scope="session")
def overflow_manager() -> OverflowManager:
    """Provides a session-scoped OverflowManager instance."""
    return OverflowManager()


@pytest.fixture(scope="session")
def api_request_generator() -> ApiRequestGenerator:
    """Provides a session-scoped ApiRequestGenerator instance."""
    return ApiRequestGenerator()
