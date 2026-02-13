"""Getting started guide for Sozo backend development."""
# Getting Started with Sozo

## Quick Start (Docker Compose)

### Prerequisites
- Docker and Docker Compose installed
- git (for cloning)

### Setup (2 minutes)
```bash
# Clone repository
git clone <repository-url>
cd Sozo

# Create environment file
cp .env.example .env

# Start all services
docker-compose up

# Verify it's running
curl http://localhost:8000/health
```

**The API is now available at**: `http://localhost:8000`
- **API Documentation**: http://localhost:8000/api/v1/docs
- **Database**: Running on localhost:1433

### Test the API
```bash
# Register a new user
curl -X POST "http://localhost:8000/api/v1/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "doctor@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "password": "SecurePassword123!",
    "role": "clinician"
  }'

# Login
curl -X POST "http://localhost:8000/api/v1/users/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "doctor@example.com",
    "password": "SecurePassword123!"
  }'

# You'll get tokens - use the access_token in Authorization header
```

---

## Local Development Setup

### Prerequisites
- Python 3.11+
- MSSQL Server (local or Docker)
- pip and virtualenv

### Installation Steps

#### 1. Create Python environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 2. Install dependencies
```bash
pip install -r requirements.txt
```

#### 3. Setup environment variables
```bash
cp .env.example .env

# Edit .env and update:
# DATABASE_HOST=localhost
# DATABASE_PASSWORD=<your_sa_password>
# JWT_SECRET_KEY=<your-secret-key-minimum-32-chars>
```

#### 4. Start MSSQL in Docker (if not installed locally)
```bash
docker run -e "ACCEPT_EULA=Y" -e "SA_PASSWORD=YourPassword123!" \
  -p 1433:1433 \
  mcr.microsoft.com/mssql/server:2022-latest
```

#### 5. Run database migrations (future)
```bash
# When Alembic is fully configured:
# alembic upgrade head
```

#### 6. Start development server
```bash
# With auto-reload
uvicorn app.main:app --reload

# Or run directly
python -m uvicorn app.main:app --reload --log-level debug
```

**API is available at**: `http://localhost:8000`

---

## Project Structure Navigation

### Where to find things:

```
app/core/              # Cross-cutting infrastructure
  ├── config.py       # ← Settings & environment
  ├── security.py     # ← JWT, password, RBAC
  ├── database.py     # ← SQLAlchemy setup
  └── dependencies.py # ← Dependency injection

app/modules/patients/ # ← Example module to study
  ├── models.py       # Database models
  ├── schemas.py      # Request/response schemas
  ├── repository.py   # Data access
  ├── service.py      # Business logic
  └── router.py       # HTTP endpoints

app/modules/prs_engine/
  └── scoring.py      # ← Pure domain logic (no FastAPI!)

app/modules/workflow/
  └── state_machine.py # ← Pure domain logic
```

---

## Common Tasks

### 1. Create a New API Endpoint

Create folder `app/modules/assessments/` with these files:

**models.py**: Database model
```python
from app.shared.models import BaseModel
from sqlalchemy import Column, String, Float, DateTime

class Assessment(BaseModel):
    __tablename__ = "assessments"
    
    patient_id = Column(String(36), nullable=False)
    assessment_type = Column(String(50), nullable=False)
    score = Column(Float, nullable=True)
    completed_at = Column(DateTime, nullable=True)
```

**schemas.py**: Request/response schemas
```python
from pydantic import BaseModel
from datetime import datetime

class AssessmentCreate(BaseModel):
    patient_id: str
    assessment_type: str

class AssessmentResponse(BaseModel):
    id: str
    patient_id: str
    score: float | None
    created_at: datetime
    
    class Config:
        from_attributes = True
```

**repository.py**: Data access
```python
from app.shared.models.base_repository import BaseRepository
from sqlalchemy import select
from .models import Assessment

class AssessmentRepository(BaseRepository[Assessment]):
    def __init__(self, session):
        super().__init__(session, Assessment)
    
    async def get_by_patient(self, patient_id: str):
        query = select(Assessment).where(
            Assessment.patient_id == patient_id
        )
        result = await self.session.execute(query)
        return result.scalars().all()
```

**service.py**: Business logic
```python
from .repository import AssessmentRepository
from .schemas import AssessmentCreate, AssessmentResponse

class AssessmentService:
    def __init__(self, session):
        self.repository = AssessmentRepository(session)
    
    async def create_assessment(self, data: AssessmentCreate):
        assessment = await self.repository.create(
            patient_id=data.patient_id,
            assessment_type=data.assessment_type
        )
        await self.repository.commit()
        return AssessmentResponse.from_attributes(assessment)
    
    async def get_patient_assessments(self, patient_id: str):
        assessments = await self.repository.get_by_patient(patient_id)
        return [AssessmentResponse.from_attributes(a) for a in assessments]
```

**router.py**: HTTP endpoints
```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user
from .schemas import AssessmentCreate, AssessmentResponse
from .service import AssessmentService

router = APIRouter(tags=["assessments"], prefix="/assessments")

@router.post("", response_model=AssessmentResponse)
async def create_assessment(
    data: AssessmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    service = AssessmentService(db)
    return await service.create_assessment(data)

@router.get("/patient/{patient_id}", response_model=list[AssessmentResponse])
async def get_patient_assessments(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    service = AssessmentService(db)
    return await service.get_patient_assessments(patient_id)
```

**Register in main.py**:
```python
from app.modules.assessments.router import router as assessments_router

@app.include_router(assessments_router, prefix=settings.api_v1_prefix)
```

### 2. Add a Business Logic Algorithm

Create `app/modules/scoring_engine/calculator.py` (pure logic, no framework imports):

```python
# NO FastAPI, SQLAlchemy imports!
# Only standard library

class ScoringCalculator:
    """Pure algorithm - testable without mocks."""
    
    def calculate_composite_score(self, components: dict) -> float:
        """Calculate weighted score."""
        return (
            components["clinical"] * 0.4 +
            components["psychosocial"] * 0.35 +
            components["social"] * 0.25
        )
    
    def get_risk_category(self, score: float) -> str:
        """Determine risk level."""
        if score >= 75:
            return "CRITICAL"
        elif score >= 60:
            return "HIGH"
        elif score >= 40:
            return "MEDIUM"
        else:
            return "LOW"
```

**Test it** (pure unit test, no database):
```python
# app/tests/test_scoring.py
import pytest
from app.modules.scoring_engine.calculator import ScoringCalculator

def test_scoring():
    calc = ScoringCalculator()
    score = calc.calculate_composite_score({
        "clinical": 70,
        "psychosocial": 60,
        "social": 50
    })
    assert 60 < score < 65
    assert calc.get_risk_category(score) == "HIGH"
```

### 3. Call Domain Logic from Service

```python
# app/modules/assessments/service.py
from app.modules.scoring_engine.calculator import ScoringCalculator

class AssessmentService:
    def __init__(self, session):
        self.repository = AssessmentRepository(session)
        self.calculator = ScoringCalculator()  # Pure logic
    
    async def score_assessment(self, assessment_id: str):
        # Fetch data
        assessment = await self.repository.get_by_id(assessment_id)
        
        # Calculate (pure logic)
        score = self.calculator.calculate_composite_score({
            "clinical": assessment.clinical_score,
            "psychosocial": assessment.psych_score,
            "social": assessment.social_score
        })
        
        # Persist result
        updated = await self.repository.update(
            assessment_id,
            final_score=score,
            category=self.calculator.get_risk_category(score)
        )
        
        await self.repository.commit()
        return updated
```

### 4. Enforce Authorization

```python
from app.core.dependencies import require_roles

@router.delete("/{assessment_id}")
async def delete_assessment(
    assessment_id: str,
    # Only clinicians and admins can delete
    current_user = Depends(require_roles("clinician", "admin")),
    db: AsyncSession = Depends(get_db)
):
    # Only proceed if user has required role
    service = AssessmentService(db)
    return await service.delete_assessment(assessment_id, current_user.user_id)
```

### 5. Add Audit Logging

```python
from app.modules.audit.audit import audit_service, AuditAction

class AssessmentService:
    async def score_assessment(self, assessment_id: str, actor_id: str):
        # ... scoring logic ...
        
        # Log the action
        await audit_service.log_action(
            actor_id=actor_id,
            action=AuditAction.CALCULATE,
            entity_type="Assessment",
            entity_id=assessment_id,
            metadata={"score": final_score, "category": category}
        )
        
        return updated
```

---

## Testing

### Run Tests
```bash
# All tests
pytest

# Specific test file
pytest app/tests/test_prs_engine.py

# With coverage report
pytest --cov=app --cov-report=html

# Watch mode (auto-run on file changes)
pytest-watch
```

### Write a Test
```python
# app/tests/test_my_feature.py
import pytest
from app.modules.patients.service import PatientService

@pytest.mark.asyncio
async def test_patient_creation(test_db):
    """Test creating a patient."""
    service = PatientService(test_db)
    
    result = await service.create_patient({
        "user_id": "user-123",
        "phone": "555-1234"
    })
    
    assert result.id is not None
    assert result.user_id == "user-123"
```

---

## Debugging

### View API Docs
- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc

### View Logs
```bash
# Development server logs (JSON format)
# Look for:
# - "level": "ERROR" for errors
# - "audit" key for audit events
# - "operation" key for SQL queries

# Filter logs in Docker
docker-compose logs -f api | grep ERROR
docker-compose logs -f api | jq '. | select(.action == "CREATE")'
```

### Database Admin Tools
```bash
# Connect with Azure Data Studio or SQL Server Management Studio
Server: localhost
User: sa
Password: (from .env)
Database: sozo_dev

# Or use command line
docker-compose exec mssql /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P YourPassword123!
```

### Debug Mode
In `.env`:
```
DEBUG=true
LOG_LEVEL=DEBUG
DATABASE_ECHO=true  # Log SQL queries
```

---

## Code Style & Quality

### Format Code
```bash
# Auto-format with black
black app/

# Sort imports
isort app/

# Lint
flake8 app/

# Type checking
mypy app/
```

### Pre-commit Hooks (Recommended)
```bash
# pip install pre-commit
# pre-commit install
# Then hooks run automatically on commit
```

---

## Common Issues & Solutions

### Issue: `ModuleNotFoundError: No module named 'app'`
**Solution**: Run from project root, ensure PYTHONPATH includes current directory
```bash
cd /path/to/Sozo
python -m uvicorn app.main:app --reload
```

### Issue: Database connection timeout
**Solution**: Ensure MSSQL is running
```bash
docker-compose up mssql  # Start just the DB
docker ps  # Verify container is running
```

### Issue: Port 8000 already in use
**Solution**: Use different port
```bash
uvicorn app.main:app --reload --port 8001
```

### Issue: JWT token expired
**Solution**: Get new token via login endpoint
```bash
curl -X POST "http://localhost:8000/api/v1/users/login" ...
```

---

## Next Steps

1. **Explore the code**: Start with `app/modules/patients/` - it's fully implemented
2. **Run tests**: `pytest` - understand test patterns
3. **Create a feature**: Follow the "Create New Endpoint" section above
4. **Read ARCHITECTURE.md**: Understand design decisions
5. **Check API docs**: Swagger at `/api/v1/docs`

---

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Pydantic v2](https://docs.pydantic.dev/latest/)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Domain-Driven Design](https://en.wikipedia.org/wiki/Domain-driven_design)

---

## Support

For questions:
1. Check the README.md
2. Check ARCHITECTURE.md
3. Review similar modules for patterns
4. Read code comments
5. Contact: dev@sozo.health
