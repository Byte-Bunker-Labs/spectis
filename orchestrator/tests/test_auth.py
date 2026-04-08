import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    # Register
    resp = await client.post("/api/auth/register", json={
        "username": "alice",
        "email": "alice@example.com",
        "password": "securepass",
        "role": "viewer",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "alice"
    assert data["role"] == "viewer"

    # Login
    resp = await client.post("/api/auth/login", json={
        "username": "alice",
        "password": "securepass",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["username"] == "alice"


@pytest.mark.asyncio
async def test_duplicate_username(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "username": "bob",
        "email": "bob@example.com",
        "password": "pass123",
    })
    resp = await client.post("/api/auth/register", json={
        "username": "bob",
        "email": "bob2@example.com",
        "password": "pass456",
    })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_wrong_password(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "username": "carol",
        "email": "carol@example.com",
        "password": "correct",
    })
    resp = await client.post("/api/auth/login", json={
        "username": "carol",
        "password": "wrong",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(client: AsyncClient):
    resp = await client.get("/api/agents")
    assert resp.status_code == 401 or resp.status_code == 403


@pytest.mark.asyncio
async def test_me_endpoint(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "testadmin"
