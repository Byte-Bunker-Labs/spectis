"""Seed the Spectis database with realistic demo data.

Generates 500 endpoints across multiple departments, each with
a mix of AI clients and MCP servers. Creates realistic scan reports
and populates the MCP server registry with tool inventories.
"""

import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone

import httpx

BASE_URL = "http://localhost:8000"
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

# --- Realistic MCP server catalog ---

MCP_SERVERS = [
    # Official MCP servers
    {"name": "filesystem", "package": "@modelcontextprotocol/server-filesystem", "runtime": "npx", "transport": "stdio", "locality": "local",
     "tools": [{"name": "read_file", "description": "Read file contents", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
               {"name": "write_file", "description": "Write content to file", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
               {"name": "list_directory", "description": "List directory contents", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
               {"name": "search_files", "description": "Search for files by pattern", "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}, "path": {"type": "string"}}, "required": ["pattern"]}},
               {"name": "edit_file", "description": "Edit file with line-based changes", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "edits": {"type": "array"}}, "required": ["path", "edits"]}}]},
    {"name": "github", "package": "@modelcontextprotocol/server-github", "runtime": "npx", "transport": "stdio", "locality": "local",
     "env_vars": ["GITHUB_PERSONAL_ACCESS_TOKEN"],
     "tools": [{"name": "create_or_update_file", "description": "Create or update a file in a repo", "input_schema": {"type": "object", "properties": {"owner": {"type": "string"}, "repo": {"type": "string"}, "path": {"type": "string"}}, "required": ["owner", "repo", "path"]}},
               {"name": "search_repositories", "description": "Search GitHub repositories", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
               {"name": "create_issue", "description": "Create a new issue", "input_schema": {"type": "object", "properties": {"owner": {"type": "string"}, "repo": {"type": "string"}, "title": {"type": "string"}}, "required": ["owner", "repo", "title"]}},
               {"name": "list_commits", "description": "List commits on a branch", "input_schema": {"type": "object", "properties": {"owner": {"type": "string"}, "repo": {"type": "string"}}, "required": ["owner", "repo"]}},
               {"name": "create_pull_request", "description": "Create a pull request", "input_schema": {"type": "object", "properties": {"owner": {"type": "string"}, "repo": {"type": "string"}, "title": {"type": "string"}, "head": {"type": "string"}, "base": {"type": "string"}}, "required": ["owner", "repo", "title", "head", "base"]}}]},
    {"name": "postgres-mcp", "package": "postgres-mcp:1.6.0-audit", "runtime": "docker", "transport": "stdio", "locality": "local",
     "env_vars": ["PG_HOST", "PG_PORT", "PG_NAME", "PG_USER", "PG_PASSWORD"],
     "tools": [{"name": "query", "description": "Execute a read-only SQL query", "input_schema": {"type": "object", "properties": {"sql": {"type": "string"}}, "required": ["sql"]}},
               {"name": "list_tables", "description": "List all tables in database", "input_schema": {"type": "object", "properties": {}}},
               {"name": "describe_table", "description": "Get table schema", "input_schema": {"type": "object", "properties": {"table": {"type": "string"}}, "required": ["table"]}}]},
    {"name": "sqlserver-mcp", "package": "sqlserver-mcp:1.2.0-audit", "runtime": "docker", "transport": "stdio", "locality": "local",
     "env_vars": ["MSSQL_HOST", "MSSQL_PORT", "MSSQL_NAME", "MSSQL_USER", "MSSQL_PASSWORD"],
     "tools": [{"name": "query", "description": "Execute a read-only SQL query", "input_schema": {"type": "object", "properties": {"sql": {"type": "string"}}, "required": ["sql"]}},
               {"name": "list_tables", "description": "List all tables", "input_schema": {"type": "object", "properties": {}}},
               {"name": "describe_table", "description": "Get table schema", "input_schema": {"type": "object", "properties": {"table": {"type": "string"}}, "required": ["table"]}}]},
    {"name": "gitguardian-mcp", "package": "gitguardian-mcp:0.5.0", "runtime": "docker", "transport": "stdio", "locality": "local",
     "env_vars": ["GITGUARDIAN_URL", "GITGUARDIAN_PERSONAL_ACCESS_TOKEN"],
     "tools": [{"name": "scan_repository", "description": "Scan repo for secrets", "input_schema": {"type": "object", "properties": {"repo_url": {"type": "string"}}, "required": ["repo_url"]}},
               {"name": "list_incidents", "description": "List security incidents", "input_schema": {"type": "object", "properties": {"status": {"type": "string"}}}},
               {"name": "get_incident_details", "description": "Get incident details", "input_schema": {"type": "object", "properties": {"incident_id": {"type": "string"}}, "required": ["incident_id"]}}]},
    {"name": "snyk-mcp", "package": "snyk@latest", "runtime": "npx", "transport": "stdio", "locality": "local",
     "env_vars": ["SNYK_TOKEN"],
     "tools": [{"name": "test_project", "description": "Test project for vulnerabilities", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
               {"name": "list_issues", "description": "List known vulnerabilities", "input_schema": {"type": "object", "properties": {"org_id": {"type": "string"}}}},
               {"name": "monitor", "description": "Monitor project for new vulns", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}]},
    {"name": "mcp-msdefenderkql", "package": "mcp-msdefenderkql", "runtime": "uvx", "transport": "stdio", "locality": "local",
     "env_vars": ["AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET"],
     "tools": [{"name": "run_hunting_query", "description": "Run KQL hunting query in Defender", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "timespan": {"type": "string"}}, "required": ["query"]}},
               {"name": "get_hunting_schema", "description": "Get available tables and columns", "input_schema": {"type": "object", "properties": {}}}]},
    {"name": "splunk-mcp", "package": "mcp-remote", "runtime": "npx", "transport": "stdio", "locality": "remote",
     "endpoint": "https://es-lalog.splunkcloud.com:8089/services/mcp",
     "env_vars": ["SPLUNK_MCP_TOKEN"],
     "tools": [{"name": "search", "description": "Run Splunk SPL search", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "earliest": {"type": "string"}, "latest": {"type": "string"}}, "required": ["query"]}},
               {"name": "list_indexes", "description": "List available indexes", "input_schema": {"type": "object", "properties": {}}},
               {"name": "get_saved_searches", "description": "Get saved searches", "input_schema": {"type": "object", "properties": {}}}]},
    {"name": "notion-mcp", "package": "notion-mcp-server", "runtime": "npx", "transport": "sse", "locality": "remote",
     "endpoint": "https://api.notion.com/mcp",
     "tools": [{"name": "search_pages", "description": "Search Notion pages", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
               {"name": "read_page", "description": "Read page content", "input_schema": {"type": "object", "properties": {"page_id": {"type": "string"}}, "required": ["page_id"]}},
               {"name": "create_page", "description": "Create a new page", "input_schema": {"type": "object", "properties": {"parent_id": {"type": "string"}, "title": {"type": "string"}}, "required": ["parent_id", "title"]}}]},
    {"name": "postman-mcp", "package": "postman-mcp-server", "runtime": "npx", "transport": "http", "locality": "remote",
     "endpoint": "https://api.postman.com/mcp",
     "tools": [{"name": "list_collections", "description": "List Postman collections", "input_schema": {"type": "object", "properties": {}}},
               {"name": "run_collection", "description": "Run a collection", "input_schema": {"type": "object", "properties": {"collection_id": {"type": "string"}}, "required": ["collection_id"]}},
               {"name": "get_environment", "description": "Get environment variables", "input_schema": {"type": "object", "properties": {"env_id": {"type": "string"}}, "required": ["env_id"]}}]},
    {"name": "context7", "package": "@upstash/context7-mcp", "runtime": "npx", "transport": "stdio", "locality": "local",
     "tools": [{"name": "resolve-library-id", "description": "Resolve a library name to Context7 ID", "input_schema": {"type": "object", "properties": {"libraryName": {"type": "string"}}, "required": ["libraryName"]}},
               {"name": "get-library-docs", "description": "Get library documentation", "input_schema": {"type": "object", "properties": {"context7CompatibleLibraryID": {"type": "string"}}, "required": ["context7CompatibleLibraryID"]}}]},
    {"name": "markitdown", "package": "markitdown-mcp", "runtime": "uvx", "transport": "stdio", "locality": "local",
     "tools": [{"name": "convert_to_markdown", "description": "Convert document to markdown", "input_schema": {"type": "object", "properties": {"uri": {"type": "string"}}, "required": ["uri"]}}]},
    {"name": "sonarqube-mcp", "package": "sonarqube-mcp:1.0.0", "runtime": "docker", "transport": "stdio", "locality": "local",
     "env_vars": ["SONAR_HOST_URL", "SONAR_TOKEN"],
     "tools": [{"name": "analyze_project", "description": "Analyze project code quality", "input_schema": {"type": "object", "properties": {"project_key": {"type": "string"}}, "required": ["project_key"]}},
               {"name": "get_issues", "description": "Get code quality issues", "input_schema": {"type": "object", "properties": {"project_key": {"type": "string"}, "severity": {"type": "string"}}, "required": ["project_key"]}},
               {"name": "get_quality_gate", "description": "Get quality gate status", "input_schema": {"type": "object", "properties": {"project_key": {"type": "string"}}, "required": ["project_key"]}}]},
    {"name": "jira-mcp", "package": "jira-mcp-server", "runtime": "npx", "transport": "http", "locality": "remote",
     "endpoint": "https://lordabbett.atlassian.net/mcp",
     "env_vars": ["JIRA_API_TOKEN", "JIRA_EMAIL"],
     "tools": [{"name": "search_issues", "description": "Search JIRA issues with JQL", "input_schema": {"type": "object", "properties": {"jql": {"type": "string"}}, "required": ["jql"]}},
               {"name": "create_issue", "description": "Create a JIRA issue", "input_schema": {"type": "object", "properties": {"project": {"type": "string"}, "summary": {"type": "string"}, "type": {"type": "string"}}, "required": ["project", "summary"]}},
               {"name": "get_issue", "description": "Get issue details", "input_schema": {"type": "object", "properties": {"issue_key": {"type": "string"}}, "required": ["issue_key"]}}]},
    {"name": "confluence-mcp", "package": "confluence-mcp-server", "runtime": "npx", "transport": "http", "locality": "remote",
     "endpoint": "https://lordabbett.atlassian.net/wiki/mcp",
     "env_vars": ["CONFLUENCE_API_TOKEN"],
     "tools": [{"name": "search_pages", "description": "Search Confluence pages", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
               {"name": "get_page", "description": "Get page content", "input_schema": {"type": "object", "properties": {"page_id": {"type": "string"}}, "required": ["page_id"]}}]},
    {"name": "slack-mcp", "package": "slack-mcp-server", "runtime": "npx", "transport": "sse", "locality": "remote",
     "endpoint": "https://slack.com/api/mcp",
     "env_vars": ["SLACK_BOT_TOKEN"],
     "tools": [{"name": "send_message", "description": "Send message to channel", "input_schema": {"type": "object", "properties": {"channel": {"type": "string"}, "text": {"type": "string"}}, "required": ["channel", "text"]}},
               {"name": "search_messages", "description": "Search Slack messages", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}]},
    {"name": "azure-devops-mcp", "package": "azure-devops-mcp:1.0.0", "runtime": "docker", "transport": "stdio", "locality": "local",
     "env_vars": ["AZURE_DEVOPS_ORG", "AZURE_DEVOPS_PAT"],
     "tools": [{"name": "list_repos", "description": "List Azure DevOps repos", "input_schema": {"type": "object", "properties": {"project": {"type": "string"}}, "required": ["project"]}},
               {"name": "get_pipeline_runs", "description": "Get pipeline run history", "input_schema": {"type": "object", "properties": {"project": {"type": "string"}, "pipeline_id": {"type": "integer"}}, "required": ["project"]}},
               {"name": "get_work_items", "description": "Query work items", "input_schema": {"type": "object", "properties": {"wiql": {"type": "string"}}, "required": ["wiql"]}}]},
    {"name": "kubernetes-mcp", "package": "k8s-mcp-server", "runtime": "npx", "transport": "stdio", "locality": "local",
     "env_vars": ["KUBECONFIG"],
     "tools": [{"name": "get_pods", "description": "List pods in namespace", "input_schema": {"type": "object", "properties": {"namespace": {"type": "string"}}, "required": ["namespace"]}},
               {"name": "get_logs", "description": "Get pod logs", "input_schema": {"type": "object", "properties": {"namespace": {"type": "string"}, "pod": {"type": "string"}}, "required": ["namespace", "pod"]}},
               {"name": "describe_resource", "description": "Describe a K8s resource", "input_schema": {"type": "object", "properties": {"kind": {"type": "string"}, "name": {"type": "string"}, "namespace": {"type": "string"}}, "required": ["kind", "name"]}}]},
    {"name": "datadog-mcp", "package": "datadog-mcp-server", "runtime": "npx", "transport": "http", "locality": "remote",
     "endpoint": "https://api.datadoghq.com/mcp",
     "env_vars": ["DD_API_KEY", "DD_APP_KEY"],
     "tools": [{"name": "query_metrics", "description": "Query Datadog metrics", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "from": {"type": "integer"}, "to": {"type": "integer"}}, "required": ["query"]}},
               {"name": "search_logs", "description": "Search log entries", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
               {"name": "list_monitors", "description": "List alert monitors", "input_schema": {"type": "object", "properties": {}}}]},
    {"name": "aws-mcp", "package": "aws-mcp-server", "runtime": "npx", "transport": "stdio", "locality": "local",
     "env_vars": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"],
     "tools": [{"name": "list_s3_buckets", "description": "List S3 buckets", "input_schema": {"type": "object", "properties": {}}},
               {"name": "query_cloudwatch", "description": "Query CloudWatch metrics", "input_schema": {"type": "object", "properties": {"namespace": {"type": "string"}, "metric": {"type": "string"}}, "required": ["namespace", "metric"]}},
               {"name": "describe_instances", "description": "Describe EC2 instances", "input_schema": {"type": "object", "properties": {"filters": {"type": "object"}}}}]},
]

# Shadow / unapproved servers that appear on some endpoints
SHADOW_SERVERS = [
    {"name": "chatgpt-retrieval", "package": "chatgpt-retrieval-plugin", "runtime": "npx", "transport": "stdio", "locality": "remote",
     "endpoint": "https://chat.openai.com/retrieval", "env_vars": ["OPENAI_API_KEY"],
     "tools": [{"name": "query_documents", "description": "Query uploaded documents", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}]},
    {"name": "browser-mcp", "package": "browser-mcp", "runtime": "npx", "transport": "stdio", "locality": "remote",
     "endpoint": "https://browserless.io/mcp",
     "tools": [{"name": "browse_url", "description": "Navigate to URL and extract content", "input_schema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}},
               {"name": "screenshot", "description": "Take page screenshot", "input_schema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}}]},
    {"name": "web-search-mcp", "package": "tavily-mcp", "runtime": "npx", "transport": "stdio", "locality": "remote",
     "endpoint": "https://api.tavily.com/mcp", "env_vars": ["TAVILY_API_KEY"],
     "tools": [{"name": "search", "description": "Search the web", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}]},
]

CLIENTS = ["VS Code", "VS Code Insiders", "Claude Desktop", "Claude Code", "Cursor", "Codex CLI", "Windsurf"]
DEPARTMENTS = ["Engineering", "Security", "Data Science", "DevOps", "QA", "Product", "Finance IT", "Compliance"]
OS_PLATFORMS = ["darwin", "windows", "linux"]
OS_WEIGHTS = [0.4, 0.45, 0.15]

# Department -> likely MCP servers
DEPT_SERVER_PROFILES = {
    "Engineering": ["filesystem", "github", "postgres-mcp", "context7", "snyk-mcp", "jira-mcp", "kubernetes-mcp"],
    "Security": ["mcp-msdefenderkql", "splunk-mcp", "snyk-mcp", "gitguardian-mcp", "sonarqube-mcp"],
    "Data Science": ["filesystem", "postgres-mcp", "aws-mcp", "context7", "markitdown"],
    "DevOps": ["kubernetes-mcp", "azure-devops-mcp", "github", "datadog-mcp", "aws-mcp", "splunk-mcp"],
    "QA": ["filesystem", "postman-mcp", "jira-mcp", "sonarqube-mcp"],
    "Product": ["notion-mcp", "jira-mcp", "confluence-mcp", "slack-mcp"],
    "Finance IT": ["postgres-mcp", "sqlserver-mcp", "splunk-mcp", "mcp-msdefenderkql"],
    "Compliance": ["mcp-msdefenderkql", "splunk-mcp", "gitguardian-mcp", "confluence-mcp"],
}


def generate_hostname(dept: str, idx: int, os_platform: str) -> str:
    prefix = {"darwin": "MAC", "windows": "PC", "linux": "LNX"}[os_platform]
    dept_code = dept[:3].upper()
    return f"{prefix}-{dept_code}-{idx:04d}"


def generate_username(dept: str, idx: int) -> str:
    first_names = ["james", "sarah", "mike", "emma", "alex", "lisa", "david", "maria", "chris", "anna",
                   "john", "kate", "ryan", "nina", "tom", "sophie", "mark", "julia", "eric", "diana",
                   "ali", "priya", "raj", "wei", "yuki", "omar", "fatima", "carlos", "ingrid", "sven"]
    last_names = ["smith", "jones", "patel", "chen", "garcia", "kim", "singh", "brown", "wilson", "lee",
                  "taylor", "murphy", "ali", "fischer", "berg", "nakamura", "santos", "hoffman", "malik", "rosa"]
    first = first_names[(idx * 7 + hash(dept)) % len(first_names)]
    last = last_names[(idx * 13 + hash(dept)) % len(last_names)]
    return f"{first}.{last}"


def build_scan_report(hostname: str, os_platform: str, username: str, dept: str, has_shadow: bool) -> dict:
    server_catalog = {s["name"]: s for s in MCP_SERVERS + SHADOW_SERVERS}
    dept_servers = DEPT_SERVER_PROFILES.get(dept, ["filesystem", "github"])

    # Pick 2-4 clients
    num_clients = random.randint(1, 3)
    user_clients = random.sample(CLIENTS, min(num_clients, len(CLIENTS)))

    config_findings = []
    for client in user_clients:
        # Each client gets a subset of the dept's servers
        num_servers = random.randint(2, min(5, len(dept_servers)))
        client_servers = random.sample(dept_servers, num_servers)

        # Maybe add a shadow server
        if has_shadow:
            shadow = random.choice(SHADOW_SERVERS)
            client_servers.append(shadow["name"])

        for sname in client_servers:
            sdef = server_catalog.get(sname)
            if not sdef:
                continue

            has_creds = bool(sdef.get("env_vars"))
            probe_status = "discovered" if sdef.get("tools") and sdef["transport"] == "stdio" else (
                "skipped_http" if sdef["transport"] in ("http", "sse") else "not_probed"
            )

            finding = {
                "scanner": "config",
                "server_name": sname,
                "client_name": client,
                "transport": sdef["transport"],
                "runtime": sdef["runtime"],
                "package": sdef["package"],
                "version": sdef.get("version"),
                "endpoint": sdef.get("endpoint"),
                "locality": sdef["locality"],
                "env_var_names": sdef.get("env_vars", []),
                "has_credentials": has_creds,
                "risk_level": "high" if (sdef["locality"] == "remote" or has_creds) else "medium",
                "tools": sdef.get("tools", []) if probe_status == "discovered" else [],
                "probe_status": probe_status,
                "probe_reason": {
                    "discovered": f"{len(sdef.get('tools', []))} tools discovered",
                    "skipped_http": "HTTP/SSE transport requires authentication",
                    "not_probed": "Tool discovery not enabled",
                }.get(probe_status, ""),
            }
            config_findings.append(finding)

    # Process findings (simulate 2-6 running MCP processes)
    process_findings = []
    running = random.sample(config_findings, min(random.randint(2, 6), len(config_findings)))
    for f in running:
        if f["transport"] == "stdio":
            process_findings.append({
                "scanner": "process",
                "server_name": f["server_name"],
                "process_name": random.choice(["node", "Python", "snyk", "docker"]),
                "pid": random.randint(10000, 65000),
                "endpoint": f.get("endpoint"),
                "has_credentials": False,
                "risk_level": "low",
            })

    return {
        "hostname": hostname,
        "os_platform": os_platform,
        "username": username,
        "agent_version": "0.1.0",
        "config_findings": config_findings,
        "process_findings": process_findings,
        "network_findings": [],
        "workspace_findings": [],
    }


async def main():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        # Register + login
        await client.post("/api/auth/register", json={
            "username": ADMIN_USER, "email": "admin@spectis.io",
            "password": ADMIN_PASS, "role": "admin",
        })
        resp = await client.post("/api/auth/login", json={
            "username": ADMIN_USER, "password": ADMIN_PASS,
        })
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create scanner agent
        agent_resp = await client.post("/api/agents", headers=headers, json={
            "name": "endpoint-scanner", "agent_type": "scanner",
            "description": "Endpoint scanner", "owner": "admin@spectis.io",
        })
        agent_id = agent_resp.json()["id"]
        await client.patch(f"/api/agents/{agent_id}", headers=headers, json={"status": "approved"})
        key_resp = await client.post(f"/api/agents/{agent_id}/api-key", headers=headers)
        api_key = key_resp.json()["api_key"]
        agent_headers = {"Authorization": f"Bearer {api_key}"}

        # Generate 500 endpoints
        print("Generating 500 endpoint scan reports...")
        success = 0
        for i in range(500):
            dept = random.choice(DEPARTMENTS)
            os_platform = random.choices(OS_PLATFORMS, weights=OS_WEIGHTS, k=1)[0]
            hostname = generate_hostname(dept, i, os_platform)
            username = generate_username(dept, i)
            has_shadow = random.random() < 0.12  # 12% have shadow servers

            report = build_scan_report(hostname, os_platform, username, dept, has_shadow)
            resp = await client.post("/api/report", headers=agent_headers, json=report)
            if resp.status_code == 201:
                success += 1
            else:
                print(f"  Failed {hostname}: {resp.status_code} {resp.text[:100]}")

            if (i + 1) % 50 == 0:
                print(f"  {i + 1}/500 endpoints seeded ({success} ok)")

        print(f"\nDone! {success}/500 endpoints seeded.")

        # Verify
        resp = await client.get("/api/scans", headers=headers)
        scans = resp.json()
        print(f"Scans in DB: {len(scans)}")

        resp = await client.get("/api/servers", headers=headers)
        servers = resp.json()
        print(f"MCP servers in registry: {len(servers)}")
        total_tools = sum(s.get("tool_count", 0) for s in servers)
        print(f"Total tools: {total_tools}")


if __name__ == "__main__":
    asyncio.run(main())
