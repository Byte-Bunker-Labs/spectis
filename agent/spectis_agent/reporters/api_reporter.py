"""API reporter -- posts scan results to the Spectis orchestrator."""

from __future__ import annotations

import getpass
import logging
import platform
import socket
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0)


def report_to_orchestrator(
    findings: list[dict],
    orchestrator_url: str,
    api_key: str | None = None,
) -> bool:
    """POST scan results to the orchestrator's ``/api/report`` endpoint."""
    url = f"{orchestrator_url.rstrip('/')}/api/report"

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # Split findings by scanner type to match API schema
    config_findings = [f for f in findings if f.get("scanner") == "config"]
    process_findings = [f for f in findings if f.get("scanner") == "process"]
    network_findings = [f for f in findings if f.get("scanner") == "network"]
    workspace_findings = [f for f in findings if f.get("scanner") == "workspace"]

    payload: dict[str, Any] = {
        "hostname": socket.gethostname(),
        "os_platform": platform.system().lower(),
        "username": getpass.getuser(),
        "agent_version": _get_version(),
        "config_findings": config_findings,
        "process_findings": process_findings,
        "network_findings": network_findings,
        "workspace_findings": workspace_findings,
    }

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            logger.info("Report accepted by orchestrator (%s)", response.status_code)
            return True

    except httpx.ConnectError:
        logger.warning(
            "Cannot connect to orchestrator at %s. Is it running?", orchestrator_url
        )
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Orchestrator rejected report: %s %s",
            exc.response.status_code,
            exc.response.text[:200],
        )
    except httpx.TimeoutException:
        logger.warning("Timeout connecting to orchestrator at %s", orchestrator_url)
    except Exception as exc:
        logger.warning("Unexpected error reporting to orchestrator: %s", exc)

    return False


def _get_version() -> str:
    try:
        from spectis_agent import __version__
        return __version__
    except ImportError:
        return "unknown"
