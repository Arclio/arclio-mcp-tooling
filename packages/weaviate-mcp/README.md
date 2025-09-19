# Weaviate MCP Server

<div align="center">

**Weaviate vector database integration for AI assistants via Model Context Protocol (MCP)**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

_Developed and maintained by [Arclio](https://arclio.ai)_ - _Secure MCP service management for AI applications_

</div>

---

## 🚀 Quick Start

Test the server immediately using the Model Context Protocol (MCP) Inspector, or install and run it directly.

### Option 1: Instant Setup with MCP Inspector (Recommended for Testing)

```bash
# First, start a local Weaviate instance
docker-compose -f docker-compose.weaviate.yml up -d

# Then test with MCP Inspector
npx @modelcontextprotocol/inspector \
  -e WEAVIATE_URL="localhost" \
  -e WEAVIATE_HTTP_PORT="8080" \
  -e WEAVIATE_GRPC_PORT="50051" \
  -e WEAVIATE_OPENAI_API_KEY="your-openai-api-key" \
  -- \
  uvx --from weaviate-mcp weaviate-mcp
```

Replace `your-openai-api-key` with your actual OpenAI API key.

### Option 2: Direct Installation & Usage

1. **Install the package:**

   ```bash
   pip install weaviate-mcp
   ```

2. **Set Environment Variables:**

   ```bash
   export WEAVIATE_URL="localhost"
   export WEAVIATE_HTTP_PORT="8080"
   export WEAVIATE_GRPC_PORT="50051"
   export WEAVIATE_OPENAI_API_KEY="your-openai-api-key"
   ```

3. **Run the MCP Server:**

   ```bash
   python -m weaviate_mcp
   ```

### Option 3: Using `uvx` (Run without full installation)

```bash
# Ensure WEAVIATE_* environment variables are set as shown above
uvx --from weaviate-mcp weaviate-mcp
```

## 📋 Overview

`weaviate-mcp` is a Python package that enables AI models to interact with Weaviate vector databases through the Model Context Protocol (MCP). It acts as a secure and standardized bridge, allowing AI assistants to leverage Weaviate's powerful vector search and storage capabilities without direct database credential exposure.

### What is MCP?

The Model Context Protocol (MCP) provides a standardized interface for AI models to discover and utilize external tools and services. This package implements an MCP server that exposes Weaviate capabilities as discrete, callable "tools."

### Key Benefits

- **AI-Ready Integration**: Purpose-built for AI assistants to naturally interact with vector databases.
- **Standardized Protocol**: Ensures seamless integration with MCP-compatible AI systems and hubs.
- **Enhanced Security**: Database credentials remain on the server, isolated from the AI models.
- **Comprehensive Vector Operations**: Offers semantic search, hybrid search, and full CRUD operations.
- **Dynamic Schema Management**: Create and manage collections on-the-fly without predefined schemas.
- **Robust Error Handling**: Provides consistent error patterns for reliable operation.
- **Extensive Testing**: Underpinned by a comprehensive test suite for correctness and stability.

## 🏗️ Prerequisites & Setup

### Step 1: Weaviate Instance Setup

You need a running Weaviate instance. Choose one of these options:

#### Option A: Local Development with Docker (Recommended)

1. **Download the Docker Compose file:**
   ```bash
   curl -O https://raw.githubusercontent.com/your-repo/arclio-mcp-tooling/main/docker-compose.weaviate.yml
   ```

2. **Create environment file:**
   ```bash
   cp weaviate-mcp.env.example .env
   # Edit .env and add your OpenAI API key
   ```

3. **Start Weaviate:**
   ```bash
   docker-compose -f docker-compose.weaviate.yml up -d
   ```

4. **Verify Weaviate is running:**
   ```bash
   curl http://localhost:8080/v1/.well-known/ready
   ```

#### Option B: Weaviate Cloud Services (WCS)

1. Sign up at [Weaviate Cloud Services](https://console.weaviate.cloud/)
2. Create a new cluster
3. Note your cluster URL and API key
4. Set environment variables accordingly

### Step 2: OpenAI API Key

This MCP server uses OpenAI's text embedding models for vectorization:

1. Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys)
2. Set the `WEAVIATE_OPENAI_API_KEY` environment variable

## ⚙️ Configuration

### Environment Variables

The MCP server requires the following environment variables:

```bash
# Essential connection settings
export WEAVIATE_URL="localhost"                    # Weaviate host (without http/https)
export WEAVIATE_HTTP_PORT="8080"                  # HTTP port
export WEAVIATE_GRPC_PORT="50051"                 # gRPC port (for better performance)

# Required for text vectorization
export WEAVIATE_OPENAI_API_KEY="your-api-key"     # OpenAI API key

# Optional authentication (if your Weaviate instance requires it)
# export WEAVIATE_API_KEY="your-weaviate-api-key"
# export WEAVIATE_USERNAME="username"
# export WEAVIATE_PASSWORD="password"

# Optional performance settings
# export WEAVIATE_TIMEOUT="60"                    # Connection timeout in seconds
# export WEAVIATE_USE_SSL="false"                 # Use SSL/TLS connection
```

### Configuration File

For persistent configuration, create a `.env` file:

```bash
# Copy the example file
cp weaviate-mcp.env.example .env

# Edit with your actual values
nano .env
```

## 🛠️ Exposed Capabilities (Tools)

This package exposes comprehensive tools for AI interaction with Weaviate.

### Collection Management Tools

- **`weaviate_create_collection`**: Create new collections with custom schemas
- **`weaviate_delete_collection`**: Delete existing collections
- **`weaviate_get_schema`**: Retrieve current database schema

### Data Management Tools

- **`weaviate_insert_object`**: Insert single objects with duplicate checking
- **`weaviate_batch_insert_objects`**: Batch insert multiple objects efficiently
- **`weaviate_get_object`**: Retrieve objects by UUID
- **`weaviate_get_objects`**: Query multiple objects with filtering and pagination
- **`weaviate_update_object`**: Update existing objects
- **`weaviate_delete_object`**: Delete objects by UUID

### Search & Query Tools

- **`weaviate_vector_search`**: Semantic vector search using embeddings
- **`weaviate_hybrid_search`**: Combined semantic and keyword search

### Analytics & Schema Tools

- **`weaviate_aggregate`**: Perform aggregation operations
- **`weaviate_get_schema_info`**: Get detailed schema information with statistics
- **`weaviate_validate_collection_exists`**: Check if a collection exists
- **`weaviate_get_collection_stats`**: Get statistics for a specific collection

## 🔍 Troubleshooting

### Connection Issues

- **"Connection refused"**: Ensure Weaviate is running on the specified host and port
  ```bash
  curl http://localhost:8080/v1/.well-known/ready
  ```

- **"Authentication failed"**: Check your Weaviate credentials and API keys
- **"SSL/TLS errors"**: Verify `WEAVIATE_USE_SSL` setting matches your Weaviate configuration

### OpenAI Integration Issues

- **"Invalid API key"**: Verify your `WEAVIATE_OPENAI_API_KEY` is correct and active
- **"Rate limit exceeded"**: OpenAI API has usage limits; check your quota

### MCP Server Issues

- **"Tool not found"**: Verify the tool name matches exactly (case-sensitive)
- **"Invalid arguments"**: Check the tool's parameter requirements and types
- **"Server not responding"**: Check server logs for error messages

For detailed debugging, inspect the server's stdout/stderr logs.

## 📚 Usage Examples

### Creating Collections with Vectorization

```python
# Create a collection with OpenAI vectorization for semantic search
await weaviate_create_collection(
    name="Articles",
    description="Collection for storing articles with semantic search",
    properties=[
        {
            "name": "title",
            "data_type": "text",
            "description": "Article title"
        },
        {
            "name": "content",
            "data_type": "text",
            "description": "Article content"
        },
        {
            "name": "author",
            "data_type": "text",
            "description": "Article author"
        }
    ],
    vectorizer_config={
        "type": "text2vec_openai",
        "model": "text-embedding-3-small"
    }
)
```

### Basic CRUD Operations

```python
# Insert an article
result = await weaviate_insert_object(
    collection_name="Articles",
    data={
        "title": "The Future of AI",
        "content": "Artificial intelligence is transforming...",
        "author": "Dr. Jane Smith"
    }
)
object_id = result["object_id"]

# Retrieve the article
article = await weaviate_get_object(
    collection_name="Articles",
    uuid=object_id
)

# Update the article
await weaviate_update_object(
    collection_name="Articles",
    uuid=object_id,
    data={
        "title": "The Future of AI - Updated",
        "content": "Artificial intelligence is rapidly transforming..."
    }
)
```

### Semantic Search (Requires Vectorizer)

```python
# Perform semantic search
results = await weaviate_vector_search(
    collection_name="Articles",
    query_text="machine learning algorithms",
    limit=5
)

# Hybrid search (semantic + keyword)
results = await weaviate_hybrid_search(
    collection_name="Articles",
    query_text="neural networks deep learning",
    alpha=0.7,  # More semantic, less keyword
    limit=10
)
```

### Schema Management

```python
# Get detailed schema information
schema_info = await weaviate_get_schema_info()

# Validate collection exists
validation = await weaviate_validate_collection_exists("Articles")
if validation["exists"]:
    print(f"Collection has {validation['object_count']} objects")

# Compare two collections
comparison = await weaviate_compare_collections("Articles", "Products")
print(f"Common properties: {comparison['common_properties']}")
```

## 📝 Contributing

Contributions are welcome! Please refer to the main `README.md` in the `arclio-mcp-tooling` monorepo for guidelines on contributing, setting up the development environment, and project-wide commands.

## 📄 License

This package is licensed under the MIT License. See the `LICENSE` file in the monorepo root for full details.

## 🏢 About Arclio

[Arclio](https://arclio.com) provides secure and robust Model Context Protocol (MCP) solutions, enabling AI applications to safely and effectively interact with enterprise systems and external services.

---

<div align="center">
<p>Built with ❤️ by the Arclio team</p>
</div>
