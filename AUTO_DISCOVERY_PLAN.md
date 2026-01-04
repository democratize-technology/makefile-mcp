# Auto-Discovery Implementation Plan

## Overview

Add automatic target discovery to `mcp-server-make`. Instead of exposing a single `make` tool where the target is a parameter, expose each Makefile target as its own MCP tool.

## What's Done

- [x] `parser.py` - Makefile parser that extracts targets with `## descriptions`
- [x] `server_v2.py` - Proof-of-concept server with auto-discovery

## What Remains

### 1. Integrate into Main Server

Replace `server.py` with `server_v2.py` functionality:

```bash
# Option A: Replace server.py entirely
mv src/mcp_server_make/server_v2.py src/mcp_server_make/server.py

# Option B: Add feature flag (backward compatible)
# Add --auto-discover flag to CLI
```

### 2. Update CLI (`__init__.py`)

Add new arguments:

```python
parser.add_argument("--auto-discover", action="store_true", default=True,
                    help="Auto-discover targets from Makefile (default: True)")
parser.add_argument("--no-auto-discover", action="store_false", dest="auto_discover",
                    help="Disable auto-discovery, use single 'make' tool")
parser.add_argument("--include", type=str,
                    help="Comma-separated list of targets to include")
parser.add_argument("--exclude", type=str,
                    help="Comma-separated list of targets to exclude")
parser.add_argument("--prefix", type=str, default="make_",
                    help="Prefix for tool names (default: make_)")
```

### 3. Write Tests

- `test_parser.py` - Unit tests for Makefile parsing
- Update `test_server.py` - Test auto-discovery functionality

### 4. Update Documentation

- `README.md` - Document new CLI flags
- `docs/user_guide.md` - Explain auto-discovery feature
- Add examples showing discovered tools

### 5. Version Bump

- Bump to `0.4.0` (new feature)
- Update CHANGELOG

## Files Changed

```
src/mcp_server_make/
├── __init__.py      # Update CLI args
├── parser.py        # NEW - Makefile parser
├── server.py        # Update with auto-discovery
└── server_v2.py     # Can delete after merge

tests/
├── test_parser.py   # NEW
└── test_server.py   # Update

docs/
├── README.md        # Update
└── user_guide.md    # Update
```

## Backward Compatibility

The generic `make` tool is preserved for:
- Targets without `## descriptions`
- Targets filtered out by `--include`/`--exclude`
- Users who prefer the old behavior (`--no-auto-discover`)

## Example: Before vs After

### Before (current)

```json
{
  "tools": [
    {
      "name": "make",
      "description": "Run a make target from the Makefile",
      "inputSchema": {
        "properties": {
          "target": {"type": "string"}
        }
      }
    }
  ]
}
```

### After (with auto-discovery)

```json
{
  "tools": [
    {
      "name": "make",
      "description": "Run any make target (fallback)"
    },
    {
      "name": "make_test",
      "description": "Run the test suite"
    },
    {
      "name": "make_lint",
      "description": "Check code quality with ruff"
    },
    {
      "name": "make_format",
      "description": "Format code"
    }
  ]
}
```

## Security Considerations

- `--exclude` should be used to block dangerous targets like `deploy`, `publish`
- Default behavior is safe (only targets with descriptions are exposed)
- Subprocess execution unchanged from original (no shell=True)
