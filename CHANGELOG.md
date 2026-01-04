# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-01-04

### Added

- Initial release
- Auto-discover Makefile targets with `## description` comments
- Register each target as an individual MCP tool
- CLI options:
  - `--makefile` / `-m`: Specify Makefile path
  - `--cwd` / `-C`: Set working directory
  - `--include` / `-i`: Filter targets (glob patterns)
  - `--exclude` / `-e`: Exclude targets (glob patterns)
  - `--prefix` / `-p`: Custom tool name prefix
  - `--timeout` / `-t`: Command timeout
  - `--list` / `-l`: Preview discovered targets
  - `--version` / `-V`: Show version
- Tool parameters:
  - `args`: Pass additional arguments to make
  - `dry_run`: Show commands without executing (`make -n`)
- Built with [FastMCP](https://github.com/jlowin/fastmcp)

[Unreleased]: https://github.com/democratize-technology/makefile-mcp/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/democratize-technology/makefile-mcp/releases/tag/v0.1.0
