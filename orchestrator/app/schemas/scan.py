import uuid
from datetime import datetime

from pydantic import BaseModel


class ScanReportRequest(BaseModel):
    hostname: str
    os_platform: str
    username: str | None = None
    agent_version: str | None = None
    config_findings: list[dict] = []
    process_findings: list[dict] = []
    network_findings: list[dict] = []
    workspace_findings: list[dict] = []


class ScanResultResponse(BaseModel):
    id: uuid.UUID
    hostname: str
    os_platform: str
    username: str | None
    agent_version: str | None
    unique_server_count: int
    unique_server_names: list[str]
    config_count: int
    process_count: int
    network_count: int
    workspace_count: int
    local_count: int
    remote_count: int
    docker_count: int
    clients_detected: list[str]
    total_findings: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    unapproved_count: int
    scanned_at: datetime

    model_config = {"from_attributes": True}


class ScanResultDetailResponse(ScanResultResponse):
    config_findings: list[dict]
    process_findings: list[dict]
    network_findings: list[dict]
    workspace_findings: list[dict]
