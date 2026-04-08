import uuid
from datetime import datetime

from pydantic import BaseModel


class AgentCreate(BaseModel):
    name: str
    agent_type: str
    description: str = ""
    owner: str
    allowed_commands: list[str] = []
    blocked_verbs: list[str] = []
    allowed_mcp_tools: list[str] = []
    keywords: list[str] = []
    version: str = "1.0.0"


class AgentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    allowed_commands: list[str] | None = None
    blocked_verbs: list[str] | None = None
    allowed_mcp_tools: list[str] | None = None
    keywords: list[str] | None = None
    version: str | None = None


class AgentResponse(BaseModel):
    id: uuid.UUID
    name: str
    agent_type: str
    description: str
    owner: str
    status: str
    allowed_commands: list[str]
    blocked_verbs: list[str]
    allowed_mcp_tools: list[str]
    keywords: list[str]
    version: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentApiKeyResponse(BaseModel):
    agent_id: uuid.UUID
    api_key: str
    message: str = "Store this key securely — it cannot be retrieved again."
