# CRITICAL: MCP Tool Description Visibility Fix

## The Problem

LLMs using MCP tools only see:
1. **The `description` parameter from the `@mcp.tool` decorator**
2. **Parameter names and types** (but NOT docstring parameter descriptions)

They **DO NOT** see the detailed docstrings with usage examples and critical information like apostrophe escaping requirements.

## Root Cause Discovery

Through research of FastMCP documentation, we discovered:

> When this tool is registered, FastMCP automatically:
> - Uses the function name as the tool name
> - **Uses the function's docstring as the tool description**
> - Generates an input schema based on the function's parameters and type annotations

**CRITICAL**: `description`: Provides the description exposed via MCP. **If set, the function's docstring is ignored for this purpose.**

## The Solution

**Remove the `description` parameter from `@mcp.tool` decorators** and put critical information directly in the docstring.

### Before (LLMs can't see apostrophe escaping info):
```python
@mcp.tool(
    name="drive_search_files",
    description="Search for files in Google Drive with optional shared drive support.",  # ← LLM sees this
)
async def drive_search_files(query: str) -> dict[str, Any]:
    """
    CRITICAL: If search queries contain apostrophes ('), you MUST escape them with backslash (\').
    Example: "Frank's RedHot" → "Frank\'s RedHot"
    # ↑ LLM NEVER SEES THIS because description parameter is provided
    """
```

### After (LLMs can see critical info):
```python
@mcp.tool(
    name="drive_search_files",
    # ← No description parameter, so docstring is used
)
async def drive_search_files(query: str) -> dict[str, Any]:
    """
    Search for files in Google Drive with optional shared drive support.
    
    CRITICAL: If search queries contain apostrophes ('), you MUST escape them with backslash (\').
    Example: "Frank's RedHot" → "Frank\'s RedHot"
    # ↑ LLM NOW SEES THIS because it's in the docstring and no description param is provided
    """
```

## Implementation Status

✅ **Fixed tools:**
- `drive_search_files` - Main search with critical apostrophe escaping info
- `drive_find_folder_by_name` - Folder search with escaping info  
- `drive_search_files_in_folder` - Folder-specific search with escaping info
- `drive_get_folder_info` - Folder metadata tool
- `drive_list_shared_drives` - Shared drives discovery

## Key Success Factors

1. **Docstring is now visible to LLMs** - Critical escaping information is accessible
2. **Clear examples** - "Frank's RedHot" → "Frank\'s RedHot" 
3. **Prominent placement** - CRITICAL warnings at the top of descriptions
4. **Multiple tools covered** - Consistent messaging across all search tools

## Next Steps

1. **Test with real LLM clients** to verify they now see the escaping requirements
2. **Apply same pattern** to any other tools that need critical usage information
3. **Monitor for improved success rates** with apostrophe-containing queries

## Technical Notes

- FastMCP automatically uses docstrings when no `description` parameter is provided
- This pattern works for all MCP decorators: `@mcp.tool`, `@mcp.resource`, `@mcp.prompt`
- The docstring becomes the primary interface documentation for LLMs
- Parameter type hints and names are still automatically extracted for schema generation

## Validation

To validate this fix works:
1. Use an MCP client to connect to the tools
2. Call `list_tools()` to see tool descriptions
3. Verify the docstring content (including CRITICAL warnings) appears in tool descriptions
4. Test with "Frank's RedHot" queries to confirm LLMs now know to escape apostrophes 