"""Windows-specific MCP configuration paths.

Covers all known MCP clients as of 2026-04. Sources:
  https://modelcontextprotocol.io/clients
"""

from __future__ import annotations

import os
from pathlib import Path


def get_mcp_configs() -> list[dict]:
    """Return MCP config descriptors for Windows workstations."""
    appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    userprofile = Path(os.environ.get("USERPROFILE", Path.home()))
    vscode_global = appdata / "Code" / "User" / "globalStorage"
    vscode_ins_global = appdata / "Code - Insiders" / "User" / "globalStorage"

    return [
        # ── VS Code ──
        {"client_name": "VS Code", "config_path": appdata / "Code" / "User" / "mcp.json", "root_key": "servers"},
        {"client_name": "VS Code Insiders", "config_path": appdata / "Code - Insiders" / "User" / "mcp.json", "root_key": "servers"},

        # ── VS Code extensions (globalStorage) ──
        {"client_name": "Cline", "config_path": vscode_global / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json", "root_key": "mcpServers"},
        {"client_name": "Cline (Insiders)", "config_path": vscode_ins_global / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json", "root_key": "mcpServers"},
        {"client_name": "Roo Code", "config_path": vscode_global / "rooveterinaryinc.roo-cline" / "settings" / "mcp_settings.json", "root_key": "mcpServers"},
        {"client_name": "Roo Code (Insiders)", "config_path": vscode_ins_global / "rooveterinaryinc.roo-cline" / "settings" / "mcp_settings.json", "root_key": "mcpServers"},

        # ── Cursor ──
        {"client_name": "Cursor", "config_path": userprofile / ".cursor" / "mcp.json", "root_key": "mcpServers"},

        # ── Windsurf ──
        {"client_name": "Windsurf", "config_path": appdata / "Windsurf" / "User" / "mcp.json", "root_key": "mcpServers"},

        # ── Claude Desktop ──
        {"client_name": "Claude Desktop", "config_path": appdata / "Claude" / "claude_desktop_config.json", "root_key": "mcpServers"},

        # ── Claude Code ──
        {"client_name": "Claude Code", "config_path": userprofile / ".claude.json", "root_key": "mcpServers"},
        {"client_name": "Claude Code", "config_path": userprofile / ".claude" / "settings.json", "root_key": "mcpServers"},
        {"client_name": "Claude Code (managed)", "config_path": Path("C:/Program Files/ClaudeCode/managed-settings.json"), "root_key": "mcpServers"},

        # ── Codex CLI (OpenAI) ──
        {"client_name": "Codex CLI", "config_path": userprofile / ".codex" / "config.toml", "root_key": "mcp_servers"},

        # ── Gemini CLI (Google) ──
        {"client_name": "Gemini CLI", "config_path": userprofile / ".gemini" / "settings.json", "root_key": "mcpServers"},

        # ── Amazon Q ──
        {"client_name": "Amazon Q CLI", "config_path": userprofile / ".amazon-q" / "mcp.json", "root_key": "mcpServers"},

        # ── Zed ──
        {"client_name": "Zed", "config_path": appdata / "Zed" / "settings.json", "root_key": "context_servers"},

        # ── JetBrains (global — scans all product variants) ──
        {"client_name": "JetBrains", "config_path": appdata / "JetBrains", "root_key": "mcpServers", "glob": "*/options/mcp.json"},

        # ── Goose (Block) ──
        {"client_name": "Goose", "config_path": appdata / "goose" / "profiles.yaml", "root_key": "extensions"},

        # ── Warp ──
        {"client_name": "Warp", "config_path": userprofile / ".warp" / "mcp.json", "root_key": "mcpServers"},

        # ── Continue ──
        {"client_name": "Continue", "config_path": userprofile / ".continue" / "config.json", "root_key": "mcpServers"},

        # ── ChatGPT Desktop ──
        {"client_name": "ChatGPT", "config_path": appdata / "com.openai.chat" / "mcp.json", "root_key": "mcpServers"},

        # ── LM Studio ──
        {"client_name": "LM Studio", "config_path": userprofile / ".lmstudio" / "mcp.json", "root_key": "mcpServers"},
    ]
