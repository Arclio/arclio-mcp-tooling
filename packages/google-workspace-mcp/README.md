# Google Workspace MCP

<div align="center">

**Google Workspace integration for AI assistants via Model Context Protocol (MCP)**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

_Developed and maintained by [Arclio](https://arclio.com)_ - _Secure MCP service management for AI applications_

</div>

---

## 🚀 Quick Start

Test the server immediately using the Model Context Protocol (MCP) Inspector, or install and run it directly.

### Option 1: Instant Setup with MCP Inspector (Recommended for Testing)

```bash
npx @modelcontextprotocol/inspector \
  -e GOOGLE_WORKSPACE_CLIENT_ID="your-client-id.apps.googleusercontent.com" \
  -e GOOGLE_WORKSPACE_CLIENT_SECRET="your-client-secret" \
  -e GOOGLE_WORKSPACE_REFRESH_TOKEN="your-refresh-token" \
  -e GOOGLE_WORKSPACE_ENABLED_CAPABILITIES='["drive", "docs", "gmail", "calendar", "sheets", "slides"]' \
  -- \
  uvx --from google-workspace-mcp google-workspace-worker
```

Replace placeholder credentials with your actual values.

### Option 2: Direct Installation & Usage

1.  **Install the package:**

    ```bash
    pip install google-workspace-mcp
    ```

2.  **Set Environment Variables:**

    ```bash
    export GOOGLE_WORKSPACE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
    export GOOGLE_WORKSPACE_CLIENT_SECRET="your-client-secret"
    export GOOGLE_WORKSPACE_REFRESH_TOKEN="your-refresh-token"
    export GOOGLE_WORKSPACE_ENABLED_CAPABILITIES='["drive", "docs", "gmail", "calendar", "sheets", "slides"]'
    # Optional: For development/integration testing
    # export RUN_INTEGRATION_TESTS="1"
    ```

3.  **Run the MCP Server:**

    ```bash
    google-workspace-worker
    ```

### Option 3: Using `uvx` (Run without full installation)

```bash
# Ensure GOOGLE_WORKSPACE_* environment variables are set as shown above
uvx --from google-workspace-mcp google-workspace-worker
```

## 📋 Overview

`google-workspace-mcp` is a Python package that enables AI models to interact with Google Workspace services (Drive, Docs, Gmail, Calendar, Sheets, and Slides) through the Model Context Protocol (MCP). It acts as a secure and standardized bridge, allowing AI assistants to leverage Google Workspace functionalities without direct API credential exposure.

### What is MCP?

The Model Context Protocol (MCP) provides a standardized interface for AI models to discover and utilize external tools and services. This package implements an MCP server that exposes Google Workspace capabilities as discrete, callable "tools."

### Key Benefits

- **AI-Ready Integration**: Purpose-built for AI assistants to naturally interact with Google Workspace.
- **Standardized Protocol**: Ensures seamless integration with MCP-compatible AI systems and hubs.
- **Enhanced Security**: Google API credentials remain on the server, isolated from the AI models.
- **Comprehensive Capabilities**: Offers a wide range of tools across core Google Workspace services.
- **Robust Error Handling**: Provides consistent error patterns for reliable operation.
- **Extensive Testing**: Underpinned by a comprehensive test suite for correctness and stability.

## 🔑 Authentication Setup

Accessing Google Workspace APIs requires OAuth 2.0 credentials.

### Step 1: Google Cloud Console Setup

1.  Navigate to the [Google Cloud Console](https://console.cloud.google.com/).
2.  Create a new project or select an existing one.
3.  Enable the following APIs for your project:
    - Google Drive API
    - Gmail API
    - Google Calendar API
    - Google Docs API
    - Google Sheets API
    - Google Slides API
4.  Go to "APIs & Services" -\> "Credentials".
5.  Click "Create Credentials" -\> "OAuth 2.0 Client ID".
6.  Select "Web application" as the application type.
7.  Under "Authorized redirect URIs", add `https://developers.google.com/oauthplayground` (for easy refresh token generation) and any other URIs required for your specific setup (e.g., `http://localhost:8080/callback` if using the Python script method locally).
8.  Note your `Client ID` and `Client Secret`.

### Step 2: Obtain a Refresh Token

**Option A: Using OAuth 2.0 Playground (Recommended)**

1.  Go to the [OAuth 2.0 Playground](https://developers.google.com/oauthplayground/).
2.  Click the gear icon (⚙️) in the top right corner.
3.  Check the box "Use your own OAuth credentials."
4.  Enter the `Client ID` and `Client Secret` obtained from the Google Cloud Console.
5.  In "Step 1: Select & authorize APIs", input the following scopes (or select them from the list):
    - `https://www.googleapis.com/auth/drive`
    - `https://www.googleapis.com/auth/gmail.modify` (includes send, read, delete)
    - `https://www.googleapis.com/auth/calendar`
    - `https://www.googleapis.com/auth/docs`
    - `https://www.googleapis.com/auth/spreadsheets`
    - `https://www.googleapis.com/auth/presentations`
6.  Click "Authorize APIs." You will be prompted to sign in with the Google account you want the MCP server to act on behalf of and grant permissions.
7.  After authorization, you'll be redirected back. In "Step 2: Exchange authorization code for tokens," click "Exchange authorization code for tokens."
8.  Copy the `Refresh token` displayed.

**Option B: Using a Python Script (Advanced)**
You can adapt a Python script using the `google-auth-oauthlib` library to perform the OAuth flow and retrieve a refresh token. Ensure your script uses the correct client ID, client secret, redirect URI, and scopes as listed above.

### Step 3: Configure Environment Variables

The MCP server requires the following environment variables to be set:

```bash
# Essential for authentication
export GOOGLE_WORKSPACE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export GOOGLE_WORKSPACE_CLIENT_SECRET="your-client-secret"
export GOOGLE_WORKSPACE_REFRESH_TOKEN="your-refresh-token"

# Controls which services are active (see "Capabilities Configuration" below)
export GOOGLE_WORKSPACE_ENABLED_CAPABILITIES='["drive", "docs", "gmail", "calendar", "sheets", "slides"]'
```

## ⚙️ Capabilities Configuration

The `GOOGLE_WORKSPACE_ENABLED_CAPABILITIES` environment variable dictates which Google Workspace services are active and discoverable by AI models. It **must** be a JSON-formatted array of strings.

**Format Examples:**

```bash
# Enable all currently supported services
export GOOGLE_WORKSPACE_ENABLED_CAPABILITIES='["drive", "docs", "gmail", "calendar", "sheets", "slides"]'

# Enable a subset of services
export GOOGLE_WORKSPACE_ENABLED_CAPABILITIES='["drive", "gmail", "calendar"]'

# Enable a single service
export GOOGLE_WORKSPACE_ENABLED_CAPABILITIES='["docs"]'

# Disable all services (server will run but offer no tools)
export GOOGLE_WORKSPACE_ENABLED_CAPABILITIES='[]'
```

**Available Capability Values:**

- `"drive"`: Google Drive (file search, read, creation, etc.)
- `"docs"`: Google Docs (document creation, metadata, content operations)
- `"gmail"`: Gmail (email query, read, send, draft management, etc.)
- `"calendar"`: Google Calendar (event retrieval, creation, deletion)
- `"sheets"`: Google Sheets (spreadsheet creation, data read/write operations)
- `"slides"`: Google Slides (presentation creation from Markdown, slide listing)

**Important Notes:**

- The value **must** be a valid JSON array string. In bash, it's best to enclose the JSON string in single quotes.
- Service names within the array are case-insensitive but lowercase is conventional.
- An invalid JSON string or a JSON type other than an array will result in a warning, and the server may effectively disable all tools.
- If the `GOOGLE_WORKSPACE_ENABLED_CAPABILITIES` variable is not set, it defaults to an empty list (`"[]"`), meaning no services will be enabled by default.

## 🛠️ Exposed Capabilities (Tools & Resources)

This package exposes a variety of tools and resources for AI interaction.

### Google Drive Tools

- **`drive_search_files`**: Searches files in Google Drive.
  - `query` (string): Drive query string.
  - `page_size` (integer, optional): Max files to return.
  - `shared_drive_id` (string, optional): ID of a shared drive to search within.
- **`drive_read_file_content`**: Reads content of a file.
  - `file_id` (string): The ID of the file.
- **`drive_create_folder`**: Creates a new folder.
  - `folder_name` (string): Name of the new folder.
  - `parent_folder_id` (string, optional): ID of the parent folder.
  - `shared_drive_id` (string, optional): ID of a shared drive.
- **`drive_list_shared_drives`**: Lists shared drives accessible by the user.
  - `page_size` (integer, optional): Max shared drives to return.
- **`drive_upload_file`**: Uploads a local file to Google Drive. (Requires server access to the file path)
  - `file_path` (string): Local path to the file.
- **`drive_delete_file`**: Deletes a file from Google Drive.
  - `file_id` (string): The ID of the file to delete.

### Google Drive Resources

- `drive://files/{file_id}/metadata`: Get metadata for a specific file.
- `drive://files/recent` or `drive://recent`: Get recently modified files. _(Note: `drive://recent` is the primary)_
- `drive://files/shared_with_me` or `drive://shared`: Get files shared with the user. _(Note: `drive://shared` is the primary)_

### Google Docs Tools

- **`docs_create_document`**: Creates a new document.
  - `title` (string): Title for the new document.
- **`docs_get_document_metadata`**: Retrieves metadata for a document.
  - `document_id` (string): The ID of the document.
- **`docs_get_content_as_markdown`**: Retrieves document content as Markdown.
  - `document_id` (string): The ID of the document.
- **`docs_append_text`**: Appends text to a document.
  - `document_id` (string): The ID of the document.
  - `text` (string): Text to append.
  - `ensure_newline` (boolean, optional): Prepend a newline if document is not empty (default: True).
- **`docs_prepend_text`**: Prepends text to a document.
  - `document_id` (string): The ID of the document.
  - `text` (string): Text to prepend.
  - `ensure_newline` (boolean, optional): Append a newline if document was not empty (default: True).
- **`docs_insert_text`**: Inserts text at a specific location.
  - `document_id` (string): The ID of the document.
  - `text` (string): Text to insert.
  - `index` (integer, optional): 0-based index for insertion.
  - `segment_id` (string, optional): Segment ID (e.g., header).
- **`docs_batch_update`**: Applies a list of raw Google Docs API update requests (advanced).
  - `document_id` (string): The ID of the document.
  - `requests` (list[dict]): List of Docs API request objects.

### Gmail Tools

- **`query_gmail_emails`**: Searches emails using Gmail query syntax.
  - `query` (string): Gmail search query.
  - `max_results` (integer, optional): Maximum emails to return.
- **`gmail_get_message_details`**: Retrieves a complete email message.
  - `email_id` (string): The ID of the Gmail message.
- **`gmail_get_attachment_content`**: Retrieves a specific email attachment.
  - `message_id` (string): The ID of the email message.
  - `attachment_id` (string): The ID of the attachment.
- **`create_gmail_draft`**: Creates a draft email.
  - `to` (string): Recipient's email address.
  - `subject` (string): Email subject.
  - `body` (string): Email body content.
  - `cc` (list[string], optional): CC recipients.
  - `bcc` (list[string], optional): BCC recipients.
- **`delete_gmail_draft`**: Deletes a draft email.
  - `draft_id` (string): The ID of the draft.
- **`gmail_send_draft`**: Sends an existing draft.
  - `draft_id` (string): The ID of the draft.
- **`gmail_send_email`**: Composes and sends an email directly.
  - `to` (list[string]): Primary recipients.
  - `subject` (string): Email subject.
  - `body` (string): Email body content.
  - `cc` (list[string], optional): CC recipients.
  - `bcc` (list[string], optional): BCC recipients.
- **`gmail_reply_to_email`**: Creates a reply to an email (saves as draft by default).
  - `email_id` (string): ID of the message to reply to.
  - `reply_body` (string): Content of the reply.
  - `send` (boolean, optional): Send immediately if true (default: False, creates draft).
  - `reply_all` (boolean, optional): Reply to all recipients if true (default: False).
- **`gmail_bulk_delete_messages`**: Deletes multiple emails.
  - `message_ids` (list[string]): List of email message IDs.

### Gmail Resources

- `gmail://labels`: List all Gmail labels.
- `gmail://unread_count`: Get count of unread emails in the inbox.
- _(Search functionality is primarily handled by the `query_gmail_emails` tool)_

### Google Calendar Tools

- **`calendar_get_events`**: Retrieves events within a time range.
  - `time_min` (string): Start time (RFC3339).
  - `time_max` (string): End time (RFC3339).
  - `calendar_id` (string, optional): Calendar ID (default: "primary").
  - `max_results` (integer, optional): Max events.
  - `show_deleted` (boolean, optional): Include deleted events.
- **`calendar_get_event_details`**: Retrieves details for a specific event.
  - `event_id` (string): The ID of the event.
  - `calendar_id` (string, optional): Calendar ID (default: "primary").
- **`Calendar`**: Creates a new event.
  - `summary` (string): Event title.
  - `start_time` (string): Start time (RFC3339).
  - `end_time` (string): End time (RFC3339).
  - `calendar_id` (string, optional): Calendar ID (default: "primary").
  - `attendees` (list[string], optional): Attendee emails.
  - _(Other optional parameters: `location`, `description`, `send_notifications`, `timezone`)_
- **`delete_calendar_event`**: Deletes an event.
  - `event_id` (string): The ID of the event.
  - `calendar_id` (string, optional): Calendar ID (default: "primary").
  - `send_notifications` (boolean, optional): Notify attendees.

### Google Calendar Resources

- `calendar://calendars/list`: Lists all accessible calendars.
- `calendar://events/today`: Get all events for today from the primary calendar.

### Google Sheets Tools

- **`sheets_create_spreadsheet`**: Creates a new spreadsheet.
  - `title` (string): Title for the new spreadsheet.
- **`sheets_read_range`**: Reads data from a range.
  - `spreadsheet_id` (string): The ID of the spreadsheet.
  - `range_a1` (string): Range in A1 notation (e.g., "Sheet1\!A1:C5").
- **`sheets_write_range`**: Writes data to a range.
  - `spreadsheet_id` (string): The ID of the spreadsheet.
  - `range_a1` (string): Range in A1 notation.
  - `values` (list[list]): Data to write (list of rows, where each row is a list of cell values).
  - `value_input_option` (string, optional): "USER_ENTERED" or "RAW" (default: "USER_ENTERED").
- **`sheets_append_rows`**: Appends rows to a sheet/table.
  - `spreadsheet_id` (string): The ID of the spreadsheet.
  - `range_a1` (string): Sheet or table range (e.g., "Sheet1").
  - `values` (list[list]): Data rows to append.
  - `value_input_option` (string, optional): "USER_ENTERED" or "RAW" (default: "USER_ENTERED").
  - `insert_data_option` (string, optional): "INSERT_ROWS" or "OVERWRITE" (default: "INSERT_ROWS").
- **`sheets_clear_range`**: Clears values from a range.
  - `spreadsheet_id` (string): The ID of the spreadsheet.
  - `range_a1` (string): Range to clear.
- **`sheets_add_sheet`**: Adds a new sheet (tab).
  - `spreadsheet_id` (string): The ID of the spreadsheet.
  - `title` (string): Title for the new sheet.
- **`sheets_delete_sheet`**: Deletes a sheet.
  - `spreadsheet_id` (string): The ID of the spreadsheet.
  - `sheet_id` (integer): Numeric ID of the sheet to delete.

### Google Sheets Resources

- `sheets://spreadsheets/{spreadsheet_id}/metadata`: Retrieves metadata for a specific Google Spreadsheet.
- `sheets://spreadsheets/{spreadsheet_id}/sheets/{sheet_identifier}/metadata`: Retrieves metadata for a specific sheet within a spreadsheet (identified by name or numeric ID).

### Google Slides Tools

- **`create_presentation_from_markdown`**: Creates a presentation from Markdown content using the `markdowndeck` library. This is the primary tool for complex slide creation.
  - `title` (string): Title for the new presentation.
  - `markdown_content` (string): Markdown content. Refer to the `slides://markdown_formatting_guide` resource for syntax.
- **`get_presentation`**: Retrieves presentation details.
  - `presentation_id` (string): The ID of the presentation.
- **`get_slides`**: Lists all slides in a presentation with their elements.
  - `presentation_id` (string): The ID of the presentation.
- _(Other granular slide manipulation tools like `create_slide`, `add_text_to_slide`, `delete_slide` are available but are expected to be superseded by enhanced `markdowndeck` functionality in future updates.)_

### Google Slides Resources

- `slides://markdown_formatting_guide`: Comprehensive guide on formatting Markdown for slide creation using the `markdowndeck` library.

## 🏗️ Architecture

The `google-workspace-mcp` package is structured as follows:

```
google-workspace-mcp/
└── src/
    └── google_workspace_mcp/
        ├── __init__.py         # Package initializer
        ├── __main__.py         # Main entry point for the worker, registers components
        ├── app.py              # Central FastMCP application instance
        ├── config.py           # Configuration (e.g., GOOGLE_WORKSPACE_ENABLED_CAPABILITIES)
        ├── auth/               # Authentication logic
        │   └── gauth.py
        ├── services/           # Modules interacting directly with Google APIs
        │   ├── base.py         # BaseGoogleService class
        │   ├── drive.py
        │   ├── docs_service.py
        │   ├── gmail.py
        │   ├── calendar.py
        │   ├── sheets_service.py
        │   └── slides.py
        ├── tools/              # MCP Tool definitions
        │   ├── drive_tools.py
        │   ├── docs_tools.py
        │   ├── gmail_tools.py
        │   ├── calendar_tools.py
        │   ├── sheets_tools.py
        │   └── slides_tools.py
        ├── resources/          # MCP Resource definitions
        │   ├── drive.py
        │   ├── gmail.py
        │   ├── calendar.py
        │   ├── sheets_resources.py
        │   └── slides.py
        └── prompts/            # MCP Prompt definitions (for LLM interaction patterns)
            ├── drive.py
            ├── gmail.py
            ├── calendar.py
            └── slides.py
```

**Execution Flow:**

1.  An MCP Hub (or a tool like MCP Inspector) starts the `google-workspace-worker` process.
2.  `google_workspace_mcp.__main__.py` is executed. Importing modules from `tools/`, `resources/`, and `prompts/` causes the components (decorated with `@mcp.tool`, `@mcp.resource`, `@mcp.prompt`) to register themselves with the central `FastMCP` instance defined in `app.py`.
3.  The MCP server listens for requests (typically over stdio).
4.  Upon a discovery request, the server lists available tools/resources based on `GOOGLE_WORKSPACE_ENABLED_CAPABILITIES`.
5.  Upon a tool/resource call:
    - The `FastMCP` server routes the request to the appropriate handler function in the `tools/` or `resources/` modules.
    - The handler function validates arguments and calls methods on the relevant service class in `services/`.
    - The service class interacts with the Google API, handling authentication (via `auth/gauth.py`) and error translation.
    - Results are returned to the AI model via the MCP Hub.

## 🧩 Development

### Setup Development Environment

Ensure you are in the root of the `arclio-mcp-tooling` monorepo.

```bash
# From the monorepo root
make setup-dev # Installs uv and sets up the virtual environment

# Install this package and its dependencies in editable mode
make install google-workspace-mcp
```

### Environment Variables for Development

Copy `.env.example` (if available in the package or monorepo root) to `.env` and populate it with your Google Cloud credentials and desired enabled capabilities.

```bash
# Example:
# GOOGLE_WORKSPACE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
# ... other variables ...
```

Source the `.env` file before running the server locally: `source .env`

### Adding New Tools or Resources (FastMCP Pattern)

1.  **Define the function** in the appropriate module within `tools/` or `resources/`.
2.  **Decorate it**: Use `@mcp.tool(...)` or `@mcp.resource(...)`.
    - Provide `name` and `description`.
    - Type hints in the function signature are used by `FastMCP` to generate the input schema.
3.  **Implement Logic**: The function should call the relevant service method.
4.  **Register**: Ensure the module containing the new tool/resource is imported in `google_workspace_mcp/__main__.py` (this is how `FastMCP` discovers it).

**Example Tool Definition:**

```python
# In google_workspace_mcp/tools/your_new_tools.py
from google_workspace_mcp.app import mcp
from ..services.your_service import YourService # Assuming YourService exists

@mcp.tool(
    name="your_service_action_name",
    description="A brief description of what this tool does."
)
async def your_tool_function(parameter1: str, count: int = 5) -> dict:
    """
    More detailed docstring for your tool.
    Args:
        parameter1: Description of the first parameter.
        count: Description of the optional count parameter.
    Returns:
        A dictionary containing the result of the operation.
    """
    # ... (input validation if needed beyond type hints)
    service = YourService()
    result = service.perform_action(param1=parameter1, num_items=count)
    # ... (handle service result, raise ValueError on error, or return data)
    return {"status": "success", "data": result}
```

Remember to add a corresponding import in `google_workspace_mcp/__main__.py` for `your_new_tools`.

### Running Tests

From the `arclio-mcp-tooling` monorepo root:

```bash
# Run all tests for this package
make test google-workspace-mcp

# Run only unit tests for this package
make test-unit google-workspace-mcp

# Run integration tests for this package (ensure RUN_INTEGRATION_TESTS=1 is set in your environment)
export RUN_INTEGRATION_TESTS=1
make test-integration google-workspace-mcp
```

### Code Quality

From the `arclio-mcp-tooling` monorepo root:

```bash
# Run linting (Ruff)
make lint

# Attempt to auto-fix linting issues
make fix

# Format code (Ruff Formatter)
make format
```

## 🔍 Troubleshooting

- **Authentication Errors**:
  - Double-check `GOOGLE_WORKSPACE_CLIENT_ID`, `GOOGLE_WORKSPACE_CLIENT_SECRET`, and `GOOGLE_WORKSPACE_REFRESH_TOKEN`.
  - Ensure the refresh token is valid and has not been revoked.
  - Verify all required API scopes were granted during the OAuth flow.
- **Tool Not Found / Capability Disabled**:
  - Confirm the desired service (e.g., `"drive"`) is included in the `GOOGLE_WORKSPACE_ENABLED_CAPABILITIES` JSON array in your environment.
  - Check server logs for warnings about invalid capability configurations.
- **API Errors (403 Permission Denied, 404 Not Found, etc.)**:
  - Ensure the authenticated Google account has the necessary permissions for the attempted operation on the specific resource (e.g., file access, calendar edit rights).
  - Verify that the correct Google APIs are enabled in your Google Cloud Project.
- **Rate Limits**: Be mindful of Google API rate limits. If you encounter frequent 403 or 429 errors related to quotas, you may need to implement retry logic with backoff or request a quota increase from Google.

For detailed debugging, inspect the server's stdout/stderr logs.

## 📝 Contributing

Contributions are welcome\! Please refer to the main `README.md` in the `arclio-mcp-tooling` monorepo for guidelines on contributing, setting up the development environment, and project-wide commands.

## 📄 License

This package is licensed under the MIT License. See the `LICENSE` file in the monorepo root for full details.

## 🏢 About Arclio

[Arclio](https://arclio.com) provides secure and robust Model Context Protocol (MCP) solutions, enabling AI applications to safely and effectively interact with enterprise systems and external services.

---

<div align="center">
<p>Built with ❤️ by the Arclio team</p>
</div>
