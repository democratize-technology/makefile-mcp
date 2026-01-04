# makefile-mcp

Auto-discover Makefile targets and expose them as individual MCP tools.

## Why This Exists

Existing `mcp-server-make` exposes a single generic `make` tool where you pass the target as a parameter. This means:
- LLM can't "see" available targets in the tool list
- Requires manual introduction each conversation ("Our Makefile has test, lint, build...")
- No descriptions visible without running `make help`

**This server parses your Makefile and registers each documented target as its own tool.**

## Installation

```bash
uv pip install makefile-mcp
# or
pip install makefile-mcp
```

## Usage

```bash
# Auto-discover from ./Makefile
makefile-mcp

# Specify Makefile path
makefile-mcp --makefile /path/to/Makefile

# Set working directory
makefile-mcp --cwd /project/root

# Filter targets
makefile-mcp --include "test,lint,build"
makefile-mcp --exclude "deploy,publish"

# Custom tool prefix (default: make_)
makefile-mcp --prefix "project_"
```

## Claude Desktop Configuration

```json
{
  "mcpServers": {
    "makefile": {
      "command": "uvx",
      "args": [
        "makefile-mcp",
        "--makefile", "/path/to/project/Makefile",
        "--cwd", "/path/to/project"
      ]
    }
  }
}
```

## Makefile Convention

Document targets with `## comments`:

```makefile
.PHONY: test lint format build

test: ## Run the test suite
	pytest tests/

lint: ## Check code quality
	ruff check src/

format: ## Format code with ruff
	ruff format src/

build: deps ## Build distribution
	python -m build

deploy: ## Deploy to production (DANGEROUS)
	./scripts/deploy.sh
```

This produces MCP tools:
- `make_test` - "Run the test suite"
- `make_lint` - "Check code quality"
- `make_format` - "Format code with ruff"
- `make_build` - "Build distribution"
- `make_deploy` - "Deploy to production (DANGEROUS)"

## Tool Schema

Each auto-discovered tool accepts optional parameters:

```json
{
  "args": "Additional arguments (e.g., VERBOSE=1)",
  "dry_run": "Show commands without executing (make -n)"
}
```

## Security

- Use `--exclude` to block dangerous targets
- Commands run with user permissions in specified working directory
- No shell expansion (subprocess with list args)
- 5 minute timeout per command

## Development

```bash
git clone https://github.com/democratize-technology/makefile-mcp
cd makefile-mcp
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
pytest tests/
```

## License

MIT
