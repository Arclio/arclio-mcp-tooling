"""
Service implementations for Google Workspace MCP.
"""

from .base import BaseGoogleService
from .calendar import CalendarService
from .docs_service import DocsService
from .drive import DriveService
from .gmail import GmailService
from .slides import SlidesService

__all__ = [
    "BaseGoogleService",
    "DriveService",
    "GmailService",
    "CalendarService",
    "SlidesService",
    "DocsService",
]
