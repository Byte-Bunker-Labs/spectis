"""Platform dispatcher for MCP config path discovery.

Selects the correct platform module based on the current operating system
and exposes a unified ``get_mcp_configs()`` interface.
"""

from __future__ import annotations

import platform


def get_mcp_configs() -> list[dict]:
    """Return MCP config descriptors for the current platform.

    Each descriptor is a dict with keys:
        client_name  - human-readable AI client name (e.g. "VS Code / Copilot")
        config_path  - pathlib.Path to the config file
        root_key     - JSON/TOML key that holds the server map
        description  - short explanation of what this config covers
    """
    system = platform.system()

    if system == "Windows":
        from spectis_agent.platforms.windows import get_mcp_configs as _get
    elif system == "Darwin":
        from spectis_agent.platforms.macos import get_mcp_configs as _get
    elif system == "Linux":
        from spectis_agent.platforms.linux import get_mcp_configs as _get
    else:
        raise RuntimeError(f"Unsupported platform: {system}")

    return _get()
