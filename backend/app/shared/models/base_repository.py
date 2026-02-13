"""Base repository pattern for data access."""
from typing import Generic, TypeVar, Optional, List
from uuid import UUID

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Base repository providing common data access operations."""
    
    def __init__(self, session: AsyncSession, model_class):
        self.session = session
        self.model_class = model_class
    
    async def create(self, **kwargs) -> T:
        """Create and persist entity."""
        entity = self.model_class(**kwargs)
        self.session.add(entity)
        await self.session.flush()
        return entity
    
    async def get_by_id(self, entity_id: UUID) -> Optional[T]:
        """Get entity by ID."""
        query = select(self.model_class).where(
            self.model_class.id == entity_id
        )
        result = await self.session.execute(query)
        return result.scalars().first()
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 20,
        filters: Optional[dict] = None
    ) -> tuple[List[T], int]:
        """Get all entities with pagination and filters."""
        query = select(self.model_class)
        
        # Apply filters
        if filters:
            for key, value in filters.items():
                if hasattr(self.model_class, key) and value is not None:
                    query = query.where(
                        getattr(self.model_class, key) == value
                    )
        
        # Count total
        count_query = select(self.model_class)
        if filters:
            for key, value in filters.items():
                if hasattr(self.model_class, key) and value is not None:
                    count_query = count_query.where(
                        getattr(self.model_class, key) == value
                    )
        
        total = (await self.session.execute(count_query)).scalars().all().__len__()
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        entities = result.scalars().all()
        
        return entities, total
    
    async def update(self, entity_id: UUID, **kwargs) -> Optional[T]:
        """Update entity."""
        entity = await self.get_by_id(entity_id)
        if not entity:
            return None
        
        for key, value in kwargs.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        
        await self.session.flush()
        return entity
    
    async def delete(self, entity_id: UUID) -> bool:
        """Soft delete entity (if model supports it)."""
        entity = await self.get_by_id(entity_id)
        if not entity:
            return False
        
        if hasattr(entity, "is_deleted"):
            entity.is_deleted = True
            entity.deleted_at = __import__("datetime").datetime.utcnow()
        else:
            self.session.delete(entity)
        
        await self.session.flush()
        return True
    
    async def commit(self) -> None:
        """Commit transaction."""
        await self.session.commit()
    
    async def rollback(self) -> None:
        """Rollback transaction."""
        await self.session.rollback()
