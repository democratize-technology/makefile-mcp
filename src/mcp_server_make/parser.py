"""Makefile parser for extracting targets and descriptions."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Set


@dataclass
class MakeTarget:
    """Represents a parsed Makefile target."""
    
    name: str
    description: str
    is_phony: bool = False


def parse_makefile(makefile_path: str) -> List[MakeTarget]:
    """Parse a Makefile and extract targets with ## descriptions.
    
    Args:
        makefile_path: Path to the Makefile
        
    Returns:
        List of MakeTarget objects with name, description, and phony status
        
    Convention:
        Targets are documented with ## comments on the same line:
        
            target: deps ## This is the description
            
        Only targets with ## descriptions are extracted.
    """
    content = Path(makefile_path).read_text()
    
    # Find .PHONY targets
    phony_pattern = r'\.PHONY\s*:\s*(.+)'
    phony_targets: Set[str] = set()
    for match in re.finditer(phony_pattern, content):
        phony_targets.update(match.group(1).split())
    
    # Find targets with ## descriptions
    # Pattern: target: [deps] ## description
    target_pattern = r'^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:(?:[^#]*)##\s*(.+)$'
    
    targets: List[MakeTarget] = []
    for match in re.finditer(target_pattern, content, re.MULTILINE):
        name = match.group(1)
        description = match.group(2).strip()
        targets.append(MakeTarget(
            name=name,
            description=description,
            is_phony=name in phony_targets
        ))
    
    return targets


def normalize_tool_name(target_name: str, prefix: str = "make_") -> str:
    """Convert a Makefile target name to a valid MCP tool name.
    
    Args:
        target_name: The Makefile target name (e.g., "lint:fix", "build-prod")
        prefix: Prefix to add to avoid collisions (default: "make_")
        
    Returns:
        Normalized tool name (e.g., "make_lint_fix", "make_build_prod")
    """
    # Replace hyphens and colons with underscores
    normalized = re.sub(r'[-:]', '_', target_name)
    return f"{prefix}{normalized}"
