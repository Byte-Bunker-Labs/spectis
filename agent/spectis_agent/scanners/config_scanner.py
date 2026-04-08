"""Config scanner -- reads AI client MCP config files and extracts server entries.

SECURITY PRINCIPLE: This scanner NEVER collects secrets, tokens, credentials,
or any sensitive values. It only collects:
  - Server name, client name, transport type
  - Runtime (docker, npx, uvx, native)
  - Package name or container image (no tags with secrets)
  - Endpoint URL (hostname + path only, auth stripped)
  - Locality (local vs remote) for data exfiltration risk
  - Env var NAMES (never values)
  - Whether credentials are present (boolean)
  - Container image version if available
"""

from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore[no-redef]

logger = logging.getLogger(__name__)

_SECRET_ARG_PATTERNS = re.compile(
    r"(bearer\s+\S+|token[=:]\S+|key[=:]\S+|password[=:]\S+"
    r"|secret[=:]\S+|authorization[=:]\S+|--header\s+\S+|--token\s+\S+|--api-key\s+\S+)",
    re.IGNORECASE,
)
_CREDENTIAL_KEYWORDS = ("token", "secret", "key", "password", "credential", "bearer", "auth")
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "[::1]"}


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _read_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as fh:
        return tomllib.load(fh)


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError:
        # PyYAML not installed — skip YAML configs
        return {}
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
        return data if isinstance(data, dict) else {}


def _detect_transport(server_cfg: dict[str, Any]) -> str:
    if "url" in server_cfg:
        url = server_cfg["url"]
        if "sse" in url.lower() or url.startswith("http"):
            return "sse" if "sse" in url.lower() else "http"
    if "command" in server_cfg:
        return "stdio"
    return "unknown"


def _detect_runtime(server_cfg: dict[str, Any]) -> str:
    """Detect the runtime: docker, npx, uvx, pip, or native."""
    command = server_cfg.get("command", "")
    runner = Path(command).name.lower() if command else ""
    if runner == "docker":
        return "docker"
    if runner == "npx":
        return "npx"
    if runner in ("uvx", "uv"):
        return "uvx"
    if runner in ("pip", "pipx"):
        return "pip"
    return "native"


def _extract_docker_image(server_cfg: dict[str, Any]) -> str | None:
    """Extract Docker container image name from args. Strip registry prefix for display."""
    args = server_cfg.get("args", [])
    if not isinstance(args, list):
        return None

    # Docker image is typically the last non-flag arg, or after "run" ... flags
    # Pattern: docker run -i --rm -e FOO -e BAR <image>
    # Skip flags (-i, --rm, -e and their values)
    skip_next = False
    for arg in args:
        arg_str = str(arg)
        if skip_next:
            skip_next = False
            continue
        if arg_str in ("run", "-i", "--rm", "--init", "-t", "--tty"):
            continue
        if arg_str == "-e":
            skip_next = True
            continue
        if arg_str.startswith("-"):
            if "=" not in arg_str:
                skip_next = True
            continue
        # This should be the image name
        # Could be: hosted.nexus.lordabbett.com/mcp/github/github-mcp-server:0.28.1
        # or: https://docker.io/docker.io/mcp/markitdown
        image = arg_str.removeprefix("https://").removeprefix("http://")
        return image

    return None


def _extract_package_name(server_cfg: dict[str, Any]) -> str:
    """Extract the package/binary name."""
    runtime = _detect_runtime(server_cfg)

    if runtime == "docker":
        image = _extract_docker_image(server_cfg)
        if image:
            # Return just image basename:tag (e.g. "github-mcp-server:0.28.1")
            parts = image.rsplit("/", 1)
            return parts[-1] if parts else image
        return "docker"

    command = server_cfg.get("command", "")
    args = server_cfg.get("args", [])
    if not isinstance(args, list):
        args = []

    runner = Path(command).name.lower() if command else ""
    if runner in ("npx", "uvx", "pipx", "pip"):
        for arg in args:
            arg_str = str(arg)
            if arg_str.startswith("-"):
                continue
            if arg_str.startswith("http"):
                break
            return arg_str
        return runner

    return Path(command).name if command else ""


def _extract_endpoint(server_cfg: dict[str, Any]) -> str | None:
    """Extract clean endpoint URL — hostname and path only, NO auth/tokens."""
    if "url" in server_cfg:
        return _sanitize_url(server_cfg["url"])
    args = server_cfg.get("args", [])
    if isinstance(args, list):
        for arg in args:
            arg_str = str(arg)
            if arg_str.startswith("http://") or arg_str.startswith("https://"):
                # Skip Docker image URLs (docker.io, registry URLs used as image refs)
                if _detect_runtime(server_cfg) == "docker":
                    continue
                return _sanitize_url(arg_str)
    return None


def _sanitize_url(url: str) -> str:
    """Strip credentials, auth params, tokens from a URL."""
    try:
        parsed = urlparse(url)
        clean = f"{parsed.scheme}://{parsed.hostname}"
        if parsed.port:
            clean += f":{parsed.port}"
        if parsed.path:
            clean += parsed.path
        return clean
    except Exception:
        return url.split("?")[0].split(" ")[0]


def _classify_locality(
    runtime: str, endpoint: str | None, server_cfg: dict[str, Any]
) -> str:
    """Classify as 'local' or 'remote'.

    Local: docker containers, localhost endpoints, stdio with no external URL.
    Remote: connects to external endpoints (data exfiltration risk).
    """
    # Docker containers are local by default (unless they connect outward,
    # but that's the container's business, not the MCP config's)
    if runtime == "docker":
        return "local"

    # If there's an external endpoint URL, it's remote
    if endpoint:
        try:
            parsed = urlparse(endpoint)
            host = (parsed.hostname or "").lower()
            if host and host not in _LOCAL_HOSTS:
                return "remote"
        except Exception:
            pass

    # stdio with no external URL = local
    return "local"


def _extract_env_var_names(server_cfg: dict[str, Any]) -> list[str]:
    env = server_cfg.get("env", {})
    if isinstance(env, dict):
        return sorted(env.keys())
    return []


def _has_credentials(env_var_names: list[str], server_cfg: dict[str, Any]) -> bool:
    for name in env_var_names:
        if any(kw in name.lower() for kw in _CREDENTIAL_KEYWORDS):
            return True
    args = server_cfg.get("args", [])
    if isinstance(args, list):
        full_args = " ".join(str(a) for a in args)
        if _SECRET_ARG_PATTERNS.search(full_args):
            return True
    return False


def _extract_version(server_cfg: dict[str, Any]) -> str | None:
    """Extract version from config if available."""
    if "version" in server_cfg:
        return str(server_cfg["version"])
    # Try to extract from Docker image tag
    if _detect_runtime(server_cfg) == "docker":
        image = _extract_docker_image(server_cfg)
        if image and ":" in image:
            return image.rsplit(":", 1)[-1]
    return None


def scan_config(config_descriptor: dict) -> list[dict]:
    """Scan a single MCP config file. Returns safe findings only — no secrets."""
    config_path: Path = config_descriptor["config_path"]
    client_name: str = config_descriptor["client_name"]
    root_key: str = config_descriptor["root_key"]

    # Handle glob patterns (e.g. JetBrains scans multiple product dirs)
    if "glob" in config_descriptor:
        if not config_path.is_dir():
            return []
        all_findings: list[dict] = []
        for match in config_path.glob(config_descriptor["glob"]):
            sub_descriptor = {**config_descriptor, "config_path": match}
            del sub_descriptor["glob"]
            all_findings.extend(scan_config(sub_descriptor))
        return all_findings

    if not config_path.exists():
        return []

    try:
        if config_path.suffix == ".toml":
            data = _read_toml(config_path)
        elif config_path.suffix in (".yaml", ".yml"):
            data = _read_yaml(config_path)
        else:
            data = _read_json(config_path)
    except Exception as exc:
        logger.warning("Failed to parse %s: %s", config_path, exc)
        return []

    servers: dict[str, Any] | None = data.get(root_key)
    if not servers or not isinstance(servers, dict):
        return []

    findings: list[dict] = []
    for server_name, server_cfg in servers.items():
        if not isinstance(server_cfg, dict):
            continue

        transport = _detect_transport(server_cfg)
        runtime = _detect_runtime(server_cfg)
        package_name = _extract_package_name(server_cfg)
        endpoint = _extract_endpoint(server_cfg)
        locality = _classify_locality(runtime, endpoint, server_cfg)
        env_var_names = _extract_env_var_names(server_cfg)
        creds_detected = _has_credentials(env_var_names, server_cfg)
        version = _extract_version(server_cfg)

        findings.append({
            "scanner": "config",
            "server_name": server_name,
            "client_name": client_name,
            "transport": transport,
            "runtime": runtime,
            "package": package_name,
            "version": version,
            "endpoint": endpoint,
            "locality": locality,
            "env_var_names": env_var_names,
            "has_credentials": creds_detected,
            "risk_level": "",
        })

    return findings


def scan_all_configs(config_descriptors: list[dict] | None = None) -> list[dict]:
    if config_descriptors is None:
        from spectis_agent.platforms import get_mcp_configs
        config_descriptors = get_mcp_configs()

    all_findings: list[dict] = []
    for descriptor in config_descriptors:
        all_findings.extend(scan_config(descriptor))
    return all_findings
