import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, get_current_user
from app.database import get_db
from app.models.mcp_server import McpServer
from app.models.scan_result import ScanResult
from app.schemas.scan import ScanReportRequest, ScanResultDetailResponse, ScanResultResponse
from app.services.audit_logger import log_event

router = APIRouter(prefix="/api", tags=["reports"])


@router.post("/report", response_model=ScanResultResponse, status_code=201)
async def submit_scan_report(
    body: ScanReportRequest,
    request: Request,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    all_findings = (
        body.config_findings + body.process_findings
        + body.network_findings + body.workspace_findings
    )

    high = sum(1 for f in all_findings if f.get("risk_level") == "high")
    medium = sum(1 for f in all_findings if f.get("risk_level") == "medium")
    low = sum(1 for f in all_findings if f.get("risk_level") == "low")
    unapproved = sum(1 for f in all_findings if not f.get("approved", True))

    # Unique server names (deduplicated across clients)
    unique_names = sorted(set(
        f.get("server_name", "") for f in body.config_findings if f.get("server_name")
    ))

    # Locality — count unique servers, not config entries
    # A server is remote if ANY of its config entries is remote
    server_locality: dict[str, str] = {}
    for f in body.config_findings:
        name = f.get("server_name", "")
        if not name:
            continue
        loc = f.get("locality", "local")
        # remote wins over local (worst-case)
        if server_locality.get(name) != "remote":
            server_locality[name] = loc
    local_count = sum(1 for v in server_locality.values() if v == "local")
    remote_count = sum(1 for v in server_locality.values() if v == "remote")
    docker_count = sum(1 for f in body.config_findings if f.get("runtime") == "docker")
    clients_detected = sorted(set(
        f.get("client_name", "") for f in body.config_findings if f.get("client_name")
    ))

    scan = ScanResult(
        hostname=body.hostname,
        os_platform=body.os_platform,
        username=body.username,
        agent_version=body.agent_version,
        config_findings=body.config_findings,
        process_findings=body.process_findings,
        network_findings=body.network_findings,
        workspace_findings=body.workspace_findings,
        unique_server_count=len(unique_names),
        unique_server_names=unique_names,
        config_count=len(body.config_findings),
        process_count=len(body.process_findings),
        network_count=len(body.network_findings),
        workspace_count=len(body.workspace_findings),
        local_count=local_count,
        remote_count=remote_count,
        docker_count=docker_count,
        clients_detected=clients_detected,
        total_findings=len(all_findings),
        high_risk_count=high,
        medium_risk_count=medium,
        low_risk_count=low,
        unapproved_count=unapproved,
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    # Upsert MCP server registry from config findings
    for f in body.config_findings:
        sname = f.get("server_name", "")
        if not sname:
            continue
        result = await db.execute(select(McpServer).where(McpServer.server_name == sname))
        existing = result.scalar_one_or_none()
        if existing:
            # Update
            existing.last_seen = scan.scanned_at
            if f.get("tools"):
                existing.tools = f["tools"]
                existing.tool_count = len(f["tools"])
            # Merge clients and endpoints
            clients_set = set(existing.clients or [])
            clients_set.add(f.get("client_name", ""))
            existing.clients = sorted(c for c in clients_set if c)
            ep_set = set(existing.endpoints_seen or [])
            ep_set.add(body.hostname)
            existing.endpoints_seen = sorted(ep_set)
            existing.risk_level = f.get("risk_level")
            existing.has_credentials = f.get("has_credentials", False)
            if f.get("probe_status"):
                existing.probe_status = f["probe_status"]
                existing.probe_reason = f.get("probe_reason")
        else:
            # Insert new
            new_server = McpServer(
                server_name=sname,
                package=f.get("package", ""),
                transport=f.get("transport", ""),
                runtime=f.get("runtime", ""),
                locality=f.get("locality", "local"),
                endpoint=f.get("endpoint"),
                tools=f.get("tools", []),
                tool_count=len(f.get("tools", [])),
                clients=[f.get("client_name", "")],
                endpoints_seen=[body.hostname],
                risk_level=f.get("risk_level"),
                has_credentials=f.get("has_credentials", False),
                env_var_names=f.get("env_var_names", []),
                probe_status=f.get("probe_status"),
                probe_reason=f.get("probe_reason"),
                version=f.get("version"),
            )
            db.add(new_server)
    await db.commit()

    risk_level = "high" if high > 0 else "medium" if medium > 0 else "low"
    await log_event(
        db,
        action="scan_report",
        agent_id=auth.agent_id,
        agent_name=auth.agent_name,
        user_id=auth.user_id,
        username=auth.username or body.username,
        source_ip=request.client.host if request.client else None,
        risk_level=risk_level,
        details={
            "hostname": body.hostname,
            "total_findings": len(all_findings),
            "high": high,
            "medium": medium,
            "low": low,
            "unapproved": unapproved,
        },
    )
    return scan


@router.get("/scans", response_model=list[ScanResultResponse])
async def list_scans(
    hostname: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(ScanResult).order_by(ScanResult.scanned_at.desc())
    if hostname:
        query = query.where(ScanResult.hostname == hostname)
    query = query.limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.delete("/scans/{scan_id}", status_code=204)
async def delete_scan(
    scan_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from fastapi import HTTPException
    result = await db.execute(select(ScanResult).where(ScanResult.id == scan_id))
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    await db.delete(scan)
    await db.commit()


@router.get("/scans/{scan_id}", response_model=ScanResultDetailResponse)
async def get_scan(
    scan_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ScanResult).where(ScanResult.id == scan_id))
    scan = result.scalar_one_or_none()
    if not scan:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan
