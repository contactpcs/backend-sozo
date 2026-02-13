# Sozo Healthcare Platform API

Production-grade healthcare SaaS backend built with clean architecture principles, domain-driven design, and modular monolith structure.

## Overview

Sozo is a comprehensive healthcare platform designed to handle:
- Patient intake and registration
- Clinical and psychosocial assessments
- PRS (Patient Risk Score) computation
- Intelligent patient routing and center assignment
- Workflow state management
- Document handling and AI-based summarization
- Comprehensive audit logging
- HIPAA-compliant data management

## Architecture Principles

### Clean Architecture
The application follows clean architecture with strict separation of concerns:

```
User (HTTP Request)
        ↓
    Router/Handler (HTTP layer - no business logic)
        ↓
    Service (Business logic & orchestration)
        ↓
    Repository (Data access - SQLAlchemy only)
        ↓
    Database
```

### Domain-Driven Design
Each domain module is self-contained with:
- **Models**: Domain entities and ORM models
- **Schemas**: Pydantic v2 request/response validation
- **Service**: Business logic and orchestration
- **Repository**: Data access layer
- **Router**: HTTP endpoints and handlers

### Modular Monolith (Not Microservices)
The application is structured as a monolith with clear module boundaries:
- **Autonomy**: Each module can be independently developed/tested
- **Shared Infrastructure**: Core database, auth, config shared
- **Future Microservices**: Clear boundaries for later decomposition
- **Deployment**: Single containerized unit for simplicity

### Domain Logic Isolation
Pure business logic (PRS Scoring, Routing, Workflow) is completely isolated:
- No FastAPI imports
- No SQLAlchemy imports
- Deterministic & versionable
- Fully testable in isolation
- Reusable across layers

## Project Structure

```
Sozo/
├── app/
│   ├── core/                          # Cross-cutting concerns
│   │   ├── config.py                  # Environment-based configuration
│   │   ├── database.py               # Async SQLAlchemy setup
│   │   ├── security.py               # JWT, password hashing, RBAC
│   │   ├── dependencies.py           # Dependency injection
│   │   ├── logging.py                # Structured logging
│   │   └── constants.py              # App-wide constants
│   │
│   ├── shared/                        # Shared domain models & utilities
│   │   ├── models/
│   │   │   ├── base_repository.py    # Generic repository pattern
│   │   │   └── __init__.py           # Base SQLAlchemy model
│   │   ├── schemas/
│   │   │   ├── __init__.py           # Pagination, responses
│   │   │   └── auth.py               # Auth schemas
│   │   ├── exceptions/
│   │   │   └── __init__.py           # Custom exception hierarchy
│   │   ├── utils/
│   │   │   └── __init__.py           # Helper functions
│   │   └── types.py                  # Type aliases
│   │
│   ├── modules/                       # Domain modules (modular monolith)
│   │
│   │   ├── users/
│   │   │   ├── models.py             # User ORM models
│   │   │   ├── schemas.py            # Request/response schemas
│   │   │   ├── repository.py         # Data access
│   │   │   ├── service.py            # Business logic
│   │   │   └── router.py             # HTTP endpoints
│   │   │
│   │   ├── patients/                 # Core domain entity
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── repository.py
│   │   │   ├── service.py
│   │   │   └── router.py
│   │   │
│   │   ├── assessments/              # Clinical assessments
│   │   │   └── models.py
│   │   │
│   │   ├── prs_engine/               # Pure domain logic
│   │   │   └── scoring.py            # PRS calculation (no FastAPI/SQLAlchemy)
│   │   │
│   │   ├── routing_engine/           # Pure domain logic
│   │   │   └── routing.py            # Patient routing algorithm
│   │   │
│   │   ├── workflow/                 # Workflow state machine
│   │   │   └── state_machine.py      # Finite state machine (pure logic)
│   │   │
│   │   ├── ai/                       # LLM abstraction layer
│   │   │   └── llm_provider.py       # Provider-agnostic LLM client
│   │   │
│   │   ├── audit/                    # Audit logging
│   │   │   └── audit.py              # Centralized audit service
│   │   │
│   │   ├── documents/                # Document handling
│   │   │   └── models.py
│   │   │
│   │   └── centers/                  # Healthcare centers
│   │       └── models.py
│   │
│   ├── infrastructure/                # External integrations
│   │   ├── external_clients/
│   │   │   └── azure_storage.py      # Azure Blob Storage
│   │   ├── storage/
│   │   ├── messaging/
│   │   └── providers/
│   │
│   ├── tests/                         # Testing
│   │   ├── conftest.py               # Pytest fixtures
│   │   └── test_prs_engine.py        # Example tests
│   │
│   └── main.py                        # FastAPI application entry point
│
├── alembic/                           # Database migrations
│   ├── versions/
│   │   └── 001_initial.py
│   ├── env.py
│   └── script.py.mako
│
├── requirements.txt                   # Python dependencies
├── Dockerfile                         # Production container
├── docker-compose.yml                 # Local development setup
├── .env.example                       # Environment template
├── alembic.ini                        # Alembic configuration
└── README.md                          # This file
```

## Architecture Boundaries

### Layer 1: HTTP Layer (Router)
**Responsibility**: Handle HTTP concerns only

- Transform requests to domain input
- Transform domain output to responses
- Authentication/Authorization checks
- No business logic

```python
# Example: Patient router
@router.post("/patients", response_model=PatientResponse)
async def create_patient(
    patient_data: PatientCreate,
    current_user: JWTClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = PatientService(db)
    return await service.create_patient(patient_data)
```

### Layer 2: Business Logic Layer (Service)
**Responsibility**: Orchestrate use cases and domain logic

- Validate business rules
- Call repositories for data
- Call domain logic (PRS, Routing, Workflow)
- Coordinate transactions
- Handle orchestration

```python
# Example: Patient service
class PatientService:
    def __init__(self, session: AsyncSession):
        self.repository = PatientRepository(session)
    
    async def complete_intake(self, patient_id: str, intake_data):
        # Business validation
        patient = await self.repository.get_by_id(patient_id)
        
        # Check state transition validity
        if patient.workflow_state != WorkflowState.INTAKE.value:
            raise InvalidStateTransition(...)
        
        # Update state
        updated = await self.repository.update(...)
        await self.repository.commit()
        
        return PatientResponse.from_attributes(updated)
```

### Layer 3: Data Access Layer (Repository)
**Responsibility**: Pure data operations

- SQL queries only
- No business logic
- Generic base repository pattern
- SQLAlchemy async only

```python
# Example: Patient repository
class PatientRepository(BaseRepository[Patient]):
    async def get_by_user_id(self, user_id: str):
        query = select(Patient).where(Patient.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalars().first()
```

### Layer 4: Domain Logic (Pure Domain)
**Responsibility**: Core business algorithms

- PRS Scoring Engine: Calculate patient risk scores
- Routing Engine: Determine optimal center assignment
- Workflow State Machine: Validate state transitions
- Audit Service: Centralized event logging

**These modules MUST NOT import from**:
- `fastapi` 
- `sqlalchemy`
- `pydantic` (except for data classes)
- Any HTTP layer code

This ensures domain logic is:
- Testable in isolation
- Reusable across channels (CLI, API, batch jobs)
- Framework-agnostic
- Easy to version and maintain

### Layer 5: Infrastructure
**Responsibility**: External service integration

- Azure Storage Client
- LLM Provider Clients
- Messaging systems
- Cache/Redis
- Monitoring/Logging

## Key Design Patterns

### 1. Dependency Injection
```python
# Core dependencies
async def get_current_user(claims: JWTClaims = Depends(get_jwt_bearer())):
    return claims

async def require_roles(*allowed_roles: str):
    async def check(claims: JWTClaims = Depends(get_current_user)):
        # Validate roles
        return claims
    return check
```

### 2. Repository Pattern
```python
class BaseRepository(Generic[T]):
    async def create(self, **kwargs) -> T: ...
    async def get_by_id(self, entity_id: UUID) -> Optional[T]: ...
    async def update(self, entity_id: UUID, **kwargs) -> Optional[T]: ...
    async def delete(self, entity_id: UUID) -> bool: ...
```

### 3. Service Layer Orchestration
```python
class PatientService:
    """Orchestrates use cases using repositories and domain logic."""
    
    async def complete_intake(self, patient_id, intake_data):
        # Fetch data
        patient = await self.repository.get_by_id(patient_id)
        
        # Validate business rules
        if patient.workflow_state != INTAKE:
            raise InvalidStateTransition(...)
        
        # Update data
        updated = await self.repository.update(...)
        
        # Log audit event
        await audit_service.log_action(...)
        
        # Commit transaction
        await self.repository.commit()
        
        return response
```

### 4. Pure Domain Logic
```python
# NO imports from fastapi, sqlalchemy, http libs
# Only standard library and dataclasses

class PRSScoringEngine:
    """Pure algorithm - testable in isolation."""
    
    def calculate_prs(self, clinical_data, psychosocial_data, social_data):
        # Pure computation
        score = self._calculate_components(...)
        category = self._determine_category(score)
        recommendations = self._generate_recommendations(...)
        
        return PRSScore(...)
```

### 5. AI Abstraction Layer
```python
# Provider-agnostic interface
class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> LLMResponse: pass

# Pluggable implementations
class OpenAIProvider(LLMProvider): ...
class AzureOpenAIProvider(LLMProvider): ...
class ClaudeProvider(LLMProvider): ...

# Factory pattern
provider = LLMFactory.create_provider("openai", api_key="...")
```

## Security Architecture

### Authentication
- **Scheme**: JWT (HS256 or RS256)
- **Token Types**: Access (15min default) & Refresh (7 days)
- **Bearer**: HTTP Authorization header
- **Storage**: Never in local storage (httponly cookies recommended)

### Authorization
- **RBAC**: Role-based access control
- **Roles**: admin, clinician, nurse, patient, center_manager
- **Decorators**: `@require_roles("admin", "clinician")`

### Data Protection
- **Passwords**: bcrypt hashing (passlib)
- **HTTPS**: Required in production
- **CORS**: Configurable origin restrictions
- **Secrets**: Azure Key Vault integration ready

### Audit Logging
Every state change is logged:
- Actor (user ID)
- Action (CREATE, UPDATE, TRANSITION, etc.)
- Entity (Patient, Assessment, etc.)
- Changes (before/after values)
- Timestamp
- Metadata (context)

## Database Design

### Schema Principles
- **UUIDs**: Primary keys (string format)
- **Soft Deletes**: `is_deleted`, `deleted_at` columns
- **Audit Trail**: `created_at`, `updated_at`, `created_by`, `updated_by`
- **Versioning**: Assessment versions tracked
- **Immutability**: Historical data preserved

### Supported Databases
- **Production**: Azure SQL Server (MSSQL)
- **Development**: SQLite (in-memory for tests)
- **Future**: PostgreSQL, MySQL

### Async SQL
- **Engine**: SQLAlchemy 2.0+ async
- **Driver**: `mssql+pyodbc_asyncio` for SQL Server
- **Pooling**: Connection pooling with configurable size
- **ORM**: Full async support with `AsyncSession`

## Configuration

### Environment-Based
```python
# Loaded from .env via Pydantic Settings v2
settings = get_settings()  # Cached singleton

# Access pattern
print(settings.database.host)
print(settings.jwt.access_token_expire_minutes)
print(settings.ai.provider)
```

### Configuration Hierarchy
1. `.env` file (local overrides)
2. Environment variables with `__` prefix
3. Default values in Settings class
4. Type validation via Pydantic

## Deployment

### Local Development
```bash
# Setup
cp .env.example .env

# With Docker Compose
docker-compose up

# Or with local install
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Azure App Service
```dockerfile
# Single container deployment
docker build -t sozo:latest .
az acr build --registry <registry> --image sozo:latest .
az containerapp create --resource-group <rg> --image sozo:latest
```

### Health Checks
- `/health`: Basic health status
- `/readiness`: Kubernetes readiness probe
- `/liveness`: Kubernetes liveness probe

### Monitoring
- Structured JSON logging
- Request ID tracking
- Performance metrics ready
- Error rate monitoring

## Testing

### Unit Tests (Pure Logic)
```python
# Test domain logic in isolation
def test_prs_low_risk():
    engine = PRSScoringEngine()
    result = engine.calculate_prs(low_risk_data)
    assert result.category == "LOW"
```

### Integration Tests
```python
# Test repository + database
@pytest.mark.asyncio
async def test_patient_creation(test_db):
    repo = PatientRepository(test_db)
    patient = await repo.create(...)
    assert patient.id is not None
```

### API Tests
```python
# Test endpoints
def test_create_patient_endpoint(client):
    response = client.post("/api/v1/patients", json=patient_data)
    assert response.status_code == 201
```

## API Endpoints

### Authentication
```
POST   /api/v1/users/register       # Register new user
POST   /api/v1/users/login          # User login
POST   /api/v1/users/refresh        # Refresh token
```

### Patients (Core Domain)
```
POST   /api/v1/patients             # Create patient
GET    /api/v1/patients/{id}        # Get patient details
PATCH  /api/v1/patients/{id}        # Update patient
GET    /api/v1/patients/search      # Search patients
POST   /api/v1/patients/{id}/intake/complete      # Complete intake
POST   /api/v1/patients/{id}/workflow/transition  # State transition
POST   /api/v1/patients/{id}/assign/center/{center_id}         # Assign to center
POST   /api/v1/patients/{id}/assign/clinician/{clinician_id}   # Assign to clinician
```

### Health/Status
```
GET    /health      # Application health
GET    /readiness   # Kubernetes readiness
GET    /liveness    # Kubernetes liveness
GET    /            # API root with metadata
```

## Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Framework | FastAPI | Type safety, async, auto docs |
| ORM | SQLAlchemy 2.0 | Async support, flexibility |
| Database | Azure SQL | Enterprise support, MSSQL |
| Validation | Pydantic v2 | Type validation, serialization |
| Authentication | JWT | Stateless, scalable |
| Security | bcrypt | Industry standard hashing |
| Logging | Python JSON Logger | Structured, cloud-ready |
| Testing | pytest | Async support, fixtures |
| AI/LLM | Abstract providers | OpenAI, Azure OpenAI, Claude |
| Storage | Azure Blob | Enterprise cloud storage |

## Running the Application

### Prerequisites
- Python 3.11+
- Docker (optional)
- Azure SQL Server (production)

### Development Setup
```bash
# Create environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your configuration

# Run migrations (if using Alembic)
alembic upgrade head

# Start development server
uvicorn app.main:app --reload

# Access API
# Docs: http://localhost:8000/api/v1/docs
# ReDoc: http://localhost:8000/api/v1/redoc
```

### Docker Deployment
```bash
# Build image
docker build -t sozo:latest .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_HOST=<host> \
  -e DATABASE_PASSWORD=<password> \
  sozo:latest

# Or with Docker Compose
docker-compose up
```

## Future Roadmap

### Phase 2: Enhanced Features
- [ ] Questionnaire engine
- [ ] Advanced assessment workflows
- [ ] Document processing (OCR, summarization)
- [ ] Real-time notifications
- [ ] Batch processing jobs

### Phase 3: Microservices Decomposition
- Separate PRS/Routing engines as services
- Extract AI/LLM as dedicated service
- Audit logging service
- Document processing service

### Phase 4: Advanced Capabilities
- Complex workflow orchestration
- Real-time analytics dashboard
- Advanced FHIR support
- HL7 message processing

## Contributing

### Code Quality
- Follow PEP 8
- Use type hints
- Write docstrings
- Add unit tests
- Format with black

### Pull Request Process
1. Create feature branch
2. Write tests first (TDD)
3. Ensure all tests pass
4. Format code
5. Submit PR with description

## License

Proprietary - Sozo Healthcare Platform

## Support

For questions or issues, contact: support@sozo.health
