# Arclio MCP Tooling Monorepo

<div align="center">

**Model Context Protocol (MCP) tooling for AI assistants**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Built with: UV](https://img.shields.io/badge/built%20with-uv-blueviolet.svg)](https://github.com/astral-sh/uv)

_Developed and maintained by [Arclio](https://arclio.com)_ - _Secure MCP service management for AI applications_

</div>

---

## 📋 Overview

The `arclio-mcp-tooling` monorepo houses a collection of Model Context Protocol (MCP) packages that enable AI models to interact with external services securely. Each package in this repository provides a standardized interface for AI assistants to access and manipulate data in various systems.

### What is MCP?

The Model Context Protocol (MCP) provides a standardized interface for AI models to access external tools and services. Each package in this monorepo implements an MCP server that exposes capabilities as tools that can be discovered and called by AI models.

## 🛠️ Packages

This monorepo contains the following packages:

### 📚 arclio-mcp-gsuite

Google Workspace integration for AI assistants, providing tools for:

- Google Drive (file operations)
- Gmail (email management)
- Google Calendar (event scheduling)
- Google Slides (presentation creation)

## 🏗️ Architecture

The monorepo follows a standardized structure:

```
arclio-mcp-tooling/
├── packages/                    # Package implementations
│   └── arclio-mcp-gsuite/       # Google Workspace integration
├── tests/                       # Testing infrastructure
├── Makefile                     # Build and development tasks
└── README.md                    # Documentation
```

## 📦 Getting Started

### Prerequisites

- Python 3.10 or higher
- Make

### Installation

```bash
# Clone the repository
git clone https://github.com/arclio/arclio-mcp-tooling.git
cd arclio-mcp-tooling

# Set up the development environment
make setup-dev

# Install all packages in development mode
make install-all
```

### Running Tests

```bash
# Run all tests
make test

# Run only unit tests
make test-unit

# Run only integration tests
make test-integration

# Run tests for a specific package
make test-gsuite
```

### Running Servers

```bash
# Run the Google Workspace MCP server
make run-gsuite
```

## 🧩 Development

### Adding Dependencies

```bash
# Add a dependency to the Google Workspace package
make add gsuite google-api-python-client
```

### Code Quality

```bash
# Run linting
make lint

# Fix linting issues
make fix

# Format code
make format
```

### Building Packages

```bash
# Build all packages
make build

# Publish all packages
make publish
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file in each package for details.

## 🏢 About Arclio

[Arclio](https://arclio.com) is a leading provider of secure MCP service management for AI applications. We specialize in creating robust, enterprise-grade tools that enable AI models to interact with external services safely and effectively.
