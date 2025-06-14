"""
Global test configuration and fixtures.
"""

import logging
import os
import sys
from pathlib import Path

# Add the package to Python path for testing
package_path = Path(__file__).parent.parent / "packages" / "google-workspace-mcp" / "src"
sys.path.insert(0, str(package_path))

# Test that the import works
try:
    import google_workspace_mcp

    print(f"Successfully imported google_workspace_mcp from {google_workspace_mcp.__file__}")

    # Additional imports to test module structure
    import google_workspace_mcp.services

    print("Successfully imported services module")

    # Import some tools to verify structure
    import google_workspace_mcp.tools

    print("Successfully imported tools module")

except ImportError as e:
    print(f"ERROR importing google_workspace_mcp: {e}")
    print(f"Python path: {sys.path}")
    print(f"Package path: {package_path}")
    print(f"Package path exists: {package_path.exists()}")

# Set up logging for tests
logging.basicConfig(level=logging.DEBUG)

# Skip integration tests by default unless explicitly enabled
os.environ.setdefault("RUN_INTEGRATION_TESTS", "0")
