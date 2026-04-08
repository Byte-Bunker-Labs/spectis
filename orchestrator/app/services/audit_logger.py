"""Dual audit logging service — writes to both JSONL files and PostgreSQL.

JSONL provides backward compatibility and file-based archival.
PostgreSQL provides queryable, indexed storage for the dashboard.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.audit_log import AuditLog


def _jsonl_path() -> Path:
    log_dir = Path(settings.audit_log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return log_dir / f"audit-{today}.jsonl"


def _write_jsonl(entry: dict) -> None:
    """Append a single audit entry to today's JSONL file."""
    path = _jsonl_path()
    serializable = {}
    for k, v in entry.items():
        if isinstance(v, uuid.UUID):
            serializable[k] = str(v)
        elif isinstance(v, datetime):
            serializable[k] = v.isoformat()
        else:
            serializable[k] = v

    with open(path, "a") as f:
        f.write(json.dumps(serializable) + "\n")


async def log_event(
    db: AsyncSession,
    *,
    action: str,
    agent_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    session_id: str | None = None,
    username: str | None = None,
    agent_name: str | None = None,
    command: str | None = None,
    prompt: str | None = None,
    result: str | None = None,
    risk_level: str | None = None,
    status: str = "success",
    source_ip: str | None = None,
    details: dict | None = None,
) -> AuditLog:
    """Log an audit event to both PostgreSQL and JSONL."""
    now = datetime.now(timezone.utc)

    # Write to PostgreSQL
    log_entry = AuditLog(
        agent_id=agent_id,
        user_id=user_id,
        session_id=session_id,
        username=username,
        agent_name=agent_name,
        action=action,
        command=command,
        prompt=prompt,
        result=result,
        risk_level=risk_level,
        status=status,
        source_ip=source_ip,
        details=details,
        timestamp=now,
    )
    db.add(log_entry)
    await db.commit()
    await db.refresh(log_entry)

    # Write to JSONL (best-effort, don't fail the request if file write fails)
    try:
        _write_jsonl({
            "id": log_entry.id,
            "agent_id": agent_id,
            "user_id": user_id,
            "session_id": session_id,
            "username": username,
            "agent_name": agent_name,
            "action": action,
            "command": command,
            "prompt": prompt,
            "result": result,
            "risk_level": risk_level,
            "status": status,
            "source_ip": source_ip,
            "details": details,
            "timestamp": now,
        })
    except OSError:
        pass  # JSONL is best-effort; DB is the source of truth

    return log_entry
