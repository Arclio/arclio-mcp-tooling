# arclio-mcp-gsuite

<div align="center">

**Google Workspace integration for AI assistants via Model Context Protocol (MCP)**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 125 passing](https://img.shields.io/badge/tests-125%20passing-brightgreen.svg)](https://github.com/arclio/arclio-mcp-gsuite)

_Developed and maintained by [Arclio](https://arclio.com)_ - _Secure MCP service management for AI applications_

</div>

---

## 📋 Overview

`arclio-mcp-gsuite` is a robust Python package that enables AI models to interact with Google Workspace services via the Model Context Protocol (MCP). It serves as an intelligent middleware between AI assistants and Google APIs, allowing models to execute complex operations without direct API access.

### What is MCP?

The Model Context Protocol (MCP) provides a standardized interface for AI models to access external tools and services. `arclio-mcp-gsuite` implements an MCP server that exposes Google Workspace capabilities as tools that can be discovered and called by AI models.

### Key Benefits

- **AI-Ready Integration**: Purpose-built for AI assistants to interact with Google Workspace
- **Standardized Protocol**: Clean integration with MCP-compatible AI systems
- **Enterprise Security**: Credentials remain isolated from AI models
- **Comprehensive APIs**: Support for Drive, Gmail, Calendar, and Slides
- **Robust Error Handling**: Consistent error patterns and graceful failure modes
- **Extensive Testing**: 125+ tests ensuring reliability and correctness

## 🛠️ Capabilities

`arclio-mcp-gsuite` provides tools across four major Google Workspace services:

### 📁 Google Drive

- **gdrive_search**: Find files in Google Drive using query syntax
- **gdrive_read_file**: Read file content with automatic format handling
- **gdrive_upload_file**: Upload local files to Google Drive
- **gdrive_delete_file**: Remove files from Google Drive

### 📧 Gmail

- **query_gmail_emails**: Search emails with Gmail query syntax
- **get_gmail_email**: Retrieve complete message content and metadata
- **create_gmail_draft**: Create draft emails
- **get_gmail_attachment**: Download email attachments
- **reply_gmail_email**: Reply to existing email threads
- **delete_gmail_draft**: Remove draft emails
- **bulk_delete_gmail_emails**: Delete multiple emails in one operation

### 📅 Google Calendar

- **list_calendars**: View all accessible calendars
- **get_calendar_events**: Retrieve calendar events
- **create_calendar_event**: Create new calendar events
- **delete_calendar_event**: Remove calendar events

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
- **Calendar Management**: Schedule meetings based on email communications
- **Document Generation**: Create structured documents from AI-generated content
- **Multi-stage Operations**: Combine tools for complex operations like creating a presentation based on data from a spreadsheet

## 🏗️ Architecture

The project is designed with a clean, layered architecture:

```
arclio-mcp-gsuite/
├── server.py             # MCP server implementation
├── auth/                 # Authentication components
│   ├── __init__.py
│   └── gauth.py          # Google OAuth handling
├── services/             # API service implementations
│   ├── __init__.py
│   ├── base.py           # Base service class
│   ├── drive.py          # Google Drive implementation
│   ├── gmail.py          # Gmail implementation
│   ├── calendar.py       # Calendar implementation
│   └── slides.py         # Slides implementation
└── tools/                # MCP tool handlers
    ├── __init__.py
    ├── base.py           # Base tool handler
    ├── drive.py          # Drive tools
    ├── gmail.py          # Gmail tools
    ├── calendar.py       # Calendar tools
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

![Architecture Flow](https://i.imgur.com/XPSXYzM.png)

## 📦 Installation & Setup

### Prerequisites

- Python 3.9 or higher
- Google Cloud project with API access
- OAuth credentials with appropriate scopes

### Installation

```bash
# Install from source
git clone https://github.com/arclio/arclio-mcp-gsuite.git
cd arclio-mcp-gsuite
pip install -e .

# Or via pip (when available)
pip install arclio-mcp-gsuite

# For development with CLI tools
pip install "arclio-mcp-gsuite[dev]"
```

### OAuth Setup

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the APIs you need (Drive, Gmail, Calendar, Slides)
3. Create OAuth credentials (web application type)
4. Use the [OAuth 2.0 Playground](https://developers.google.com/oauthplayground/) or your own app to get a refresh token
5. Set environment variables with your credentials

### Environment Variables

```bash
# Required variables
export GSUITE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export GSUITE_CLIENT_SECRET="your-client-secret"
export GSUITE_REFRESH_TOKEN="your-refresh-token"
export GSUITE_ENABLED_CAPABILITIES="drive,gmail,calendar,slides"

# Optional variables
export RUN_INTEGRATION_TESTS="0"  # Set to "1" to enable integration tests
```

## 🚀 Usage

### Running the Server

```bash
# Directly
python -m arclio_mcp_gsuite

# As a module
python -c "from arclio_mcp_gsuite import main; main()"
```

### Integrating with MCP Hub

1. Ensure your MCP Hub is configured to connect to this server
2. Provide the required environment variables
3. The MCP Hub will handle communication with this server, allowing AI models to:
   - Discover available tools
   - Call tools with appropriate arguments
   - Receive structured responses

### Tool Call Format

Each tool call must include a `__user_id__` parameter representing the Google account email:

```json
{
  "name": "gdrive_search",
  "arguments": {
    "__user_id__": "user@example.com",
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

- `__user_id__` (string, required): Google account email
- `query` (string, required): Drive query syntax (e.g., `"mimeType='image/jpeg'"`)
- `page_size` (integer, optional): Maximum number of files to return (default: 10)

**Returns:**

- List of file metadata objects with ID, name, MIME type, and webViewLink

#### gdrive_read_file

Reads file content from Google Drive.

**Arguments:**

- `__user_id__` (string, required): Google account email
- `file_id` (string, required): Drive file ID

**Returns:**

- For text files: mimeType, content as text, encoding
- For binary files: mimeType, base64-encoded content, encoding
- For Google Docs: Converts to Markdown
- For Google Sheets: Converts to CSV

### Gmail Tools

#### query_gmail_emails

Searches for emails using Gmail query syntax.

**Arguments:**

- `__user_id__` (string, required): Google account email
- `query` (string, optional): Gmail search query (e.g., `"is:unread from:example.com"`)
- `max_results` (integer, optional): Maximum emails to return (default: 100)

**Returns:**

- List of email metadata objects (subject, from, to, date, snippet, id)

#### get_gmail_email

Retrieves a complete email message by ID.

**Arguments:**

- `__user_id__` (string, required): Google account email
- `email_id` (string, required): Gmail message ID

**Returns:**

- Complete email object with headers, body content, and attachment information

### Calendar Tools

#### list_calendars

Lists all accessible calendars.

**Arguments:**

- `__user_id__` (string, required): Google account email

**Returns:**

- List of calendar objects with id, summary, timeZone, and access information

#### create_calendar_event

Creates a new calendar event.

**Arguments:**

- `__user_id__` (string, required): Google account email
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

### Slides Tools

#### create_presentation_from_markdown

Creates a Google Slides presentation from Markdown content.

**Arguments:**

- `__user_id__` (string, required): Google account email
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
git clone https://github.com/arclio/arclio-mcp-gsuite.git
cd arclio-mcp-gsuite

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

The project features a comprehensive testing suite with 125+ tests organized by service and functionality:

```
tests/
├── unit/                     # Unit tests
│   ├── services/             # Service tests
│   │   ├── drive/            # Drive service tests
│   │   ├── gmail/            # Gmail service tests
│   │   ├── calendar/         # Calendar service tests
│   │   └── slides/           # Slides service tests
│   └── tools/                # Tool handler tests
│       ├── drive/            # Drive tool tests
│       ├── gmail/            # Gmail tool tests
│       ├── calendar/         # Calendar tool tests
│       └── slides/           # Slides tool tests
└── integration/              # Integration tests (requires API credentials)
    ├── test_drive_api.py
    ├── test_gmail_api.py
    ├── test_calendar_api.py
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
            "__user_id__": {
                "type": "string",
                "description": "The email address of the Google account"
            },
            "arg1": {
                "type": "string",
                "description": "Description of arg1"
            }
        },
        "required": ["__user_id__", "arg1"]
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

- **Authentication Errors**: Verify OAuth credentials and scopes
- **Missing Dependencies**: Run `make install-dev` to install all dependencies
- **Tool Not Found**: Ensure the capability is enabled in `GSUITE_ENABLED_CAPABILITIES`
- **API Limits**: Be aware of Google API quotas and rate limits
- **Permission Issues**: Check that the authenticated user has appropriate permissions

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
