"""File reporter -- saves scan results as timestamped JSON files."""

from __future__ import annotations

import json
import logging
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def save_report(
    findings: list[dict],
    output_dir: Path | None = None,
) -> Path:
    """Write scan results to a JSON file.

    Parameters
    ----------
    findings : list[dict]
        Scored findings from all scanners.
    output_dir : Path or None
        Directory for report files.  Defaults to ``./spectis-reports``.

    Returns
    -------
    Path
        The path to the written report file.
    """
    if output_dir is None:
        output_dir = Path.cwd() / "spectis-reports"

    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    hostname = socket.gethostname()
    filename = f"spectis-scan-{hostname}-{timestamp}.json"
    filepath = output_dir / filename

    report: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hostname": hostname,
        "scanner_version": _get_version(),
        "summary": _build_summary(findings),
        "findings": findings,
    }

    with filepath.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, default=str)

    logger.info("Report saved to %s", filepath)
    return filepath


def _build_summary(findings: list[dict]) -> dict[str, Any]:
    """Build a summary object for the report."""
    risk_counts = {"high": 0, "medium": 0, "low": 0}
    scanner_counts: dict[str, int] = {}

    for f in findings:
        level = f.get("risk_level", "low")
        risk_counts[level] = risk_counts.get(level, 0) + 1

        scanner = f.get("scanner", "unknown")
        scanner_counts[scanner] = scanner_counts.get(scanner, 0) + 1

    return {
        "total_findings": len(findings),
        "risk_counts": risk_counts,
        "scanner_counts": scanner_counts,
    }


def _get_version() -> str:
    """Return the package version string."""
    try:
        from spectis_agent import __version__

        return __version__
    except ImportError:
        return "unknown"
