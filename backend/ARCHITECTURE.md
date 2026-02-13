"""Detailed architecture and design decisions."""
# Sozo Architecture Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architectural Decisions](#architectural-decisions)
3. [Module Design](#module-design)
4. [Data Flow](#data-flow)
5. [Scalability Considerations](#scalability-considerations)

## System Overview

### Purpose
Sozo is a healthcare platform designed to:
- Streamline patient intake and assessment
- Calculate risk scores using evidence-based algorithms
- Route patients to appropriate care centers
- Manage clinical workflows
- Provide audit trails for compliance

### Design Paradigm: Clean Architecture + Domain-Driven Design

```
                        External Interfaces
                        (HTTP, Files, etc)
                              ↓
        ╔════════════════════════════════════════╗
        ║        FastAPI Routes (HTTP Layer)     ║
        ║          • No business logic           ║
        ║          • Request/response handling   ║
        ║          • Authentication checks       ║
        ╚════════════════════════════════════════╝
                              ↓
        ╔════════════════════════════════════════╗
        ║      Service Layer (Business Logic)    ║
        ║      • Orchestration & composition     ║
        ║      • Business rule validation        ║
        ║      • Transaction management          ║
        ║      • Error handling                  ║
        ╚════════════════════════════════════════╝
                              ↓
        ╔════════════════════════════════════════╗
        ║     Domain Logic (Pure & Testable)     ║
        ║     • PRS Scoring Algorithm            ║
        ║     • Routing Engine                   ║
        ║     • Workflow State Machine           ║
        ║     • Audit Service                    ║
        ╚════════════════════════════════════════╝
                              ↓
        ╔════════════════════════════════════════╗
        ║   Repository Layer (Data Access)       ║
        ║     • SQL queries only                 ║
        ║     • ORM mapping                      ║
        ║     • No business rules                ║
        ╚════════════════════════════════════════╝
                              ↓
                        Database Layer
```

## Architectural Decisions

### 1. Modular Monolith (Not Microservices)

**Decision**: Build as a single deployable unit with clear module boundaries.

**Rationale**:
- ✅ Simpler initial deployment
- ✅ Easier distributed transactions
- ✅ Shared database simplifies consistency
- ✅ Clear path to microservices later
- ⚠️ Requires strict module boundaries to prevent coupling

**Trade-offs**:
- Single point of failure (mitigated with redundancy)
- Shared databases can become bottleneck (addressable via sharding)
- Module boundaries must be enforced in code review

**Future Path**: Extract high-load modules as microservices:
1. PRS/Routing engines → Compute service
2. AI/LLM → Dedicated service
3. Audit logging → Event stream service
4. Documents → File processing service

### 2. Async-First Architecture

**Decision**: Use async/await throughout with SQLAlchemy async ORM.

**Rationale**:
- ✅ Handles high concurrency efficiently
- ✅ Better CPU utilization
- ✅ Naturally scales horizontally
- ✅ Modern Python best practice
- ⚠️ Requires careful error handling

**Implementation**:
- FastAPI with uvicorn
- SQLAlchemy + asyncpg + aiosqlite
- Async context managers for resource cleanup

### 3. Azure SQL as Primary Database

**Decision**: Use Azure SQL Server (MSSQL) with SQLAlchemy async.

**Rationale**:
- ✅ Enterprise-grade ACID compliance
- ✅ Azure ecosystem integration
- ✅ Automatic backups, redundancy
- ✅ Secure by default
- ✅ HIPAA compliance ready

**Fallback Options**:
- PostgreSQL (via `asyncpg`)
- MySQL (via `aiomysql`)
- SQLite (for testing)

### 4. JWT for Authentication

**Decision**: Stateless JWT tokens with separate access/refresh tokens.

**Rationale**:
- ✅ Scalable across multiple servers
- ✅ No session state to maintain
- ✅ Mobile-friendly
- ✅ CORS-friendly
- ⚠️ Token revocation requires additional mechanism

**Security**:
- HS256 with strong secret (rotate in production)
- Access token: 15 minutes
- Refresh token: 7 days
- httponly cookies recommended

### 5. Pure Domain Logic Encapsulation

**Decision**: All business algorithms (PRS, Routing, Workflow) are framework-agnostic.

**Rationale**:
- ✅ Reusable in any context (CLI, batch, API, another service)
- ✅ Fully testable without mocks
- ✅ Version-controlled algorithms
- ✅ Easier to understand business intent
- ✅ Prevents framework creep into business logic

**Enforcement**:
- No FastAPI imports in domain modules
- No SQLAlchemy imports in domain modules
- Only standard library + dataclasses
- Code review checklists for verification

### 6. Repository Pattern for Data Access

**Decision**: SQLAlchemy queries hidden behind repository interfaces.

**Rationale**:
- ✅ Prevents SQL leakage into services
- ✅ Easier to swap storage implementations
- ✅ Testable with mocked repositories
- ✅ Clear data access API
- ⚠️ Some query complexity might require raw SQL

**Implementation**:
- Generic `BaseRepository[T]` with CRUD operations
- Module-specific repos extend base
- Specialized query methods as needed

### 7. Role-Based Access Control (RBAC)

**Decision**: Simple, role-based authorization with fastapi dependencies.

**Rationale**:
- ✅ Easy to understand and implement
- ✅ Sufficient for healthcare domain
- ✅ Well-supported by FastAPI
- ⚠️ Doesn't handle complex attribute-based policies (future: ABAC)

**Roles**:
- `admin`: Full system access
- `clinician`: Clinical operations
- `nurse`: Assessments and patient care
- `patient`: Self-service access
- `center_manager`: Center management

### 8. Structured Logging with JSON Format

**Decision**: All logs structured as JSON for cloud-native deployment.

**Rationale**:
- ✅ Easily ingested into log aggregation (ELK, Azure Monitor)
- ✅ Searchable and queryable
- ✅ Standardized format
- ✅ Machine-parseable
- ⚠️ Less human-readable in local development

**Local Development**: Can override with text format via env var.

### 9. Soft Deletes for Data Preservation

**Decision**: Mark deleted records with `is_deleted` flag instead of removing.

**Rationale**:
- ✅ Preserves audit trail
- ✅ Enables accidental deletion recovery
- ✅ Maintains referential integrity
- ✅ Required for healthcare compliance
- ⚠️ Requires WHERE filters on every active record query

**Implementation**:
```python
is_deleted = Column(Boolean, default=False, nullable=False)
deleted_at = Column(DateTime, nullable=True)

# Query active records
query = select(Model).where(Model.is_deleted == False)
```

### 10. UUID Primary Keys

**Decision**: Use UUID (string) instead of auto-increment integers.

**Rationale**:
- ✅ Globally unique across services
- ✅ Prepared for microservices/sharding
- ✅ Better for distributed systems
- ✅ No ID collision on merge/migration
- ⚠️ Larger index size
- ⚠️ Less sortable for time-based queries

**Trade-off**: Can add `created_at` indexed column for time-based sorting.

## Module Design

### Users Module
**Responsibility**: User management and authentication

**Components**:
- `models.User`: User entity with roles and credentials
- `UserRepository`: User CRUD and lookup operations
- `UserService`: Registration, authentication, token generation
- `router`: Login, registration, profile endpoints

**Key Operations**:
- User registration with email verification
- Password hashing (bcrypt)
- JWT token generation
- User profile management

### Patients Module
**Responsibility**: Core patient domain

**Components**:
- `models.Patient`: Patient entity with workflow state
- `PatientRepository`: Patient queries and searches
- `PatientService`: Patient lifecycle management
- `router`: Patient endpoints with auth checks

**Key Operations**:
- Patient intake process
- Workflow state transitions
- Center/clinician assignment
- Patient search and filtering

### PRS Engine
**Responsibility**: Patient risk score calculation

**Nature**: Pure domain logic (no framework dependencies)

**Components**:
- `PRSScoringEngine`: Algorithm implementation
- `PRSScore`: Result data class

**Algorithm**:
- Weighted scoring across 3 dimensions:
  - Clinical Risk (40%): Conditions, meds, hospitalizations, etc.
  - Psychosocial Risk (35%): Mental health, substance abuse, suicide risk
  - Social Determinants (25%): Housing, employment, education, barriers
- Risk category: LOW, MEDIUM, HIGH, CRITICAL
- Explanations and recommendations generated

**Versioning**: All scoring versions tracked for reproducibility.

### Routing Engine
**Responsibility**: Optimal patient-to-center assignment

**Nature**: Pure domain logic

**Components**:
- `RoutingEngine`: Routing algorithm
- `RoutingDecision`: Assignment result

**Scoring Factors**:
- Geographic proximity (20%)
- Clinical specialty match (25%)
- Available clinician capacity (20%)
- Center performance metrics (15%)
- Patient language/cultural fit (10%)
- Insurance acceptance (10%)

**Output**: Ranked list of centers with reasoning.

### Workflow Engine
**Responsibility**: Finite state machine for patient journey

**States**:
```
INTAKE → ASSESSMENT → SCORING → ROUTING → ASSIGNMENT → ACTIVE → [COMPLETED|ARCHIVED]
```

**Validation**: Only allows defined state transitions. Prevents invalid flows.

### Audit Module
**Responsibility**: Centralized event logging

**Logged Events**:
- CREATE: New entity created
- UPDATE: Entity modified
- DELETE: Entity deleted
- TRANSITION: Workflow state change
- CALCULATE: PRS or other calculations
- ASSIGN: Patient assigned to center/clinician
- APPROVE: Document or assessment approved

**Attributes**:
- Actor (user_id)
- Action type
- Entity type & ID
- Before/after values
- Timestamp
- Metadata (context)

**Storage**: Persisted to database + structured logging.

### AI Module
**Responsibility**: LLM abstraction for summarization and extraction

**Providers**:
1. OpenAI (GPT-4, GPT-3.5)
2. Azure OpenAI (same models, Azure hosting)
3. Claude (Anthropic)

**Interface**:
```python
class LLMProvider(ABC):
    async def generate(prompt: str, max_tokens: int) -> str
    async def summarize(text: str) -> str
```

**Use Cases**:
- Clinical note summarization
- Key finding extraction
- Document processing

## Data Flow

### Patient Intake Flow
```
1. User (Patient) Registration
   └─ Router receives UserCreate
   └─ UserService validates & creates
   └─ PasswordManager hashes password
   └─ User persisted via UserRepository
   └─ JWT tokens generated
   └─ Response sent with tokens

2. Patient Record Creation
   └─ Clinician creates patient from user
   └─ PatientService creates record
   └─ Workflow state: INTAKE
   └─ AuditService logs CREATE event

3. Intake Questionnaire
   └─ Patient fills intake form
   └─ PatientService validates data
   └─ WorkflowEngine validates transition
   └─ State changes: INTAKE → ASSESSMENT
   └─ AuditService logs TRANSITION

4. Assessment & PRS Calculation
   └─ Clinician enters assessment data
   └─ AssessmentService persists responses
   └─ PRSScoringEngine calculates score (pure logic)
   └─ Score persisted with assessment
   └─ AuditService logs CALCULATE
   └─ Recommendations generated

5. Routing & Assignment
   └─ RoutingEngine evaluates available centers
   └─ Scores centers against patient profile
   └─ PatientService calls RoutingEngine
   └─ Recommended center selected
   └─ Patient assigned to center
   └─ Clinician assigned
   └─ AuditService logs ASSIGN
   └─ Workflow progresses: ASSESSMENT → SCORING → ROUTING → ASSIGNMENT → ACTIVE

6. Document Processing
   └─ Clinician uploads document
   └─ DocumentService validates file
   └─ AzureStorageClient uploads to blob
   └─ Document metadata persisted
   └─ AI module summarizes if needed
   └─ AuditService logs CREATE + PROCESS
```

### API Request-Response Cycle
```
HTTP Request
    ↓
Router Layer
    • Authentication -> JWT validation
    • Authorization -> Role checks
    • Parsing -> Pydantic schema validation
    ↓
Service Layer
    • Business rules validation
    • Authorization checks
    • Repository calls
    • Domain logic invocation
    • Audit log creation
    ↓
Repository Layer
    • Database query execution
    • Model hydration
    ↓
Service Layer (continued)
    • Response preparation
    ↓
Router Layer
    • Pydantic response serialization
    ↓
HTTP Response
```

## Scalability Considerations

### Horizontal Scaling
The architecture supports running multiple instances:
- **Stateless HTTP layer**: API servers can be stateless
- **Shared database**: All instances write/read from same DB
- **JWT tokens**: No session state needed
- **Load balancer**: Route requests across instances

**Scaling Plan**:
1. API tier (horizontal): Multiple FastAPI instances
2. Database: Azure SQL with read replicas
3. Cache layer: Redis for frequent queries (future)
4. Background jobs: Celery for async tasks (future)

### Database Optimization
- **Indexes**: On frequently queried columns (email, user_id, patient_id)
- **Partitioning**: Future - partition by center or date range
- **Archiving**: Soft delete + historical tables for old records
- **Connection pooling**: Configured per environment

### Caching Strategy
- **HTTP caching**: Cache public endpoints (future)
- **Database caching**: Redis for role/permission lookups
- **Application cache**: LRU for patient lists

### Async I/O
- **Database**: SQLAlchemy async
- **External APIs**: aiohttp for LLM/storage calls
- **File uploads**: Async streaming to Azure Blob

### Rate Limiting (Future)
```python
# Add rate limiting middleware
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.get("/patients")
@limiter.limit("100/minute")
async def list_patients(): ...
```

### Monitoring & Observability
- **Metrics**: Request count, latency, error rates
- **Tracing**: Request ID correlation across logs
- **Profiling**: Memory and CPU profiling in staging
- **Alerting**: Critical errors and performance degrades

## Security Considerations

### Data Protection
- ✅ PII encrypted at rest (future: field-level encryption)
- ✅ HTTPS enforced in production
- ✅ SQL injection prevention via ORM
- ✅ XSS prevention via proper serialization
- ✅ CSRF protection headers

### Access Control
- ✅ Role-based authorization
- ✅ Audit log for all modifications
- ✅ Soft deletes preserve history
- ✅ User cannot access other users' data

### Compliance
- ✅ HIPAA-ready architecture
- ✅ Audit trails for all operations
- ✅ User activity logging
- ✅ Secure password hashing
- ✅ Encryption-ready (Azure Key Vault integration)

## Testing Strategy

### Unit Tests
- Pure domain logic (PRSScoringEngine, RoutingEngine)
- Repository methods with mocked DB
- Service methods with mocked repos
- Schema validation with Pydantic

### Integration Tests
- Service + Repository + Database
- Full workflow scenarios
- State transition validation
- Audit log verification

### API Tests
- Endpoint authentication
- Request/response validation
- Authorization checks
- Error handling

### Load Tests
- Concurrent user simulation
- Database connection pooling limits
- Memory leak detection
- Response time SLAs

## Migration Path

### Current (MVP)
- Single node FastAPI app
- Azure SQL Server
- JWT authentication
- Core workflows

### Phase 2 (6 months)
- Add caching layer (Redis)
- Background job queue (Celery)
- Enhanced monitoring
- Widget SDKs for partner integration

### Phase 3 (1 year)
- Microservices extraction
- Event streaming (Kafka)
- Real-time notifications
- Advanced analytics

### Phase 4+ (18+ months)
- HL7/FHIR full support
- Third-party EHR integrations
- Global deployment
- Compliance certifications

## References

- Clean Architecture: Robert C. Martin
- Domain-Driven Design: Eric Evans
- Building Microservices: Sam Newman (for future decomposition)
- SQLAlchemy 2.0 Best Practices
- FastAPI Documentation
- Azure Well-Architected Framework
