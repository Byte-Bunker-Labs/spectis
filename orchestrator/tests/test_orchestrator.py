import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_agent_crud(client: AsyncClient, auth_headers: dict):
    # Create agent
    resp = await client.post("/api/agents", headers=auth_headers, json={
        "name": "dlp-agent",
        "agent_type": "dlp",
        "description": "DLP compliance auditor",
        "owner": "admin@test.com",
        "allowed_commands": ["Get-DlpCompliancePolicy", "Get-Label"],
        "blocked_verbs": ["Set-", "Remove-", "New-"],
        "keywords": ["dlp", "purview", "data loss"],
    })
    assert resp.status_code == 201
    agent = resp.json()
    assert agent["name"] == "dlp-agent"
    assert agent["status"] == "pending_review"
    agent_id = agent["id"]

    # List agents
    resp = await client.get("/api/agents", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    # Get agent
    resp = await client.get(f"/api/agents/{agent_id}", headers=auth_headers)
    assert resp.status_code == 200

    # Update agent
    resp = await client.patch(f"/api/agents/{agent_id}", headers=auth_headers, json={
        "status": "approved",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    # Retire agent
    resp = await client.delete(f"/api/agents/{agent_id}", headers=auth_headers)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_validate_command(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/validate", headers=auth_headers, json={
        "command": "Get-DlpCompliancePolicy",
    })
    assert resp.status_code == 200
    assert resp.json()["is_valid"] is True


@pytest.mark.asyncio
async def test_validate_blocked_command(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/validate", headers=auth_headers, json={
        "command": "Set-MgUser -UserId 123",
    })
    assert resp.status_code == 200
    assert resp.json()["is_valid"] is False


@pytest.mark.asyncio
async def test_prompt_routing(client: AsyncClient, auth_headers: dict):
    # Create an approved agent first
    await client.post("/api/agents", headers=auth_headers, json={
        "name": "test-dlp",
        "agent_type": "dlp",
        "owner": "admin@test.com",
        "keywords": ["dlp", "purview", "data loss", "compliance"],
    })
    # Approve it
    resp = await client.get("/api/agents", headers=auth_headers)
    agent_id = resp.json()[0]["id"]
    await client.patch(f"/api/agents/{agent_id}", headers=auth_headers, json={
        "status": "approved",
    })

    # Route a prompt
    resp = await client.post("/api/prompt", headers=auth_headers, json={
        "prompt": "Show me the DLP compliance policies for data loss prevention",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["routed_to"] == "test-dlp"
    assert data["confidence"] > 0


@pytest.mark.asyncio
async def test_stats(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_events" in data
    assert "risk_breakdown" in data


@pytest.mark.asyncio
async def test_history(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/history", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
