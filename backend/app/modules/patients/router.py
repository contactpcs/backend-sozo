"""Patient routes - HTTP layer."""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.core.constants import UserRole
from app.shared.exceptions import NeurowellnessException
from app.shared.schemas.auth import JWTClaims
from .schemas import (
    PatientCreate,
    PatientUpdate,
    PatientResponse,
    PatientDetailResponse,
    PatientIntakeData
)
from .service import PatientService

router = APIRouter(tags=["patients"], prefix="/patients")
logger = logging.getLogger(__name__)


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    patient_data: PatientCreate,
    current_user: JWTClaims = Depends(require_roles(UserRole.DOCTOR.value, UserRole.SUPER_ADMIN.value)),
    db: AsyncSession = Depends(get_db)
):
    """Create new patient record."""
    try:
        service = PatientService(db)
        return await service.create_patient(patient_data)
    except NeurowellnessException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"error_code": e.error_code, "message": e.message}
        )


@router.get("/search", response_model=dict)
async def search_patients(
    q: str = Query(min_length=2),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: JWTClaims = Depends(require_roles(
        UserRole.DOCTOR.value,
        UserRole.CLINICAL_ASSISTANT.value,
        UserRole.SUPER_ADMIN.value
    )),
    db: AsyncSession = Depends(get_db)
):
    """Search patients by MRN or name."""
    try:
        service = PatientService(db)
        return await service.search_patients(q, page, page_size)
    except NeurowellnessException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message
        )


@router.get("/me/profile", response_model=PatientDetailResponse)
async def get_my_profile(
    current_user: JWTClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's patient profile."""
    # Ensure ONLY patients can access this endpoint
    if "patient" not in [role.lower() for role in current_user.roles]:
        logger.warning(f"Non-patient user {current_user.email} (roles: {current_user.roles}) tried to access patient profile")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can have a patient profile"
        )
        
    try:
        service = PatientService(db)
        return await service.get_patient_by_user(current_user.user_id)
    except NeurowellnessException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message
        )


@router.get("/center/{center_id}/list", response_model=dict)
async def list_center_patients(
    center_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: JWTClaims = Depends(require_roles(
        UserRole.CLINICAL_ADMIN.value,
        UserRole.DOCTOR.value,
        UserRole.SUPER_ADMIN.value
    )),
    db: AsyncSession = Depends(get_db)
):
    """List patients at a center."""
    try:
        service = PatientService(db)
        return await service.list_patients_by_center(center_id, page, page_size)
    except NeurowellnessException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message
        )


@router.get("/clinician/{clinician_id}/list", response_model=dict)
async def list_clinician_patients(
    clinician_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: JWTClaims = Depends(require_roles(
        UserRole.DOCTOR.value,
        UserRole.SUPER_ADMIN.value
    )),
    db: AsyncSession = Depends(get_db)
):
    """List patients assigned to clinician."""
    try:
        service = PatientService(db)
        return await service.list_patients_by_clinician(clinician_id, page, page_size)
    except NeurowellnessException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message
        )


@router.get("/{patient_id}", response_model=PatientDetailResponse)
async def get_patient(
    patient_id: str,
    current_user: JWTClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get patient details."""
    try:
        service = PatientService(db)
        patient = await service.get_patient(patient_id)
        
        # Authorization check - patients can view own, clinicians can view assigned
        if (patient_id != current_user.user_id and
            UserRole.DOCTOR.value not in current_user.roles and
            UserRole.SUPER_ADMIN.value not in current_user.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access this patient record"
            )
        
        return patient
    except NeurowellnessException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message
        )


@router.patch("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: str,
    update_data: PatientUpdate,
    current_user: JWTClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update patient information."""
    try:
        service = PatientService(db)
        return await service.update_patient(patient_id, update_data)
    except NeurowellnessException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message
        )


@router.post("/{patient_id}/intake/complete", response_model=PatientResponse)
async def complete_intake(
    patient_id: str,
    intake_data: PatientIntakeData,
    current_user: JWTClaims = Depends(require_roles(
        UserRole.DOCTOR.value,
        UserRole.CLINICAL_ASSISTANT.value,
        UserRole.SUPER_ADMIN.value
    )),
    db: AsyncSession = Depends(get_db)
):
    """Complete patient intake process."""
    try:
        service = PatientService(db)
        return await service.complete_intake(patient_id, intake_data)
    except NeurowellnessException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"error_code": e.error_code, "message": e.message}
        )


@router.post("/{patient_id}/workflow/transition", response_model=PatientResponse)
async def transition_workflow(
    patient_id: str,
    new_state: str = Query(),
    current_user: JWTClaims = Depends(require_roles(
        UserRole.DOCTOR.value,
        UserRole.SUPER_ADMIN.value
    )),
    db: AsyncSession = Depends(get_db)
):
    """Transition patient workflow state."""
    try:
        service = PatientService(db)
        return await service.transition_workflow_state(patient_id, new_state)
    except NeurowellnessException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"error_code": e.error_code, "message": e.message}
        )


@router.post("/{patient_id}/assign/center/{center_id}", response_model=PatientResponse)
async def assign_to_center(
    patient_id: str,
    center_id: str,
    current_user: JWTClaims = Depends(require_roles(UserRole.SUPER_ADMIN.value)),
    db: AsyncSession = Depends(get_db)
):
    """Assign patient to center (admin only)."""
    try:
        service = PatientService(db)
        return await service.assign_to_center(patient_id, center_id)
    except NeurowellnessException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message
        )


@router.post("/{patient_id}/assign/clinician/{clinician_id}", response_model=PatientResponse)
async def assign_to_clinician(
    patient_id: str,
    clinician_id: str,
    current_user: JWTClaims = Depends(require_roles(
        UserRole.CLINICAL_ADMIN.value,
        UserRole.SUPER_ADMIN.value
    )),
    db: AsyncSession = Depends(get_db)
):
    """Assign patient to clinician."""
    try:
        service = PatientService(db)
        return await service.assign_to_clinician(patient_id, clinician_id)
    except NeurowellnessException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message
        )
