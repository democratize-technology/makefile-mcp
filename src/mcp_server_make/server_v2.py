"""MCP server implementation for make functionality with auto-discovery."""

from typing import Any, Dict, List, Optional, Set
import os
import asyncio
from subprocess import PIPE

from mcp.shared.exceptions import McpError
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    ErrorData,
    GetPromptResult,
    Prompt,
    TextContent,
    Tool,
    INVALID_PARAMS,
)
from pydantic import BaseModel, Field

from .parser import parse_makefile, normalize_tool_name, MakeTarget


class Make(BaseModel):
    """Parameters for the generic make tool (backward compatibility)."""
    target: str = Field(description="Make target to run")


class MakeWithArgs(BaseModel):
    """Parameters for auto-discovered make target tools."""
    args: str = Field(default="", description="Additional arguments to pass to make")
    dry_run: bool = Field(default=False, description="Print commands without executing (make -n)")


async def run_make_target(
    make_path: str,
    target: str,
    extra_args: str = "",
    dry_run: bool = False
) -> str:
    """Execute a make target and return the output.
    
    Args:
        make_path: Path to the Makefile
        target: Make target to run
        extra_args: Additional arguments to pass
        dry_run: If True, use make -n to show commands without executing
        
    Returns:
        Combined stdout/stderr output
    """
    cmd = ["make", "-f", make_path]
    if dry_run:
        cmd.append("-n")
    cmd.append(target)
    if extra_args:
        cmd.extend(extra_args.split())
    
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=PIPE,
            stderr=PIPE,
            start_new_session=True,
        )
    except Exception as e:
        return f"Failed to start make process: {str(e)}"

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=300  # 5 minute timeout
        )
    except asyncio.TimeoutError:
        if proc.returncode is None:
            proc.terminate()
        return "Make command timed out after 5 minutes"
    except asyncio.CancelledError:
        if proc.returncode is None:
            try:
                proc.terminate()
                await asyncio.sleep(0.1)
                if proc.returncode is None:
                    proc.kill()
            except Exception:
                pass
        raise
    except Exception as e:
        return f"Error during make execution: {str(e)}"

    stderr_text = stderr.decode() if stderr else ""
    stdout_text = stdout.decode() if stdout else ""

    if proc.returncode != 0:
        return f"Make failed with exit code {proc.returncode}:\n{stderr_text}\n{stdout_text}"

    return stdout_text or stderr_text or "(no output)"


async def serve(
    make_path: Optional[str] = None,
    working_dir: Optional[str] = None,
    auto_discover: bool = True,
    include: Optional[Set[str]] = None,
    exclude: Optional[Set[str]] = None,
    prefix: str = "make_",
) -> None:
    """Run the make MCP server with optional auto-discovery.

    Args:
        make_path: Optional path to Makefile
        working_dir: Optional working directory
        auto_discover: If True, parse Makefile and create tool per target
        include: Set of target names to include (None = all)
        exclude: Set of target names to exclude (None = none)
        prefix: Prefix for auto-discovered tool names (default: "make_")
    """
    server: Server = Server("mcp-make")

    # Set working directory
    if working_dir:
        os.chdir(working_dir)

    # Set make path
    make_path = make_path or "Makefile"
    if not os.path.exists(make_path):
        raise McpError(
            ErrorData(code=INVALID_PARAMS, message=f"Makefile not found at {make_path}")
        )

    # Parse Makefile for auto-discovery
    discovered_targets: Dict[str, MakeTarget] = {}
    if auto_discover:
        targets = parse_makefile(make_path)
        for t in targets:
            # Apply include/exclude filters
            if include and t.name not in include:
                continue
            if exclude and t.name in exclude:
                continue
            tool_name = normalize_tool_name(t.name, prefix)
            discovered_targets[tool_name] = t

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        """List available tools including auto-discovered targets."""
        tools: List[Tool] = []
        
        # Always include the generic make tool for backward compatibility
        tools.append(Tool(
            name="make",
            description="Run any make target (use for targets not in the auto-discovered list)",
            inputSchema=Make.model_json_schema(),
        ))
        
        # Add auto-discovered target-specific tools
        for tool_name, target in discovered_targets.items():
            tools.append(Tool(
                name=tool_name,
                description=target.description,
                inputSchema=MakeWithArgs.model_json_schema(),
            ))
        
        return tools


    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Execute a tool (generic make or auto-discovered target)."""
        
        # Handle generic make tool
        if name == "make":
            try:
                args = Make(**arguments)
            except Exception as e:
                return [TextContent(type="text", text=f"Invalid arguments: {str(e)}")]
            
            output = await run_make_target(make_path, args.target)
            return [TextContent(type="text", text=output)]
        
        # Handle auto-discovered tools
        if name in discovered_targets:
            target = discovered_targets[name]
            try:
                args = MakeWithArgs(**arguments)
            except Exception as e:
                return [TextContent(type="text", text=f"Invalid arguments: {str(e)}")]
            
            output = await run_make_target(
                make_path,
                target.name,
                extra_args=args.args,
                dry_run=args.dry_run
            )
            return [TextContent(type="text", text=output)]
        
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    @server.list_prompts()
    async def list_prompts() -> List[Prompt]:
        """List available prompts."""
        return []

    @server.get_prompt()
    async def get_prompt(
        name: str, arguments: Optional[Dict[str, Any]]
    ) -> GetPromptResult:
        """Get a prompt by name."""
        raise McpError(
            ErrorData(code=INVALID_PARAMS, message=f"Unknown prompt: {name}")
        )

    options = server.create_initialization_options()
    async with stdio_server() as streams:
        read_stream, write_stream = streams
        await server.run(read_stream, write_stream, options, raise_exceptions=True)
