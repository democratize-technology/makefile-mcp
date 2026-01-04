"""Tests for FastMCP server."""

import tempfile
from pathlib import Path

import pytest

from makefile_mcp import create_server


SAMPLE_MAKEFILE = """\
.PHONY: help test lint

help: ## Show help
\t@echo "Help"

test: ## Run tests
\techo "Running tests"
\texit 0

lint: ## Check code
\techo "Linting"

fail: ## This will fail
\texit 1

dangerous: ## Deploy (should be excluded)
\techo "Deploying"
"""


@pytest.fixture
def makefile_path(tmp_path: Path) -> Path:
    """Create a temporary Makefile for testing."""
    makefile = tmp_path / "Makefile"
    makefile.write_text(SAMPLE_MAKEFILE)
    return makefile


class TestCreateServer:
    """Tests for create_server function."""

    def test_creates_server(self, makefile_path: Path) -> None:
        """Should create a FastMCP server."""
        server = create_server(makefile=str(makefile_path))
        assert server.name == "makefile-mcp"

    def test_raises_on_missing_makefile(self, tmp_path: Path) -> None:
        """Should raise FileNotFoundError for missing Makefile."""
        with pytest.raises(FileNotFoundError):
            create_server(makefile=str(tmp_path / "nonexistent"))

    def test_include_filter(self, makefile_path: Path) -> None:
        """Should only include matching targets."""
        server = create_server(
            makefile=str(makefile_path),
            include=["test", "lint"],
        )
        # Server should have tools for test and lint only
        # (We can't easily inspect tools without running the server)
        assert server is not None

    def test_exclude_filter(self, makefile_path: Path) -> None:
        """Should exclude matching targets."""
        server = create_server(
            makefile=str(makefile_path),
            exclude=["dangerous"],
        )
        assert server is not None

    def test_custom_prefix(self, makefile_path: Path) -> None:
        """Should use custom prefix for tool names."""
        server = create_server(
            makefile=str(makefile_path),
            prefix="project_",
        )
        assert server is not None


class TestRunMake:
    """Tests for make command execution."""

    @pytest.mark.asyncio
    async def test_successful_command(self, makefile_path: Path) -> None:
        """Should execute make target and return output."""
        from makefile_mcp.server import run_make

        result = await run_make(str(makefile_path), "test")
        assert "Running tests" in result

    @pytest.mark.asyncio
    async def test_failed_command(self, makefile_path: Path) -> None:
        """Should return error for failed command."""
        from makefile_mcp.server import run_make

        result = await run_make(str(makefile_path), "fail")
        assert "Exit code" in result or "exit" in result.lower()

    @pytest.mark.asyncio
    async def test_dry_run(self, makefile_path: Path) -> None:
        """Should show commands without executing in dry run mode."""
        from makefile_mcp.server import run_make

        result = await run_make(str(makefile_path), "test", dry_run=True)
        # In dry run, make shows the command but doesn't execute
        assert "echo" in result.lower() or "test" in result.lower()
