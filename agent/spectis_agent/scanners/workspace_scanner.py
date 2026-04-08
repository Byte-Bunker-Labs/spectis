"""Workspace scanner -- discovers project-level MCP config files in directory trees."""

from __future__ import annotations

import logging
from pathlib import Path

from spectis_agent.scanners.config_scanner import scan_config

logger = logging.getLogger(__name__)

# Well-known project-level MCP config locations relative to a project root.
_WORKSPACE_CONFIGS: list[dict] = [
    {
        "relative_path": Path(".vscode") / "mcp.json",
        "client_name": "VS Code (workspace)",
        "root_key": "servers",
        "description": "Project-level VS Code MCP configuration",
    },
    {
        "relative_path": Path(".cursor") / "mcp.json",
        "client_name": "Cursor (workspace)",
        "root_key": "mcpServers",
        "description": "Project-level Cursor MCP configuration",
    },
    {
        "relative_path": Path(".mcp.json"),
        "client_name": "MCP (workspace)",
        "root_key": "mcpServers",
        "description": "Project-level generic .mcp.json configuration",
    },
    {
        "relative_path": Path(".claude") / "settings.json",
        "client_name": "Claude Code (workspace)",
        "root_key": "mcpServers",
        "description": "Project-level Claude Code configuration",
    },
]


def _iter_directories(root: Path, max_depth: int) -> list[Path]:
    """Yield directories under *root* up to *max_depth* levels deep.

    Skips hidden directories (starting with ```.```) and common non-project
    directories to avoid excessive traversal.
    """
    skip_names = {
        "node_modules", "__pycache__", ".git", ".hg", ".svn",
        "venv", ".venv", "env", ".env", "dist", "build", "target",
    }

    dirs: list[Path] = [root]
    results: list[Path] = [root]

    for _ in range(max_depth):
        next_dirs: list[Path] = []
        for d in dirs:
            try:
                for child in d.iterdir():
                    if child.is_dir() and child.name not in skip_names:
                        next_dirs.append(child)
                        results.append(child)
            except PermissionError:
                continue
        dirs = next_dirs

    return results


def scan_workspace(
    root: Path | None = None,
    max_depth: int = 3,
) -> list[dict]:
    """Scan a directory tree for project-level MCP config files.

    Parameters
    ----------
    root : Path or None
        Starting directory.  Defaults to the current working directory.
    max_depth : int
        How many directory levels to descend.  Default ``3``.

    Returns
    -------
    list[dict]
        Findings from any discovered workspace MCP configs.
    """
    if root is None:
        root = Path.cwd()
    root = root.resolve()

    findings: list[dict] = []
    directories = _iter_directories(root, max_depth)

    for directory in directories:
        for ws_cfg in _WORKSPACE_CONFIGS:
            config_path = directory / ws_cfg["relative_path"]
            descriptor = {
                "client_name": ws_cfg["client_name"],
                "config_path": config_path,
                "root_key": ws_cfg["root_key"],
                "description": ws_cfg["description"],
            }
            results = scan_config(descriptor)
            for r in results:
                r["workspace_root"] = str(directory)
            findings.extend(results)

    return findings
