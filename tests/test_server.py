"""Tests for FastMCP server."""

import os
import tempfile
from pathlib import Path

import pytest

from makefile_mcp import create_server


SAMPLE_MAKEFILE = """\
.PHONY: help test lint pwd_target

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

pwd_target: ## Print working directory
\t@pwd
\t@echo "File exists: $(shell test -f marker.txt && echo yes || echo no)"
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

    @pytest.mark.asyncio
    async def test_include_filter(self, makefile_path: Path) -> None:
        """Should only include matching targets."""
        # Create server with include filter
        server = create_server(
            makefile=str(makefile_path),
            include=["test", "lint"],
        )

        # Inspect actual tools registered on server
        tools = await server.get_tools()

        # Verify only test and lint tools exist
        tool_names = set(tools.keys())
        expected_tools = {"make_test", "make_lint"}

        assert tool_names == expected_tools, (
            f"Include filter failed. Expected {expected_tools}, got {tool_names}. "
            f"Found tools: {sorted(tool_names)}"
        )

        # Verify tool count matches expected
        assert len(tools) == 2, (
            f"Expected exactly 2 tools (test, lint), but got {len(tools)}"
        )

    @pytest.mark.asyncio
    async def test_exclude_filter(self, makefile_path: Path) -> None:
        """Should exclude matching targets."""
        # Create server with exclude filter
        server = create_server(
            makefile=str(makefile_path),
            exclude=["dangerous"],
        )

        # Inspect actual tools registered on server
        tools = await server.get_tools()
        tool_names = set(tools.keys())

        # Verify dangerous target is excluded
        assert "make_dangerous" not in tool_names, (
            f"Exclude filter failed. 'make_dangerous' should not exist, "
            f"but found: {sorted(tool_names)}"
        )

        # Verify other targets are still present
        expected_tools = {"make_help", "make_test", "make_lint", "make_fail", "make_pwd_target"}
        assert tool_names == expected_tools, (
            f"Expected {expected_tools}, got {tool_names}. "
            f"Found tools: {sorted(tool_names)}"
        )

        # Verify tool count (all 6 targets - 1 excluded = 5 tools)
        assert len(tools) == 5, (
            f"Expected exactly 5 tools (all targets except 'dangerous'), but got {len(tools)}"
        )

    @pytest.mark.asyncio
    async def test_custom_prefix(self, makefile_path: Path) -> None:
        """Should use custom prefix for tool names."""
        # Create server with custom prefix
        server = create_server(
            makefile=str(makefile_path),
            prefix="project_",
        )

        # Inspect actual tools registered on server
        tools = await server.get_tools()
        tool_names = set(tools.keys())

        # Verify all tools use custom prefix
        for tool_name in tool_names:
            assert tool_name.startswith("project_"), (
                f"Custom prefix failed. Expected all tools to start with 'project_', "
                f"but found: {tool_name}"
            )

        # Verify expected tools with custom prefix exist
        expected_tools = {
            "project_help",
            "project_test",
            "project_lint",
            "project_fail",
            "project_dangerous",
            "project_pwd_target",
        }
        assert tool_names == expected_tools, (
            f"Expected {expected_tools}, got {tool_names}. "
            f"Found tools: {sorted(tool_names)}"
        )

        # Verify tool count (all 6 targets with custom prefix)
        assert len(tools) == 6, (
            f"Expected exactly 6 tools with custom prefix, but got {len(tools)}"
        )


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


class TestWorkingDirectory:
    """Tests for working directory handling."""

    @pytest.mark.asyncio
    async def test_commands_execute_in_working_dir(self, tmp_path: Path) -> None:
        """Should execute make commands in the specified working_dir."""
        from makefile_mcp.server import run_make

        # Create a test directory structure
        work_dir = tmp_path / "workspace"
        work_dir.mkdir()
        marker_file = work_dir / "marker.txt"
        marker_file.write_text("test")

        # Create Makefile in workspace
        makefile = work_dir / "Makefile"
        makefile.write_text(SAMPLE_MAKEFILE)

        # Execute with working_dir parameter
        result = await run_make(
            makefile=str(makefile),
            target="pwd_target",
            working_dir=str(work_dir),
        )

        # Verify command executed in working_dir
        assert str(work_dir) in result, f"Expected {work_dir} in output: {result}"
        assert "File exists: yes" in result, "marker.txt should exist in working_dir"

    def test_create_server_does_not_change_global_cwd(self, tmp_path: Path) -> None:
        """Should NOT change the global working directory when creating server."""
        # Create a test directory
        work_dir = tmp_path / "workspace"
        work_dir.mkdir()
        makefile = work_dir / "Makefile"
        makefile.write_text(SAMPLE_MAKEFILE)

        # Save original working directory
        original_cwd = Path.cwd()

        # Create server with different working_dir
        create_server(
            makefile=str(makefile),
            working_dir=str(work_dir),
        )

        # Verify global CWD is unchanged
        current_cwd = Path.cwd()
        assert current_cwd == original_cwd, (
            f"Global CWD was changed! "
            f"Expected: {original_cwd}, Got: {current_cwd}"
        )


class TestTimeoutHandling:
    """Tests for timeout handling and process cleanup."""

    @pytest.mark.asyncio
    async def test_timeout_kills_subprocess(self, tmp_path: Path) -> None:
        """Should kill subprocess when timeout occurs (no resource leak)."""
        import psutil
        from makefile_mcp.server import run_make

        # Create a Makefile with a long-running target
        long_running_makefile = tmp_path / "Makefile"
        long_running_makefile.write_text(
            """\
.PHONY: long_running

long_running: ## A target that runs for a long time
\tsleep 30
\techo "This should never complete"
"""
        )

        # Get initial process count
        parent = psutil.Process()
        initial_children = len(parent.children(recursive=True))

        # Run with very short timeout to trigger timeout
        result = await run_make(
            makefile=str(long_running_makefile),
            target="long_running",
            timeout=1,  # 1 second timeout
        )

        # Verify timeout was reported
        assert "timed out" in result.lower(), f"Expected timeout message, got: {result}"

        # Give OS time to clean up zombie processes
        import asyncio
        await asyncio.sleep(0.5)

        # Verify no orphaned 'sleep' processes remain
        # This is the critical test - we're checking for resource leaks
        current_children = parent.children(recursive=True)
        sleep_processes = [
            p for p in current_children
            if 'sleep' in p.name().lower()
        ]

        assert len(sleep_processes) == 0, (
            f"Resource leak detected! {len(sleep_processes)} orphaned 'sleep' "
            f"process(es) still running after timeout. PIDs: "
            f"{[p.pid for p in sleep_processes]}"
        )

        # Verify child process count returned to baseline
        # Allow some tolerance for other system processes
        final_children = len(parent.children(recursive=True))
        assert final_children <= initial_children + 1, (
            f"Process leak detected! Started with {initial_children} children, "
            f"now have {final_children} children"
        )
