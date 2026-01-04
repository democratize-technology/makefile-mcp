"""Tests for Makefile parser."""

from pathlib import Path

import pytest

from makefile_mcp import MakeTarget, normalize_tool_name, parse_makefile


@pytest.fixture
def makefile_path(tmp_path: Path) -> Path:
    """Create a temporary Makefile for testing."""
    content = """.PHONY: help test lint format

help: ## Display available commands
\t@echo "Available commands"

test: ## Run the test suite
\tpytest tests/

lint: ## Check code quality
\truff check src/

format: lint ## Format code with ruff
\truff format src/

clean:
\trm -rf dist/

deploy: ## Deploy to production (DANGEROUS)
\t./scripts/deploy.sh

no-description:
\techo "I have no description"
"""
    makefile = tmp_path / "Makefile"
    makefile.write_text(content)
    return makefile


class TestParseMakefile:
    """Tests for parse_makefile function."""

    def test_extracts_targets_with_descriptions(self, makefile_path: Path) -> None:
        """Should extract targets that have ## descriptions."""
        targets = parse_makefile(makefile_path)
        names = [t.name for t in targets]

        assert "help" in names
        assert "test" in names
        assert "lint" in names
        assert "format" in names
        assert "deploy" in names

    def test_ignores_targets_without_descriptions(self, makefile_path: Path) -> None:
        """Should not extract targets without ## descriptions."""
        targets = parse_makefile(makefile_path)
        names = [t.name for t in targets]

        assert "clean" not in names
        assert "no-description" not in names

    def test_extracts_descriptions(self, makefile_path: Path) -> None:
        """Should correctly extract target descriptions."""
        targets = parse_makefile(makefile_path)
        by_name = {t.name: t for t in targets}

        assert by_name["help"].description == "Display available commands"
        assert by_name["test"].description == "Run the test suite"
        assert by_name["deploy"].description == "Deploy to production (DANGEROUS)"

    def test_identifies_phony_targets(self, makefile_path: Path) -> None:
        """Should mark .PHONY targets correctly."""
        targets = parse_makefile(makefile_path)
        by_name = {t.name: t for t in targets}

        assert by_name["help"].is_phony is True
        assert by_name["test"].is_phony is True
        assert by_name["deploy"].is_phony is False  # Not in .PHONY

    def test_handles_missing_file(self, tmp_path: Path) -> None:
        """Should raise error for missing Makefile."""
        with pytest.raises(FileNotFoundError):
            parse_makefile(tmp_path / "nonexistent")


class TestNormalizeToolName:
    """Tests for normalize_tool_name function."""

    def test_adds_prefix(self) -> None:
        """Should add the prefix to tool names."""
        assert normalize_tool_name("test") == "make_test"
        assert normalize_tool_name("lint") == "make_lint"

    def test_replaces_hyphens(self) -> None:
        """Should replace hyphens with underscores."""
        assert normalize_tool_name("build-prod") == "make_build_prod"

    def test_replaces_colons(self) -> None:
        """Should replace colons with underscores."""
        assert normalize_tool_name("lint:fix") == "make_lint_fix"

    def test_custom_prefix(self) -> None:
        """Should use custom prefix when provided."""
        assert normalize_tool_name("test", prefix="project_") == "project_test"
        assert normalize_tool_name("test", prefix="") == "test"
