"""MCP Tool Prober — discovers tools exposed by MCP servers using the MCP SDK.

SECURITY: No credential env vars passed, only PATH/HOME. Admin-controlled.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_PROBE_TIMEOUT = 15
_SAFE_ENV_KEYS = {"PATH", "HOME", "USER", "LANG", "TERM", "SHELL", "TMPDIR"}


def _build_safe_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k in _SAFE_ENV_KEYS}


@dataclass
class ProbeResult:
    tools: list[dict]
    status: str  # discovered, skipped_http, skipped_docker, failed_timeout, failed_auth, failed_error, not_probed
    reason: str


async def _probe_stdio_server(command: str, args: list[str], server_name: str) -> ProbeResult:
    try:
        from mcp.client.stdio import stdio_client, StdioServerParameters
        from mcp.client.session import ClientSession

        server = StdioServerParameters(command=command, args=args, env=_build_safe_env())
        async with stdio_client(server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                tools = []
                for t in result.tools:
                    tools.append({
                        "name": t.name,
                        "description": t.description or "",
                        "input_schema": t.inputSchema if isinstance(t.inputSchema, dict) else {},
                    })
                return ProbeResult(tools, "discovered", f"{len(tools)} tools discovered")
    except Exception as exc:
        msg = str(exc).lower()
        if "token" in msg or "auth" in msg or "credential" in msg or "unauthorized" in msg:
            return ProbeResult([], "failed_auth", "Server requires credentials to start")
        return ProbeResult([], "failed_error", str(exc)[:200])


def _get_probe_command(finding: dict) -> tuple[str, list[str]] | None:
    runtime = finding.get("runtime", "native")
    package = finding.get("package", "")
    if runtime == "docker":
        return None
    if runtime == "npx":
        return "npx", ["-y", package]
    if runtime == "uvx":
        return "uvx", [package]
    if runtime == "native" and package:
        return package, []
    return None


def probe_server(finding: dict) -> ProbeResult:
    """Probe a single MCP server. Always returns a ProbeResult with status."""
    transport = finding.get("transport", "")
    server_name = finding.get("server_name", "unknown")

    if transport in ("http", "sse"):
        return ProbeResult([], "skipped_http", "HTTP/SSE transport requires authentication — cannot probe without credentials")

    if finding.get("runtime") == "docker":
        return ProbeResult([], "skipped_docker", "Docker-based server — container probing not yet supported")

    cmd = _get_probe_command(finding)
    if not cmd:
        return ProbeResult([], "failed_error", "Could not determine probe command")

    command, args = cmd
    logger.info("Probing %s via %s: %s %s", server_name, finding.get("runtime", "?"), command, " ".join(args))

    try:
        result = asyncio.run(asyncio.wait_for(
            _probe_stdio_server(command, args, server_name),
            timeout=_PROBE_TIMEOUT,
        ))
        return result
    except asyncio.TimeoutError:
        return ProbeResult([], "failed_timeout", f"Probe timed out after {_PROBE_TIMEOUT}s — server may need credentials to initialize")
    except Exception as exc:
        return ProbeResult([], "failed_error", str(exc)[:200])


def probe_all_servers(findings: list[dict]) -> dict[str, ProbeResult]:
    """Probe all config findings. Returns server_name -> ProbeResult."""
    results: dict[str, ProbeResult] = {}
    for finding in findings:
        if finding.get("scanner") != "config":
            continue
        server_name = finding.get("server_name", "")
        if not server_name or server_name in results:
            continue
        results[server_name] = probe_server(finding)
    return results
