"""FastMCP server that auto-discovers Makefile targets as tools."""

import asyncio
import fnmatch
import os
from pathlib import Path
from subprocess import PIPE
from typing import Callable

from fastmcp import FastMCP

from .parser import MakeTarget, normalize_tool_name, parse_makefile

# Module-level state for dynamic working directory configuration
# Precedence: tool setting > env var > cli arg > None
_current_working_dir: str | None = None


def set_working_directory(path: str | None) -> str:
    """Set the working directory for all make commands.

    This setting takes highest precedence in the chain:
    tool setting > MAKEFILE_MCP_CWD > CLI arg > None

    Args:
        path: Directory path, or None to clear the setting

    Returns:
        Confirmation message

    Examples:
        >>> set_working_directory("/path/to/project")
        'Working directory set to: /path/to/project'
        >>> set_working_directory(None)
        'Working directory cleared'
    """
    global _current_working_dir
    _current_working_dir = path

    if path is None:
        return "Working directory cleared"
    return f"Working directory set to: {path}"


def get_working_directory() -> str | None:
    """Get the currently configured working directory.

    Returns:
        The current working directory path, or None if not set
    """
    return _current_working_dir


async def run_make(
    makefile: str,
    target: str,
    working_dir: str | None = None,
    args: str = "",
    dry_run: bool = False,
    timeout: int = 300,
) -> str:
    """Execute a make target and return output.

    Args:
        makefile: Path to Makefile
        target: Target to run
        working_dir: Working directory for command execution (from create_server)
        args: Additional arguments
        dry_run: If True, use make -n
        timeout: Timeout in seconds

    Returns:
        Command output or error message

    Note:
        Working directory precedence:
        1. tool setting (set_working_directory) - highest
        2. working_dir parameter (from create_server, already resolved from CLI/env in __init__.py)
        3. None (current directory)

        The environment variable MAKEFILE_MCP_CWD is handled in __init__.py
        and passed through working_dir parameter.
    """
    # Resolve working directory with precedence chain
    # Note: working_dir parameter already includes env var resolution from __init__.py
    resolved_working_dir = _current_working_dir or working_dir
    cmd = ["make", "-f", makefile]
    if dry_run:
        cmd.append("-n")
    cmd.append(target)
    if args:
        cmd.extend(args.split())

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=PIPE,
            stderr=PIPE,
            cwd=resolved_working_dir,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        # Kill the process to prevent resource leak
        proc.kill()
        await proc.wait()
        return f"Command timed out after {timeout} seconds"
    except Exception as e:
        return f"Failed to execute: {e}"

    output = stdout.decode() if stdout else ""
    errors = stderr.decode() if stderr else ""

    if proc.returncode != 0:
        return f"Exit code {proc.returncode}:\n{errors}\n{output}"

    return output or errors or "(no output)"


def create_server(
    makefile: str = "Makefile",
    working_dir: str | None = None,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    prefix: str = "make_",
    timeout: int = 300,
) -> FastMCP:
    """Create a FastMCP server with auto-discovered Makefile targets.

    Args:
        makefile: Path to Makefile
        working_dir: Working directory for make commands
        include: Glob patterns for targets to include (None = all)
        exclude: Glob patterns for targets to exclude (None = none)
        prefix: Prefix for tool names
        timeout: Command timeout in seconds

    Returns:
        Configured FastMCP server
    """
    # Resolve paths
    makefile_path = Path(makefile).resolve()
    if not makefile_path.exists():
        raise FileNotFoundError(f"Makefile not found: {makefile_path}")

    # Parse targets
    all_targets = parse_makefile(makefile_path)

    # Filter targets
    def matches_patterns(name: str, patterns: list[str]) -> bool:
        return any(fnmatch.fnmatch(name, p) for p in patterns)

    filtered: list[MakeTarget] = []
    for t in all_targets:
        if include and not matches_patterns(t.name, include):
            continue
        if exclude and matches_patterns(t.name, exclude):
            continue
        filtered.append(t)

    # Create server
    server = FastMCP(
        name="makefile-mcp",
        instructions=f"Makefile tools from {makefile_path.name}. "
        f"Discovered {len(filtered)} targets. "
        f"Use the makefile:// resources to inspect the Makefile.",
    )

    # =========================================================================
    # Resources - Let LLM inspect the Makefile
    # =========================================================================

    @server.resource(f"makefile://{makefile_path.name}")
    def get_makefile_contents() -> str:
        """Get the full contents of the Makefile."""
        return makefile_path.read_text()

    @server.resource("makefile://targets")
    def get_target_list() -> str:
        """Get a summary of all available Make targets."""
        lines = [f"# Available targets in {makefile_path.name}\n"]
        for t in filtered:
            tool_name = normalize_tool_name(t.name, prefix)
            phony = " [PHONY]" if t.is_phony else ""
            lines.append(f"- **{tool_name}**: {t.description}{phony}")
        return "\n".join(lines)

    # =========================================================================
    # Tools - One per Makefile target
    # =========================================================================

    for target in filtered:
        tool_name = normalize_tool_name(target.name, prefix)

        # Create tool function with closure
        def make_tool_factory(t: MakeTarget) -> Callable:
            async def tool_fn(
                args: str = "",
                dry_run: bool = False,
            ) -> str:
                """Run this make target.

                Args:
                    args: Additional arguments to pass to make (e.g., "VERBOSE=1")
                    dry_run: If True, show commands without executing (make -n)
                """
                return await run_make(
                    str(makefile_path),
                    t.name,
                    working_dir=working_dir,
                    args=args,
                    dry_run=dry_run,
                    timeout=timeout,
                )

            return tool_fn

        # Register the tool
        server.tool(name=tool_name, description=target.description)(
            make_tool_factory(target)
        )

    return server
