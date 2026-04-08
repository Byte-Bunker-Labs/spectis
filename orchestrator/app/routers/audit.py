import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, get_current_user
from app.database import get_db
from app.models.agent import Agent
from app.models.audit_log import AuditLog
from app.schemas.audit import (
    ExecuteRequest,
    ExecuteResponse,
    PromptRequest,
    PromptResponse,
    StatsResponse,
    ValidateRequest,
    ValidateResponse,
)
from app.services.audit_logger import log_event
from app.services.orchestrator import select_agent
from app.services.validator import validate_command

router = APIRouter(prefix="/api", tags=["audit"])


@router.post("/prompt", response_model=PromptResponse)
async def route_prompt(
    body: PromptRequest,
    request: Request,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent))
    agents = result.scalars().all()

    agent, confidence = select_agent(body.prompt, agents)
    session_id = body.session_id or str(uuid.uuid4())

    if agent:
        await log_event(
            db,
            action="prompt",
            agent_id=agent.id,
            agent_name=agent.name,
            user_id=auth.user_id,
            username=auth.username,
            session_id=session_id,
            prompt=body.prompt,
            source_ip=request.client.host if request.client else None,
            details={"confidence": confidence},
        )
        return PromptResponse(
            routed_to=agent.name,
            agent_type=agent.agent_type,
            confidence=confidence,
            session_id=session_id,
        )

    await log_event(
        db,
        action="prompt",
        user_id=auth.user_id,
        username=auth.username,
        session_id=session_id,
        prompt=body.prompt,
        result="no_matching_agent",
        source_ip=request.client.host if request.client else None,
    )
    return PromptResponse(
        routed_to="none",
        agent_type="unknown",
        confidence=0.0,
        session_id=session_id,
    )


@router.post("/validate", response_model=ValidateResponse)
async def validate(
    body: ValidateRequest,
    request: Request,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    allowed_commands = None
    blocked_verbs = None

    if body.agent_name:
        result = await db.execute(select(Agent).where(Agent.name == body.agent_name))
        agent = result.scalar_one_or_none()
        if agent:
            allowed_commands = agent.allowed_commands or None
            blocked_verbs = agent.blocked_verbs or None

    is_valid, reason, matched = validate_command(body.command, allowed_commands, blocked_verbs)

    await log_event(
        db,
        action="validate",
        user_id=auth.user_id,
        username=auth.username,
        agent_name=body.agent_name,
        command=body.command,
        status="success" if is_valid else "blocked",
        result=reason,
        source_ip=request.client.host if request.client else None,
    )

    return ValidateResponse(
        command=body.command,
        is_valid=is_valid,
        blocked_reason=reason,
        matched_verbs=matched,
    )


@router.post("/execute", response_model=ExecuteResponse)
async def execute(
    body: ExecuteRequest,
    request: Request,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Look up agent
    result = await db.execute(select(Agent).where(Agent.name == body.agent_name))
    agent = result.scalar_one_or_none()

    # Three-lane enforcement
    if not agent:
        await log_event(
            db,
            action="execute",
            user_id=auth.user_id,
            username=auth.username,
            command=body.command,
            status="blocked",
            result="Agent not found in registry",
            source_ip=request.client.host if request.client else None,
        )
        return ExecuteResponse(
            command=body.command,
            agent_name=body.agent_name,
            status="blocked",
            result="Agent not found in registry",
            session_id=body.session_id or "",
        )

    if agent.status == "blocked":
        await log_event(
            db,
            action="execute",
            agent_id=agent.id,
            agent_name=agent.name,
            user_id=auth.user_id,
            username=auth.username,
            command=body.command,
            status="blocked",
            result="Agent is in blocked state",
            source_ip=request.client.host if request.client else None,
        )
        return ExecuteResponse(
            command=body.command,
            agent_name=agent.name,
            status="blocked",
            result="Agent is in blocked state",
            session_id=body.session_id or "",
        )

    if agent.status == "pending_review":
        await log_event(
            db,
            action="execute",
            agent_id=agent.id,
            agent_name=agent.name,
            user_id=auth.user_id,
            username=auth.username,
            command=body.command,
            status="queued",
            result="Agent pending review — queued for inspection lane",
            source_ip=request.client.host if request.client else None,
        )
        return ExecuteResponse(
            command=body.command,
            agent_name=agent.name,
            status="queued",
            result="Agent pending review — queued for inspection lane",
            session_id=body.session_id or "",
        )

    # Fast lane — validate command
    is_valid, reason, matched = validate_command(
        body.command, agent.allowed_commands or None, agent.blocked_verbs or None
    )

    if not is_valid:
        await log_event(
            db,
            action="execute",
            agent_id=agent.id,
            agent_name=agent.name,
            user_id=auth.user_id,
            username=auth.username,
            command=body.command,
            status="blocked",
            result=reason,
            risk_level="high",
            source_ip=request.client.host if request.client else None,
        )
        return ExecuteResponse(
            command=body.command,
            agent_name=agent.name,
            status="blocked",
            result=reason,
            session_id=body.session_id or "",
        )

    # Command is valid — log execution (actual execution is out of scope for the API;
    # the orchestrator logs intent and the CopilotBridge/agent handles execution)
    session_id = body.session_id or str(uuid.uuid4())
    await log_event(
        db,
        action="execute",
        agent_id=agent.id,
        agent_name=agent.name,
        user_id=auth.user_id,
        username=auth.username,
        session_id=session_id,
        command=body.command,
        status="success",
        result="Command validated and dispatched",
        source_ip=request.client.host if request.client else None,
        details={"delegation": f"{agent.name} (agent:{agent.id}) acting for {auth.username}"},
    )

    return ExecuteResponse(
        command=body.command,
        agent_name=agent.name,
        status="success",
        result="Command validated and dispatched",
        session_id=session_id,
    )


@router.get("/history")
async def get_history(
    action: str | None = Query(None),
    agent_name: str | None = Query(None),
    username: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(AuditLog).order_by(AuditLog.timestamp.desc())
    if action:
        query = query.where(AuditLog.action == action)
    if agent_name:
        query = query.where(AuditLog.agent_name == agent_name)
    if username:
        query = query.where(AuditLog.username == username)
    if status:
        query = query.where(AuditLog.status == status)

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()

    return [
        {
            "id": str(log.id),
            "agent_name": log.agent_name,
            "username": log.username,
            "action": log.action,
            "command": log.command,
            "prompt": log.prompt,
            "status": log.status,
            "risk_level": log.risk_level,
            "source_ip": log.source_ip,
            "timestamp": log.timestamp.isoformat(),
        }
        for log in logs
    ]


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Total events
    total = await db.execute(select(func.count(AuditLog.id)))
    total_events = total.scalar() or 0

    # Events today
    today = await db.execute(
        select(func.count(AuditLog.id)).where(AuditLog.timestamp >= today_start)
    )
    events_today = today.scalar() or 0

    # Blocked commands
    blocked = await db.execute(
        select(func.count(AuditLog.id)).where(AuditLog.status == "blocked")
    )
    blocked_commands = blocked.scalar() or 0

    # Active agents
    active = await db.execute(
        select(func.count(Agent.id)).where(Agent.status == "approved")
    )
    active_agents = active.scalar() or 0

    # Active sessions (unique session_ids in last 24h)
    day_ago = now - timedelta(hours=24)
    sessions = await db.execute(
        select(func.count(func.distinct(AuditLog.session_id))).where(
            AuditLog.timestamp >= day_ago, AuditLog.session_id.isnot(None)
        )
    )
    active_sessions = sessions.scalar() or 0

    # Risk breakdown
    risk_q = await db.execute(
        select(AuditLog.risk_level, func.count(AuditLog.id))
        .where(AuditLog.risk_level.isnot(None))
        .group_by(AuditLog.risk_level)
    )
    risk_breakdown = {row[0]: row[1] for row in risk_q.all()}

    # Top agents by event count
    top_q = await db.execute(
        select(AuditLog.agent_name, func.count(AuditLog.id))
        .where(AuditLog.agent_name.isnot(None))
        .group_by(AuditLog.agent_name)
        .order_by(func.count(AuditLog.id).desc())
        .limit(5)
    )
    top_agents = [{"name": row[0], "event_count": row[1]} for row in top_q.all()]

    return StatsResponse(
        total_events=total_events,
        events_today=events_today,
        blocked_commands=blocked_commands,
        active_agents=active_agents,
        active_sessions=active_sessions,
        risk_breakdown=risk_breakdown,
        top_agents=top_agents,
    )
