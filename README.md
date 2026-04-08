# Spectis

**AI Observability Platform for Enterprise Security Teams**

See every agent. Know every action. Trust every outcome.

---

## What Is This?

Spectis gives security teams unified visibility into AI agent activity across **all clients** (VS Code, Cursor, Claude, Codex, Windsurf, Zed, JetBrains, and 14 more), **all model providers** (OpenAI, Anthropic, Google), and **all tool ecosystems** (MCP servers, function calling, plugins).

It is **not a gateway or proxy** — it observes and correlates with zero latency impact.

```
┌─────────────────────────────────────────────────────────────┐
│                    Spectis Dashboard                      │
├─────────────────────────────────────────────────────────────┤
│                   Correlation Engine                         │
│        Joins by: username × hostname × timestamp × agent    │
├──────────────┬──────────────┬────────────┬──────────────────┤
│  Endpoint    │ Orchestrator │  Provider  │    Network       │
│  Agent       │    Hooks     │  Audit Logs│   Telemetry      │
│              │              │            │                  │
│  21 clients  │  Agent ID    │  API logs  │  Zscaler/FW      │
│  MCP scanner │  User ID     │  Token use │  DNS logs        │
│  Process mon │  Tool calls  │            │                  │
│  Tool prober │  Sessions    │            │                  │
└──────────────┴──────────────┴────────────┴──────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for dashboard)
- Docker (optional, for PostgreSQL)

### Option 1: Run locally (fastest)

```bash
# Clone
git clone https://github.com/bytebunkerlabs/spectis.git
cd spectis

# Create Python virtual environment
python3 -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows

# Install orchestrator
cd orchestrator
pip install -e ".[dev]"

# Start API (uses SQLite — no database setup needed)
DATABASE_URL="sqlite+aiosqlite:///./spectis.db" uvicorn app.main:app --host 0.0.0.0 --port 8000

# The API is now running at http://localhost:8000
# Auto-generated API docs at http://localhost:8000/docs
```

In a second terminal:

```bash
# Install and start dashboard
cd dashboard
npm install
npm run dev

# Dashboard is now at http://localhost:5173
```

In a third terminal:

```bash
# Install and run endpoint agent
source .venv/bin/activate
cd agent
pip install -e .

# Run a scan (no orchestrator needed — saves local report)
spectis-agent scan

# Run a scan and report to orchestrator
spectis-agent scan --orchestrator-url http://localhost:8000 --api-key <your-key>

# Run with MCP tool discovery (admin-controlled)
spectis-agent scan --discover-tools --orchestrator-url http://localhost:8000 --api-key <your-key>
```

### Option 2: Docker Compose

```bash
docker compose up -d          # Starts orchestrator + PostgreSQL
# Dashboard: http://localhost:8000
# API docs:  http://localhost:8000/docs
```

### Option 3: Kubernetes (Helm)

```bash
helm install spectis ./helm/spectis -n spectis --create-namespace
kubectl port-forward svc/spectis 8000:8000 -n spectis
```

### First Steps After Starting

```bash
# 1. Register an admin user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","email":"admin@example.com","password":"changeme","role":"admin"}'

# 2. Login to get a JWT token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"changeme"}'
# → Returns {"access_token": "eyJ..."}

# 3. Register the endpoint scanner agent
curl -X POST http://localhost:8000/api/agents \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"name":"endpoint-scanner","agent_type":"scanner","owner":"admin@example.com"}'

# 4. Approve it and generate an API key
curl -X PATCH http://localhost:8000/api/agents/<agent-id> \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"status":"approved"}'

curl -X POST http://localhost:8000/api/agents/<agent-id>/api-key \
  -H "Authorization: Bearer <token>"
# → Returns {"api_key": "aw_..."}  (store this — shown once)

# 5. Run the endpoint scanner
spectis-agent scan --orchestrator-url http://localhost:8000 --api-key aw_...

# 6. Open the dashboard and login
open http://localhost:5173
```

## What the Endpoint Agent Scans

The agent scans **21 MCP clients** across macOS, Windows, and Linux:

| Category | Clients |
|----------|---------|
| **IDEs** | VS Code, VS Code Insiders, Cursor, Windsurf, Zed, JetBrains (all products) |
| **VS Code Extensions** | Cline, Roo Code, Continue, Augment Code |
| **AI Desktop Apps** | Claude Desktop, ChatGPT, BoltAI, LM Studio |
| **CLI Tools** | Claude Code, Codex CLI, Gemini CLI, Amazon Q CLI, Goose, Warp |

For each client, it detects:
- **Configured MCP servers** — server name, package, runtime (Docker/npx/uvx), local vs remote
- **Running MCP processes** — deduplicated, with endpoint detection
- **MCP tool inventory** — via protocol probing (admin-controlled `--discover-tools` flag)

**Security by design:**
- Never collects credential values (only env var names)
- Never captures raw command lines (strips tokens, auth headers)
- Classifies servers as local (safe) vs remote (data exfiltration risk)
- Flags servers with credentials in their configuration

## Architecture

```
spectis/
├── orchestrator/         # FastAPI API server
│   ├── app/
│   │   ├── main.py       # App entry, middleware, static files
│   │   ├── auth.py       # JWT + API key authentication
│   │   ├── models/       # SQLAlchemy ORM (User, Agent, AuditLog, ScanResult, McpServer)
│   │   ├── schemas/      # Pydantic request/response models
│   │   ├── routers/      # API routes (auth, agents, audit, reports, servers, ws)
│   │   └── services/     # Business logic (validator, orchestrator, audit_logger)
│   ├── alembic/          # Database migrations
│   └── tests/            # pytest test suite
├── agent/                # Cross-platform endpoint scanner
│   └── spectis_agent/
│       ├── cli.py        # Typer CLI (scan, watch, version)
│       ├── platforms/    # OS-specific config paths (macOS, Windows, Linux)
│       ├── scanners/     # Config, process, network, workspace, tool prober
│       ├── reporters/    # API + file reporters
│       └── scoring.py    # Risk scoring engine
├── dashboard/            # React + Tailwind + TypeScript
│   └── src/
│       ├── pages/        # Overview, LiveFeed, Agents, Scans, Servers
│       ├── components/   # Layout, LoginForm
│       └── api/          # API client, WebSocket hook
├── helm/spectis/      # Kubernetes Helm chart
├── docker-compose.yml    # Local dev (API + PostgreSQL)
├── Makefile              # Common commands
└── scripts/seed_demo.py  # Generate 500 endpoints of demo data
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| API | Python 3.11+, FastAPI, async SQLAlchemy, Pydantic v2 |
| Database | PostgreSQL 16 (prod) / SQLite (dev) |
| Endpoint Agent | Python, Typer CLI, psutil, MCP SDK |
| Dashboard | React 18, Tailwind CSS, Vite, TypeScript |
| Auth | JWT (HS256) for users, `aw_` API keys for agents |
| Deployment | Helm chart, Docker Compose |

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /api/health | None | Health check |
| POST | /api/auth/register | None | Register user |
| POST | /api/auth/login | None | Login, get JWT |
| GET | /api/auth/me | JWT | Current user |
| GET/POST | /api/agents | JWT | List/create agents |
| PATCH | /api/agents/{id} | JWT | Update agent status |
| DELETE | /api/agents/{id} | JWT (admin) | Retire agent |
| POST | /api/agents/{id}/api-key | JWT (admin) | Generate API key |
| POST | /api/prompt | JWT/API key | Route prompt to agent |
| POST | /api/validate | JWT/API key | Validate command |
| POST | /api/execute | JWT/API key | Execute via agent |
| GET | /api/history | JWT/API key | Audit log (filterable) |
| GET | /api/stats | JWT/API key | Dashboard statistics |
| POST | /api/report | API key | Submit endpoint scan |
| GET | /api/scans | JWT/API key | List scan results |
| GET | /api/servers | JWT/API key | MCP server registry |
| GET | /api/servers/inventory | JWT/API key | Governance: User → Client → Server → Tools |
| WS | /ws/feed | None | Real-time event stream |

## Development

```bash
# Run tests
cd orchestrator && python -m pytest tests/ -v

# Lint
cd orchestrator && python -m ruff check app/
cd agent && python -m ruff check spectis_agent/

# Type check dashboard
cd dashboard && npx tsc --noEmit

# Generate demo data (500 endpoints)
python scripts/seed_demo.py

# All common commands
make help
```

## Security Principles

- **No secrets collected** — agent captures env var names only, never values
- **No raw command lines** — strips tokens, auth headers, bearer tokens from process data
- **Local vs remote classification** — Docker containers = local, external URLs = remote (exfiltration risk)
- **Dual auth** — JWT for humans, API keys for machines
- **Three-lane enforcement** — approved (fast), pending (inspect), blocked (deny)
- **Dual audit logging** — PostgreSQL (queryable) + JSONL (archival)
- **Admin-controlled tool probing** — `--discover-tools` flag, not default

## License

Apache 2.0

## Contributing

See [CLAUDE.md](CLAUDE.md) for architecture details and code standards.
