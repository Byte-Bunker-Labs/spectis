import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ScanResult(Base):
    __tablename__ = "scan_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    os_platform: Mapped[str] = mapped_column(String(50), nullable=False)  # windows, darwin, linux
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    agent_version: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Scan results
    config_findings: Mapped[dict] = mapped_column(JSON, default=list)
    process_findings: Mapped[dict] = mapped_column(JSON, default=list)
    network_findings: Mapped[dict] = mapped_column(JSON, default=list)
    workspace_findings: Mapped[dict] = mapped_column(JSON, default=list)

    # Per-scanner counts
    unique_server_count: Mapped[int] = mapped_column(default=0)
    unique_server_names: Mapped[dict] = mapped_column(JSON, default=list)
    config_count: Mapped[int] = mapped_column(default=0)
    process_count: Mapped[int] = mapped_column(default=0)
    network_count: Mapped[int] = mapped_column(default=0)
    workspace_count: Mapped[int] = mapped_column(default=0)

    # Locality breakdown (config findings only)
    local_count: Mapped[int] = mapped_column(default=0)
    remote_count: Mapped[int] = mapped_column(default=0)

    # Runtime breakdown
    docker_count: Mapped[int] = mapped_column(default=0)

    # AI clients that have MCP configs (JSON list of client names)
    clients_detected: Mapped[dict] = mapped_column(JSON, default=list)

    # Risk summary
    total_findings: Mapped[int] = mapped_column(default=0)
    high_risk_count: Mapped[int] = mapped_column(default=0)
    medium_risk_count: Mapped[int] = mapped_column(default=0)
    low_risk_count: Mapped[int] = mapped_column(default=0)
    unapproved_count: Mapped[int] = mapped_column(default=0)

    scanned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
