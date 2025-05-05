"""Configure pytest environment for all tests."""

import sys
from pathlib import Path

# Add the src directories to the Python path
src_path = Path(__file__).parent.parent / "packages" / "arclio-mcp-gsuite" / "src"
if src_path.exists() and str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Print debug information
print(f"Python path in conftest.py: {sys.path}")
print(f"Added src path: {src_path}")

# Try to import the package to verify it works
try:
    import arclio_mcp_gsuite

    print(f"Successfully imported arclio_mcp_gsuite from {arclio_mcp_gsuite.__file__}")

    try:
        import arclio_mcp_gsuite.services

        print("Services module imported successfully")
    except ImportError as e:
        print(f"ERROR importing services: {e}")

    try:
        import arclio_mcp_gsuite.tools

        print("Tools module imported successfully")
    except ImportError as e:
        print(f"ERROR importing tools: {e}")

except ImportError as e:
    print(f"ERROR importing arclio_mcp_gsuite: {e}")
