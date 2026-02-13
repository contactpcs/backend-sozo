"""User service - business logic layer."""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import PasswordManager, JWTManager
from app.shared.exceptions import (
    ValidationError,
    NotFoundError,
    ConflictError,
    AuthenticationError
)
from .models import User
from .repository import UserRepository
from .schemas import UserCreate, UserUpdate, UserResponse, UserDetailResponse

logger = logging.getLogger(__name__)


class UserService:
    """User business logic."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = UserRepository(session)
        self.password_manager = PasswordManager()
        self.jwt_manager = JWTManager()
    
    async def register_user(self, user_create: UserCreate) -> UserResponse:
        """Register new user."""
        # Check if email already exists
        if await self.repository.email_exists(user_create.email):
            raise ConflictError(
                f"User with email {user_create.email} already exists"
            )
        
        # Hash password
        hashed_password = self.password_manager.hash_password(user_create.password)
        
        # Create user
        user = await self.repository.create(
            email=user_create.email,
            first_name=user_create.first_name,
            last_name=user_create.last_name,
            hashed_password=hashed_password,
            role=user_create.role.value
        )
        
        await self.repository.commit()
        
        logger.info(f"User registered: {user.email}")
        
        return UserResponse.from_attributes(user)
    
    async def authenticate_user(
        self,
        email: str,
        password: str
    ) -> tuple[str, str]:
        """Authenticate user and return tokens."""
        # Get user by email
        user = await self.repository.get_by_email(email)
        if not user:
            raise AuthenticationError("Invalid email or password")
        
        # Check if active
        if not user.is_active:
            raise AuthenticationError("User account is inactive")
        
        # Verify password
        if not self.password_manager.verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")
        
        # Create tokens
        access_token = self.jwt_manager.create_access_token(
            user_id=user.id,
            user_email=user.email,
            roles=[user.role]
        )
        
        refresh_token = self.jwt_manager.create_refresh_token(user.id)
        
        logger.info(f"User authenticated: {user.email}")
        
        return access_token, refresh_token
    
    async def get_user(self, user_id: str) -> UserDetailResponse:
        """Get user by ID."""
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        
        return UserDetailResponse.from_attributes(user)
    
    async def update_user(
        self,
        user_id: str,
        update_data: UserUpdate
    ) -> UserResponse:
        """Update user."""
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        
        # Update only provided fields
        update_dict = update_data.model_dump(exclude_unset=True)
        updated_user = await self.repository.update(user_id, **update_dict)
        
        await self.repository.commit()
        
        logger.info(f"User updated: {user_id}")
        
        return UserResponse.from_attributes(updated_user)
    
    async def deactivate_user(self, user_id: str) -> UserResponse:
        """Deactivate user."""
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        
        updated_user = await self.repository.update(user_id, is_active=False)
        await self.repository.commit()
        
        logger.info(f"User deactivated: {user_id}")
        
        return UserResponse.from_attributes(updated_user)
    
    async def list_users(
        self,
        page: int = 1,
        page_size: int = 20
    ) -> dict:
        """List all users."""
        skip = (page - 1) * page_size
        users, total = await self.repository.get_active_users(skip, page_size)
        
        from app.shared.utils import calculate_pagination
        
        return {
            "data": [UserResponse.from_attributes(u) for u in users],
            "pagination": calculate_pagination(total, page, page_size)
        }
