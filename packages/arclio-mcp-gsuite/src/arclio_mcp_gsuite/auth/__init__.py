"""
Authentication utilities for MCP-GSuite.
"""

from .gauth import SCOPES, get_credentials

__all__ = ["get_credentials", "SCOPES"]
