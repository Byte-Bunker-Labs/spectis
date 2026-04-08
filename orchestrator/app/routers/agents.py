import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, generate_api_key, get_current_user, hash_api_key, require_role
from app.database import get_db
from app.models.agent import Agent
from app.schemas.agent import AgentApiKeyResponse, AgentCreate, AgentResponse, AgentUpdate
from app.services.audit_logger import log_event

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).order_by(Agent.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    body: AgentCreate,
    request: Request,
    auth: AuthContext = Depends(require_role("admin", "operator")),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(Agent).where(Agent.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Agent name already exists")

    agent = Agent(**body.model_dump())
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    await log_event(
        db,
        action="agent_create",
        agent_id=agent.id,
        agent_name=agent.name,
        user_id=auth.user_id,
        username=auth.username,
        source_ip=request.client.host if request.client else None,
        details={"agent_type": agent.agent_type, "owner": agent.owner},
    )
    return agent


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: uuid.UUID,
    body: AgentUpdate,
    request: Request,
    auth: AuthContext = Depends(require_role("admin", "operator")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)

    await db.commit()
    await db.refresh(agent)

    await log_event(
        db,
        action="agent_update",
        agent_id=agent.id,
        agent_name=agent.name,
        user_id=auth.user_id,
        username=auth.username,
        source_ip=request.client.host if request.client else None,
        details={"updated_fields": list(update_data.keys())},
    )
    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def retire_agent(
    agent_id: uuid.UUID,
    request: Request,
    auth: AuthContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.status = "retired"
    await db.commit()

    await log_event(
        db,
        action="agent_retire",
        agent_id=agent.id,
        agent_name=agent.name,
        user_id=auth.user_id,
        username=auth.username,
        source_ip=request.client.host if request.client else None,
    )


@router.post("/{agent_id}/api-key", response_model=AgentApiKeyResponse)
async def generate_agent_api_key(
    agent_id: uuid.UUID,
    request: Request,
    auth: AuthContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    raw_key = generate_api_key()
    agent.api_key_hash = hash_api_key(raw_key)
    await db.commit()

    await log_event(
        db,
        action="agent_api_key_generated",
        agent_id=agent.id,
        agent_name=agent.name,
        user_id=auth.user_id,
        username=auth.username,
        source_ip=request.client.host if request.client else None,
    )

    return AgentApiKeyResponse(agent_id=agent.id, api_key=raw_key)
