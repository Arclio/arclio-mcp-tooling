"""
Service implementations for MCP-GSuite.
"""

from .base import BaseGoogleService
from .calendar import CalendarService
from .drive import DriveService
from .gmail import GmailService
from .slides import SlidesService

__all__ = [
    "BaseGoogleService",
    "DriveService",
    "GmailService",
    "CalendarService",
    "SlidesService",
]
