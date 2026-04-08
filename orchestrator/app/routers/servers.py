import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, get_current_user
from app.database import get_db
from app.models.mcp_server import McpServer
from app.models.scan_result import ScanResult
from app.schemas.server import McpServerDetailResponse, McpServerResponse

router = APIRouter(prefix="/api/servers", tags=["servers"])


@router.get("", response_model=list[McpServerResponse])
async def list_servers(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(McpServer).order_by(McpServer.last_seen.desc()))
    return result.scalars().all()


@router.get("/inventory")
async def get_inventory(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Governance view: User → Client → Server → Tools hierarchy.

    Built from scan data (per-endpoint, per-user) cross-referenced with
    the MCP server registry (tools, probe status).
    """
    # Get all scans
    scans_result = await db.execute(select(ScanResult).order_by(ScanResult.scanned_at.desc()))
    scans = scans_result.scalars().all()

    # Get server registry for tool/probe data
    servers_result = await db.execute(select(McpServer))
    server_registry = {s.server_name: s for s in servers_result.scalars().all()}

    # Build hierarchy: user -> client -> servers
    # Use latest scan per hostname
    seen_hosts: set[str] = set()
    users: dict[str, dict] = {}

    for scan in scans:
        if scan.hostname in seen_hosts:
            continue
        seen_hosts.add(scan.hostname)

        username = scan.username or scan.hostname
        if username not in users:
            users[username] = {
                "username": username,
                "hostname": scan.hostname,
                "os_platform": scan.os_platform,
                "clients": {},
            }

        # Group config findings by client
        for f in (scan.config_findings or []):
            client_name = f.get("client_name", "Unknown")
            if client_name not in users[username]["clients"]:
                users[username]["clients"][client_name] = []

            sname = f.get("server_name", "")
            reg = server_registry.get(sname)

            users[username]["clients"][client_name].append({
                "server_name": sname,
                "package": f.get("package", ""),
                "transport": f.get("transport", ""),
                "runtime": f.get("runtime", ""),
                "locality": f.get("locality", "local"),
                "endpoint": f.get("endpoint"),
                "version": f.get("version"),
                "risk_level": f.get("risk_level"),
                "has_credentials": f.get("has_credentials", False),
                "env_var_names": f.get("env_var_names", []),
                "probe_status": reg.probe_status if reg else f.get("probe_status", "not_probed"),
                "probe_reason": reg.probe_reason if reg else f.get("probe_reason"),
                "tool_count": reg.tool_count if reg else 0,
                "tools": reg.tools if reg else [],
            })

    # Convert to list
    result = []
    for udata in users.values():
        clients_list = []
        for cname, servers in udata["clients"].items():
            clients_list.append({
                "client_name": cname,
                "server_count": len(servers),
                "servers": servers,
            })
        result.append({
            "username": udata["username"],
            "hostname": udata["hostname"],
            "os_platform": udata["os_platform"],
            "client_count": len(clients_list),
            "clients": clients_list,
        })

    return result


@router.get("/{server_id}", response_model=McpServerDetailResponse)
async def get_server(
    server_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(McpServer).where(McpServer.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    return server
