import uuid
from datetime import datetime

from pydantic import BaseModel


class McpToolResponse(BaseModel):
    name: str
    description: str
    input_schema: dict

    model_config = {"from_attributes": True}


class McpServerResponse(BaseModel):
    id: uuid.UUID
    server_name: str
    package: str
    transport: str
    runtime: str
    locality: str
    endpoint: str | None
    tools: list[dict]
    tool_count: int
    clients: list[str]
    endpoints_seen: list[str]
    risk_level: str | None
    has_credentials: bool
    env_var_names: list[str]
    probe_status: str | None
    probe_reason: str | None
    version: str | None
    first_seen: datetime
    last_seen: datetime

    model_config = {"from_attributes": True}


class McpServerDetailResponse(McpServerResponse):
    """Single-item detail response — same fields, distinct type for documentation."""
    pass
