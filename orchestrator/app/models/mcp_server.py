import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class McpServer(Base):
    __tablename__ = "mcp_servers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    server_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    package: Mapped[str] = mapped_column(String(255), default="")
    transport: Mapped[str] = mapped_column(String(20), default="")  # stdio/sse/http
    runtime: Mapped[str] = mapped_column(String(20), default="")  # docker/npx/uvx/native
    locality: Mapped[str] = mapped_column(String(20), default="local")  # local/remote
    endpoint: Mapped[str | None] = mapped_column(Text, nullable=True)
    tools: Mapped[dict] = mapped_column(JSON, default=list)  # [{name, description, input_schema}]
    tool_count: Mapped[int] = mapped_column(Integer, default=0)
    clients: Mapped[dict] = mapped_column(JSON, default=list)  # AI client names
    endpoints_seen: Mapped[dict] = mapped_column(JSON, default=list)  # hostnames
    risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    has_credentials: Mapped[bool] = mapped_column(Boolean, default=False)
    env_var_names: Mapped[dict] = mapped_column(JSON, default=list)
    probe_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    probe_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
