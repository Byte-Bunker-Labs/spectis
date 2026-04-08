"""macOS-specific MCP configuration paths.

Covers all known MCP clients as of 2026-04. Sources:
  https://modelcontextprotocol.io/clients
"""

from __future__ import annotations

from pathlib import Path


def get_mcp_configs() -> list[dict]:
    """Return MCP config descriptors for macOS workstations."""
    home = Path.home()
    app_support = home / "Library" / "Application Support"
    vscode_global = app_support / "Code" / "User" / "globalStorage"
    vscode_ins_global = app_support / "Code - Insiders" / "User" / "globalStorage"

    return [
        # ── VS Code ──
        {"client_name": "VS Code", "config_path": app_support / "Code" / "User" / "mcp.json", "root_key": "servers"},
        {"client_name": "VS Code Insiders", "config_path": app_support / "Code - Insiders" / "User" / "mcp.json", "root_key": "servers"},

        # ── VS Code extensions (globalStorage) ──
        {"client_name": "Cline", "config_path": vscode_global / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json", "root_key": "mcpServers"},
        {"client_name": "Cline (Insiders)", "config_path": vscode_ins_global / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json", "root_key": "mcpServers"},
        {"client_name": "Roo Code", "config_path": vscode_global / "rooveterinaryinc.roo-cline" / "settings" / "mcp_settings.json", "root_key": "mcpServers"},
        {"client_name": "Roo Code (Insiders)", "config_path": vscode_ins_global / "rooveterinaryinc.roo-cline" / "settings" / "mcp_settings.json", "root_key": "mcpServers"},

        # ── Cursor ──
        {"client_name": "Cursor", "config_path": home / ".cursor" / "mcp.json", "root_key": "mcpServers"},

        # ── Windsurf ──
        {"client_name": "Windsurf", "config_path": app_support / "Windsurf" / "User" / "mcp.json", "root_key": "mcpServers"},

        # ── Claude Desktop ──
        {"client_name": "Claude Desktop", "config_path": app_support / "Claude" / "claude_desktop_config.json", "root_key": "mcpServers"},

        # ── Claude Code ──
        {"client_name": "Claude Code", "config_path": home / ".claude.json", "root_key": "mcpServers"},
        {"client_name": "Claude Code", "config_path": home / ".claude" / "settings.json", "root_key": "mcpServers"},

        # ── Codex CLI (OpenAI) ──
        {"client_name": "Codex CLI", "config_path": home / ".codex" / "config.toml", "root_key": "mcp_servers"},

        # ── Gemini CLI (Google) ──
        {"client_name": "Gemini CLI", "config_path": home / ".gemini" / "settings.json", "root_key": "mcpServers"},

        # ── Amazon Q ──
        {"client_name": "Amazon Q CLI", "config_path": home / ".amazon-q" / "mcp.json", "root_key": "mcpServers"},

        # ── Zed ──
        {"client_name": "Zed", "config_path": home / ".config" / "zed" / "settings.json", "root_key": "context_servers"},

        # ── JetBrains (global — scans all product variants) ──
        {"client_name": "JetBrains", "config_path": app_support / "JetBrains", "root_key": "mcpServers", "glob": "*/options/mcp.json"},

        # ── Goose (Block) ──
        {"client_name": "Goose", "config_path": home / ".config" / "goose" / "profiles.yaml", "root_key": "extensions"},

        # ── Warp ──
        {"client_name": "Warp", "config_path": home / ".warp" / "mcp.json", "root_key": "mcpServers"},

        # ── Continue ──
        {"client_name": "Continue", "config_path": home / ".continue" / "config.json", "root_key": "mcpServers"},

        # ── ChatGPT Desktop ──
        {"client_name": "ChatGPT", "config_path": app_support / "com.openai.chat" / "mcp.json", "root_key": "mcpServers"},

        # ── BoltAI (macOS only) ──
        {"client_name": "BoltAI", "config_path": app_support / "BoltAI" / "mcp.json", "root_key": "mcpServers"},

        # ── LM Studio ──
        {"client_name": "LM Studio", "config_path": home / ".lmstudio" / "mcp.json", "root_key": "mcpServers"},
    ]
