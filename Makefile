.DEFAULT_GOAL := help
.PHONY: help dev-setup test lint format check build clean publish

# Project settings
PYTHON := python3
VENV := .venv
BIN := $(VENV)/bin

help: ## Show this help message
	@echo "makefile-mcp development commands:"
	@echo
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

$(VENV)/bin/activate:
	uv venv $(VENV)

dev-setup: $(VENV)/bin/activate ## Set up development environment
	uv pip install -e ".[dev]"
	@echo "\n✅ Run 'source $(VENV)/bin/activate' to activate"

test: ## Run tests
	$(BIN)/pytest tests/ -v

lint: ## Check code quality
	$(BIN)/ruff check src/ tests/
	$(BIN)/mypy src/

format: ## Format code
	$(BIN)/ruff format src/ tests/
	$(BIN)/ruff check --fix src/ tests/

check: format lint test ## Run all checks (format, lint, test)

build: clean ## Build distribution packages
	uv build

clean: ## Clean build artifacts
	rm -rf dist/ build/ *.egg-info .pytest_cache .ruff_cache .mypy_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

publish: build ## Publish to PyPI
	uv publish

list: ## List discovered targets (dogfooding test)
	$(BIN)/makefile-mcp --list
