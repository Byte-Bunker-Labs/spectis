"""Network scanner -- detects listening TCP ports with MCP-like processes."""

from __future__ import annotations

import logging
import re

import psutil

logger = logging.getLogger(__name__)

# Reuse the same MCP command-line heuristics as the process scanner.
_MCP_RE = re.compile(
    r"(\bmcp\b|model-context-protocol|mcp-server)", re.IGNORECASE
)


def scan_network_listeners() -> list[dict]:
    """Find listening TCP sockets whose owning process has an MCP-like
    command line.

    Returns
    -------
    list[dict]
        Each finding contains ``pid``, ``port``, ``address``,
        ``process_name``, ``cmdline``, and ``scanner``.
    """
    findings: list[dict] = []

    try:
        connections = psutil.net_connections(kind="tcp")
    except psutil.AccessDenied:
        logger.warning(
            "Insufficient privileges to enumerate network connections. "
            "Run with elevated permissions for full results."
        )
        return findings

    # Collect unique PIDs that are in LISTEN state.
    listening_pids: dict[int, list[tuple[str, int]]] = {}
    for conn in connections:
        if conn.status == psutil.CONN_LISTEN and conn.pid:
            addr_str = conn.laddr.ip if conn.laddr else "0.0.0.0"
            port = conn.laddr.port if conn.laddr else 0
            listening_pids.setdefault(conn.pid, []).append((addr_str, port))

    for pid, endpoints in listening_pids.items():
        try:
            proc = psutil.Process(pid)
            cmdline_parts = proc.cmdline()
            cmdline_str = " ".join(cmdline_parts) if cmdline_parts else ""
            proc_name = proc.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

        if not _MCP_RE.search(cmdline_str):
            continue

        for addr, port in endpoints:
            findings.append({
                "scanner": "network",
                "pid": pid,
                "port": port,
                "address": addr,
                "process_name": proc_name,
                "cmdline": cmdline_str,
                "risk_level": "",  # populated later by scoring engine
            })

    return findings
