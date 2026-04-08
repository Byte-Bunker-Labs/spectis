import uuid
from datetime import datetime

from pydantic import BaseModel


class PromptRequest(BaseModel):
    prompt: str
    session_id: str | None = None


class ValidateRequest(BaseModel):
    command: str
    agent_name: str | None = None


class ExecuteRequest(BaseModel):
    command: str
    agent_name: str
    session_id: str | None = None


class PromptResponse(BaseModel):
    routed_to: str
    agent_type: str
    confidence: float
    session_id: str


class ValidateResponse(BaseModel):
    command: str
    is_valid: bool
    blocked_reason: str | None = None
    matched_verbs: list[str] = []


class ExecuteResponse(BaseModel):
    command: str
    agent_name: str
    status: str
    result: str | None = None
    session_id: str


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID | None
    user_id: uuid.UUID | None
    session_id: str | None
    username: str | None
    agent_name: str | None
    action: str
    command: str | None
    prompt: str | None
    result: str | None
    risk_level: str | None
    status: str
    source_ip: str | None
    timestamp: datetime

    model_config = {"from_attributes": True}


class StatsResponse(BaseModel):
    total_events: int
    events_today: int
    blocked_commands: int
    active_agents: int
    active_sessions: int
    risk_breakdown: dict[str, int]
    top_agents: list[dict]
