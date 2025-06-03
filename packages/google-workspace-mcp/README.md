# google-workspace-mcp

<div align="center">

**Google Workspace integration for AI assistants via Model Context Protocol (MCP)**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 125 passing](https://img.shields.io/badge/tests-125%20passing-brightgreen.svg)](https://github.com/arclio/google-workspace-mcp)

_Developed and maintained by [Arclio](https://arclio.com)_ - _Secure MCP service management for AI applications_

</div>

---

## 🚀 Quick Start

### Prerequisites

1. **Google OAuth Credentials**: Get these from [Google Cloud Console](https://console.cloud.google.com/)
2. **Python 3.10+**: Required for the MCP server

### Instant Setup with MCP Inspector

Test the server immediately using MCP Inspector:

```bash
npx @modelcontextprotocol/inspector \
  -e GOOGLE_WORKSPACE_CLIENT_ID="your-client-id.apps.googleusercontent.com" \
  -e GOOGLE_WORKSPACE_CLIENT_SECRET="your-client-secret" \
  -e GOOGLE_WORKSPACE_REFRESH_TOKEN="your-refresh-token" \
  -e GOOGLE_WORKSPACE_ENABLED_CAPABILITIES='["slides", "calendar", "drive", "gmail"]' \
  -- \
  uvx --from google-workspace-mcp google-workspace-worker
```

### Direct Installation & Usage

```bash
# Install the package
pip install google-workspace-mcp

# Set environment variables
export GOOGLE_WORKSPACE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export GOOGLE_WORKSPACE_CLIENT_SECRET="your-client-secret"
export GOOGLE_WORKSPACE_REFRESH_TOKEN="your-refresh-token"
export GOOGLE_WORKSPACE_ENABLED_CAPABILITIES='["drive", "docs", "gmail", "calendar", "slides"]'

# Run the MCP server
google-workspace-worker
```

### Using with uvx (Recommended)

```bash
# Run without installation
uvx --from google-workspace-mcp google-workspace-worker

# Or with environment variables inline
GOOGLE_WORKSPACE_CLIENT_ID="your-id" GOOGLE_WORKSPACE_CLIENT_SECRET="your-secret" \
GOOGLE_WORKSPACE_REFRESH_TOKEN="your-token" GOOGLE_WORKSPACE_ENABLED_CAPABILITIES='["drive", "docs", "gmail", "calendar", "slides"]' \
uvx --from google-workspace-mcp google-workspace-worker
```

## 🔑 Authentication Setup

### Step 1: Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the required APIs:
   - Google Drive API
   - Gmail API
   - Google Calendar API
   - Google Slides API
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
5. Choose "Web application" as application type
6. Add authorized redirect URIs (for OAuth flow)

### Step 2: Get Refresh Token

**Option A: Using OAuth 2.0 Playground (Easiest)**

1. Go to [OAuth 2.0 Playground](https://developers.google.com/oauthplayground/)
2. Click the gear icon (⚙️) and check "Use your own OAuth credentials"
3. Enter your Client ID and Client Secret
4. In Step 1, select the required scopes:
   ```
   https://www.googleapis.com/auth/drive
   https://www.googleapis.com/auth/gmail.modify
   https://www.googleapis.com/auth/calendar
   https://www.googleapis.com/auth/presentations
   ```
5. Click "Authorize APIs" and complete the OAuth flow
6. In Step 2, click "Exchange authorization code for tokens"
7. Copy the `refresh_token` value

**Option B: Using Python Script**

```python
from google_auth_oauthlib.flow import Flow

# Configure the OAuth flow
flow = Flow.from_client_config(
    {
        "web": {
            "client_id": "your-client-id",
            "client_secret": "your-client-secret",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost:8080/callback"]
        }
    },
    scopes=[
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/presentations"
    ]
)

flow.redirect_uri = "http://localhost:8080/callback"
auth_url, _ = flow.authorization_url(prompt='consent')
print(f"Visit this URL: {auth_url}")

# After visiting URL and getting the code:
# flow.fetch_token(code="authorization-code-from-callback")
# print(f"Refresh token: {flow.credentials.refresh_token}")
```

### Step 3: Environment Variables

Set these environment variables before running the server:

```bash
# Required
export GOOGLE_WORKSPACE_CLIENT_ID="144233821775-example.apps.googleusercontent.com"
export GOOGLE_WORKSPACE_CLIENT_SECRET="GOCSPX-example_secret"
export GOOGLE_WORKSPACE_REFRESH_TOKEN="1//05example_refresh_token"

# Optional - specify which services to enable (default: all)
export GOOGLE_WORKSPACE_ENABLED_CAPABILITIES='["drive", "docs", "gmail", "calendar", "slides"]'

# Optional - for development/testing
export RUN_INTEGRATION_TESTS="0"
```

### Capabilities Configuration

The `GOOGLE_WORKSPACE_ENABLED_CAPABILITIES` environment variable specifies which Google Workspace services should be enabled. This must be formatted as a **JSON array of strings**.

**Valid format examples:**

```bash
# Enable all services
export GOOGLE_WORKSPACE_ENABLED_CAPABILITIES='["drive", "docs", "gmail", "calendar", "slides"]'

# Enable only specific services
export GOOGLE_WORKSPACE_ENABLED_CAPABILITIES='["drive", "docs", "gmail"]'

# Enable single service
export GOOGLE_WORKSPACE_ENABLED_CAPABILITIES='["docs"]'

# Empty array (disables all services)
export GOOGLE_WORKSPACE_ENABLED_CAPABILITIES='[]'
```

**Available capability values:**

- `"drive"` - Google Drive file operations
- `"docs"` - Google Docs document creation and metadata retrieval
- `"gmail"` - Gmail email management
- `"calendar"` - Google Calendar events
- `"slides"` - Google Slides presentations
- `"sheets"` - Google Sheets spreadsheet operations

**⚠️ Important Notes:**

- The value **must** be valid JSON (use single quotes around the JSON string in bash)
- Service names are case-insensitive but should be lowercase
- Invalid JSON or non-array values will result in all services being disabled
- If the environment variable is not set, defaults to empty array (all services disabled)

## 📋 Overview

`google-workspace-mcp` is a robust Python package that enables AI models to interact with Google Workspace services via the Model Context Protocol (MCP). It serves as an intelligent middleware between AI assistants and Google APIs, allowing models to execute complex operations without direct API access.

### What is MCP?

The Model Context Protocol (MCP) provides a standardized interface for AI models to access external tools and services. `google-workspace-mcp` implements an MCP server that exposes Google Workspace capabilities as tools that can be discovered and called by AI models.

### Key Benefits

- **AI-Ready Integration**: Purpose-built for AI assistants to interact with Google Workspace
- **Standardized Protocol**: Clean integration with MCP-compatible AI systems
- **Enterprise Security**: Credentials remain isolated from AI models
- **Comprehensive APIs**: Support for Drive, Gmail, Calendar, Slides, and Sheets
- **Robust Error Handling**: Consistent error patterns and graceful failure modes
- **Extensive Testing**: 536+ tests ensuring reliability and correctness

## 🛠️ Capabilities

`google-workspace-mcp` provides tools across six major Google Workspace services:

### 📁 Google Drive

- **drive_search_files**: Find files in Google Drive using query syntax
- **drive_read_file_content**: Read file content with automatic format handling
- **drive_upload_file**: Upload local files to Google Drive
- **drive_delete_file**: Remove files from Google Drive

### 📄 Google Docs

- **docs_create_document**: Create new Google Documents with specified titles
- **docs_get_document_metadata**: Retrieve metadata (title, ID, link) for existing documents
- **docs_get_content_as_markdown**: Retrieve the content of a Google Document as Markdown
- **docs_append_text**: Append text to the end of a specified Google Document
- **docs_prepend_text**: Prepend text to the beginning of a specified Google Document
- **docs_insert_text**: Insert text at a specific location within a Google Document
- **docs_batch_update**: Apply multiple raw Google Docs API requests in a single operation (advanced)

### 📧 Gmail

- **query_gmail_emails**: Search emails with Gmail query syntax
- **get_gmail_email**: Retrieve complete message content and metadata
- **create_gmail_draft**: Create draft emails
- **get_gmail_attachment**: Download email attachments
- **reply_gmail_email**: Reply to existing email threads
- **delete_gmail_draft**: Remove draft emails
- **bulk_delete_gmail_emails**: Delete multiple emails in one operation

### 📅 Google Calendar

- **calendar_get_events**: Retrieve calendar events within a time range
- **calendar_get_event_details**: Retrieve detailed information for a specific calendar event by its ID
- **create_calendar_event**: Create new calendar events
- **delete_calendar_event**: Remove calendar events

### 📊 Google Sheets

- **sheets_create_spreadsheet**: Create new Google Spreadsheets with specified titles
- **sheets_read_range**: Read data from specified ranges using A1 notation (e.g., "Sheet1!A1:C5")

### 🖼️ Google Slides

- **get_presentation**: Retrieve presentation details
- **create_presentation**: Create new presentations
- **get_slides**: List all slides in a presentation
- **create_slide**: Add new slides to a presentation
- **add_text_to_slide**: Insert text content into slides
- **delete_slide**: Remove slides from a presentation
- **create_presentation_from_markdown**: Generate entire presentations from Markdown

## 🔄 AI-Powered Workflows

The tools above enable AI assistants to handle complex workflows such as:

- **Email Analysis → Presentation Creation**: Parse emails and convert insights into slides
- **Drive Document Processing**: Read, analyze, and create summaries of documents
- **Document Creation & Management**: Create new Google Docs and retrieve metadata for existing documents
- **Calendar Management**: Schedule meetings based on email communications
- **Document Generation**: Create structured documents from AI-generated content
- **Multi-stage Operations**: Combine tools for complex operations like creating a presentation based on data from a spreadsheet

## 🏗️ Architecture

The project is designed with a clean, layered architecture:

```
google-workspace-mcp/
├── server.py             # MCP server implementation
├── auth/                 # Authentication components
│   ├── __init__.py
│   └── gauth.py          # Google OAuth handling
├── services/             # API service implementations
│   ├── __init__.py
│   ├── base.py           # Base service class
│   ├── drive.py          # Google Drive implementation
│   ├── docs_service.py   # Google Docs implementation
│   ├── gmail.py          # Gmail implementation
│   ├── calendar.py       # Calendar implementation
│   ├── sheets_service.py # Google Sheets implementation
│   └── slides.py         # Slides implementation
└── tools/                # MCP tool handlers
    ├── __init__.py
    ├── base.py           # Base tool handler
    ├── drive.py          # Drive tools
    ├── docs_tools.py     # Docs tools
    ├── gmail.py          # Gmail tools
    ├── calendar.py       # Calendar tools
    ├── sheets_tools.py   # Sheets tools
    └── slides.py         # Slides tools
```

### How It Works

1. MCP Hub initiates the server process
2. The server dynamically discovers all available tool handlers
3. When queried by an AI model, the server returns accessible tools based on enabled capabilities
4. When a tool is called, the server:
   - Validates arguments
   - Routes the request to the appropriate tool handler
   - The tool handler uses a service implementation to interact with Google APIs
   - Results are formatted and returned to the model through the MCP Hub

## 🔧 Integration Examples

### With MCP Inspector

```bash
# Test all capabilities
npx @modelcontextprotocol/inspector \
  -e GOOGLE_WORKSPACE_CLIENT_ID="your-client-id" \
  -e GOOGLE_WORKSPACE_CLIENT_SECRET="your-secret" \
  -e GOOGLE_WORKSPACE_REFRESH_TOKEN="your-token" \
  -e GOOGLE_WORKSPACE_ENABLED_CAPABILITIES='["drive", "docs", "gmail", "calendar", "slides", "sheets"]' \
  -- \
  uvx --from google-workspace-mcp google-workspace-worker

# Test only specific services
npx @modelcontextprotocol/inspector \
  -e GOOGLE_WORKSPACE_CLIENT_ID="your-client-id" \
  -e GOOGLE_WORKSPACE_CLIENT_SECRET="your-secret" \
  -e GOOGLE_WORKSPACE_REFRESH_TOKEN="your-token" \
  -e GOOGLE_WORKSPACE_ENABLED_CAPABILITIES='["drive", "docs", "gmail", "sheets"]' \
  -- \
  uvx --from google-workspace-mcp google-workspace-worker
```

### With Claude Desktop

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "google-workspace": {
      "command": "uvx",
      "args": ["--from", "google-workspace-mcp", "google-workspace-worker"],
      "env": {
        "GOOGLE_WORKSPACE_CLIENT_ID": "your-client-id",
        "GOOGLE_WORKSPACE_CLIENT_SECRET": "your-secret",
        "GOOGLE_WORKSPACE_REFRESH_TOKEN": "your-token",
        "GOOGLE_WORKSPACE_ENABLED_CAPABILITIES": "[\"drive\", \"docs\", \"gmail\", \"calendar\", \"slides\", \"sheets\"]"
      }
    }
  }
}
```

### With Other MCP Clients

The server can be started directly and connected to via stdio:

```bash
# Start the server
GOOGLE_WORKSPACE_CLIENT_ID="your-id" \
GOOGLE_WORKSPACE_CLIENT_SECRET="your-secret" \
GOOGLE_WORKSPACE_REFRESH_TOKEN="your-token" \
GOOGLE_WORKSPACE_ENABLED_CAPABILITIES='["drive", "docs", "gmail", "calendar", "slides", "sheets"]' \
google-workspace-worker

# Or using uvx
uvx --from google-workspace-mcp google-workspace-worker
```

### Tool Call Format

Tools can be called directly without needing to specify user identification:

```json
{
  "name": "gdrive_search",
  "arguments": {
    "query": "name contains 'Project Proposal'",
    "page_size": 5
  }
}
```

## 📋 API Reference

### Response Formats

Tools return different formats based on their function:

- **Gmail tools**: Structured JSON with email metadata and content
- **Drive tools**: File metadata and content (text or base64-encoded for binary files)
- **Calendar tools**: Event details and metadata
- **Slides tools**: Presentation and slide objects

### Google Drive Tools

#### gdrive_search

Searches for files in Google Drive.

**Arguments:**

- `query` (string, required): Drive query syntax (e.g., `"mimeType='image/jpeg'"`)
- `page_size` (integer, optional): Maximum number of files to return (default: 10)

**Returns:**

- List of file metadata objects with ID, name, MIME type, and webViewLink

#### gdrive_read_file

Reads file content from Google Drive.

**Arguments:**

- `file_id` (string, required): Drive file ID

**Returns:**

- For text files: mimeType, content as text, encoding
- For binary files: mimeType, base64-encoded content, encoding
- For Google Docs: Converts to Markdown
- For Google Sheets: Converts to CSV

### Google Docs Tools

#### docs_create_document

Creates a new Google Document with a specified title.

**Arguments:**

- `title` (string, required): The title for the new Google Document

**Returns:**

- Dictionary containing `document_id`, `title`, and `document_link` of the created document

#### docs_get_document_metadata

Retrieves metadata for a specific Google Document.

**Arguments:**

- `document_id` (string, required): The ID of the Google Document

**Returns:**

- Dictionary containing the document's `document_id`, `title`, and `document_link`

#### docs_get_content_as_markdown

Retrieves the content of a Google Document as Markdown.

**Arguments:**

- `document_id` (string, required): The ID of the Google Document

**Returns:**

- Markdown formatted content of the document

#### docs_append_text

Appends text to the end of a specified Google Document.

**Arguments:**

- `document_id` (string, required): The ID of the Google Document
- `text` (string, required): The text to append to the document

**Returns:**

- Updated document object with appended text

#### docs_prepend_text

Prepends text to the beginning of a specified Google Document.

**Arguments:**

- `document_id` (string, required): The ID of the Google Document
- `text` (string, required): The text to prepend to the document

**Returns:**

- Updated document object with prepended text

#### docs_insert_text

Inserts text at a specific location within a specified Google Document.

**Arguments:**

- `document_id` (string, required): The ID of the Google Document
- `text` (string, required): The text to insert into the document
- `index` (integer, optional): The 0-based index where text should be inserted (defaults to 1 for beginning of body)
- `segment_id` (string, optional): The ID of a specific document segment (e.g., header, footer)

**Returns:**

- Dictionary indicating success or failure of the operation

#### docs_batch_update

Applies multiple raw Google Docs API requests in a single operation.

**Arguments:**

- `document_id` (string, required): The ID of the Google Document
- `requests` (array, required): An array of raw Google Docs API request objects

**Returns:**

- API response containing replies for each request and write control information

### Gmail Tools

#### query_gmail_emails

Retrieves detailed information for a specific calendar event by its ID.

**Arguments:**

- `event_id` (string, required): The ID of the event to retrieve
- `calendar_id` (string, optional): The ID of the calendar containing the event (defaults to "primary")

**Returns:**

- Event details object with summary, start, end, description, attendees, location, and other event metadata

#### create_calendar_event

Creates a new calendar event.

**Arguments:**

- `__calendar_id__` (string, optional): Calendar ID (default: primary)
- `summary` (string, required): Event title
- `start_time` (string, required): RFC3339 format (e.g., "2024-05-01T14:00:00Z")
- `end_time` (string, required): RFC3339 format
- `location` (string, optional): Event location
- `description` (string, optional): Event description
- `attendees` (array, optional): List of attendee email addresses
- `send_notifications` (boolean, optional): Whether to notify attendees
- `timezone` (string, optional): Timezone (e.g., "America/New_York")

**Returns:**

- Created event object with ID, details, and web link

### Google Sheets Tools

#### sheets_create_spreadsheet

Creates a new Google Spreadsheet with a specified title.

**Arguments:**

- `title` (string, required): The title for the new Google Spreadsheet

**Returns:**

- Dictionary containing `spreadsheet_id`, `title`, and `spreadsheet_url` of the created spreadsheet

#### sheets_read_range

Reads data from a specified range in a Google Spreadsheet using A1 notation.

**Arguments:**

- `spreadsheet_id` (string, required): The ID of the Google Spreadsheet
- `range_a1` (string, required): The A1 notation of the range to read (e.g., "Sheet1!A1:C5", or "A1:C5")

**Returns:**

- Dictionary containing:
  - `spreadsheet_id`: The ID of the spreadsheet
  - `range_requested`: The requested range
  - `range_returned`: The actual range returned by the API
  - `major_dimension`: How the data is organized (typically "ROWS")
  - `values`: List of lists representing the cell values

### Slides Tools

#### create_presentation_from_markdown

Creates a Google Slides presentation from Markdown content.

**Arguments:**

- `title` (string, required): Presentation title
- `markdown_content` (string, required): Markdown formatted as:

  ```markdown
  # Slide Title

  Content for first slide

  - Bullet point 1
  - Bullet point 2

  ---

  # Second Slide Title

  ## Subtitle

  More content here
  ```

**Returns:**

- Created presentation object with ID, title, and slide count

## 🧩 Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/arclio/google-workspace-mcp.git
cd google-workspace-mcp

# Create virtual environment and install dependencies
make install-dev

# Set up environment variables
cp .env.example .env
# Edit .env with your credentials
source .env
```

### Development Commands

```bash
# Lint code
make lint

# Format code
make format

# Run all tests
make test

# Run unit tests only
make test-unit

# Run integration tests
export RUN_INTEGRATION_TESTS=1
make test-integration

# Build package
make build

# Run server
make run
```

### Testing Structure

The project features a comprehensive testing suite with 580+ tests organized by service and functionality:

```
tests/
├── unit/                     # Unit tests
│   ├── services/             # Service tests
│   │   ├── drive/            # Drive service tests
│   │   ├── docs/             # Docs service tests
│   │   ├── gmail/            # Gmail service tests
│   │   ├── calendar/         # Calendar service tests
│   │   ├── sheets/           # Sheets service tests
│   │   └── slides/           # Slides service tests
│   └── tools/                # Tool handler tests
│       ├── drive/            # Drive tool tests
│       ├── docs/             # Docs tool tests
│       ├── gmail/            # Gmail tool tests
│       ├── calendar/         # Calendar tool tests
│       ├── sheets/           # Sheets tool tests
│       └── slides/           # Slides tool tests
└── integration/              # Integration tests (requires API credentials)
    ├── test_drive_api.py
    ├── test_docs_api.py
    ├── test_gmail_api.py
    ├── test_calendar_api.py
    ├── test_sheets_api.py
    └── test_slides_api.py
```

Unit tests mock the Google API calls, while integration tests make actual API calls (only when explicitly enabled).

## 🧠 Adding New Tools

Adding support for a new Google service or tool is straightforward:

1. **Create a Service Class**:

```python
# services/new_service.py
from .base import BaseGoogleService

class NewService(BaseGoogleService):
    def __init__(self):
        super().__init__("service_name", "version")

    def some_operation(self, arg1, arg2):
        try:
            # Implement the operation using self.service
            return result
        except Exception as e:
            return self.handle_api_error("some_operation", e)
```

2. **Create Tool Handlers**:

```python
# tools/new_service.py
from ..services.new_service import NewService
from .base import BaseToolHandler

class NewOperationToolHandler(BaseToolHandler):
    name = "new_operation"
    capability = "new_service"
    description = "Description of what this tool does"
    input_schema = {
        "type": "object",
        "properties": {
            "arg1": {
                "type": "string",
                "description": "Description of arg1"
            }
        },
        "required": ["arg1"]
    }

    def execute_tool(self, args):
        service = NewService()
        return service.some_operation(args["arg1"], args.get("arg2"))
```

3. **Update Imports**:

   - Add the new service to `services/__init__.py`
   - Import handlers in `tools/__init__.py`

4. **Update Scopes**:
   - Add any necessary OAuth scopes to `auth/gauth.py`

The server's dynamic discovery mechanism will automatically find and register new tool handlers.

## 🔍 Troubleshooting

### Common Issues

- **Authentication Errors**: Verify OAuth credentials and scopes
- **Tool Not Found**: Ensure the capability is enabled in `GOOGLE_WORKSPACE_ENABLED_CAPABILITIES`
- **API Limits**: Be aware of Google API quotas and rate limits
- **Permission Issues**: Check that the authenticated user has appropriate permissions

### Debug Mode

Enable debug logging by setting:

```bash
export PYTHONPATH=.
export DEBUG=1
uvx --from google-workspace-mcp google-workspace-worker
```

### Testing Your Setup

Use MCP Inspector to verify your configuration:

```bash
npx @modelcontextprotocol/inspector \
  -e GOOGLE_WORKSPACE_CLIENT_ID="your-client-id" \
  -e GOOGLE_WORKSPACE_CLIENT_SECRET="your-secret" \
  -e GOOGLE_WORKSPACE_REFRESH_TOKEN="your-token" \
  -e GOOGLE_WORKSPACE_ENABLED_CAPABILITIES='["drive"]' \
  -- \
  uvx --from google-workspace-mcp google-workspace-worker
```

## 📝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure your code passes tests and follows the project's style guidelines.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🏢 About Arclio

[Arclio](https://arclio.com) is a leading provider of secure MCP service management for AI applications. We specialize in creating robust, enterprise-grade tools that enable AI models to interact with external services safely and effectively.

---

<div align="center">
<p>Built with ❤️ by the Arclio team</p>
</div>

```

```
