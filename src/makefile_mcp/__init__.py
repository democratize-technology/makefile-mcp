"""makefile-mcp: Auto-discover Makefile targets as MCP tools."""

from .parser import MakeTarget, normalize_tool_name, parse_makefile
from .server import create_server

__all__ = [
    "MakeTarget",
    "create_server",
    "normalize_tool_name",
    "parse_makefile",
]


def main() -> None:
    """CLI entry point."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        prog="makefile-mcp",
        description="Auto-discover Makefile targets as MCP tools",
    )
    parser.add_argument(
        "--makefile",
        "-m",
        default="Makefile",
        help="Path to Makefile (default: ./Makefile)",
    )
    parser.add_argument(
        "--cwd",
        "-C",
        dest="working_dir",
        help="Working directory for make commands",
    )
    parser.add_argument(
        "--include",
        "-i",
        help="Comma-separated glob patterns for targets to include",
    )
    parser.add_argument(
        "--exclude",
        "-e",
        help="Comma-separated glob patterns for targets to exclude",
    )
    parser.add_argument(
        "--prefix",
        "-p",
        default="make_",
        help="Tool name prefix (default: make_)",
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=300,
        help="Command timeout in seconds (default: 300)",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List discovered targets and exit",
    )

    args = parser.parse_args()

    # Parse include/exclude patterns
    include = args.include.split(",") if args.include else None
    exclude = args.exclude.split(",") if args.exclude else None

    try:
        server = create_server(
            makefile=args.makefile,
            working_dir=args.working_dir,
            include=include,
            exclude=exclude,
            prefix=args.prefix,
            timeout=args.timeout,
        )
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # List mode
    if args.list:
        from .parser import parse_makefile as parse
        
        targets = parse(args.makefile)
        print(f"Discovered {len(targets)} targets:\n")
        for t in targets:
            skip = ""
            if include and not any(__import__("fnmatch").fnmatch(t.name, p) for p in include):
                skip = " [excluded by --include]"
            elif exclude and any(__import__("fnmatch").fnmatch(t.name, p) for p in exclude):
                skip = " [excluded by --exclude]"
            print(f"  {normalize_tool_name(t.name, args.prefix):25} {t.description}{skip}")
        sys.exit(0)

    # Run server
    server.run()


if __name__ == "__main__":
    main()
