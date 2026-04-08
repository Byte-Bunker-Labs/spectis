"""Process scanner -- detects running MCP server processes via psutil.

SECURITY PRINCIPLE: NEVER capture raw command lines — they contain secrets
(bearer tokens, API keys passed as args). Only extract:
  - MCP server package name
  - Process binary name
  - PID
  - Whether credentials were detected in args (boolean)
  - Clean endpoint URL (if found)

Also filters out noise: only reports actual MCP servers, not helper
processes (disclaimer wrappers, package runners, build tools, shells).
"""

from __future__ import annotations

import logging
import re
from pathlib import PurePosixPath
from urllib.parse import urlparse

import psutil

logger = logging.getLogger(__name__)

# Patterns to identify actual MCP server processes (not noise)
_MCP_SERVER_PATTERN = re.compile(r"mcp[-_]?server|mcp[-_]remote", re.IGNORECASE)
_MCP_PACKAGE_PATTERN = re.compile(r"mcp", re.IGNORECASE)

# Processes to SKIP — these are wrappers, build tools, shells, not MCP servers
_SKIP_PROCESS_NAMES = {
    "disclaimer",  # Claude Desktop sandbox wrapper
    "esbuild",     # build tool
    "vite",        # dev server
    "zsh", "bash", "sh", "fish",  # shells
    "npm", "npx",  # package runners (the child node process is what matters)
    "uv", "uvx",   # package runners
    "pip", "pipx",
}

# Patterns in cmdline that mean "this is NOT an MCP server"
_NOISE_PATTERNS = [
    re.compile(r"uvicorn\s+app\.main", re.IGNORECASE),  # our own orchestrator
    re.compile(r"spectis", re.IGNORECASE),                 # our own agent
    re.compile(r"vite|esbuild|webpack", re.IGNORECASE),  # build tools
    re.compile(r"--service=.*--ping", re.IGNORECASE),    # esbuild service
]

# Patterns that indicate secrets in args
_SECRET_PATTERN = re.compile(
    r"(bearer\s+\S|authorization[:\s]+\S|--token\s+\S|--api-key\s+\S"
    r"|--secret\s+\S|--password\s+\S|token=\S|key=\S)",
    re.IGNORECASE,
)

# URL pattern
_URL_PATTERN = re.compile(r"https?://[^\s]+")


def _extract_mcp_server_name(cmdline_parts: list[str]) -> str | None:
    """Try to extract the MCP server package name from cmdline args.

    Matches patterns like:
      node .../mcp-server-github   -> mcp-server-github
      node .../mcp-remote ...      -> mcp-remote
      python .../mcp-msdefenderkql -> mcp-msdefenderkql
      node .../context7-mcp        -> context7-mcp       (*-mcp suffix)
      snyk mcp -t stdio            -> snyk (mcp)
    """
    for part in cmdline_parts:
        basename = PurePosixPath(part).name
        # mcp-server-*, mcp-remote, mcp-*
        if _MCP_SERVER_PATTERN.search(basename):
            return basename
        if basename.startswith("mcp-") and not basename.startswith("mcp."):
            return basename
        # *-mcp suffix pattern (like context7-mcp, defender-mcp)
        if basename.endswith("-mcp") and len(basename) > 4:
            return basename

    # "mcp" as subcommand (like "snyk mcp -t stdio")
    for i, part in enumerate(cmdline_parts):
        if part.lower() == "mcp" and i > 0:
            parent = PurePosixPath(cmdline_parts[i - 1]).name
            if parent not in ("npx", "uvx", "node", "python", "python3"):
                return f"{parent} (mcp)"

    return None


def _extract_clean_endpoint(cmdline_parts: list[str]) -> str | None:
    """Extract a clean URL from cmdline — hostname + path only, no auth."""
    for part in cmdline_parts:
        if part.startswith("http://") or part.startswith("https://"):
            try:
                parsed = urlparse(part)
                clean = f"{parsed.scheme}://{parsed.hostname}"
                if parsed.port:
                    clean += f":{parsed.port}"
                if parsed.path:
                    clean += parsed.path
                return clean
            except Exception:
                pass
    return None


def _has_credentials_in_args(cmdline_parts: list[str]) -> bool:
    """Check if any cmdline args contain secrets."""
    full = " ".join(cmdline_parts)
    return bool(_SECRET_PATTERN.search(full))


def _is_noise(process_name: str, cmdline_parts: list[str]) -> bool:
    """Return True if this process is noise (not an actual MCP server)."""
    if process_name.lower() in _SKIP_PROCESS_NAMES:
        return True
    full = " ".join(cmdline_parts)
    return any(p.search(full) for p in _NOISE_PATTERNS)


def scan_processes() -> list[dict]:
    """Find running MCP server processes. Returns safe findings — no raw cmdlines."""
    findings: list[dict] = []
    seen_servers: set[str] = set()

    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            info = proc.info
            cmdline_parts: list[str] | None = info.get("cmdline")
            if not cmdline_parts:
                continue

            process_name = info.get("name", "")
            full_cmdline = " ".join(cmdline_parts)

            # Skip if no MCP reference at all
            if not _MCP_PACKAGE_PATTERN.search(full_cmdline):
                continue

            # Skip noise processes
            if _is_noise(process_name, cmdline_parts):
                continue

            # Extract the actual MCP server name
            server_name = _extract_mcp_server_name(cmdline_parts)
            if not server_name:
                continue

            # Deduplicate — same server might have parent+child processes
            dedup_key = server_name.lower()
            if dedup_key in seen_servers:
                continue
            seen_servers.add(dedup_key)

            findings.append({
                "scanner": "process",
                "server_name": server_name,
                "process_name": process_name,
                "pid": info["pid"],
                "endpoint": _extract_clean_endpoint(cmdline_parts),
                "has_credentials": _has_credentials_in_args(cmdline_parts),
                "risk_level": "",
            })

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return findings
