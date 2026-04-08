# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

Spectis is an AI observability platform for enterprise security teams. It correlates telemetry from three planes — external API calls, internal network (MCP servers), and local endpoint (processes, config files) — to give unified visibility into AI agent activity across all clients and providers.

**This is NOT a gateway or proxy.** It observes and correlates — zero latency impact, no conflict with existing SASE/proxy infrastructure.

## Build & Run Commands

```bash
# === Quick Start (local dev, SQLite) ===
python3 -m venv .venv && source .venv/bin/activate
cd orchestrator && pip install -e ".[dev]"
DATABASE_URL="sqlite+aiosqlite:///./spectis.db" uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Dashboard (separate terminal)
cd dashboard && npm install && npm run dev    # Dev server at :5173, proxies /api to :8000

# Endpoint agent (separate terminal)
cd agent && pip install -e .
spectis-agent scan                         # Local scan only
spectis-agent scan --orchestrator-url http://localhost:8000 --api-key aw_...
spectis-agent scan --discover-tools ...    # Admin: probe MCP servers for tool lists

# === Docker Compose (PostgreSQL) ===
docker compose up -d                          # Orchestrator + PostgreSQL
docker compose logs -f

# === Testing ===
cd orchestrator && python -m pytest tests/ -v
cd dashboard && npx tsc --noEmit

# === Linting ===
cd orchestrator && python -m ruff check app/ tests/
cd agent && python -m ruff check spectis_agent/ tests/

# === Helm ===
helm template spectis ./helm/spectis
helm install spectis ./helm/spectis -n spectis --create-namespace

# === Demo data (500 endpoints) ===
python scripts/seed_demo.py

# === All commands ===
make help
```

## Architecture

### Tech Stack
| Component | Technology |
|-----------|-----------|
| Orchestrator API | Python (FastAPI) + async SQLAlchemy |
| Database | PostgreSQL 16 (prod) / SQLite (dev) |
| Endpoint Agent | Python (Typer CLI + psutil + MCP SDK) |
| Dashboard | React 18 + Tailwind CSS + Vite + TypeScript |
| Auth | JWT (HS256) for users, API keys (aw_...) for agents |
| Audit Logs | Dual: JSONL files + database |
| Deployment | Helm chart on Kubernetes, Docker Compose for dev |

### Key Design Patterns

**Dual Auth** (`app/auth.py`): JWT bearer tokens for human users (dashboard), `aw_` prefixed API keys for machine-to-machine (endpoint agents). Both validated via `get_current_user` dependency.

**Three-Lane Enforcement** (`app/routers/audit.py:execute`):
- Fast lane: `agent.status == "approved"` → validate command → dispatch
- Inspection lane: `agent.status == "pending_review"` → queue
- Blocked lane: `agent.status == "blocked"` → 403

**Dual Audit Logging** (`app/services/audit_logger.py`): Every event writes to both database (queryable) and JSONL files (archival). JSONL is best-effort — DB is source of truth.

**Command Validation** (`app/services/validator.py`): Strips quoted strings before regex matching to prevent false positives. Validates against agent's allowed_commands allowlist and blocked_verbs denylist.

**Cross-Platform Agent** (`agent/spectis_agent/platforms/`): `platform.system()` dispatches to OS-specific modules. Single codebase, 21 MCP clients scanned across macOS/Windows/Linux.

**Security-First Scanner**: Never collects credential values (env var names only), never captures raw command lines (strips tokens/auth headers), classifies local vs remote for data exfiltration risk.

**MCP Tool Discovery** (`agent/spectis_agent/scanners/tool_prober.py`): Uses the MCP Python SDK to start temp server instances, send `initialize` + `tools/list`, capture tool catalog, then kill. Admin-controlled via `--discover-tools` flag. Only probes STDIO servers; skips HTTP/SSE (need auth).

### API Endpoints
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /api/health | None | Health check |
| POST | /api/auth/register | None | Register user |
| POST | /api/auth/login | None | Get JWT token |
| GET | /api/auth/me | JWT | Current user info |
| GET/POST | /api/agents | JWT | List/create agents |
| PATCH | /api/agents/{id} | JWT (admin/operator) | Update agent |
| DELETE | /api/agents/{id} | JWT (admin) | Retire agent |
| POST | /api/agents/{id}/api-key | JWT (admin) | Generate API key |
| POST | /api/prompt | JWT/API key | Route prompt to agent |
| POST | /api/validate | JWT/API key | Validate command |
| POST | /api/execute | JWT/API key | Execute via agent |
| GET | /api/history | JWT/API key | Audit log with filters |
| GET | /api/stats | JWT/API key | Dashboard statistics |
| POST | /api/report | API key | Submit endpoint scan |
| GET | /api/scans | JWT/API key | List scan results |
| DELETE | /api/scans/{id} | JWT | Delete scan |
| GET | /api/servers | JWT/API key | MCP server registry |
| GET | /api/servers/inventory | JWT/API key | Governance hierarchy |
| GET | /api/servers/{id} | JWT/API key | Server detail |
| WS | /ws/feed | None | Real-time event stream |

### MCP Clients Scanned (21)
| Category | Clients |
|----------|---------|
| IDEs | VS Code, VS Code Insiders, Cursor, Windsurf, Zed, JetBrains (all products) |
| VS Code Extensions | Cline, Roo Code, Continue |
| AI Desktop Apps | Claude Desktop, ChatGPT, BoltAI, LM Studio |
| CLI Tools | Claude Code, Codex CLI, Gemini CLI, Amazon Q CLI, Goose, Warp |

### Database Models
- `User` — username, email, password_hash, role (admin/operator/viewer)
- `Agent` — name, type, owner, status, permissions (allowed_commands, blocked_verbs), api_key_hash
- `AuditLog` — agent_id, user_id, session_id, action, command, result, risk_level, timestamp
- `ScanResult` — hostname, os_platform, config/process/network/workspace findings, risk counts, locality counts, clients_detected
- `McpServer` — server_name, package, runtime, locality, tools (JSON), probe_status, clients, endpoints_seen

## Code Standards

- **Security-first**: no secrets collected, no raw cmdlines stored
- **Attribution**: every action traceable to both agent and human
- **SQLAlchemy async ORM** for all database operations
- **Pydantic v2** for all request/response validation
- **FastAPI dependency injection** for auth, DB sessions
- **All credentials via environment variables**, never hardcoded
- Python 3.11+, ruff for linting, pytest for testing
- TypeScript strict mode for dashboard

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_URL | postgresql+asyncpg://... | Database connection string |
| JWT_SECRET_KEY | (required) | Secret for JWT signing (min 32 chars) |
| JWT_EXPIRE_MINUTES | 60 | Token expiry |
| CORS_ORIGINS | * | Comma-separated allowed origins |
| AUDIT_LOG_DIR | ./logs | JSONL audit log directory |
