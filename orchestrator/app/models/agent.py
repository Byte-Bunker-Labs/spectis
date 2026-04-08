import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)  # dlp, entra, security, custom
    description: Mapped[str] = mapped_column(Text, default="")
    owner: Mapped[str] = mapped_column(String(255), nullable=False)  # email of responsible human
    status: Mapped[str] = mapped_column(
        String(20), default="pending_review"
    )  # pending_review, approved, blocked, retired
    api_key_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Permissions
    allowed_commands: Mapped[dict] = mapped_column(JSON, default=list)  # ["Get-DlpCompliancePolicy", ...]
    blocked_verbs: Mapped[dict] = mapped_column(JSON, default=list)  # ["Set-", "Remove-", "New-", ...]
    allowed_mcp_tools: Mapped[dict] = mapped_column(JSON, default=list)  # MCP tool names this agent can call

    # Routing keywords for prompt-based agent selection
    keywords: Mapped[dict] = mapped_column(JSON, default=list)  # ["dlp", "purview", "data loss", ...]

    # Metadata
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
