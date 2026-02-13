"""Patient repository - data access layer."""
from typing import Optional, List
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.models.base_repository import BaseRepository
from .models import Patient


class PatientRepository(BaseRepository[Patient]):
    """Patient data access."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Patient)
    
    async def get_by_user_id(self, user_id: str) -> Optional[Patient]:
        """Get patient by user ID."""
        query = select(Patient).where(Patient.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalars().first()
    
    async def get_by_mrn(self, mrn: str) -> Optional[Patient]:
        """Get patient by MRN."""
        query = select(Patient).where(Patient.mrn == mrn)
        result = await self.session.execute(query)
        return result.scalars().first()
    
    async def search(
        self,
        query_text: str,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[List[Patient], int]:
        """Search patients by name or MRN."""
        # Note: This is a simplified search, in production use full-text search
        search_filter = or_(
            Patient.mrn.ilike(f"%{query_text}%"),
        )
        
        query = select(Patient).where(
            search_filter,
            Patient.is_deleted == False
        ).offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        patients = result.scalars().all()
        
        # Count total
        count_query = select(Patient).where(
            search_filter,
            Patient.is_deleted == False
        )
        total = len((await self.session.execute(count_query)).scalars().all())
        
        return patients, total
    
    async def get_by_center(
        self,
        center_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[List[Patient], int]:
        """Get patients assigned to a center."""
        query = select(Patient).where(
            Patient.center_id == center_id,
            Patient.is_deleted == False
        ).offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        patients = result.scalars().all()
        
        # Count total
        count_query = select(Patient).where(
            Patient.center_id == center_id,
            Patient.is_deleted == False
        )
        total = len((await self.session.execute(count_query)).scalars().all())
        
        return patients, total
    
    async def get_by_clinician(
        self,
        clinician_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[List[Patient], int]:
        """Get patients assigned to a clinician."""
        query = select(Patient).where(
            Patient.assigned_clinician_id == clinician_id,
            Patient.is_deleted == False
        ).offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        patients = result.scalars().all()
        
        # Count total
        count_query = select(Patient).where(
            Patient.assigned_clinician_id == clinician_id,
            Patient.is_deleted == False
        )
        total = len((await self.session.execute(count_query)).scalars().all())
        
        return patients, total
    
    async def get_by_workflow_state(
        self,
        state: str,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[List[Patient], int]:
        """Get patients by workflow state."""
        query = select(Patient).where(
            Patient.workflow_state == state,
            Patient.is_deleted == False
        ).offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        patients = result.scalars().all()
        
        # Count total
        count_query = select(Patient).where(
            Patient.workflow_state == state,
            Patient.is_deleted == False
        )
        total = len((await self.session.execute(count_query)).scalars().all())
        
        return patients, total
