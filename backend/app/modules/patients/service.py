"""Patient service - business logic layer."""
import logging
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import WorkflowState
from app.shared.exceptions import (
    NotFoundError,
    ConflictError,
    InvalidStateTransition,
    ValidationError
)
from app.shared.utils import calculate_pagination, generate_uuid
from .models import Patient
from .repository import PatientRepository
from .schemas import (
    PatientCreate,
    PatientUpdate,
    PatientResponse,
    PatientDetailResponse,
    PatientIntakeData
)

logger = logging.getLogger(__name__)


class PatientService:
    """Patient business logic."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = PatientRepository(session)
    
    async def create_patient(self, patient_create: PatientCreate) -> PatientResponse:
        """Create new patient record."""
        # Check if patient already exists for this user
        existing = await self.repository.get_by_user_id(patient_create.user_id)
        if existing:
            raise ConflictError(
                f"Patient record already exists for user {patient_create.user_id}"
            )
        
        # Create patient
        patient = await self.repository.create(
            user_id=patient_create.user_id,
            date_of_birth=patient_create.date_of_birth,
            gender=patient_create.gender,
            phone=patient_create.phone,
            address=patient_create.address,
            emergency_contact=patient_create.emergency_contact,
            preferred_language=patient_create.preferred_language,
            workflow_state=WorkflowState.INTAKE.value
        )
        
        await self.repository.commit()
        
        logger.info(f"Patient created: {patient.id}")
        
        return PatientResponse.from_attributes(patient)
    
    async def get_patient(self, patient_id: str) -> PatientDetailResponse:
        """Get patient by ID."""
        patient = await self.repository.get_by_id(patient_id)
        if not patient:
            raise NotFoundError("Patient", patient_id)
        
        return PatientDetailResponse.from_attributes(patient)
    
    async def get_patient_by_user(self, user_id: str) -> PatientDetailResponse:
        """Get patient record by user ID."""
        patient = await self.repository.get_by_user_id(user_id)
        if not patient:
            raise NotFoundError("Patient record for user", user_id)
        
        return PatientDetailResponse.from_attributes(patient)
    
    async def update_patient(
        self,
        patient_id: str,
        update_data: PatientUpdate
    ) -> PatientResponse:
        """Update patient information."""
        patient = await self.repository.get_by_id(patient_id)
        if not patient:
            raise NotFoundError("Patient", patient_id)
        
        update_dict = update_data.model_dump(exclude_unset=True)
        
        # Update patient
        updated_patient = await self.repository.update(patient_id, **update_dict)
        await self.repository.commit()
        
        logger.info(f"Patient updated: {patient_id}")
        
        return PatientResponse.from_attributes(updated_patient)
    
    async def complete_intake(
        self,
        patient_id: str,
        intake_data: PatientIntakeData
    ) -> PatientResponse:
        """Complete patient intake process."""
        patient = await self.repository.get_by_id(patient_id)
        if not patient:
            raise NotFoundError("Patient", patient_id)
        
        # Validate state transition
        if patient.workflow_state != WorkflowState.INTAKE.value:
            raise InvalidStateTransition(
                current_state=patient.workflow_state,
                requested_state=WorkflowState.ASSESSMENT.value,
                allowed_transitions=[WorkflowState.ASSESSMENT.value]
            )
        
        # Update with intake data
        updated_patient = await self.repository.update(
            patient_id,
            date_of_birth=intake_data.date_of_birth,
            gender=intake_data.gender,
            phone=intake_data.phone,
            address=intake_data.address,
            emergency_contact=intake_data.emergency_contact,
            workflow_state=WorkflowState.ASSESSMENT.value,
            intake_completed_at=datetime.now(timezone.utc)
        )
        
        await self.repository.commit()
        
        logger.info(f"Patient intake completed: {patient_id}")
        
        return PatientResponse.from_attributes(updated_patient)
    
    async def transition_workflow_state(
        self,
        patient_id: str,
        new_state: str
    ) -> PatientResponse:
        """Transition patient workflow state."""
        patient = await self.repository.get_by_id(patient_id)
        if not patient:
            raise NotFoundError("Patient", patient_id)
        
        # Define valid transitions
        valid_transitions = {
            WorkflowState.INTAKE.value: [WorkflowState.ASSESSMENT.value],
            WorkflowState.ASSESSMENT.value: [WorkflowState.SCORING.value],
            WorkflowState.SCORING.value: [WorkflowState.ROUTING.value],
            WorkflowState.ROUTING.value: [WorkflowState.ASSIGNMENT.value],
            WorkflowState.ASSIGNMENT.value: [WorkflowState.ACTIVE.value],
            WorkflowState.ACTIVE.value: [WorkflowState.COMPLETED.value],
        }
        
        current_state = patient.workflow_state
        
        if current_state not in valid_transitions:
            raise InvalidStateTransition(
                current_state=current_state,
                requested_state=new_state
            )
        
        if new_state not in valid_transitions[current_state]:
            raise InvalidStateTransition(
                current_state=current_state,
                requested_state=new_state,
                allowed_transitions=valid_transitions[current_state]
            )
        
        # Perform transition
        updated_patient = await self.repository.update(
            patient_id,
            workflow_state=new_state
        )
        
        await self.repository.commit()
        
        logger.info(f"Patient workflow transitioned: {patient_id} -> {new_state}")
        
        return PatientResponse.from_attributes(updated_patient)
    
    async def assign_to_center(
        self,
        patient_id: str,
        center_id: str
    ) -> PatientResponse:
        """Assign patient to center."""
        patient = await self.repository.get_by_id(patient_id)
        if not patient:
            raise NotFoundError("Patient", patient_id)
        
        updated_patient = await self.repository.update(
            patient_id,
            center_id=center_id
        )
        
        await self.repository.commit()
        
        logger.info(f"Patient assigned to center: {patient_id} -> {center_id}")
        
        return PatientResponse.from_attributes(updated_patient)
    
    async def assign_to_clinician(
        self,
        patient_id: str,
        clinician_id: str
    ) -> PatientResponse:
        """Assign patient to clinician."""
        patient = await self.repository.get_by_id(patient_id)
        if not patient:
            raise NotFoundError("Patient", patient_id)
        
        updated_patient = await self.repository.update(
            patient_id,
            assigned_clinician_id=clinician_id
        )
        
        await self.repository.commit()
        
        logger.info(f"Patient assigned to clinician: {patient_id} -> {clinician_id}")
        
        return PatientResponse.from_attributes(updated_patient)
    
    async def search_patients(
        self,
        query: str,
        page: int = 1,
        page_size: int = 20
    ) -> dict:
        """Search patients."""
        skip = (page - 1) * page_size
        patients, total = await self.repository.search(query, skip, page_size)
        
        return {
            "data": [PatientResponse.from_attributes(p) for p in patients],
            "pagination": calculate_pagination(total, page, page_size)
        }
    
    async def list_patients_by_center(
        self,
        center_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> dict:
        """List patients at a center."""
        skip = (page - 1) * page_size
        patients, total = await self.repository.get_by_center(center_id, skip, page_size)
        
        return {
            "data": [PatientResponse.from_attributes(p) for p in patients],
            "pagination": calculate_pagination(total, page, page_size)
        }
    
    async def list_patients_by_clinician(
        self,
        clinician_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> dict:
        """List patients assigned to clinician."""
        skip = (page - 1) * page_size
        patients, total = await self.repository.get_by_clinician(clinician_id, skip, page_size)
        
        return {
            "data": [PatientResponse.from_attributes(p) for p in patients],
            "pagination": calculate_pagination(total, page, page_size)
        }
    
    async def list_patients_by_state(
        self,
        state: str,
        page: int = 1,
        page_size: int = 20
    ) -> dict:
        """List patients by workflow state."""
        skip = (page - 1) * page_size
        patients, total = await self.repository.get_by_workflow_state(state, skip, page_size)
        
        return {
            "data": [PatientResponse.from_attributes(p) for p in patients],
            "pagination": calculate_pagination(total, page, page_size)
        }
