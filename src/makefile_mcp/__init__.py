"""makefile-mcp: Auto-discover Makefile targets as MCP tools."""

from .parser import MakeTarget, normalize_tool_name, parse_makefile
from .server import create_server

__version__ = "0.1.0"
__all__ = [
    "__version__",
    "MakeTarget",
    "create_server",
    "normalize_tool_name",
    "parse_makefile",
]


def main() -> None:
    """CLI entry point."""
    import argparse
    import fnmatch
    import os
    import sys

    parser = argparse.ArgumentParser(
        prog="makefile-mcp",
        description="Auto-discover Makefile targets as MCP tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  makefile-mcp                          # Use ./Makefile
  makefile-mcp --list                   # Preview targets
  makefile-mcp -C /path/to/project      # Specify working directory
  makefile-mcp --exclude "deploy,*-prod" # Block dangerous targets

Environment Variables:
  MAKEFILE_MCP_CWD                     # Default working directory (overridden by -C)
""",
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-m", "--makefile",
        default="Makefile",
        metavar="PATH",
        help="Path to Makefile (default: ./Makefile)",
    )
    parser.add_argument(
        "-C", "--cwd",
        dest="working_dir",
        metavar="PATH",
        help="Working directory for make commands",
    )
    parser.add_argument(
        "-i", "--include",
        metavar="GLOB",
        help="Only include matching targets (comma-separated globs)",
    )
    parser.add_argument(
        "-e", "--exclude",
        metavar="GLOB",
        help="Exclude matching targets (comma-separated globs)",
    )
    parser.add_argument(
        "-p", "--prefix",
        default="make_",
        metavar="TEXT",
        help="Tool name prefix (default: make_)",
    )
    parser.add_argument(
        "-t", "--timeout",
        type=int,
        default=300,
        metavar="SECS",
        help="Command timeout in seconds (default: 300)",
    )
    parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="List discovered targets and exit",
    )

    args = parser.parse_args()

    # Parse include/exclude patterns
    include = [p.strip() for p in args.include.split(",")] if args.include else None
    exclude = [p.strip() for p in args.exclude.split(",")] if args.exclude else None

    # Resolve working directory: CLI arg overrides environment variable
    working_dir = args.working_dir or os.environ.get("MAKEFILE_MCP_CWD")

    # List mode - show targets without starting server
    if args.list:
        try:
            targets = parse_makefile(args.makefile)
        except FileNotFoundError:
            print(f"Error: Makefile not found: {args.makefile}", file=sys.stderr)
            sys.exit(1)

        print(f"Discovered {len(targets)} targets:\n")
        for t in targets:
            tool_name = normalize_tool_name(t.name, args.prefix)
            skip = ""
            if include and not any(fnmatch.fnmatch(t.name, p) for p in include):
                skip = " \033[90m[excluded by --include]\033[0m"
            elif exclude and any(fnmatch.fnmatch(t.name, p) for p in exclude):
                skip = " \033[90m[excluded by --exclude]\033[0m"
            print(f"  \033[36m{tool_name:25}\033[0m {t.description}{skip}")
        sys.exit(0)

    # Create and run server
    try:
        server = create_server(
            makefile=args.makefile,
            working_dir=working_dir,
            include=include,
            exclude=exclude,
            prefix=args.prefix,
            timeout=args.timeout,
        )
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    server.run()


if __name__ == "__main__":
    main()
