.PHONY: help install setup setup-dev clean lint fix format test build publish encrypt-root decrypt-root encrypt-pkg decrypt-pkg encrypt decrypt
.DEFAULT_GOAL := help

# Default Python interpreter
PYTHON := python3
# Virtual environment directory
VENV := .venv
# Source directories
PACKAGES_DIR := packages
TESTS_DIR := tests

# Package names (abbreviated and full)
GSUITE := arclio-mcp-gsuite

# Package abbreviations for easy reference in commands
PKG_MAPPINGS := gsuite:$(GSUITE)

# Auto-discover all packages
PACKAGES := $(GSUITE)

# Package directories
GSUITE_DIR := $(PACKAGES_DIR)/$(GSUITE)

# Color codes
GREEN  := $(shell tput -Txterm setaf 2)
YELLOW := $(shell tput -Txterm setaf 3)
CYAN   := $(shell tput -Txterm setaf 6)
BLUE   := $(shell tput -Txterm setaf 4)
MAGENTA := $(shell tput -Txterm setaf 5)
RED    := $(shell tput -Txterm setaf 1)
WHITE  := $(shell tput -Txterm setaf 7)
BOLD   := $(shell tput -Txterm bold)
UNDERLINE := $(shell tput -Txterm smul)
RESET  := $(shell tput -Txterm sgr0)

# Create virtual environment
venv:
	@echo "${CYAN}Creating virtual environment...${RESET}"
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	@echo "${GREEN}Virtual environment created successfully${RESET}"

# Install dependencies
install: venv
	@echo "${CYAN}Installing dependencies...${RESET}"
	$(VENV)/bin/pip install -e .
	@echo "${GREEN}Dependencies installed successfully${RESET}"

# Install development dependencies
setup-dev: install
	@echo "${CYAN}Installing development dependencies...${RESET}"
	$(VENV)/bin/pip install -e ".[dev]"
	@echo "${GREEN}Development dependencies installed successfully${RESET}"

# Setup the monorepo - install uv and sync all packages
setup: venv
	@echo "${CYAN}Setting up monorepo...${RESET}"
	$(VENV)/bin/pip install uv
	$(VENV)/bin/uv sync --all-packages --no-install-workspace --extra dev
	@echo "${GREEN}Monorepo setup complete${RESET}"

# Clean build artifacts and cache files
clean:
	@echo "${CYAN}Cleaning build artifacts and cache files...${RESET}"
	rm -rf dist build *.egg-info .pytest_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf $(VENV) .ruff_cache
	@echo "${GREEN}Cleanup complete${RESET}"

# Linting and formatting
lint:
	@echo "${CYAN}Running linters...${RESET}"
	$(VENV)/bin/ruff check $(PACKAGES_DIR) $(TESTS_DIR)
	@echo "${GREEN}Linting complete${RESET}"

fix:
	@echo "${CYAN}Fixing linting issues...${RESET}"
	$(VENV)/bin/ruff check --fix $(PACKAGES_DIR) $(TESTS_DIR)
	@echo "${GREEN}Fixes applied${RESET}"

format:
	@echo "${CYAN}Formatting code...${RESET}"
	$(VENV)/bin/ruff format $(PACKAGES_DIR) $(TESTS_DIR)
	@echo "${GREEN}Formatting complete${RESET}"

# Testing
test: install-all
	@echo "${CYAN}Running all tests...${RESET}"
	$(VENV)/bin/uv run pytest $(TESTS_DIR)
	@echo "${GREEN}Tests completed${RESET}"

# Run unit tests only
test-unit: install-all
	@echo "${CYAN}Running unit tests...${RESET}"
	$(VENV)/bin/uv run pytest $(TESTS_DIR)/arclio_mcp_gsuite/unit
	@echo "${GREEN}Unit tests completed${RESET}"

# Run integration tests only
test-integration: install-all
	@echo "${CYAN}Running integration tests...${RESET}"
	$(VENV)/bin/uv run pytest $(TESTS_DIR)/arclio_mcp_gsuite/integration
	@echo "${GREEN}Integration tests completed${RESET}"

# Pattern rule for package-specific tests
test-%:
	@echo "${CYAN}Running tests for $*...${RESET}"
	$(VENV)/bin/uv run pytest $(TESTS_DIR)/$(subst -,_,$*)
	@echo "${GREEN}Tests for $* completed${RESET}"

# Build all packages
build: clean
	@echo "${CYAN}Building all packages...${RESET}"
	mkdir -p dist
	$(VENV)/bin/uv build -p $(GSUITE_DIR) -o dist
	@echo "${GREEN}All packages built successfully${RESET}"

# Publish all packages
publish: build
	@echo "${CYAN}Publishing all packages...${RESET}"
	$(VENV)/bin/uv publish dist/arclio_mcp_gsuite-*.whl
	@echo "${GREEN}All packages published successfully${RESET}"

# Add a dependency to a package using positional arguments (make add gsuite pydantic)
add: setup
	@if [ -z "$(word 2,$(MAKECMDGOALS))" ]; then \
		echo "${RED}Error: Package name is required.${RESET}"; \
		echo "${YELLOW}Usage: make add <package_abbrev> <dependency_spec>${RESET}"; \
		exit 1; \
	fi
	@if [ -z "$(word 3,$(MAKECMDGOALS))" ]; then \
		echo "${RED}Error: Dependency specification is required.${RESET}"; \
		echo "${YELLOW}Usage: make add <package_abbrev> <dependency_spec>${RESET}"; \
		exit 1; \
	fi
	@pkg="$(word 2,$(MAKECMDGOALS))"; \
	dep="$(word 3,$(MAKECMDGOALS))"; \
	case "$$pkg" in \
		gsuite) pkg_full="$(GSUITE)" ;; \
		*) echo "${RED}Unknown package abbreviation: $$pkg${RESET}"; exit 1 ;; \
	esac; \
	echo "${CYAN}Adding dependency '$$dep' to package '$$pkg_full'...${RESET}"; \
	$(VENV)/bin/uv add "$$dep" --package "$$pkg_full"; \
	echo "${GREEN}Dependency added successfully${RESET}"

# Make the positional arguments not be interpreted as targets
%:
	@:

# Install packages in development mode
install-all: setup
	@echo "${CYAN}Installing all packages in development mode...${RESET}"
	$(VENV)/bin/uv pip install -e $(GSUITE_DIR)
	@echo "${GREEN}All packages installed in development mode${RESET}"

# Run the MCP server
run-gsuite:
	@echo "${CYAN}Running arclio-mcp-gsuite server...${RESET}"
	$(VENV)/bin/python -m arclio_mcp_gsuite
	@echo "${GREEN}Server executed${RESET}"

# Encrypt root .env to .env.sops
encrypt-root: setup
	@if [ ! -f ".env" ]; then \
		echo "${RED}Error: Root .env file not found${RESET}"; \
		exit 1; \
	fi
	@if [ -z "$$SOPS_AGE_KEY_FILE" ]; then \
		echo "${RED}Error: SOPS_AGE_KEY_FILE not set. Try: source ~/.zshrc ${RESET}"; \
		exit 1; \
	fi
	@echo "${CYAN}Encrypting root .env to .env.sops...${RESET}"
	@SOPS_AGE_KEY_FILE="$$SOPS_AGE_KEY_FILE" sops --input-type dotenv --output-type yaml -e .env > .env.sops
	@echo "${GREEN}Root encryption complete${RESET}"

# Decrypt root .env.sops to .env
decrypt-root: setup
	@if [ ! -f ".env.sops" ]; then \
		echo "${RED}Error: Root .env.sops file not found${RESET}"; \
		exit 1; \
	fi
	@if [ -z "$$SOPS_AGE_KEY_FILE" ]; then \
		echo "${RED}Error: SOPS_AGE_KEY_FILE not set. Try: source ~/.zshrc ${RESET}"; \
		exit 1; \
	fi
	@echo "${CYAN}Decrypting root .env.sops to .env...${RESET}"
	@SOPS_AGE_KEY_FILE="$$SOPS_AGE_KEY_FILE" sops --input-type yaml --output-type dotenv -d .env.sops > .env 2>/tmp/sops_error || { \
		echo "${RED}Root decryption failed. Error:${RESET}"; \
		cat /tmp/sops_error; \
		exit 1; \
	}
	@echo "${GREEN}Root decryption complete${RESET}"

# Encrypt package .env to .env.sops
# Usage: make encrypt-pkg PKG=gsuite
encrypt-pkg: setup
	@if [ -z "$(PKG)" ]; then \
		echo "${RED}Error: PKG argument is required.${RESET}"; \
		echo "${YELLOW}Usage: make encrypt-pkg PKG=gsuite${RESET}"; \
		exit 1; \
	fi
	@pkg="$(PKG)"; \
	case "$$pkg" in \
		gsuite) pkg_dir="$(GSUITE_DIR)" ;; \
		*) echo "${RED}Unknown package abbreviation: $$pkg${RESET}"; exit 1 ;; \
	esac; \
	if [ ! -f "$$pkg_dir/.env" ]; then \
		echo "${RED}Error: .env file not found for package $$pkg${RESET}"; \
		exit 1; \
	fi; \
	if [ -z "$$SOPS_AGE_KEY_FILE" ]; then \
		echo "${RED}Error: SOPS_AGE_KEY_FILE not set. Try: source ~/.zshrc ${RESET}"; \
		exit 1; \
	fi; \
	echo "${CYAN}Encrypting $$pkg_dir/.env to $$pkg_dir/.env.sops...${RESET}"; \
	SOPS_AGE_KEY_FILE="$$SOPS_AGE_KEY_FILE" sops --input-type dotenv --output-type yaml -e $$pkg_dir/.env > $$pkg_dir/.env.sops; \
	echo "${GREEN}Package $$pkg encryption complete${RESET}"

# Usage: make decrypt-pkg PKG=gsuite
decrypt-pkg: setup
	@if [ -z "$(PKG)" ]; then \
		echo "${RED}Error: PKG argument is required.${RESET}"; \
		echo "${YELLOW}Usage: make decrypt-pkg PKG=gsuite${RESET}"; \
		exit 1; \
	fi
	@pkg="$(PKG)"; \
	case "$$pkg" in \
		gsuite) pkg_dir="$(GSUITE_DIR)" ;; \
		*) echo "${RED}Unknown package abbreviation: $$pkg${RESET}"; exit 1 ;; \
	esac; \
	if [ ! -f "$$pkg_dir/.env.sops" ]; then \
		echo "${RED}Error: .env.sops file not found for package $$pkg${RESET}"; \
		exit 1; \
	fi; \
	if [ -z "$$SOPS_AGE_KEY_FILE" ]; then \
		echo "${RED}Error: SOPS_AGE_KEY_FILE not set. Try: source ~/.zshrc ${RESET}"; \
		exit 1; \
	fi; \
	echo "${CYAN}Decrypting $$pkg_dir/.env.sops to $$pkg_dir/.env...${RESET}"; \
	SOPS_AGE_KEY_FILE="$$SOPS_AGE_KEY_FILE" sops --input-type yaml --output-type dotenv -d $$pkg_dir/.env.sops > $$pkg_dir/.env 2>/tmp/sops_error || { \
		echo "${RED}Package $$pkg decryption failed. Error:${RESET}"; \
		cat /tmp/sops_error; \
		exit 1; \
	}; \
	echo "${GREEN}Package $$pkg decryption complete${RESET}"

# Encrypt all .env files in the monorepo
encrypt: encrypt-root
	@echo "${CYAN}Encrypting all package .env files...${RESET}"
	@make encrypt-pkg PKG=gsuite 2>/dev/null || echo "${YELLOW}Skipping gsuite (no .env file)${RESET}"
	@echo "${GREEN}All encryption complete${RESET}"

# Decrypt all .env.sops files in the monorepo
decrypt: decrypt-root
	@echo "${CYAN}Decrypting all package .env.sops files...${RESET}"
	@make decrypt-pkg PKG=gsuite 2>/dev/null || echo "${YELLOW}Skipping gsuite (no .env.sops file)${RESET}"
	@echo "${GREEN}All decryption complete${RESET}"

# Initialize a new age key if needed
init-key:
	@if [ -f "$$HOME/.config/sops/key.txt" ]; then \
		echo "${YELLOW}Key already exists at $$HOME/.config/sops/key.txt${RESET}"; \
		echo "${YELLOW}To create a new key, first move or delete the existing one${RESET}"; \
		exit 1; \
	fi
	@mkdir -p $$HOME/.config/sops
	@echo "${CYAN}Generating new age key...${RESET}"
	@age-keygen -o $$HOME/.config/sops/key.txt
	@echo "${GREEN}Key generated. Add this public key to .sops.yaml:${RESET}"
	@age-keygen -y $$HOME/.config/sops/key.txt | sed 's/^public key: //'
	@echo "${YELLOW}Then add to your shell profile: export SOPS_AGE_KEY_FILE=\$$HOME/.config/sops/key.txt${RESET}"

# Help message with examples and tips
help:
	@echo "$(BOLD)$(BLUE)╔══════════════════════════════════════════════════════════╗$(RESET)"
	@echo "$(BOLD)$(BLUE)║$(RESET) $(BOLD)$(MAGENTA)               ARCLIO MCP TOOLING COMMANDS              $(BLUE)║$(RESET)"
	@echo "$(BOLD)$(BLUE)╚══════════════════════════════════════════════════════════╝$(RESET)"
	@echo ""
	@echo "$(BOLD)$(CYAN)┌─────────────────────────────────────────────────────────┐$(RESET)"
	@echo "$(BOLD)$(CYAN)│$(RESET) $(BOLD)$(WHITE)𝗦𝗲𝘁𝘂𝗽:$(RESET)                                                  $(BOLD)$(CYAN)│$(RESET)"
	@echo "$(BOLD)$(CYAN)└─────────────────────────────────────────────────────────┘$(RESET)"
	@echo "  $(GREEN)make setup$(RESET)              Setup the monorepo for development"
	@echo "  $(GREEN)make install$(RESET)            Install dependencies in a virtual environment"
	@echo "  $(GREEN)make setup-dev$(RESET)          Install development dependencies"
	@echo ""
	@echo "$(BOLD)$(CYAN)┌─────────────────────────────────────────────────────────┐$(RESET)"
	@echo "$(BOLD)$(CYAN)│$(RESET) $(BOLD)$(WHITE)𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗺𝗲𝗻𝘁:$(RESET)                                            $(BOLD)$(CYAN)│$(RESET)"
	@echo "$(BOLD)$(CYAN)└─────────────────────────────────────────────────────────┘$(RESET)"
	@echo "  $(GREEN)make lint$(RESET)               Run linters on all packages"
	@echo "  $(GREEN)make format$(RESET)             Format code in all packages"
	@echo "  $(GREEN)make fix$(RESET)                Fix linting issues automatically"
	@echo ""
	@echo "$(BOLD)$(CYAN)┌─────────────────────────────────────────────────────────┐$(RESET)"
	@echo "$(BOLD)$(CYAN)│$(RESET) $(BOLD)$(WHITE)𝗧𝗲𝘀𝘁𝗶𝗻𝗴:$(RESET)                                                $(BOLD)$(CYAN)│$(RESET)"
	@echo "$(BOLD)$(CYAN)└─────────────────────────────────────────────────────────┘$(RESET)"
	@echo "  $(GREEN)make test$(RESET)               Run all tests"
	@echo "  $(GREEN)make test-unit$(RESET)          Run only unit tests"
	@echo "  $(GREEN)make test-integration$(RESET)   Run only integration tests"
	@echo "  $(GREEN)make test-gsuite$(RESET)        Run tests for arclio-mcp-gsuite package"
	@echo ""
	@echo "$(BOLD)$(CYAN)┌─────────────────────────────────────────────────────────┐$(RESET)"
	@echo "$(BOLD)$(CYAN)│$(RESET) $(BOLD)$(WHITE)𝗣𝗮𝗰𝗸𝗮𝗴𝗲 𝗠𝗮𝗻𝗮𝗴𝗲𝗺𝗲𝗻𝘁:$(RESET)                                     $(BOLD)$(CYAN)│$(RESET)"
	@echo "$(BOLD)$(CYAN)└─────────────────────────────────────────────────────────┘$(RESET)"
	@echo "  $(GREEN)make add gsuite pydantic$(RESET) Add dependency to arclio-mcp-gsuite package"
	@echo "  $(GREEN)make install-all$(RESET)        Install all packages in development mode"
	@echo ""
	@echo "$(BOLD)$(CYAN)┌─────────────────────────────────────────────────────────┐$(RESET)"
	@echo "$(BOLD)$(CYAN)│$(RESET) $(BOLD)$(WHITE)𝗥𝘂𝗻𝗻𝗶𝗻𝗴:$(RESET)                                                $(BOLD)$(CYAN)│$(RESET)"
	@echo "$(BOLD)$(CYAN)└─────────────────────────────────────────────────────────┘$(RESET)"
	@echo "  $(GREEN)make run-gsuite$(RESET)         Run arclio-mcp-gsuite MCP server"
	@echo ""
	@echo "$(BOLD)$(CYAN)┌─────────────────────────────────────────────────────────┐$(RESET)"
	@echo "$(BOLD)$(CYAN)│$(RESET) $(BOLD)$(WHITE)𝗕𝘂𝗶𝗹𝗱𝗶𝗻𝗴:$(RESET)                                               $(BOLD)$(CYAN)│$(RESET)"
	@echo "$(BOLD)$(CYAN)└─────────────────────────────────────────────────────────┘$(RESET)"
	@echo "  $(GREEN)make build$(RESET)              Build all packages"
	@echo "  $(GREEN)make publish$(RESET)            Publish all packages"
	@echo ""
	@echo "$(BOLD)$(CYAN)┌─────────────────────────────────────────────────────────┐$(RESET)"
	@echo "$(BOLD)$(CYAN)│$(RESET) $(BOLD)$(WHITE)𝗨𝘁𝗶𝗹𝗶𝘁𝗶𝗲𝘀:$(RESET)                                              $(BOLD)$(CYAN)│$(RESET)"
	@echo "$(BOLD)$(CYAN)└─────────────────────────────────────────────────────────┘$(RESET)"
	@echo "  $(GREEN)make clean$(RESET)              Clean build artifacts and cache files"
	@echo ""
	@echo "$(BOLD)$(CYAN)┌─────────────────────────────────────────────────────────┐$(RESET)"
	@echo "$(BOLD)$(CYAN)│$(RESET) $(BOLD)$(WHITE)𝗦𝗢𝗣𝗦:$(RESET)                                                   $(BOLD)$(CYAN)│$(RESET)"
	@echo "$(BOLD)$(CYAN)└─────────────────────────────────────────────────────────┘$(RESET)"
	@echo "  $(GREEN)make encrypt-root$(RESET)       Encrypt root .env to .env.sops"
	@echo "  $(GREEN)make decrypt-root$(RESET)       Decrypt root .env.sops to .env"
	@echo "  $(GREEN)make encrypt-pkg PKG=gsuite$(RESET) Encrypt package .env file"
	@echo "  $(GREEN)make decrypt-pkg PKG=gsuite$(RESET) Decrypt package .env.sops file"
	@echo "  $(GREEN)make encrypt$(RESET)            Encrypt all .env files in the monorepo"
	@echo "  $(GREEN)make decrypt$(RESET)            Decrypt all .env.sops files in the monorepo"
	@echo "  $(GREEN)make init-key$(RESET)           Generate a new age key for SOPS"
	@echo ""
	@echo "$(BOLD)$(MAGENTA)Happy coding! 🚀$(RESET)"
