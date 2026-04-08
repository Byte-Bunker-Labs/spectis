"""Risk scoring engine for Spectis findings.

Assigns a risk_level of ``low``, ``medium``, or ``high`` to each finding
based on heuristics such as credential exposure, external endpoints, and
approval status.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Environment variable names that commonly hold secrets.
_CREDENTIAL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(api[_-]?key|secret|token|password|credential)", re.IGNORECASE),
    re.compile(r"(auth|bearer|jwt)", re.IGNORECASE),
    re.compile(r"(aws_secret|azure_.*key|gcp_.*key)", re.IGNORECASE),
]

# Hostnames/IPs that are considered "local" (non-external).
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "[::1]"}

# Regex to pull a hostname from a URL-like string.
_HOST_RE = re.compile(r"https?://([^/:]+)")


def load_approved_servers(path: Path | None) -> set[str]:
    """Load the set of approved server names from a JSON file.

    The file should be a JSON object with a top-level ``servers`` array,
    where each element has at least a ``name`` key.  Falls back to
    ``{"name": ...}`` or a flat list of strings.
    """
    if path is None or not path.exists():
        return set()

    try:
        with path.open("r", encoding="utf-8") as fh:
            data: Any = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load approved servers from %s: %s", path, exc)
        return set()

    names: set[str] = set()

    # Support {"servers": [{"name": "x"}, ...]}
    if isinstance(data, dict) and "servers" in data:
        for entry in data["servers"]:
            if isinstance(entry, dict) and "name" in entry:
                names.add(entry["name"].lower())
            elif isinstance(entry, str):
                names.add(entry.lower())
    # Support flat list: ["server-a", "server-b"]
    elif isinstance(data, list):
        for entry in data:
            if isinstance(entry, dict) and "name" in entry:
                names.add(entry["name"].lower())
            elif isinstance(entry, str):
                names.add(entry.lower())

    return names


def _has_credential_env_vars(env_vars: dict[str, str]) -> bool:
    """Return True if any env var name matches a credential pattern."""
    for var_name in env_vars:
        for pat in _CREDENTIAL_PATTERNS:
            if pat.search(var_name):
                return True
    return False


def _is_external_endpoint(command_or_url: str) -> bool:
    """Return True if the command/URL references a non-localhost address."""
    match = _HOST_RE.search(command_or_url)
    if match:
        host = match.group(1).lower()
        return host not in _LOCAL_HOSTS
    return False


def score_finding(
    finding: dict,
    approved_servers: set[str] | None = None,
) -> str:
    """Assign a risk level to a single finding.

    Parameters
    ----------
    finding : dict
        A finding produced by one of the scanners.
    approved_servers : set[str] or None
        Lowercased names of approved MCP servers.

    Returns
    -------
    str
        One of ``"high"``, ``"medium"``, or ``"low"``.
    """
    if approved_servers is None:
        approved_servers = set()

    # --- High-risk conditions ---
    if finding.get("has_credentials"):
        return "high"
    env_var_names = finding.get("env_var_names", [])
    if isinstance(env_var_names, list):
        for name in env_var_names:
            for pat in _CREDENTIAL_PATTERNS:
                if pat.search(name):
                    return "high"

    # Remote locality = data exfiltration risk
    if finding.get("locality") == "remote":
        return "high"

    # Check endpoint for external hosts
    endpoint = finding.get("endpoint", "") or ""
    if endpoint and _is_external_endpoint(endpoint):
        return "high"

    # Network findings on non-local addresses
    address = finding.get("address", "")
    if address and address not in _LOCAL_HOSTS:
        return "high"

    # --- Medium-risk conditions ---
    server_name = finding.get("server_name", "").lower()
    if server_name and approved_servers and server_name not in approved_servers:
        return "medium"

    # Process / network findings where we cannot determine approval status
    scanner = finding.get("scanner", "")
    if scanner in ("process", "network"):
        server = finding.get("server_name", "").lower()
        if approved_servers and server not in approved_servers:
            return "medium"

    # Unknown server (no approved list provided at all)
    if server_name and not approved_servers:
        return "medium"

    # --- Low-risk ---
    return "low"


def score_findings(
    findings: list[dict],
    approved_servers: set[str] | None = None,
) -> list[dict]:
    """Score a batch of findings in place and return them.

    Each finding dict gets its ``risk_level`` key populated.
    """
    for finding in findings:
        finding["risk_level"] = score_finding(finding, approved_servers)
    return findings
