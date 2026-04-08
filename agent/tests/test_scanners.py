"""Tests for the Spectis scoring engine and config scanner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from spectis_agent.scanners.config_scanner import scan_all_configs, scan_config
from spectis_agent.scoring import (
    load_approved_servers,
    score_finding,
    score_findings,
)


# ---------------------------------------------------------------------------
# Scoring engine tests
# ---------------------------------------------------------------------------


class TestScoreFinding:
    """Tests for scoring.score_finding."""

    def test_high_risk_credential_in_env(self):
        finding = {
            "scanner": "config",
            "server_name": "some-server",
            "env_vars": {"OPENAI_API_KEY": "sk-abc123"},
            "command_or_url": "npx some-mcp-server",
        }
        assert score_finding(finding) == "high"

    def test_high_risk_secret_token_in_env(self):
        finding = {
            "scanner": "config",
            "server_name": "some-server",
            "env_vars": {"GITHUB_TOKEN": "ghp_xxxx"},
            "command_or_url": "npx some-mcp-server",
        }
        assert score_finding(finding) == "high"

    def test_high_risk_external_endpoint(self):
        finding = {
            "scanner": "config",
            "server_name": "remote-server",
            "env_vars": {},
            "command_or_url": "https://evil.example.com/mcp",
        }
        assert score_finding(finding) == "high"

    def test_high_risk_non_local_network_address(self):
        finding = {
            "scanner": "network",
            "pid": 1234,
            "address": "10.0.0.5",
            "port": 8080,
            "cmdline": "node mcp-server",
        }
        assert score_finding(finding) == "high"

    def test_medium_risk_unapproved_server(self):
        approved = {"postgres-mcp", "github-mcp"}
        finding = {
            "scanner": "config",
            "server_name": "shady-unknown-server",
            "env_vars": {},
            "command_or_url": "npx shady-unknown-server",
        }
        assert score_finding(finding, approved) == "medium"

    def test_medium_risk_no_approved_list(self):
        """Without an approved list, every server is medium risk."""
        finding = {
            "scanner": "config",
            "server_name": "any-server",
            "env_vars": {},
            "command_or_url": "npx any-server",
        }
        assert score_finding(finding) == "medium"

    def test_low_risk_approved_server(self):
        approved = {"postgres-mcp", "github-mcp"}
        finding = {
            "scanner": "config",
            "server_name": "postgres-mcp",
            "env_vars": {},
            "command_or_url": "npx postgres-mcp",
        }
        assert score_finding(finding, approved) == "low"

    def test_low_risk_localhost_url(self):
        approved = {"local-mcp"}
        finding = {
            "scanner": "config",
            "server_name": "local-mcp",
            "env_vars": {},
            "command_or_url": "http://localhost:3000/mcp",
        }
        assert score_finding(finding, approved) == "low"

    def test_network_finding_local_address(self):
        finding = {
            "scanner": "network",
            "pid": 100,
            "address": "127.0.0.1",
            "port": 9090,
            "cmdline": "node mcp-server",
        }
        # No approved list, but local address -- medium (unknown process)
        assert score_finding(finding) in ("medium", "low")

    def test_process_finding_unapproved(self):
        approved = {"approved-mcp"}
        finding = {
            "scanner": "process",
            "pid": 999,
            "name": "node",
            "cmdline": "node unknown-mcp-server",
            "matched_pattern": "mcp-server",
        }
        assert score_finding(finding, approved) == "medium"


class TestScoreFindings:
    """Tests for scoring.score_findings (batch)."""

    def test_scores_all_findings(self):
        findings = [
            {
                "scanner": "config",
                "server_name": "safe",
                "env_vars": {},
                "command_or_url": "npx safe",
            },
            {
                "scanner": "config",
                "server_name": "leaky",
                "env_vars": {"DB_PASSWORD": "secret"},
                "command_or_url": "npx leaky",
            },
        ]
        approved = {"safe"}
        scored = score_findings(findings, approved)

        assert len(scored) == 2
        assert scored[0]["risk_level"] == "low"
        assert scored[1]["risk_level"] == "high"


class TestLoadApprovedServers:
    """Tests for scoring.load_approved_servers."""

    def test_load_from_servers_array(self, tmp_path: Path):
        data = {"servers": [{"name": "postgres-mcp"}, {"name": "GitHub-MCP"}]}
        f = tmp_path / "approved.json"
        f.write_text(json.dumps(data))
        result = load_approved_servers(f)
        assert result == {"postgres-mcp", "github-mcp"}

    def test_load_from_flat_list(self, tmp_path: Path):
        data = ["postgres-mcp", "github-mcp"]
        f = tmp_path / "approved.json"
        f.write_text(json.dumps(data))
        result = load_approved_servers(f)
        assert result == {"postgres-mcp", "github-mcp"}

    def test_load_missing_file(self):
        result = load_approved_servers(Path("/nonexistent/path.json"))
        assert result == set()

    def test_load_none(self):
        result = load_approved_servers(None)
        assert result == set()

    def test_load_invalid_json(self, tmp_path: Path):
        f = tmp_path / "bad.json"
        f.write_text("not json at all")
        result = load_approved_servers(f)
        assert result == set()


# ---------------------------------------------------------------------------
# Config scanner tests
# ---------------------------------------------------------------------------


class TestScanConfig:
    """Tests for config_scanner.scan_config with mocked filesystem."""

    def test_scan_json_config(self, tmp_path: Path):
        config = {
            "mcpServers": {
                "postgres": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-postgres"],
                    "env": {"PGHOST": "localhost", "PGPASSWORD": "secret"},
                },
                "github": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-github"],
                    "env": {"GITHUB_TOKEN": "ghp_test"},
                },
            }
        }

        config_path = tmp_path / "mcp.json"
        config_path.write_text(json.dumps(config))

        descriptor = {
            "client_name": "Cursor",
            "config_path": config_path,
            "root_key": "mcpServers",
            "description": "test config",
        }

        findings = scan_config(descriptor)

        assert len(findings) == 2
        names = {f["server_name"] for f in findings}
        assert names == {"postgres", "github"}

        # Check structure of a finding
        pg = next(f for f in findings if f["server_name"] == "postgres")
        assert pg["client_name"] == "Cursor"
        assert pg["transport"] == "stdio"
        assert "npx" in pg["command_or_url"]
        assert pg["env_vars"]["PGPASSWORD"] == "secret"
        assert pg["scanner"] == "config"

    def test_scan_missing_config(self, tmp_path: Path):
        descriptor = {
            "client_name": "Cursor",
            "config_path": tmp_path / "does-not-exist.json",
            "root_key": "mcpServers",
            "description": "missing",
        }
        findings = scan_config(descriptor)
        assert findings == []

    def test_scan_empty_servers(self, tmp_path: Path):
        config_path = tmp_path / "mcp.json"
        config_path.write_text(json.dumps({"mcpServers": {}}))

        descriptor = {
            "client_name": "Test",
            "config_path": config_path,
            "root_key": "mcpServers",
            "description": "empty",
        }
        findings = scan_config(descriptor)
        assert findings == []

    def test_scan_wrong_root_key(self, tmp_path: Path):
        config_path = tmp_path / "mcp.json"
        config_path.write_text(json.dumps({"servers": {"x": {"command": "y"}}}))

        descriptor = {
            "client_name": "Test",
            "config_path": config_path,
            "root_key": "mcpServers",
            "description": "wrong key",
        }
        findings = scan_config(descriptor)
        assert findings == []

    def test_scan_sse_transport(self, tmp_path: Path):
        config = {
            "mcpServers": {
                "remote": {"url": "https://remote.example.com/sse/mcp"},
            }
        }
        config_path = tmp_path / "mcp.json"
        config_path.write_text(json.dumps(config))

        descriptor = {
            "client_name": "Claude Desktop",
            "config_path": config_path,
            "root_key": "mcpServers",
            "description": "sse test",
        }
        findings = scan_config(descriptor)
        assert len(findings) == 1
        assert findings[0]["transport"] == "sse"
        assert findings[0]["command_or_url"] == "https://remote.example.com/sse/mcp"

    def test_scan_http_transport(self, tmp_path: Path):
        config = {
            "mcpServers": {
                "api": {"url": "http://localhost:8080/mcp"},
            }
        }
        config_path = tmp_path / "mcp.json"
        config_path.write_text(json.dumps(config))

        descriptor = {
            "client_name": "VS Code",
            "config_path": config_path,
            "root_key": "mcpServers",
            "description": "http test",
        }
        findings = scan_config(descriptor)
        assert len(findings) == 1
        assert findings[0]["transport"] == "http"

    def test_scan_malformed_json(self, tmp_path: Path):
        config_path = tmp_path / "mcp.json"
        config_path.write_text("{broken json")

        descriptor = {
            "client_name": "Test",
            "config_path": config_path,
            "root_key": "mcpServers",
            "description": "broken",
        }
        findings = scan_config(descriptor)
        assert findings == []


class TestScanAllConfigs:
    """Tests for config_scanner.scan_all_configs with explicit descriptors."""

    def test_aggregates_from_multiple_configs(self, tmp_path: Path):
        # Config A
        config_a = tmp_path / "a.json"
        config_a.write_text(json.dumps({
            "mcpServers": {"server-a": {"command": "npx", "args": ["a"]}}
        }))

        # Config B
        config_b = tmp_path / "b.json"
        config_b.write_text(json.dumps({
            "servers": {"server-b": {"command": "npx", "args": ["b"]}}
        }))

        descriptors = [
            {
                "client_name": "ClientA",
                "config_path": config_a,
                "root_key": "mcpServers",
                "description": "A",
            },
            {
                "client_name": "ClientB",
                "config_path": config_b,
                "root_key": "servers",
                "description": "B",
            },
        ]

        findings = scan_all_configs(descriptors)
        assert len(findings) == 2
        names = {f["server_name"] for f in findings}
        assert names == {"server-a", "server-b"}
