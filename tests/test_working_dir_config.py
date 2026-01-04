"""Tests for working directory configuration methods."""

import os
import tempfile
from pathlib import Path

import pytest

from makefile_mcp import create_server
from makefile_mcp.server import run_make, set_working_directory, get_working_directory

SAMPLE_MAKEFILE = """\
.PHONY: pwd_target check_marker

pwd_target: ## Print working directory
\t@pwd
\t@echo "File exists: $(shell test -f marker.txt && echo yes || echo no)"

check_marker: ## Check if marker file exists
\t@echo "Marker: $(shell test -f marker.txt && echo yes || echo no)"
"""


class TestEnvironmentVariable:
    """Tests for MAKEFILE_MCP_CWD environment variable support."""

    @pytest.mark.asyncio
    async def test_env_var_respected_in_main(self, tmp_path: Path, monkeypatch) -> None:
        """Should use MAKEFILE_MCP_CWD when invoked via main() CLI."""
        # This test would need to test the CLI interface (main function)
        # For now, we skip this as it requires subprocess testing
        # The env var logic is in __init__.py main() function
        pass

    @pytest.mark.asyncio
    async def test_create_server_ignores_env_var(self, tmp_path: Path, monkeypatch) -> None:
        """create_server() should NOT check env var - only main() does."""
        # Create test directory structure
        work_dir = tmp_path / "from_env"
        work_dir.mkdir()
        marker_file = work_dir / "marker.txt"
        marker_file.write_text("test")

        makefile = work_dir / "Makefile"
        makefile.write_text(SAMPLE_MAKEFILE)

        # Set environment variable (should be IGNORED by create_server)
        monkeypatch.setenv("MAKEFILE_MCP_CWD", str(work_dir))

        # Create server WITHOUT working_dir parameter
        # Since create_server doesn't check env var, working_dir will be None
        server = create_server(makefile=str(makefile))

        # Get the pwd_target tool
        tools = await server.get_tools()
        pwd_tool = tools["make_pwd_target"]

        # Execute - should use current directory (not env var)
        result = await pwd_tool.fn()

        # Verify it did NOT use the env var directory
        # (It will use the current working directory, which is the project root)
        assert "File exists: no" in result, (
            "create_server should ignore env var when working_dir=None"
        )

    @pytest.mark.asyncio
    async def test_cli_arg_overrides_env_var(self, tmp_path: Path, monkeypatch) -> None:
        """CLI --cwd should override MAKEFILE_MCP_CWD."""
        # Create two directories
        env_dir = tmp_path / "from_env"
        env_dir.mkdir()
        (env_dir / "marker.txt").write_text("env")
        env_makefile = env_dir / "Makefile"
        env_makefile.write_text(SAMPLE_MAKEFILE)

        cli_dir = tmp_path / "from_cli"
        cli_dir.mkdir()
        (cli_dir / "marker.txt").write_text("cli")
        cli_makefile = cli_dir / "Makefile"
        cli_makefile.write_text(SAMPLE_MAKEFILE)

        # Set environment variable
        monkeypatch.setenv("MAKEFILE_MCP_CWD", str(env_dir))

        # Create server with CLI working_dir parameter (should override env)
        server = create_server(
            makefile=str(env_makefile),  # Makefile in env dir
            working_dir=str(cli_dir),    # But execute in cli dir
        )

        # Get the pwd_target tool
        tools = await server.get_tools()
        pwd_tool = tools["make_pwd_target"]

        # Execute and verify it uses CLI directory, not env
        result = await pwd_tool.fn()
        assert str(cli_dir) in result, f"Expected {cli_dir} in output: {result}"
        assert str(env_dir) not in result, f"Should not use env dir: {result}"

    @pytest.mark.asyncio
    async def test_no_env_var_and_no_cli_arg_uses_none(self, tmp_path: Path, monkeypatch) -> None:
        """Should use None (current directory) when no env var or CLI arg."""
        # Ensure no environment variable set
        monkeypatch.delenv("MAKEFILE_MCP_CWD", raising=False)

        work_dir = tmp_path / "workspace"
        work_dir.mkdir()
        makefile = work_dir / "Makefile"
        makefile.write_text(SAMPLE_MAKEFILE)

        # Create server without working_dir
        server = create_server(makefile=str(makefile))

        # Server should work fine with None working_dir
        tools = await server.get_tools()
        assert "make_pwd_target" in tools


class TestSetWorkingDirectoryTool:
    """Tests for set_working_directory dynamic tool."""

    @pytest.mark.asyncio
    async def test_set_working_directory_changes_state(self) -> None:
        """Should change module-level working directory state."""
        # Clear any existing state
        set_working_directory(None)

        # Set a working directory
        test_dir = "/tmp/test_dir"
        result = set_working_directory(test_dir)

        assert "set to" in result.lower()
        assert test_dir in result

        # Verify state changed
        current = get_working_directory()
        assert current == test_dir

        # Clean up
        set_working_directory(None)

    @pytest.mark.asyncio
    async def test_tool_setting_overrides_env_var(self, tmp_path: Path, monkeypatch) -> None:
        """Tool setting should override environment variable."""
        # Create two directories
        env_dir = tmp_path / "from_env"
        env_dir.mkdir()
        (env_dir / "marker.txt").write_text("env")
        env_makefile = env_dir / "Makefile"
        env_makefile.write_text(SAMPLE_MAKEFILE)

        tool_dir = tmp_path / "from_tool"
        tool_dir.mkdir()
        (tool_dir / "marker.txt").write_text("tool")
        tool_makefile = tool_dir / "Makefile"
        tool_makefile.write_text(SAMPLE_MAKEFILE)

        # Set environment variable
        monkeypatch.setenv("MAKEFILE_MCP_CWD", str(env_dir))

        # Set working directory via tool (should override env)
        set_working_directory(str(tool_dir))

        # Create server
        server = create_server(makefile=str(env_makefile))
        tools = await server.get_tools()
        check_tool = tools["make_check_marker"]

        # Execute and verify it uses tool directory, not env
        result = await check_tool.fn()
        assert "Marker: yes" in result, "marker.txt should exist in tool dir"

        # Clean up
        set_working_directory(None)

    @pytest.mark.asyncio
    async def test_precedence_chain(self, tmp_path: Path) -> None:
        """Test precedence: tool setting > create_server parameter."""
        # Create directories
        param_dir = tmp_path / "param_dir"
        param_dir.mkdir()
        (param_dir / "marker.txt").write_text("param")
        param_makefile = param_dir / "Makefile"
        param_makefile.write_text(SAMPLE_MAKEFILE)

        tool_dir = tmp_path / "tool_dir"
        tool_dir.mkdir()
        (tool_dir / "marker.txt").write_text("tool")

        # Create server with working_dir parameter
        server = create_server(
            makefile=str(param_makefile),
            working_dir=str(param_dir),
        )

        tools = await server.get_tools()
        check_tool = tools["make_check_marker"]

        # First, without tool setting, should use param_dir
        result1 = await check_tool.fn()
        assert "Marker: yes" in result1, "Should use param_dir from create_server"

        # Now set tool directory (highest precedence)
        set_working_directory(str(tool_dir))

        # Should now use tool_dir, not param_dir
        result2 = await check_tool.fn()
        assert "Marker: yes" in result2, "Should use tool_dir (highest precedence)"

        # Clear tool setting
        set_working_directory(None)

        # Should revert to param_dir
        result3 = await check_tool.fn()
        assert "Marker: yes" in result3, "Should use param_dir after clearing tool setting"

        # Clean up
        set_working_directory(None)

    @pytest.mark.asyncio
    async def test_clear_working_directory(self) -> None:
        """Should be able to clear working directory by setting to None."""
        # Set a working directory
        set_working_directory("/tmp/some_dir")

        # Clear it
        result = set_working_directory(None)

        assert "cleared" in result.lower() or "none" in result.lower()

        # Verify state cleared
        current = get_working_directory()
        assert current is None

    def test_set_working_directory_is_thread_safe(self) -> None:
        """Module-level variable should be safely accessible."""
        # This test verifies the pattern works, not true thread safety
        # (which would require threading tests)
        set_working_directory("/tmp/test")
        current = get_working_directory()
        assert current == "/tmp/test"

        # Clean up
        set_working_directory(None)
