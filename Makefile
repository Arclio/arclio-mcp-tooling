.PHONY: help setup clean lint format fix test test-unit test-integration build publish add \
        encrypt-root decrypt-root encrypt-pkg decrypt-pkg encrypt decrypt init-key \
        run-gsuite install-editable

.DEFAULT_GOAL := help

# --- Environment Variables ---
# Attempt to load .env file if it exists
# This ensures variables like UV_PYPI_TOKEN are available to make recipes
# if they are defined in a .env file at the root of the project.
# Make sure this .env file is gitignored if it contains secrets.
# If using SOPS, 'make decrypt' should generate the .env file.
ifneq (,$(wildcard ./.env))
    include .env
    # Corrected line: Robustly export variables from .env, excluding comments and empty lines.
    export $$(shell grep -Ev '^\s*(#|$$$$)' .env | cut -d= -f1 | tr '\n' ' ')
endif

# --- Environment & Tools ---
PYTHON := python3
VENV_DIR := .venv
# Tools are activated within recipes using '. $(VENV_DIR)/bin/activate && $(TOOL)'
UV := uv
PIP := pip
RUFF := ruff
PYTEST := pytest
SOPS := sops

# --- Directories ---
PACKAGES_ROOT_DIR := packages
TESTS_ROOT_DIR := tests

# --- Package Definitions ---
# List package *directory names* under packages/
PKG_NAMES := arclio-mcp-gsuite markdowndeck

# --- Color Codes ---
GREEN  := $(shell tput -Txterm setaf 2)
YELLOW := $(shell tput -Txterm setaf 3)
CYAN   := $(shell tput -Txterm setaf 6)
BLUE   := $(shell tput -Txterm setaf 4)
MAGENTA := $(shell tput -Txterm setaf 5)
RED    := $(shell tput -Txterm setaf 1)
WHITE  := $(shell tput -Txterm setaf 7)
BOLD   := $(shell tput -Txterm bold)
RESET  := $(shell tput -Txterm sgr0)

# --- Helper for Argument Parsing ---
TARGET_ARGS = $(filter-out $@,$(MAKECMDGOALS))
FIRST_TARGET_ARG = $(firstword $(TARGET_ARGS))

# --- Core Setup ---
$(VENV_DIR)/bin/activate:
	@echo "${CYAN}Creating virtual environment and installing uv...${RESET}"
	$(PYTHON) -m venv $(VENV_DIR)
	"$(VENV_DIR)/bin/$(PIP)" install --upgrade pip
	"$(VENV_DIR)/bin/$(PIP)" install uv
	@touch "$(VENV_DIR)/bin/activate"
	@echo "${GREEN}Virtual environment and uv installed successfully.${RESET}"
	@echo "${YELLOW}Run 'source $(VENV_DIR)/bin/activate' to activate the virtual environment for subsequent manual commands.${RESET}"
	@echo "${YELLOW}Makefile commands will attempt to activate it implicitly where needed.${RESET}"

setup: $(VENV_DIR)/bin/activate
	@echo "${CYAN}Syncing all workspace packages and dependencies with uv...${RESET}"
	. "$(VENV_DIR)/bin/activate"; $(UV) sync --all-packages --no-install-workspace --extra dev
	@echo "${GREEN}Monorepo setup and sync complete.${RESET}"


install-editable: setup
	@PKGS_TO_INSTALL="$(PKGS)"; \
	if [ -z "$$PKGS_TO_INSTALL" ]; then \
		echo "${RED}Error: PKGS argument is required. Provide space-separated package dir names.${RESET}"; \
		echo "${YELLOW}Example: make install-editable PKGS=\"arclio-mcp-gsuite markdowndeck\"${RESET}"; \
		exit 1; \
	fi; \
	INSTALL_PATHS=""; \
	for pkg_name in $$PKGS_TO_INSTALL; do \
		pkg_path="$(PACKAGES_ROOT_DIR)/$$pkg_name"; \
		if [ ! -d "$$pkg_path" ]; then \
			echo "${RED}Error: Package directory '$$pkg_path' not found for package '$$pkg_name'.${RESET}"; \
			exit 1; \
		fi; \
		INSTALL_PATHS="$$INSTALL_PATHS -e $$pkg_path"; \
	done; \
	echo "${CYAN}Installing packages editable:$$INSTALL_PATHS...${RESET}"; \
	. "$(VENV_DIR)/bin/activate"; $(UV) pip install $$INSTALL_PATHS; \
	echo "${GREEN}Editable installation complete.${RESET}"

# --- Cleaning ---
clean:
	@echo "${CYAN}Cleaning build artifacts, cache files, and virtual environment...${RESET}"
	rm -rf dist build *.egg-info .pytest_cache .coverage htmlcov coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf "$(VENV_DIR)" .ruff_cache
	@echo "${GREEN}Cleanup complete.${RESET}"

# --- Code Quality ---
lint format fix: setup
	@ACTION=$@; \
	TARGET_PKG_NAME=$(FIRST_TARGET_ARG); \
	CMD_PATH=""; \
	MSG_SUFFIX=""; \
	if [ -n "$$TARGET_PKG_NAME" ] && [[ " $(PKG_NAMES) " =~ " $$TARGET_PKG_NAME " ]]; then \
		CMD_PATH_PKG="$(PACKAGES_ROOT_DIR)/$$TARGET_PKG_NAME"; \
		CMD_PATH_TESTS="$(TESTS_ROOT_DIR)/$$TARGET_PKG_NAME"; \
		if [ -d "$$CMD_PATH_PKG" ]; then CMD_PATH="$$CMD_PATH $$CMD_PATH_PKG"; fi; \
		if [ -d "$$CMD_PATH_TESTS" ]; then CMD_PATH="$$CMD_PATH $$CMD_PATH_TESTS"; fi; \
		if [ -z "$$CMD_PATH" ]; then \
			echo "${RED}No source or test directory found for package '$$TARGET_PKG_NAME'. Action: $$ACTION ${RESET}"; exit 1; \
		fi; \
		MSG_SUFFIX="for package $$TARGET_PKG_NAME"; \
	elif [ -n "$$TARGET_PKG_NAME" ]; then \
		echo "${RED}Unknown package '$$TARGET_PKG_NAME' for $$ACTION. Known: $(PKG_NAMES)${RESET}"; exit 1; \
	else \
		CMD_PATH="$(PACKAGES_ROOT_DIR) $(TESTS_ROOT_DIR)"; \
		MSG_SUFFIX="for all packages"; \
	fi; \
	echo "${CYAN}Running $$ACTION $$MSG_SUFFIX on paths:$$CMD_PATH...${RESET}"; \
	. "$(VENV_DIR)/bin/activate"; \
	if [ "$$ACTION" = "lint" ]; then \
		$(RUFF) check $$CMD_PATH; \
	elif [ "$$ACTION" = "format" ]; then \
		$(RUFF) format $$CMD_PATH; \
	elif [ "$$ACTION" = "fix" ]; then \
		$(RUFF) check --fix $$CMD_PATH; \
	fi; \
	echo "${GREEN}$$ACTION $$MSG_SUFFIX complete.${RESET}"


# --- Testing ---
test test-unit test-integration: setup
	@CMD_NAME=$@; \
	TARGET_PKG_NAME=$(FIRST_TARGET_ARG); \
	TEST_PATH="$(TESTS_ROOT_DIR)"; \
	MARKER_ARG=""; \
	PKG_MSG_SUFFIX="for all packages"; \
	TYPE_MSG_SUFFIX=""; \
	if [ "$$CMD_NAME" = "test-unit" ]; then MARKER_ARG="-m unit"; TYPE_MSG_SUFFIX="unit "; fi; \
	if [ "$$CMD_NAME" = "test-integration" ]; then MARKER_ARG="-m integration"; export RUN_INTEGRATION_TESTS=${RUN_INTEGRATION_TESTS:-0}; TYPE_MSG_SUFFIX="integration "; fi; \
	if [ -n "$$TARGET_PKG_NAME" ] && [ "$$TARGET_PKG_NAME" != "test" ] && [ "$$TARGET_PKG_NAME" != "test-unit" ] && [ "$$TARGET_PKG_NAME" != "test-integration" ]; then \
		if [[ " $(PKG_NAMES) " =~ " $$TARGET_PKG_NAME " ]]; then \
			TEST_PATH="$(TESTS_ROOT_DIR)/$$TARGET_PKG_NAME"; \
			if [ ! -d "$$TEST_PATH" ]; then \
				echo "${RED}Test directory '$$TEST_PATH' not found for package '$$TARGET_PKG_NAME'.${RESET}"; \
				echo "${YELLOW}Expected test directory naming to match package directory name: $(PKG_NAMES)${RESET}"; \
				exit 1; \
			fi; \
			PKG_MSG_SUFFIX="for package $$TARGET_PKG_NAME"; \
		else \
			echo "${RED}Unknown package '$$TARGET_PKG_NAME' for testing. Available: $(PKG_NAMES)${RESET}"; exit 1; \
		fi; \
	fi; \
	echo "${CYAN}Running $${TYPE_MSG_SUFFIX}tests $$PKG_MSG_SUFFIX (from path: $$TEST_PATH)...${RESET}"; \
	. "$(VENV_DIR)/bin/activate"; $(PYTEST) $$TEST_PATH $$MARKER_ARG; \
	echo "${GREEN}Tests $$PKG_MSG_SUFFIX completed.${RESET}"


# --- Building Packages ---
build: clean setup
	@TARGET_PKG_NAME=$(FIRST_TARGET_ARG); \
	PACKAGES_TO_BUILD=""; \
	if [ -z "$$TARGET_PKG_NAME" ] || [ "$$TARGET_PKG_NAME" = "build" ]; then \
		echo "${CYAN}Building all packages...${RESET}"; \
		PACKAGES_TO_BUILD="$(PKG_NAMES)"; \
	elif [[ " $(PKG_NAMES) " =~ " $$TARGET_PKG_NAME " ]]; then \
		echo "${CYAN}Building package: $$TARGET_PKG_NAME...${RESET}"; \
		PACKAGES_TO_BUILD="$$TARGET_PKG_NAME"; \
	else \
		echo "${RED}Unknown package '$$TARGET_PKG_NAME' for build. Available: $(PKG_NAMES)${RESET}"; exit 1; \
	fi; \
	for pkg_name in $$PACKAGES_TO_BUILD; do \
		echo "${MAGENTA}Building $$pkg_name...${RESET}"; \
		pkg_dir_path_relative="$(PACKAGES_ROOT_DIR)/$$pkg_name"; \
		dist_output_dir_abs="$$(pwd)/dist/$$pkg_name"; \
		mkdir -p "$$dist_output_dir_abs"; \
		echo "${YELLOW}Building '$$pkg_name' from directory '$$pkg_dir_path_relative'. Output will be in '$$dist_output_dir_abs'.${RESET}"; \
		activate_script_path_relative_to_pkg_dir="../../$(VENV_DIR)/bin/activate"; \
		if ( \
			cd "$$pkg_dir_path_relative" && \
			echo "  Current directory for build: $$(pwd)" && \
			echo "  Activating venv from: $$activate_script_path_relative_to_pkg_dir" && \
			. "$$activate_script_path_relative_to_pkg_dir" && \
			echo "  Using uv: $$(which uv)" && \
			echo "  Using python: $$(which python)" && \
			$(UV) build --verbose -o "$$dist_output_dir_abs" \
		); then \
			echo "${GREEN}Successfully built $$pkg_name.${RESET}"; \
		else \
			echo "${RED}Failed to build $$pkg_name. See errors above.${RESET}"; \
			exit 1; \
		fi; \
	done; \
	echo "${GREEN}Build process completed.${RESET}"


# --- Publishing Packages ---
# Usage: make publish [package_name]
publish: setup
	@echo "${MAGENTA}Starting publish process...${RESET}"; \
	if [ -z "$${UV_PYPI_TOKEN}" ]; then \
		echo "${RED}Error: UV_PYPI_TOKEN is not set or is empty in the environment.${RESET}"; \
		echo "${YELLOW}Please ensure it's correctly defined in your .env file (run 'make decrypt' if using SOPS) or exported directly.${RESET}"; \
		exit 1; \
	fi; \
	echo "${CYAN}Initial Makefile check: UV_PYPI_TOKEN appears to be set (length: $$(echo -n "$${UV_PYPI_TOKEN}" | wc -c)).${RESET}"; \
	TARGET_PKG_NAME=$(FIRST_TARGET_ARG); \
	PACKAGES_TO_PUBLISH_LIST=""; \
	if [ -z "$$TARGET_PKG_NAME" ] || [ "$$TARGET_PKG_NAME" = "publish" ]; then \
		echo "${CYAN}Preparing to publish all built packages...${RESET}"; \
		PACKAGES_TO_PUBLISH_LIST="$(PKG_NAMES)"; \
	elif [[ " $(PKG_NAMES) " =~ " $$TARGET_PKG_NAME " ]]; then \
		echo "${CYAN}Preparing to publish package: $$TARGET_PKG_NAME...${RESET}"; \
		PACKAGES_TO_PUBLISH_LIST="$$TARGET_PKG_NAME"; \
	else \
		echo "${RED}Unknown package '$$TARGET_PKG_NAME' for publish. Available: $(PKG_NAMES)${RESET}"; \
		exit 1; \
	fi; \
	found_any_build_to_publish=false; \
	overall_publish_failed=false; \
	for pkg_name_iter in $$PACKAGES_TO_PUBLISH_LIST; do \
		echo "${BLUE}Processing package '$$pkg_name_iter' for publishing...${RESET}"; \
		if [ -d "dist/$$pkg_name_iter" ] && [ -n "$$(ls -A "dist/$$pkg_name_iter"/*.whl 2>/dev/null)" ]; then \
			echo "  Found build artifacts in dist/$$pkg_name_iter/"; \
			_publish_command_str="$(UV) publish"; \
			if [ -n "$${UV_REPOSITORY_URL}" ]; then \
				_publish_command_str="$$_publish_command_str --repository-url \"$${UV_REPOSITORY_URL}\""; \
			fi; \
			_publish_command_str="$$_publish_command_str --token \"$${UV_PYPI_TOKEN}\" \"dist/$$pkg_name_iter\"/*.whl \"dist/$$pkg_name_iter\"/*.tar.gz"; \
			echo "  Publish command to be run: $$_publish_command_str"; \
			( \
				set -e; \
				echo "  Entering subshell for publishing '$$pkg_name_iter'..."; \
				. "$(VENV_DIR)/bin/activate"; \
				echo "  Inside subshell, UV_PYPI_TOKEN (first 10 chars): $$(echo -n \"$${UV_PYPI_TOKEN}\" | cut -c 1-10)..."; \
				echo "  Inside subshell, UV_REPOSITORY_URL: '$${UV_REPOSITORY_URL}'"; \
				eval "$$_publish_command_str"; \
				_publish_exit_code=$$?; \
				if [ $$_publish_exit_code -eq 0 ]; then \
					echo "${GREEN}Publish command for '$$pkg_name_iter' completed successfully in subshell.${RESET}"; \
				else \
					echo "${RED}Publish command for '$$pkg_name_iter' failed in subshell (exit code: $$_publish_exit_code).${RESET}"; \
				fi; \
				exit $$_publish_exit_code; \
			) || overall_publish_failed=true; \
			found_any_build_to_publish=true; \
		else \
			echo "${YELLOW}No build found for $$pkg_name_iter in dist/$$pkg_name_iter. Skipping.${RESET}"; \
		fi; \
	done; \
	if [ "$$found_any_build_to_publish" = "false" ] && [ -n "$$PACKAGES_TO_PUBLISH_LIST" ]; then \
		echo "${RED}No packages were found in dist/ to publish from the specified selection. Run 'make build ...' first.${RESET}"; \
		exit 1; \
	fi; \
	if [ "$$overall_publish_failed" = "true" ]; then \
		echo "${RED}One or more packages failed to publish. Review logs above.${RESET}"; \
		exit 1; \
	fi; \
	if [ "$$found_any_build_to_publish" = "true" ] && [ "$$overall_publish_failed" = "false" ]; then \
		echo "${GREEN}Publish process completed for all attempted packages. Review logs for details.${RESET}"; \
	fi


# --- Dependency Management ---
add: setup
	@ARGS_AFTER_ADD="$(TARGET_ARGS)"; \
	num_args=$$(echo $$ARGS_AFTER_ADD | wc -w); \
	if [ "$$num_args" -lt 2 ]; then \
		echo "${RED}Error: Package name (for uv --package) and dependency specification are required.${RESET}"; \
		echo "${YELLOW}Usage: make add <uv_project_name> <dependency_spec>${RESET}"; \
		echo "${YELLOW}Example: make add arclio-mcp-gsuite pydantic==2.5.0${RESET}"; \
		exit 1; \
	fi; \
	pkg_for_uv=$$(echo $$ARGS_AFTER_ADD | awk '{print $$1}'); \
	dep_spec=$$(echo $$ARGS_AFTER_ADD | cut -d' ' -f2-); \
	echo "${CYAN}Adding dependency '$$dep_spec' to package '$$pkg_for_uv'...${RESET}"; \
	. "$(VENV_DIR)/bin/activate"; $(UV) add "$$dep_spec" --package "$$pkg_for_uv"; \
	echo "${GREEN}Dependency '$$dep_spec' added successfully to $$pkg_for_uv${RESET}"


# --- Running Servers ---
run-gsuite: setup
	@echo "${CYAN}Running arclio-mcp-gsuite server...${RESET}"
	. "$(VENV_DIR)/bin/activate"; $(PYTHON) -m arclio_mcp_gsuite
	@echo "${GREEN}Server executed.${RESET}"

# --- SOPS Encryption/Decryption ---
encrypt-pkg decrypt-pkg: setup
	@CMD_NAME=$@; \
	TARGET_PKG_DIR_NAME="$(PKG_DIR)"; \
	if [ -z "$$TARGET_PKG_DIR_NAME" ]; then \
		echo "${RED}Error: PKG_DIR argument is required (e.g., PKG_DIR=arclio-mcp-gsuite).${RESET}"; exit 1; \
	fi; \
	if ! [[ " $(PKG_NAMES) " =~ " $$TARGET_PKG_DIR_NAME " ]]; then \
		echo "${RED}Unknown package directory '$$TARGET_PKG_DIR_NAME'. Available: $(PKG_NAMES)${RESET}"; exit 1; \
	fi; \
	pkg_path="$(PACKAGES_ROOT_DIR)/$$TARGET_PKG_DIR_NAME"; \
	env_file="$$pkg_path/.env"; \
	sops_file="$$pkg_path/.env.sops"; \
	if [ -z "$$SOPS_AGE_KEY_FILE" ]; then \
		echo "${RED}Error: SOPS_AGE_KEY_FILE not set. Try: source ~/.zshrc or ensure .env is loaded if defined there.${RESET}"; exit 1; \
	fi; \
	if [ "$$CMD_NAME" = "encrypt-pkg" ]; then \
		if [ ! -f "$$env_file" ]; then \
			echo "${YELLOW}Skipping encryption for $$TARGET_PKG_DIR_NAME: .env file not found at $$env_file${RESET}"; exit 0; \
		fi; \
		echo "${CYAN}Encrypting $$env_file to $$sops_file...${RESET}"; \
		SOPS_AGE_KEY_FILE="$$SOPS_AGE_KEY_FILE" $(SOPS) --input-type dotenv --output-type yaml -e "$$env_file" > "$$sops_file"; \
		echo "${GREEN}Package $$TARGET_PKG_DIR_NAME encryption complete.${RESET}"; \
	elif [ "$$CMD_NAME" = "decrypt-pkg" ]; then \
		if [ ! -f "$$sops_file" ]; then \
			echo "${YELLOW}Skipping decryption for $$TARGET_PKG_DIR_NAME: .env.sops file not found at $$sops_file${RESET}"; exit 0; \
		fi; \
		echo "${CYAN}Decrypting $$sops_file to $$env_file...${RESET}"; \
		SOPS_AGE_KEY_FILE="$$SOPS_AGE_KEY_FILE" $(SOPS) --input-type yaml --output-type dotenv -d "$$sops_file" > "$$env_file" 2>/tmp/sops_error || { \
			echo "${RED}Package $$TARGET_PKG_DIR_NAME decryption failed. Error:${RESET}"; \
			cat /tmp/sops_error; rm -f /tmp/sops_error; \
			exit 1; \
		}; \
		rm -f /tmp/sops_error; \
		echo "${GREEN}Package $$TARGET_PKG_DIR_NAME decryption complete.${RESET}"; \
	fi

encrypt-root decrypt-root: setup
	@CMD_NAME=$@; \
	env_file=".env"; \
	sops_file=".env.sops"; \
	if [ -z "$$SOPS_AGE_KEY_FILE" ]; then \
		echo "${RED}Error: SOPS_AGE_KEY_FILE not set. Ensure .env is loaded if defined there, or export it directly.${RESET}"; exit 1; \
	fi; \
	if [ "$$CMD_NAME" = "encrypt-root" ]; then \
		if [ ! -f "$$env_file" ]; then \
			echo "${YELLOW}Root .env file not found, skipping encryption.${RESET}"; exit 0; \
		fi; \
		echo "${CYAN}Encrypting root .env to .env.sops...${RESET}"; \
		SOPS_AGE_KEY_FILE="$$SOPS_AGE_KEY_FILE" $(SOPS) --input-type dotenv --output-type yaml -e "$$env_file" > "$$sops_file"; \
		echo "${GREEN}Root encryption complete.${RESET}"; \
	elif [ "$$CMD_NAME" = "decrypt-root" ]; then \
		if [ ! -f "$$sops_file" ]; then \
			echo "${YELLOW}Root .env.sops file not found, skipping decryption.${RESET}"; exit 0; \
		fi; \
		echo "${CYAN}Decrypting root .env.sops to .env...${RESET}"; \
		SOPS_AGE_KEY_FILE="$$SOPS_AGE_KEY_FILE" $(SOPS) --input-type yaml --output-type dotenv -d "$$sops_file" > "$$env_file" 2>/tmp/sops_error || { \
			echo "${RED}Root decryption failed. Error:${RESET}"; cat /tmp/sops_error; rm -f /tmp/sops_error; exit 1; \
		}; \
		rm -f /tmp/sops_error; \
		echo "${GREEN}Root decryption complete.${RESET}"; \
	fi

encrypt: encrypt-root
	@echo "${CYAN}Encrypting all package .env files...${RESET}"
	@for pkg_dir in $(PKG_NAMES); do \
		make encrypt-pkg PKG_DIR=$$pkg_dir; \
	done
	@echo "${GREEN}All encryption tasks complete.${RESET}"

decrypt: decrypt-root
	@echo "${CYAN}Decrypting all package .env.sops files...${RESET}"
	@for pkg_dir in $(PKG_NAMES); do \
		make decrypt-pkg PKG_DIR=$$pkg_dir; \
	done
	@echo "${GREEN}All decryption tasks complete.${RESET}"

init-key:
	@if [ -f "$$HOME/.config/sops/key.txt" ]; then \
		echo "${YELLOW}Key already exists at $$HOME/.config/sops/key.txt. To create a new key, first move or delete the existing one.${RESET}"; \
		exit 1; \
	fi
	@mkdir -p "$$HOME/.config/sops"
	@echo "${CYAN}Generating new age key...${RESET}"
	@age-keygen -o "$$HOME/.config/sops/key.txt"
	@echo "${GREEN}Key generated. Add this public key to .sops.yaml:${RESET}"
	@age-keygen -y "$$HOME/.config/sops/key.txt" | sed 's/^public key: //'
	@echo "${YELLOW}Then add to your shell profile (e.g., ~/.zshrc): export SOPS_AGE_KEY_FILE=\$$HOME/.config/sops/key.txt${RESET}"

# --- Help ---
help:
	@echo "$${BOLD}$${BLUE}╔══════════════════════════════════════════════════════════╗$${RESET}"
	@echo "$${BOLD}$${BLUE}║$${RESET} $${BOLD}$${MAGENTA}               ARCLIO MCP TOOLING COMMANDS               $${BLUE}║$${RESET}"
	@echo "$${BOLD}$${BLUE}╚══════════════════════════════════════════════════════════╝$${RESET}"
	@echo ""
	@echo "$${BOLD}$${CYAN}Usage: make <command> [package_name] [other_args...]$${RESET}"
	@echo "$${YELLOW}Note: For commands expecting a package_name, it should be one of: $(PKG_NAMES)$${RESET}"
	@echo ""
	@echo "$${BOLD}$${WHITE}Core Setup:$${RESET}"
	@echo "  $${GREEN}make setup$${RESET}                     Setup monorepo: creates venv, installs uv, syncs all deps."
	@echo ""
	@echo "$${BOLD}$${WHITE}Code Quality:$${RESET} $${YELLOW}(Optional package_name is one of: $(PKG_NAMES))$${RESET}"
	@echo "  $${GREEN}make lint [package_name]$${RESET}        Run linters (Ruff check)."
	@echo "  $${GREEN}make format [package_name]$${RESET}      Format code (Ruff format)."
	@echo "  $${GREEN}make fix [package_name]$${RESET}         Fix linting issues automatically."
	@echo ""
	@echo "$${BOLD}$${WHITE}Testing:$${RESET} $${YELLOW}(Optional package_name is one of: $(PKG_NAMES))$${RESET}"
	@echo "  $${GREEN}make test [package_name]$${RESET}         Run all tests (for all or specified package)."
	@echo "  $${GREEN}make test-unit [package_name]$${RESET}    Run unit tests (for all or specified package)."
	@echo "  $${GREEN}make test-integration [package_name]$${RESET} Run integration tests (for all or specified package)."
	@echo ""
	@echo "$${BOLD}$${WHITE}Building Packages:$${RESET} $${YELLOW}(Optional package_name is one of: $(PKG_NAMES))$${RESET}"
	@echo "  $${GREEN}make build [package_name]$${RESET}        Build all packages or a specific one."
	@echo ""
	@echo "$${BOLD}$${WHITE}Publishing Packages:$${RESET} $${YELLOW}(Optional package_name; UV_PYPI_TOKEN must be set; UV_REPOSITORY_URL for TestPyPI)$${RESET}"
	@echo "  $${GREEN}make publish [package_name]$${RESET}      Publish all built packages or a specific one."
	@echo ""
	@echo "$${BOLD}$${WHITE}Dependency Management:$${RESET}"
	@echo "  $${GREEN}make add <uv_pkg_name> <dep_spec>$${RESET} Add dependency to a package."
	@echo "    $${YELLOW}Example: make add arclio-mcp-gsuite pydantic==2.5.0$${RESET}"
	@echo ""
	@echo "$${BOLD}$${WHITE}Running Servers:$${RESET}"
	@echo "  $${GREEN}make run-gsuite$${RESET}                  Run the arclio-mcp-gsuite server."
	@echo ""
	@echo "$${BOLD}$${WHITE}Secrets Management (SOPS):$${RESET}"
	@echo "  $${GREEN}make encrypt-root / decrypt-root$${RESET} Encrypt/decrypt root .env file."
	@echo "  $${GREEN}make encrypt-pkg PKG_DIR=<name>$${RESET}  Encrypt .env for package (e.g., PKG_DIR=arclio-mcp-gsuite)."
	@echo "  $${GREEN}make decrypt-pkg PKG_DIR=<name>$${RESET}  Decrypt .env.sops for package."
	@echo "  $${GREEN}make encrypt / decrypt$${RESET}            Run root and all package SOPS operations."
	@echo "  $${GREEN}make init-key$${RESET}                    Generate a new age key for SOPS."
	@echo ""
	@echo "$${BOLD}$${WHITE}Utilities:$${RESET}"
	@echo "  $${GREEN}make clean$${RESET}                      Clean build artifacts, caches, and venv."
	@echo ""
	@echo "$${BOLD}$${MAGENTA}Happy coding! 🚀$${RESET}"

# Variables for specific targets like encrypt-pkg/decrypt-pkg
PKG_DIR := $(PKG_DIR)
# Fallback for targets that don't use pattern matching but might take optional args
%:
	@:
