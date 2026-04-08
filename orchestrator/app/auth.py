import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.agent import Agent

bearer_scheme = HTTPBearer(auto_error=False)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600_000)
    return f"{salt}${hashed.hex()}"


def verify_password(plain: str, stored: str) -> bool:
    salt, hashed = stored.split("$", 1)
    check = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), 600_000)
    return secrets.compare_digest(check.hex(), hashed)


def hash_api_key(api_key: str) -> str:
    return _sha256(api_key)


def verify_api_key(plain: str, hashed: str) -> bool:
    return secrets.compare_digest(_sha256(plain), hashed)


def generate_api_key() -> str:
    return f"aw_{secrets.token_urlsafe(32)}"


def create_access_token(user_id: uuid.UUID, username: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


class AuthContext:
    """Holds the authenticated identity — either a user (JWT) or an agent (API key)."""

    def __init__(
        self,
        user_id: uuid.UUID | None = None,
        username: str | None = None,
        role: str | None = None,
        agent_id: uuid.UUID | None = None,
        agent_name: str | None = None,
        auth_type: str = "jwt",
    ):
        self.user_id = user_id
        self.username = username
        self.role = role
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.auth_type = auth_type


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    """Authenticate via JWT bearer token or API key.

    JWT tokens: standard Bearer token from login.
    API keys: sent as Bearer aw_... (agent machine-to-machine auth).
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # API key path (agent auth)
    if token.startswith("aw_"):
        result = await db.execute(select(Agent).where(Agent.status == "approved"))
        agents = result.scalars().all()
        for agent in agents:
            if agent.api_key_hash and verify_api_key(token, agent.api_key_hash):
                return AuthContext(
                    agent_id=agent.id,
                    agent_name=agent.name,
                    auth_type="api_key",
                )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    # JWT path (user auth)
    payload = decode_token(token)
    return AuthContext(
        user_id=uuid.UUID(payload["sub"]),
        username=payload["username"],
        role=payload["role"],
        auth_type="jwt",
    )


def require_role(*roles: str):
    """Dependency that checks the authenticated user has one of the required roles."""

    async def _check(auth: AuthContext = Depends(get_current_user)) -> AuthContext:
        if auth.auth_type == "api_key":
            return auth  # agents bypass role checks
        if auth.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {', '.join(roles)}",
            )
        return auth

    return _check
