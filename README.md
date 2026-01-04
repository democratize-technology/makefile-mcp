# makefile-mcp

[![PyPI](https://img.shields.io/pypi/v/makefile-mcp.svg)](https://pypi.org/project/makefile-mcp/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/democratize-technology/makefile-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/democratize-technology/makefile-mcp/actions/workflows/test.yml)

Auto-discover Makefile targets and expose them as individual MCP tools.

## The Problem

Existing MCP servers for Make expose a single generic `make` tool:

```
Tools: [make(target: string)]
```

This means:
- 🔍 LLM can't "see" available targets in the tool list
- 💬 Requires manual introduction each conversation
- 📖 No descriptions visible without running `make help`

## The Solution

**makefile-mcp** parses your Makefile and registers each documented target as its own tool:

```
Tools: [make_test, make_lint, make_format, make_build, make_deploy]
       ↑ Each with its own description from ## comments
```

```
$ makefile-mcp --list

Discovered 5 targets:

  make_test     Run the test suite with pytest
  make_lint     Check code quality with ruff  
  make_format   Format code with ruff
  make_build    Build distribution packages
  make_deploy   Deploy to production (DANGEROUS)
```

## Installation

```bash
# Using uv (recommended)
uv pip install makefile-mcp

# Using pip
pip install makefile-mcp
```

## Quick Start

```bash
# Run in any directory with a Makefile
makefile-mcp

# Preview what targets will be discovered
makefile-mcp --list
```

## Claude Desktop Configuration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "make": {
      "command": "uvx",
      "args": ["makefile-mcp", "--cwd", "/path/to/your/project"]
    }
  }
}
```

## Working Directory Configuration

The working directory can be configured in three ways (in order of precedence):

### 1. Dynamic Tool (Runtime)

Change the working directory at runtime using the `set_working_directory` tool:

```python
# From within Claude
set_working_directory("/path/to/project")

# Clear the setting (use CLI/env/var)
set_working_directory(None)
```

This is useful for:
- Multi-project workflows
- Testing different Makefiles in one session
- Dynamic directory switching

### 2. Environment Variable

Set the `MAKEFILE_MCP_CWD` environment variable:

```bash
# In your shell profile
export MAKEFILE_MCP_CWD=/path/to/project

# Or per-invocation
MAKEFILE_MCP_CWD=/path/to/project makefile-mcp
```

### 3. CLI Argument

Pass `--cwd` when starting the server:

```bash
makefile-mcp --cwd /path/to/project
```

### Precedence Chain

When multiple methods are used, the precedence is (highest to lowest):

1. **Tool setting** (set via `set_working_directory()`)
2. **CLI argument** (`--cwd`)
3. **Environment variable** (`MAKEFILE_MCP_CWD`)
4. **None** (current directory at server start)

Example:
```bash
export MAKEFILE_MCP_CWD=/env_path      # Lowest
makefile-mcp --cwd /cli_path           # Middle
# Later: set_working_directory("/tool_path")  # Highest
```

## Makefile Convention

Document your targets with `## comments` (the same convention used by `make help`):

```makefile
.PHONY: test lint format build deploy

test: ## Run the test suite
	pytest tests/ -v

lint: ## Check code quality
	ruff check src/

format: ## Format code with ruff
	ruff format src/

build: lint test ## Build distribution packages
	python -m build

clean:
	rm -rf dist/  # No ## = not exposed as a tool

deploy: ## Deploy to production (DANGEROUS)
	./scripts/deploy.sh
```

## CLI Options

```bash
makefile-mcp [OPTIONS]

Options:
  -m, --makefile PATH   Path to Makefile (default: ./Makefile)
  -C, --cwd PATH        Working directory for commands
  -i, --include GLOB    Only include matching targets (comma-separated)
  -e, --exclude GLOB    Exclude matching targets (comma-separated)
  -p, --prefix TEXT     Tool name prefix (default: make_)
  -t, --timeout SECS    Command timeout (default: 300)
  -l, --list            List discovered targets and exit
  -V, --version         Show version and exit
  -h, --help            Show help and exit
```

### Examples

```bash
# Only expose safe targets
makefile-mcp --include "test,lint,format,build"

# Block dangerous targets  
makefile-mcp --exclude "deploy,publish,clean"

# Use glob patterns
makefile-mcp --exclude "docker-*,k8s-*"

# Custom prefix to avoid collisions
makefile-mcp --prefix "myproject_"
```

## Tool Schema

### Configuration Tools

**set_working_directory**
Change the working directory at runtime.

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | string | Absolute path to working directory, or null to clear |

Returns: Confirmation message with current working directory.

### Makefile Target Tools

Each discovered Makefile target becomes a tool with these parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `args` | string | Additional arguments (e.g., `VERBOSE=1`) |
| `dry_run` | boolean | Show commands without executing (`make -n`) |

### Resources

- `makefile://Makefile` - Full contents of the Makefile
- `makefile://targets` - Summary of available targets

## Security

- ✅ No shell expansion (`subprocess` with list args)
- ✅ Configurable timeout (default: 5 minutes)
- ✅ `--exclude` to block dangerous targets
- ✅ Commands run in specified working directory only

⚠️ **Warning**: Review Makefiles from untrusted sources before exposing them.

## Development

```bash
git clone https://github.com/democratize-technology/makefile-mcp
cd makefile-mcp
make dev-setup  # We eat our own dogfood 🐕
make check      # Run all checks
```

## License

MIT

## Credits

Inspired by [mcp-server-make](https://github.com/wrale/mcp-server-make) by @wrale.
Built with [FastMCP](https://github.com/jlowin/fastmcp).
