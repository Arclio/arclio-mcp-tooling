# AWS S3 MCP Server

<div align="center">

**Amazon S3 storage integration for AI assistants via Model Context Protocol (MCP)**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

_Developed and maintained by [Arclio](https://arclio.ai)_ - _Secure MCP service management for AI applications_

</div>

---

## 🚀 Quick Start

Test the server immediately using the Model Context Protocol (MCP) Inspector, or install and run it directly.

### Option 1: Instant Setup with MCP Inspector (Recommended for Testing)

```bash
# Test with MCP Inspector
npx @modelcontextprotocol/inspector \
  -e AWS_ACCESS_KEY_ID="your-aws-access-key" \
  -e AWS_SECRET_ACCESS_KEY="your-aws-secret-key" \
  -e AWS_REGION="us-east-1" \
  -e S3_BUCKETS="your-bucket-name" \
  -- \
  uvx --from aws-s3-mcp aws-s3-mcp
```

Replace the environment variables with your actual AWS credentials and bucket names.

### Option 2: Direct Installation & Usage

1. **Install the package:**

   ```bash
   pip install aws-s3-mcp
   ```

2. **Set Environment Variables:**

   ```bash
   export AWS_ACCESS_KEY_ID="your-aws-access-key"
   export AWS_SECRET_ACCESS_KEY="your-aws-secret-key"
   export AWS_REGION="us-east-1"
   export S3_BUCKETS="your-bucket-name"
   ```

3. **Run the MCP Server:**

   ```bash
   python -m aws_s3_mcp
   ```

### Option 3: Using `uvx` (Run without full installation)

```bash
# Ensure AWS_* environment variables are set as shown above
uvx --from aws-s3-mcp aws-s3-mcp
```

## 📋 Overview

`aws-s3-mcp` is a Python package that enables AI models to interact with Amazon S3 storage through the Model Context Protocol (MCP). It acts as a secure and standardized bridge, allowing AI assistants to leverage S3's powerful object storage capabilities without direct credential exposure.

### What is MCP?

The Model Context Protocol (MCP) provides a standardized interface for AI models to discover and utilize external tools and services. This package implements an MCP server that exposes S3 capabilities as discrete, callable "tools."

### Key Benefits

- **AI-Ready Integration**: Purpose-built for AI assistants to naturally interact with S3 storage.
- **Standardized Protocol**: Ensures seamless integration with MCP-compatible AI systems and hubs.
- **Enhanced Security**: AWS credentials remain on the server, isolated from the AI models.
- **Fully Asynchronous**: Uses `aioboto3` exclusively for non-blocking I/O operations.
- **Smart Content Detection**: Automatically differentiates between text and binary files.
- **Robust Error Handling**: Comprehensive error reporting with actionable messages.
- **Configurable Access**: Support for bucket filtering and access controls.

## 🏗️ Prerequisites & Setup

### Step 1: AWS Credentials Setup

You need valid AWS credentials with S3 access permissions:

#### Option A: AWS Access Keys (Recommended for Development)

1. **Get your AWS credentials:**
   - Sign in to the [AWS Management Console](https://console.aws.amazon.com/)
   - Navigate to IAM → Users → Your User → Security credentials
   - Create access key if you don't have one

2. **Set required permissions:**
   Ensure your AWS user/role has the following S3 permissions:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "s3:ListBucket",
           "s3:GetObject"
         ],
         "Resource": [
           "arn:aws:s3:::your-bucket-name",
           "arn:aws:s3:::your-bucket-name/*"
         ]
       }
     ]
   }
   ```

#### Option B: AWS CLI Configuration

If you have AWS CLI configured, the server will automatically use those credentials:

```bash
aws configure
```

### Step 2: S3 Bucket Access

Ensure you have at least one S3 bucket with objects you want to access. The server can be configured to access specific buckets or all accessible buckets.

## ⚙️ Configuration

### Environment Variables

The MCP server requires the following environment variables:

```bash
# Essential AWS credentials
export AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"        # Your AWS access key
export AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG..."  # Your AWS secret key
export AWS_REGION="us-east-1"                           # AWS region

# Optional S3 configuration
export S3_BUCKETS="bucket1,bucket2,bucket3"             # Comma-separated list of allowed buckets
export S3_MAX_BUCKETS="5"                               # Maximum buckets to list (default: 5)
export S3_OBJECT_MAX_KEYS="1000"                        # Maximum objects per request (default: 1000)
```

### Configuration File

For persistent configuration, create a `.env` file:

```bash
# Copy the example file (if available)
cp .env.example .env

# Or create your own .env file
cat > .env << EOF
AWS_ACCESS_KEY_ID=your-access-key-here
AWS_SECRET_ACCESS_KEY=your-secret-key-here
AWS_REGION=us-east-1
S3_BUCKETS=my-documents,my-images
S3_MAX_BUCKETS=10
S3_OBJECT_MAX_KEYS=500
EOF
```

## 🛠️ Exposed Capabilities (Tools)

This package exposes comprehensive tools for AI interaction with Amazon S3.

### Object Listing Tools

- **`s3_list_objects`**: List objects within a specified S3 bucket with optional prefix filtering

### Content Retrieval Tools

- **`s3_get_object_content`**: Retrieve content from S3 objects with automatic text/binary detection and proper encoding

## 🔍 Troubleshooting

### Connection Issues

- **"AWS credentials not found"**: Ensure `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are set
  ```bash
  echo $AWS_ACCESS_KEY_ID
  echo $AWS_SECRET_ACCESS_KEY
  ```

- **"Access Denied"**: Check your AWS IAM permissions for S3 access
- **"Bucket not found"**: Verify the bucket name and region are correct

### Configuration Issues

- **"InvalidAccessKeyId"**: Verify your AWS access key is correct and active
- **"SignatureDoesNotMatch"**: Check that your AWS secret key is correct
- **"Bucket not in configured list"**: Add the bucket to your `S3_BUCKETS` environment variable

### MCP Server Issues

- **"Tool not found"**: Verify the tool name matches exactly (case-sensitive)
- **"Invalid arguments"**: Check the tool's parameter requirements and types
- **"Server not responding"**: Check server logs for error messages

For detailed debugging, inspect the server's stdout/stderr logs.

## 📚 Usage Examples

### Listing S3 Objects

```python
# List all objects in a bucket
result = await s3_list_objects(bucket_name="my-documents")

# List objects with prefix filter
result = await s3_list_objects(
    bucket_name="my-documents",
    prefix="reports/2024/",
    max_keys=50
)

# Example response:
{
  "count": 2,
  "objects": [
    {
      "key": "reports/2024/q1-report.pdf",
      "last_modified": "2024-03-20T10:00:00Z",
      "size": 123456,
      "etag": "abc1234"
    },
    {
      "key": "reports/2024/q1-summary.md",
      "last_modified": "2024-03-21T14:30:00Z",
      "size": 5678,
      "etag": "def5678"
    }
  ]
}
```

### Retrieving Object Content

```python
# Get text file content
result = await s3_get_object_content(
    bucket_name="my-documents",
    key="reports/quarterly-report.md"
)
# Returns: {
#   "content": "# Q1 Report\n\nThis quarter...",
#   "mime_type": "text/markdown",
#   "encoding": "utf-8",
#   "size": 1024
# }

# Get binary file content (automatically Base64 encoded)
result = await s3_get_object_content(
    bucket_name="my-documents",
    key="reports/chart.pdf"
)
# Returns: {
#   "content": "JVBERi0xLjQ...",  # Base64 encoded
#   "mime_type": "application/pdf",
#   "encoding": "base64",
#   "size": 51200
# }
```

### Working with Different File Types

The server automatically detects content types and handles encoding:

- **Text files** (`.txt`, `.md`, `.json`, `.csv`, etc.): Returned as UTF-8 strings
- **Binary files** (`.pdf`, `.jpg`, `.zip`, etc.): Returned as Base64 encoded strings
- **Unknown types**: Analyzed heuristically for text vs binary content

## 📝 Contributing

Contributions are welcome! Please refer to the main `README.md` in the `arclio-mcp-tooling` monorepo for guidelines on contributing, setting up the development environment, and project-wide commands.

### Development Setup

```bash
# Clone the monorepo
git clone https://github.com/your-org/arclio-mcp-tooling.git
cd arclio-mcp-tooling

# Set up development environment
make setup-dev

# Run tests for AWS S3 MCP
make test tests/aws-s3-mcp

# Run with coverage
make cov tests/aws-s3-mcp

# Lint code
make lint aws-s3-mcp
```

## 📄 License

This package is licensed under the MIT License. See the `LICENSE` file in the monorepo root for full details.

## 🏢 About Arclio

[Arclio](https://arclio.com) provides secure and robust Model Context Protocol (MCP) solutions, enabling AI applications to safely and effectively interact with enterprise systems and external services.

---

<div align="center">
<p>Built with ❤️ by the Arclio team</p>
</div>
