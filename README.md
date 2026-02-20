# Sozo Healthcare Platform

A production-grade healthcare SaaS platform built with clean architecture principles, enabling comprehensive patient management, intelligent risk assessment, and HIPAA-compliant workflows.

## 📋 Overview

Sozo is a complete healthcare platform designed to streamline patient care through intelligent automation and comprehensive data management. The platform handles the entire patient journey from initial intake through clinical assessment, risk scoring, and intelligent routing to appropriate care facilities.

**Key Capabilities:**
- Patient intake and registration with role-based access control
- Clinical and psychosocial assessments
- AI-powered PRS (Patient Risk Score) computation
- Intelligent patient routing to appropriate care centers
- Workflow state machine for process management
- Document handling with AI-based summarization
- Comprehensive audit logging for compliance
- HIPAA-compliant data management

## 🚀 Tech Stack

**Backend:**
- **Framework:** FastAPI (Python 3.11+)
- **Database:** Supabase (PostgreSQL)
- **ORM:** SQLAlchemy 2.x
- **Authentication:** JWT with SHA-256 password hashing
- **Validation:** Pydantic v2
- **Migrations:** Alembic

**Frontend:**
- **Core:** Vanilla JavaScript (HTML5 + CSS3)
- **Authentication:** JWT token-based auth
- **API Communication:** Fetch API

**Infrastructure:**
- **Containerization:** Docker + Docker Compose
- **Cloud Storage:** Azure Blob Storage (for documents)
- **Development:** Python virtual environments

## 🏗️ Architecture

### Clean Architecture Principles
```
HTTP Request → Router → Service → Repository → Database
```

- **Routers:** HTTP endpoints and request handling (no business logic)
- **Services:** Business logic orchestration and validation
- **Repositories:** Data access layer (SQLAlchemy only)
- **Models:** Domain entities and ORM definitions
- **Schemas:** Pydantic v2 request/response validation

### Modular Monolith Structure
The platform is built as a modular monolith with clear domain boundaries:

```
backend/
├── app/
│   ├── core/                    # Shared infrastructure
│   │   ├── config.py           # Environment configuration
│   │   ├── database.py         # Supabase connection
│   │   ├── security.py         # JWT + password hashing
│   │   └── dependencies.py     # FastAPI dependencies
│   │
│   ├── modules/                 # Domain modules
│   │   ├── users/              # User management & authentication
│   │   ├── patients/           # Patient data & intake
│   │   ├── assessments/        # Clinical assessments
│   │   ├── prs_engine/         # Risk score computation
│   │   ├── routing_engine/     # Intelligent routing logic
│   │   ├── workflow/           # State machine management
│   │   ├── documents/          # Document handling
│   │   ├── centers/            # Care facility management
│   │   ├── ai/                 # LLM integration
│   │   ├── audit/              # Audit logging
│   │   └── authorization/      # RBAC permissions
│   │
│   ├── shared/                  # Cross-cutting concerns
│   │   ├── models/             # Base models & repositories
│   │   ├── schemas/            # Common schemas
│   │   ├── exceptions/         # Custom exceptions
│   │   └── utils/              # Utilities
│   │
│   └── infrastructure/          # External integrations
│       ├── external_clients/   # Azure Storage, etc.
│       ├── storage/
│       └── messaging/
│
frontend/
├── index.html                   # Login interface
├── auth.js                      # Authentication logic
└── styles.css                   # UI styling
```

## 🔐 Security Features

- **Authentication:** JWT-based authentication with secure token management
- **Password Security:** SHA-256 hashing for all user passwords
- **Authorization:** Role-Based Access Control (RBAC) with granular permissions
- **API Protection:** All endpoints require valid JWT + permission checks
- **HIPAA Compliance:** Audit logging and secure data handling
- **CORS:** Configured for secure cross-origin requests

### User Roles
- `PATIENT` - Regular patients
- `DOCTOR` - Healthcare providers
- `CLINICAL_ASSISTANT` - Clinical support staff
- `RECEPTIONIST` - Front desk staff
- `CLINICAL_ADMIN` - Facility managers
- `PLATFORM_ADMIN` - Platform administrators
- `SUPER_ADMIN` - System administrators

## 🗄️ Database Schema

The platform uses Supabase (PostgreSQL) with the following core tables:
- **users** - User accounts and authentication
- **roles** - System roles
- **permissions** - Granular access permissions
- **user_roles** - User-to-role mappings
- **role_permissions** - Role-to-permission mappings
- **patients** - Patient records and intake data
- **assessments** - Clinical and psychosocial assessments
- **documents** - Document metadata and references
- **centers** - Care facility information
- **audit_logs** - Comprehensive activity logging

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL (via Supabase)
- Node.js (for frontend tooling, optional)
- Docker (optional)

### Backend Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd Sozo/backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # or
   source venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase credentials and configuration
   ```

5. **Run migrations:**
   ```bash
   alembic upgrade head
   ```

6. **Start the server:**
   ```bash
   uvicorn app.main:app --reload
   ```

   API will be available at `http://localhost:8000`
   Interactive docs at `http://localhost:8000/docs`

### Docker Setup

```bash
docker-compose up --build
```

## 📚 Documentation

- **[Getting Started Guide](backend/GETTING_STARTED.md)** - Detailed setup instructions
- **[Architecture Documentation](backend/ARCHITECTURE.md)** - System design and patterns
- **[Database Schema](backend/DATABASE_SCHEMA.md)** - Complete database structure
- **[Supabase Integration](backend/SUPABASE_INTEGRATION.md)** - Database integration guide
- **[Project Walkthrough](PROJECT_WALKTHROUGH.md)** - Complete feature walkthrough

## 🔑 Key Features

### Patient Risk Scoring (PRS)
Intelligent risk assessment based on:
- Clinical data analysis
- Psychosocial factors
- Historical patterns
- AI-assisted evaluation

### Intelligent Routing Engine
Automatically routes patients to appropriate care centers based on:
- Risk score
- Center capacity and capabilities
- Geographic location
- Specialty requirements

### Workflow State Machine
Manages patient journey states:
- Intake → Assessment → Scoring → Routing → Assignment
- State transitions with validation and audit trails
- Automated workflow progression

### AI Integration
- Document summarization
- Clinical note analysis
- Risk factor extraction
- LLM-powered insights

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test module
pytest app/tests/test_prs_engine.py

# Run with coverage
pytest --cov=app
```

## 📝 API Documentation

Once the server is running, access:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## 🤝 Contributing

1. Follow clean architecture principles
2. Maintain strict separation of concerns (Router → Service → Repository)
3. Write comprehensive tests for new features
4. Update documentation for significant changes
5. Follow Python PEP 8 style guidelines

**Note:** This is a production-grade healthcare platform. Ensure compliance with HIPAA and other relevant healthcare regulations in your deployment.
