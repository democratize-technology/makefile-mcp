"""FastMCP server that auto-discovers Makefile targets as tools."""

import asyncio
import fnmatch
import os
from pathlib import Path
from subprocess import PIPE

from fastmcp import FastMCP

from .parser import MakeTarget, normalize_tool_name, parse_makefile

# Will be initialized by create_server()
mcp: FastMCP | None = None


async def run_make(
    makefile: str,
    target: str,
    args: str = "",
    dry_run: bool = False,
    timeout: int = 300,
) -> str:
    """Execute a make target and return output.

    Args:
        makefile: Path to Makefile
        target: Target to run
        args: Additional arguments
        dry_run: If True, use make -n
        timeout: Timeout in seconds

    Returns:
        Command output or error message
    """
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
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
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
    if working_dir:
        os.chdir(working_dir)
    
    makefile_path = Path(makefile).resolve()
    if not makefile_path.exists():
        raise FileNotFoundError(f"Makefile not found: {makefile_path}")

    # Parse targets
    targets = parse_makefile(makefile_path)

    # Filter targets
    def matches_patterns(name: str, patterns: list[str]) -> bool:
        return any(fnmatch.fnmatch(name, p) for p in patterns)

    filtered: list[MakeTarget] = []
    for t in targets:
        if include and not matches_patterns(t.name, include):
            continue
        if exclude and matches_patterns(t.name, exclude):
            continue
        filtered.append(t)

    # Create server
    server = FastMCP(
        name="makefile-mcp",
        instructions=f"Makefile tools from {makefile_path.name}. "
        f"Discovered {len(filtered)} targets.",
    )

    # Register each target as a tool
    for target in filtered:
        tool_name = normalize_tool_name(target.name, prefix)
        
        # Create tool function with closure
        def make_tool_factory(t: MakeTarget) -> callable:
            async def tool_fn(
                args: str = "",
                dry_run: bool = False,
            ) -> str:
                return await run_make(
                    str(makefile_path),
                    t.name,
                    args=args,
                    dry_run=dry_run,
                    timeout=timeout,
                )
            
            # Set metadata
            tool_fn.__name__ = tool_name
            tool_fn.__doc__ = t.description
            return tool_fn

        # Register the tool
        server.tool(name=tool_name, description=target.description)(
            make_tool_factory(target)
        )

    return server
