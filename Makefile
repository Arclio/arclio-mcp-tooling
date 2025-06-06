.PHONY: help setup setup-dev clean clean-debug lint format fix test install build publish add \
	    encrypt-root decrypt-root encrypt-pkg decrypt-pkg encrypt decrypt init-key \
	    run-google-workspace tree _run-tests _build-or-publish

.DEFAULT_GOAL := help

# --- Environment & Tools ---
ifneq (,$(wildcard ./.env))
	include .env
endif

PYTHON := python3
PIP := pip
VENV_DIR := .venv
UV := uv
PYTEST := pytest
RUFF := ruff
SOPS := sops

# --- Directories & Package Definitions ---
PACKAGES_ROOT_DIR := packages
TESTS_ROOT_DIR := tests
PKG_NAMES := google-workspace-mcp markdowndeck

# --- Color Codes ---
GREEN  := $(shell tput -Txterm setaf 2)
YELLOW := $(shell tput -Txterm setaf 3)
CYAN   := $(shell tput -Txterm setaf 6)
RED    := $(shell tput -Txterm setaf 1)
WHITE  := $(shell tput -Txterm setaf 7)
BOLD   := $(shell tput -Txterm bold)
RESET  := $(shell tput -Txterm sgr0)

# --- Argument Parsing Helper ---
TARGET_ARGS = $(filter-out $@,$(MAKECMDGOALS))

# --- Core Setup & Cleaning ---
setup setup-dev:
	@if [ ! -f "$(VENV_DIR)/bin/activate" ]; then \
		echo "${CYAN}Creating virtual environment and installing uv...${RESET}"; \
		$(PYTHON) -m venv $(VENV_DIR); \
		. "$(VENV_DIR)/bin/activate"; \
		pip install --upgrade pip; \
		pip install uv; \
	fi
	@echo "${CYAN}Syncing all workspace packages and dependencies with uv...${RESET}"
	. "$(VENV_DIR)/bin/activate"; $(UV) sync --all-packages --no-install-workspace --extra dev
	@echo "${GREEN}Monorepo setup and sync complete.${RESET}"

install: setup
	@PKGS_TO_INSTALL="$(PKGS)"; \
	if [ -z "$$PKGS_TO_INSTALL" ]; then \
		echo "${RED}Error: PKGS argument is required. Provide space-separated package dir names.${RESET}"; \
		echo "${YELLOW}Example: make install PKGS=\"google-workspace-mcp markdowndeck\"${RESET}"; \
		exit 1; \
	fi; \
	INSTALL_PATHS=""; \
	for pkg_name in $$PKGS_TO_INSTALL; do \
		pkg_path="$(PACKAGES_ROOT_DIR)/$$pkg_name"; \
		if [ ! -d "$$pkg_path" ]; then \
			echo "${RED}Error: Package directory '$$pkg_path' not found for package '$$pkg_name'.${RESET}"; exit 1; \
		fi; \
		INSTALL_PATHS="$$INSTALL_PATHS -e $$pkg_path"; \
	done; \
	echo "${CYAN}Installing packages editable:$$INSTALL_PATHS...${RESET}"; \
	. "$(VENV_DIR)/bin/activate"; $(UV) pip install $$INSTALL_PATHS; \
	echo "${GREEN}Editable installation complete.${RESET}"

clean:
	@echo "${CYAN}Cleaning build artifacts, cache files, and virtual environment...${RESET}"
	rm -rf dist build *.egg-info .pytest_cache .coverage coverage_html coverage.xml .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf "$(VENV_DIR)"
	@echo "${GREEN}Cleanup complete.${RESET}"

clean-debug:
	@echo "${CYAN}Cleaning up temporary debug scripts (debug_*)...${RESET}"
	find . -maxdepth 1 -type f -name "debug_*" -exec rm -v {} +
	@echo "${GREEN}Debug script cleanup complete.${RESET}"

tree:
	@tree -I ".git|__pycache__|.pytest_cache|.ruff_cache|*.egg-info|build|dist|.venv"

# --- Code Quality ---
lint format fix: setup
	@ACTION=$@; \
	TARGET_PATH=$(firstword $(TARGET_ARGS)); \
	if [ -z "$$TARGET_PATH" ]; then TARGET_PATH="$(PACKAGES_ROOT_DIR) $(TESTS_ROOT_DIR)"; MSG_SUFFIX="for all packages"; \
	elif [[ " $(PKG_NAMES) " =~ " $$TARGET_PATH " ]]; then CMD_PATH="$(PACKAGES_ROOT_DIR)/$$TARGET_PATH $(TESTS_ROOT_DIR)/$$TARGET_PATH"; MSG_SUFFIX="for package '$$TARGET_PATH'"; \
	else echo "${RED}Unknown package '$$TARGET_PATH'. Known: $(PKG_NAMES)${RESET}"; exit 1; fi; \
	echo "${CYAN}Running $$ACTION $$MSG_SUFFIX on paths: $$CMD_PATH...${RESET}"; \
	. "$(VENV_DIR)/bin/activate"; \
	if [ "$$ACTION" = "lint" ]; then $(UV) run -- ruff check $$CMD_PATH; \
	elif [ "$$ACTION" = "format" ]; then $(UV) run -- ruff format $$CMD_PATH; \
	elif [ "$$ACTION" = "fix" ]; then $(UV) run -- ruff check --fix $$CMD_PATH; fi; \
	echo "${GREEN}$$ACTION $$MSG_SUFFIX complete.${RESET}"

# --- Testing ---
_run-tests: setup
	@ARGS="$(ARGS)"; \
	TEST_PATH=""; \
	EXTRA_PYTEST_ARGS=""; \
	num_args=$$(echo $$ARGS | wc -w); \
	first_arg=$$(echo $$ARGS | awk '{print $$1}'); \
	if [ -z "$$ARGS" ]; then \
		TEST_PATH="$(TESTS_ROOT_DIR)"; \
	elif [[ " $(PKG_NAMES) " =~ " $$first_arg " ]]; then \
		TEST_PATH="$(TESTS_ROOT_DIR)/$$first_arg"; \
		if [ $$num_args -gt 1 ]; then EXTRA_PYTEST_ARGS=$$(echo $$ARGS | cut -d' ' -f2-); fi; \
	elif [ -d "$$first_arg" ] || [ -f "$$first_arg" ]; then \
		TEST_PATH="$$first_arg"; \
		if [ $$num_args -gt 1 ]; then EXTRA_PYTEST_ARGS=$$(echo $$ARGS | cut -d' ' -f2-); fi; \
	else \
		TEST_PATH="$(TESTS_ROOT_DIR)"; \
		EXTRA_PYTEST_ARGS="$$ARGS"; \
	fi; \
	COV_ARG=""; \
	if [ -n "$(COVERAGE)" ]; then COV_PKG=$$(echo $$TEST_PATH | cut -d'/' -f2); COV_ARG="--cov=packages/$${COV_PKG}/src --cov-report=$(COVERAGE)"; fi; \
	echo "${CYAN}Executing pytest on path: '$$TEST_PATH' with extra args: '$$EXTRA_PYTEST_ARGS'${RESET}"; \
	. "$(VENV_DIR)/bin/activate"; \
	$(PYTEST) -v $$TEST_PATH $$COV_ARG $$EXTRA_PYTEST_ARGS; \
	echo "${GREEN}Tests completed.${RESET}"

test:
	@$(MAKE) _run-tests ARGS="$(TARGET_ARGS)"

cov coverage:
	@$(MAKE) _run-tests COVERAGE=term-missing ARGS="$(TARGET_ARGS)"

cov-html:
	@$(MAKE) _run-tests COVERAGE=html ARGS="$(TARGET_ARGS)"

# --- Building, Publishing, Dependencies ---
_build-or-publish:
	@ACTION=$(ACTION); TARGET_PKG=$(TARGET); \
	PACKAGES_TO_PROCESS=""; \
	if [ -z "$$TARGET_PKG" ] || [ "$$TARGET_PKG" = "$$ACTION" ]; then PACKAGES_TO_PROCESS="$(PKG_NAMES)"; \
	elif [[ " $(PKG_NAMES) " =~ " $$TARGET_PKG " ]]; then PACKAGES_TO_PROCESS="$$TARGET_PKG"; \
	else echo "${RED}Unknown package '$$TARGET_PKG'. Available: $(PKG_NAMES)${RESET}"; exit 1; fi; \
	if [ "$$ACTION" = "publish" ] && [ -z "$${UV_PYPI_TOKEN}" ]; then echo "${RED}Error: UV_PYPI_TOKEN is not set.${RESET}"; exit 1; fi; \
	for pkg_name in $$PACKAGES_TO_PROCESS; do \
	    echo "${MAGENTA}Performing '$$ACTION' for $$pkg_name...${RESET}"; \
	    pkg_dir="$(PACKAGES_ROOT_DIR)/$$pkg_name"; \
	    dist_dir="$$(pwd)/dist/$$pkg_name"; \
	    if [ "$$ACTION" = "build" ]; then \
	        mkdir -p "$$dist_dir"; \
	        (cd "$$pkg_dir" && . "../../$(VENV_DIR)/bin/activate" && $(UV) build --verbose -o "$$dist_dir"); \
	    elif [ "$$ACTION" = "publish" ]; then \
	        if [ -d "$$dist_dir" ] && [ -n "$$(ls -A '$$dist_dir'/*.whl 2>/dev/null)" ]; then \
	            (cd "$$pkg_dir" && . "../../$(VENV_DIR)/bin/activate" && $(UV) publish --token "$${UV_PYPI_TOKEN}" "$$dist_dir"/*); \
	        else echo "${YELLOW}No build found for $$pkg_name. Skipping publish.${RESET}"; fi; \
	    fi; \
	done; echo "${GREEN}$$ACTION process completed.${RESET}"

build: clean setup
	@$(MAKE) _build-or-publish ACTION=build TARGET=$(firstword $(TARGET_ARGS))

publish: setup
	@$(MAKE) _build-or-publish ACTION=publish TARGET=$(firstword $(TARGET_ARGS))

add: setup
	@pkg_for_uv=$$(echo $(TARGET_ARGS) | awk '{print $$1}'); \
	dep_spec=$$(echo $(TARGET_ARGS) | cut -d' ' -f2-); \
	if [ -z "$$pkg_for_uv" ] || [ -z "$$dep_spec" ]; then \
	    echo "${RED}Usage: make add <uv_project_name> <dependency_spec>${RESET}"; exit 1; \
	fi; \
	echo "${CYAN}Adding '$$dep_spec' to '$$pkg_for_uv'...${RESET}"; \
	. "$(VENV_DIR)/bin/activate"; $(UV) add "$$dep_spec" --package "$$pkg_for_uv"; \
	echo "${GREEN}Dependency added.${RESET}"

# --- SOPS & Servers ---
run-google-workspace: setup
	@echo "${CYAN}Running google-workspace-mcp server...${RESET}"
	. "$(VENV_DIR)/bin/activate"; $(PYTHON) -m google_workspace_mcp

encrypt-pkg decrypt-pkg: setup
	@CMD_NAME=$@; PKG_DIR_NAME="$(PKG_DIR)"; \
	if [ -z "$$PKG_DIR_NAME" ]; then echo "${RED}Error: PKG_DIR must be set.${RESET}"; exit 1; fi; \
	env_file="$(PACKAGES_ROOT_DIR)/$$PKG_DIR_NAME/.env"; \
	sops_file="$$env_file.sops"; \
	if [ -z "$$SOPS_AGE_KEY_FILE" ]; then echo "${RED}Error: SOPS_AGE_KEY_FILE not set.${RESET}"; exit 1; fi; \
	if [ "$$CMD_NAME" = "encrypt-pkg" ]; then \
	    if [ ! -f "$$env_file" ]; then echo "${YELLOW}Skipping encryption: $$env_file not found.${RESET}"; exit 0; fi; \
	    echo "${CYAN}Encrypting $$env_file...${RESET}"; \
	    SOPS_AGE_KEY_FILE="$$SOPS_AGE_KEY_FILE" $(SOPS) -e "$$env_file" > "$$sops_file"; \
	elif [ "$$CMD_NAME" = "decrypt-pkg" ]; then \
	    if [ ! -f "$$sops_file" ]; then echo "${YELLOW}Skipping decryption: $$sops_file not found.${RESET}"; exit 0; fi; \
	    echo "${CYAN}Decrypting $$sops_file...${RESET}"; \
	    SOPS_AGE_KEY_FILE="$$SOPS_AGE_KEY_FILE" $(SOPS) -d "$$sops_file" > "$$env_file"; \
	fi; echo "${GREEN}Package '$$PKG_DIR_NAME' SOPS operation complete.${RESET}"

encrypt-root decrypt-root: setup
	@# (SOPS logic for root remains unchanged)
	@echo "SOPS logic for root here..."

encrypt:
	@$(MAKE) encrypt-root
	@for pkg_dir in $(PKG_NAMES); do $(MAKE) encrypt-pkg PKG_DIR=$$pkg_dir; done

decrypt:
	@$(MAKE) decrypt-root
	@for pkg_dir in $(PKG_NAMES); do $(MAKE) decrypt-pkg PKG_DIR=$$pkg_dir; done

init-key:
	@# (init-key logic remains unchanged)
	@echo "SOPS init-key logic here..."

# --- Help ---
help:
	@echo "$${BOLD}$${CYAN}Usage: make <command> [target] [pytest_args...]$${RESET}"
	@echo ""
	@echo "$${BOLD}$${WHITE}Core Setup & Cleaning:$${RESET}"
	@echo "  $${GREEN}make setup$${RESET}                   Setup monorepo: creates venv, installs uv, syncs all deps."
	@echo "  $${GREEN}make install PKGS=\"<pkgs>\"$${RESET}   Install specified packages in editable mode. Ex: make install PKGS=markdowndeck"
	@echo "  $${GREEN}make clean$${RESET}                     Clean build artifacts, caches, and venv."
	@echo "  $${GREEN}make clean-debug$${RESET}               Delete temporary debug scripts (named debug_*)."
	@echo ""
	@echo "$${BOLD}$${WHITE}Code Quality:$${RESET} $${YELLOW}(target is an optional package_name)$${RESET}"
	@echo "  $${GREEN}make lint [target]$${RESET}                Run linters (Ruff check)."
	@echo "  $${GREEN}make format [target]$${RESET}              Format code (Ruff format)."
	@echo ""
	@echo "$${BOLD}$${WHITE}Testing (Flexible Targeting):$${RESET} $${YELLOW}(target can be package_name, path, or pytest args)$${RESET}"
	@echo "  $${GREEN}make test [target]$${RESET}                  Run tests. Examples:"
	@echo "    $${YELLOW}make test markdowndeck$${RESET}                  (run all tests for the markdowndeck package)"
	@echo "    $${YELLOW}make test tests/markdowndeck/unit/parser$${RESET} (run all tests in a specific directory)"
	@echo "    $${YELLOW}make test tests/markdowndeck/unit/parser/test_section_parser.py$${RESET} (run a single file)"
	@echo "    $${YELLOW}make test -k \"test_specific_function\"$${RESET}      (run tests matching a name)"
	@echo "  $${GREEN}make cov [target]$${RESET}                    Run tests with terminal coverage report."
	@echo "  $${GREEN}make cov-html [target]$${RESET}               Run tests and generate an HTML coverage report in 'coverage_html/'."
	@echo ""
	@echo "$${BOLD}$${WHITE}Build & Publish:$${RESET} $${YELLOW}(target is an optional package_name)$${RESET}"
	@echo "  $${GREEN}make build [target]$${RESET}              Build all packages or a specific one."
	@echo "  $${GREEN}make publish [target]$${RESET}            Publish built packages (requires UV_PYPI_TOKEN)."
	@echo ""
	@echo "$${BOLD}$${WHITE}Other:$${RESET}"
	@echo "  $${GREEN}make add <uv_name> <dep>$${RESET}        Add a dependency. Ex: make add markdowndeck requests"
	@echo "  $${GREEN}make run-google-workspace$${RESET}       Run the Google Workspace MCP server."
	@echo "  $${GREEN}make tree$${RESET}                       Show directory tree."

# Prevent make from trying to find a file named after the argument
%:
	@:
