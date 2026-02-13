"""Dependency injection container."""
import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .security import get_jwt_bearer
from ..shared.schemas.auth import JWTClaims

logger = logging.getLogger(__name__)


async def get_current_user(
    claims: JWTClaims = Depends(get_jwt_bearer())
) -> JWTClaims:
    """Get current authenticated user from JWT claims."""
    return claims


async def get_current_user_optional(
    claims: Optional[JWTClaims] = None
) -> Optional[JWTClaims]:
    """Get current user if authenticated, else None."""
    return claims


def require_roles(*allowed_roles: str):
    """Dependency to enforce specific roles."""
    async def check_roles(
        claims: JWTClaims = Depends(get_current_user)
    ) -> JWTClaims:
        if not any(role in allowed_roles for role in claims.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {', '.join(allowed_roles)}"
            )
        return claims
    
    return check_roles


async def get_db_session(
    db: AsyncSession = Depends(get_db)
) -> AsyncSession:
    """Get database session."""
    return db
