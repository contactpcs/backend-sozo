"""User repository - data access layer."""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.models.base_repository import BaseRepository
from .models import User


class UserRepository(BaseRepository[User]):
    """User data access."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        query = select(User).where(User.email == email)
        result = await self.session.execute(query)
        return result.scalars().first()
    
    async def email_exists(self, email: str) -> bool:
        """Check if email already registered."""
        user = await self.get_by_email(email)
        return user is not None
    
    async def get_active_users(self, skip: int = 0, limit: int = 20):
        """Get active users."""
        query = select(User).where(
            User.is_active == True,
            User.is_deleted == False
        ).offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        users = result.scalars().all()
        
        # Count total active users
        count_query = select(User).where(
            User.is_active == True,
            User.is_deleted == False
        )
        total = (await self.session.execute(count_query)).scalars().__len__()
        
        return users, total
