# ULTRAPLAN: Spectis

## What is Spectis

Spectis is an open-source AI agent observability platform built by ByteBunker Labs. It gives enterprise security teams unified visibility into AI agent activity across the three planes that no single security tool can see today: the external API plane, the internal network plane, and the endpoint plane. Spectis observes without intercepting — it never sits in the data path, adds zero latency to AI workflows, and ships everything to whatever SIEM the organization already runs.

The repo lives at github.com/Byte-Bunker-Labs/spectis. License is Apache 2.0. Author is Mohammed Ashraf. Company brand is ByteBunker Labs at bytebunkerlabs.ai.

---

## Spectis Registry

A curated catalog of approved MCP servers for the organization. Security teams add servers, set version pins, define permission scopes, and attach credential policies. Developers browse what's available, see what each server does, and know it's been vetted before they ever touch it. Think of it as an internal app store for AI tooling — except security controls what's on the shelf.

Each server in the registry has a name, description, version, package name, transport type, category, status, list of exposed tools, scoped permissions, credential policy, and a risk score. Servers can be approved, pending review, deprecated, or blocked. The registry tracks who approved each server and when.

Categories include database, security, devtools, cloud, and custom. The registry should be searchable and filterable by category, status, and risk level. Each server card shows install count — how many endpoints across the org have it installed.

---

## One-Click Install

A developer picks a server from the registry, chooses their AI client from a dropdown, and Spectis generates the exact config block they need. It handles the format differences between clients automatically. Credentials come pre-scoped from the organization's vault — developers never see raw tokens or connection strings. No more copying JSON between Slack threads and hoping the format is right.

The dropdown should support every major AI client: VS Code, VS Code Insiders, Cursor, Claude Desktop, Claude Code (global, user, and managed), Codex CLI, Windsurf, Zed, JetBrains IDEs, Augment, Cline, Roo Code, Amazon Q, Gemini CLI, Continue, Copilot CLI, GitHub Copilot in VS Code, Amp, and Kilo Code. Each client has a different config file path depending on the operating system, and some use different root keys — VS Code uses "servers" while most others use "mcpServers", Codex CLI uses TOML with "mcp_servers", and Zed uses "context_servers". Spectis needs to know all of these and generate the correct format for each.

Two install methods should be supported. First, copy to clipboard — the developer pastes the config block into their config file manually. Second, agent push — if the Spectis endpoint agent is running on the developer's workstation, it writes the config directly to the correct file path and confirms back to the server. After any install, the installation is recorded with a hash of the config block so drift can be detected later.

---

## Endpoint Agent

A lightweight agent that runs on developer workstations across Windows, macOS, and Linux. It can run as a one-shot scan, as a daemon that scans on an interval, or as a system service. The agent performs five scan passes on every run.

First, config file scan — it reads all known AI client config paths for the current operating system, parses the JSON or TOML, and extracts every MCP server definition including its args, environment variables, and transport type.

Second, workspace scan — it traverses common workspace directories looking for project-level MCP configs that override user-level settings. These include .vscode/mcp.json, .cursor/mcp.json, .mcp.json, .claude/settings.json, and .claude/settings.local.json.

Third, process scan — it enumerates all running processes and matches command lines against known MCP server signatures. Patterns include @modelcontextprotocol packages, mcp-server prefixes, fastmcp, and transport flags like stdio and --mcp. For each match, it identifies the parent process to determine which AI client spawned it.

Fourth, network listener scan — it finds TCP connections in LISTEN state from MCP-compatible runtimes like node, python, uvx, npx, deno, and bun on non-standard ports. This detects HTTP and SSE-based MCP servers.

Fifth, tool discovery — for each detected MCP server, the agent attempts to connect and call tools/list to enumerate the actual tools the server exposes. This provides the real capability surface, not just what the config says.

The agent registers itself with the Spectis API on first run, submits scan results after every scan, and can maintain a persistent connection for real-time push commands like triggering an immediate scan or receiving a config to install.

---

## Drift Detection

Spectis knows what should be on every workstation because it controls what gets installed. After every scan, the endpoint agent's results are compared against the registry state. Any difference between what should be there and what actually is there generates a drift event.

The drift types are: unapproved server — a server was found that isn't in the registry. Config modified — an approved server's configuration was changed from what the registry expects. Version mismatch — the installed version doesn't match the registry's pinned version. Credential change — the credentials for a server were modified. Project override — a project-level config is overriding the user-level approved config. Server removed — an expected server from the registry is no longer found on the endpoint.

Each drift event has a severity — high for unapproved servers and credential changes, medium for config modifications and version mismatches, low for server removals. Drift events can be resolved by a security team member, either by approving the change, reverting it, or acknowledging it. The dashboard should show drift trends over time so the security team can see if drift is increasing or decreasing across the organization.

---

## GitHub Intelligence

Spectis crawls public GitHub to build a living index of every MCP server, agent config, and instruction file in the wild. This is supply chain security for the agentic era.

The public crawler runs on a schedule and searches GitHub's code search API for patterns that indicate MCP servers — things like the modelcontextprotocol SDK in package.json files, fastmcp in Python dependency files, MCP server class imports in source code, and mcpServers keys in config files. For each discovered repo, Spectis records the owner, stars, last commit, license, dependencies, and attempts to extract what tools the server exposes and what external services it calls. Every discovered server gets a risk score.

For enterprise organizations, Spectis offers a GitHub App that installs with read access to org repos. It scans all repos for committed MCP configuration files, agent instruction files like CLAUDE.md and .cursorrules and .github/copilot-instructions.md, and any file containing API keys, connection strings, or tokens in an MCP config context. Findings are recorded as config leaks with a severity level. The GitHub App can optionally create issues or pull requests to help developers remediate leaks.

Before a developer installs any MCP server, the security team can check the Spectis index to see who published it, what tools it exposes, what external services it calls, and whether it's been flagged. This is pre-deployment risk intelligence.

---

## Risk Scoring

Every MCP server — whether in the registry, on a developer's workstation, or discovered on GitHub — gets a risk score from 0 to 100. The score considers whether the server is in the approved registry, whether its config contains credential environment variables like tokens and keys, whether it connects to external endpoints outside the organization's network, whether the publisher is known or new, whether the server has tools that can write or delete data, how many tools it exposes, how recently it was published, and whether it has a license.

Approved servers in the registry get their score reduced. Servers that have been manually audited get a further reduction. The tiers are: 0-25 is low risk, 26-50 is medium, 51-75 is high, and 76-100 is critical. The scoring model should be configurable so organizations can adjust weights based on their own risk appetite.

---

## Agent Identity and Registry

Every autonomous agent that runs in the organization gets a registered identity with five properties. Registered identity — the agent exists in a registry before it executes, with a unique ID, name, version, and accountable human owner. Delegation chain — every action is attributed to both the agent and the human who invoked it, preserving the full causal chain from user to AI client to agent to tool call. Scoped permissions — the agent's capabilities are enforced by infrastructure through allowed and blocked tool lists, not by LLM instructions that can be overridden. Ephemeral credentials — short-lived tokens per session with no standing credentials. Full traceability — every tool call is logged with agent, user, and session identifiers.

Agents are assigned to one of three enforcement lanes. The fast lane is for registered and approved agents — the system performs a microsecond policy lookup and permits or denies execution instantly with no LLM evaluation. The inspection lane is for unregistered or new agents — execution is permitted but the session is queued for async safety LLM evaluation. The blocked lane is for explicitly denied actions — instant rejection with zero overhead. The agent's registered identity determines which lane it enters.

---

## Safety LLM

An async evaluator that analyzes agent sessions for behavioral patterns that rule-based detection would miss. Unlike static command validation which catches individual bad commands, the safety LLM evaluates session-level intent — whether a sequence of tool calls, taken together, is consistent with the agent's registered purpose.

Patterns it should detect include: reconnaissance, where an agent systematically enumerates administrative accounts or resources across multiple queries. Data exfiltration via read-only access, where an agent aggregates sensitive data across multiple systems using only read permissions. Privilege creep, where an agent progressively expands its data access scope within a single session. Prompt injection, where a prompt attempts to override the agent's safety instructions. And general policy violations, where actions fall outside the agent's registered purpose.

The safety LLM operates on completed or in-progress session transcripts, not on individual tool calls. This gives it the contextual window needed to detect multi-step attack patterns. It returns a safety score and any flagged patterns. High-risk sessions trigger alerts through the dashboard and SIEM export.

---

## Orchestrator

The orchestrator receives tool calls from registered agents and validates them against the agent's permission set stored in the registry. For read-only agents, it blocks write operations using verb pattern matching — Set, New, Remove, Add, Enable, Disable, Grant, Revoke prefixed commands. It strips quoted strings and string literals from commands before applying pattern matching to avoid false positives on decorative text inside commands.

Every decision — permit or deny — is logged with the full delegation chain: which user initiated, which AI client was used, which agent executed, what tool was called, what arguments were passed, and what was returned. This enables forensic reconstruction of any incident.

---

## SIEM Integration

Everything Spectis observes — registry changes, installs, drift events, scan results, agent sessions, tool calls, safety evaluations — ships as structured telemetry to the organization's existing SIEM. Supported targets include Splunk via HTTP Event Collector, Microsoft Sentinel via the Log Analytics HTTP Data Collector API, syslog in Common Event Format for any SIEM, generic HTTP webhook for custom integrations, and JSON-lines file output for offline ingestion.

Every telemetry event includes shared identity keys — username, hostname, agent ID, and session ID — so the SOC can correlate AI agent activity with endpoint, network, and identity telemetry they already have. No new dashboard to monitor. Analysts work where they already work.

---

## Dashboard

A unified web interface for security teams. The overview page shows platform-wide stats — total endpoints scanned, MCP servers discovered, open drift events, registered agents, and high-risk findings. It includes a risk distribution chart, a real-time activity feed, AI client distribution across the org, and drift trends over time.

The registry page shows the server catalog with install buttons, filters by category and risk level, and admin forms for adding and approving servers. The endpoints page lists all workstations with their scan history, installed servers, and drift events. The drift page shows all drift events filterable by severity, type, and resolution status. The agents page shows registered agents with their lane assignments, sessions, and safety scores. The GitHub page shows the public MCP server index and org scan results with config leak findings.

The dashboard should receive real-time updates via WebSocket so the activity feed, drift alerts, and scan results appear immediately without polling.

---

## Design and Branding

Colors use the phthalo green palette: #0B3D2E as the darkest, #14705C, #1A8F74, #7DD3C0, #A8E6CF as the lightest, and cream #FAFBF9 for backgrounds. Fonts are Chakra Petch for headings and display text, DM Sans for body and UI text. The logo is a shield shape with an open top, binary data inside, and bubbles rising out — representing security, data, and observability. Dashboard style should be clean, minimal, and data-dense with a dark sidebar and light content area.

---

## Core Principles

Observe, do not intercept. Spectis never sits in the data path. Zero latency impact on AI workflows. A failure in the observability platform must never disrupt developer workflows.

Vendor neutral. Works with any AI client, any MCP server, any SIEM. No vendor lock-in.

Developer friendly. The registry and install flow should make developers' lives easier, not harder. If security becomes friction, adoption dies.

Open source core. Everything described here is Apache 2.0. Future paid tiers add SSO, RBAC, multi-tenant isolation, managed SIEM connectors, and SLA support.
