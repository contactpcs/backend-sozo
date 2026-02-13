"""Database schema and data model documentation."""
# Sozo Data Models & Database Schema

## Database Design Principles

1. **UUID Primary Keys**: All entities use UUID (string format) for global uniqueness
2. **Audit Timestamps**: Every entity has `created_at`, `updated_at`
3. **Soft Deletes**: Records marked deleted with `is_deleted` flag, not removed
4. **Immutability**: Historical data preserved for compliance
5. **Relationships**: Foreign keys maintain referential integrity
6. **Indexes**: Frequently queried columns indexed for performance

---

## Entity Relationship Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│  Users                     Patients                  Assessments  │
│  ┌──────────────┐          ┌──────────────┐         ┌──────────────┐
│  │ id (PK)      │ 1 ─────→ │ id (PK)      │ 1 ────→ │ id (PK)      │
│  │ email (UQ)   │          │ user_id (FK) │        │ patient_id (FK)
│  │ first_name   │          │ workflow_state        │ assessment_type
│  │ last_name    │          │ center_id    │        │ score        │
│  │ role         │          │ clinician_id │        │ status       │
│  │ password_hash│          │ intake_at    │        │ completed_at │
│  │ is_active    │          │ last_assess_at        │              │
│  │ created_at   │          │ created_at   │        │ created_at   │
│  │ updated_at   │          │ updated_at   │        │ updated_at   │
│  │ is_deleted   │          │ is_deleted   │        │ is_deleted   │
│  └──────────────┘          └──────────────┘        └──────────────┘
│        ▲                           │                      ▲
│        │                           ▼                      │
│        └──────────────────────┐    ┌────────────────────┘
│                               │    │
│                        Centers │    │ Documents
│                        ┌──────┴┴──┐ │ ┌──────────────┐
│                        │ id (PK)  │ │ │ id (PK)      │
│                        │ name     │ │ │ patient_id(FK)
│                        │ address  │ │ │ file_path    │
│                        │ city     │ │ │ uploaded_by(FK)
│                        │ zip_code │ │ │ document_type
│                        │ created_at  │ │ extracted_text
│                        │ updated_at  │ │ created_at   │
│                        │ is_deleted  │ │ updated_at   │
│                        └────────────┘ │ is_deleted   │
│                                      │ └──────────────┘
│                                      │
│                              Audit Logs
│                              ┌──────────────┐
│                              │ id (PK)      │
│                              │ actor_id (FK)│
│                              │ action       │
│                              │ entity_type  │
│                              │ entity_id    │
│                              │ changes (JSON)
│                              │ metadata (JSON)
│                              │ timestamp    │
│                              │ created_at   │
│                              └──────────────┘
```

---

## Table Schemas

### Users Table

```sql
CREATE TABLE users (
    -- Primary Key
    id VARCHAR(36) PRIMARY KEY DEFAULT NEWID(),
    
    -- Credentials & Identity
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    
    -- Status
    is_active BIT NOT NULL DEFAULT 1,
    verified_email BIT NOT NULL DEFAULT 0,
    
    -- Authorization
    role VARCHAR(50) NOT NULL DEFAULT 'patient',
    -- VALUES: 'admin', 'clinician', 'nurse', 'patient', 'center_manager'
    
    -- Contact
    phone VARCHAR(20),
    
    -- Audit
    created_at DATETIME NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME NOT NULL DEFAULT GETDATE(),
    
    -- Soft Delete
    is_deleted BIT NOT NULL DEFAULT 0,
    deleted_at DATETIME,
    
    -- Indexes
    INDEX idx_email (email),
    INDEX idx_is_active (is_active),
    INDEX idx_role (role),
    INDEX idx_is_deleted (is_deleted)
);
```

### Patients Table

```sql
CREATE TABLE patients (
    -- Primary Key
    id VARCHAR(36) PRIMARY KEY DEFAULT NEWID(),
    
    -- Relationship
    user_id VARCHAR(36) NOT NULL UNIQUE,
    FOREIGN KEY (user_id) REFERENCES users(id),
    
    -- Medical Record Number
    mrn VARCHAR(50) UNIQUE,
    
    -- Demographics
    date_of_birth DATETIME,
    gender VARCHAR(20),
    phone VARCHAR(20),
    address TEXT,
    emergency_contact VARCHAR(255),
    
    -- Preferences
    preferred_language VARCHAR(50) DEFAULT 'en',
    
    -- Workflow Status
    workflow_state VARCHAR(50) NOT NULL DEFAULT 'intake',
    -- VALUES: 'intake', 'assessment', 'scoring', 'routing', 
    --         'assignment', 'active', 'completed', 'archived'
    
    -- Assignments
    center_id VARCHAR(36),
    FOREIGN KEY (center_id) REFERENCES centers(id),
    assigned_clinician_id VARCHAR(36),
    FOREIGN KEY (assigned_clinician_id) REFERENCES users(id),
    
    -- Timeline
    intake_completed_at DATETIME,
    last_assessment_at DATETIME,
    
    -- Notes
    notes TEXT,
    
    -- Audit
    created_at DATETIME NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME NOT NULL DEFAULT GETDATE(),
    
    -- Soft Delete
    is_deleted BIT NOT NULL DEFAULT 0,
    deleted_at DATETIME,
    
    -- Indexes
    INDEX idx_user_id (user_id),
    INDEX idx_mrn (mrn),
    INDEX idx_workflow_state (workflow_state),
    INDEX idx_center_id (center_id),
    INDEX idx_clinician_id (assigned_clinician_id),
    INDEX idx_is_deleted (is_deleted)
);
```

### Assessments Table

```sql
CREATE TABLE assessments (
    -- Primary Key
    id VARCHAR(36) PRIMARY KEY DEFAULT NEWID(),
    
    -- Relationships
    patient_id VARCHAR(36) NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    clinician_id VARCHAR(36),
    FOREIGN KEY (clinician_id) REFERENCES users(id),
    
    -- Assessment Details
    assessment_type VARCHAR(50) NOT NULL,
    -- VALUES: 'clinical', 'psychosocial', 'social_determinant'
    
    questionnaire_id VARCHAR(36),
    version INT DEFAULT 1,
    
    -- Responses (stored as JSON)
    responses TEXT,  -- JSON array of { question_id, answer }
    
    -- Scoring
    raw_score FLOAT,
    normalized_score FLOAT,
    
    -- Status
    status VARCHAR(50) DEFAULT 'draft',
    -- VALUES: 'draft', 'completed', 'reviewed'
    
    -- Reviewer
    reviewer_id VARCHAR(36),
    FOREIGN KEY (reviewer_id) REFERENCES users(id),
    
    -- Notes
    clinical_notes TEXT,
    
    -- Timeline
    started_at DATETIME NOT NULL DEFAULT GETDATE(),
    completed_at DATETIME,
    reviewed_at DATETIME,
    
    -- Audit
    created_at DATETIME NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME NOT NULL DEFAULT GETDATE(),
    
    -- Soft Delete
    is_deleted BIT NOT NULL DEFAULT 0,
    deleted_at DATETIME,
    
    -- Indexes
    INDEX idx_patient_id (patient_id),
    INDEX idx_type (assessment_type),
    INDEX idx_status (status),
    INDEX idx_completed_at (completed_at),
    INDEX idx_is_deleted (is_deleted)
);
```

### Centers Table

```sql
CREATE TABLE centers (
    -- Primary Key
    id VARCHAR(36) PRIMARY KEY DEFAULT NEWID(),
    
    -- Identification
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    
    -- Location
    address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(50) NOT NULL,
    zip_code VARCHAR(20) NOT NULL,
    latitude FLOAT,
    longitude FLOAT,
    
    -- Contact
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(255) NOT NULL,
    
    -- Status
    is_active BIT DEFAULT 1,
    operating_hours TEXT,  -- JSON
    
    -- Capacity
    max_patient_capacity INT DEFAULT 100,
    current_patient_count INT DEFAULT 0,
    
    -- Performance Metrics
    quality_score FLOAT DEFAULT 75.0,  -- 0-100
    patient_satisfaction_score FLOAT DEFAULT 75.0,
    
    -- Specialties & Services
    specialties TEXT,  -- JSON array: ["cardiology", "neurology"]
    accepts_insurance TEXT,  -- JSON array
    accepts_uninsured BIT DEFAULT 0,
    
    -- Language & Cultural
    supported_languages TEXT DEFAULT '["en"]',  -- JSON array
    has_interpreters BIT DEFAULT 0,
    
    -- Audit
    created_at DATETIME NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME NOT NULL DEFAULT GETDATE(),
    
    -- Soft Delete
    is_deleted BIT NOT NULL DEFAULT 0,
    deleted_at DATETIME,
    
    -- Indexes
    INDEX idx_code (code),
    INDEX idx_city (city),
    INDEX idx_is_active (is_active),
    INDEX idx_quality (quality_score),
    INDEX idx_is_deleted (is_deleted)
);
```

### Documents Table

```sql
CREATE TABLE documents (
    -- Primary Key
    id VARCHAR(36) PRIMARY KEY DEFAULT NEWID(),
    
    -- Relationships
    patient_id VARCHAR(36) NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    uploaded_by VARCHAR(36) NOT NULL,
    FOREIGN KEY (uploaded_by) REFERENCES users(id),
    
    -- File Information
    document_type VARCHAR(50) NOT NULL,
    -- VALUES: 'intake_form', 'questionnaire', 'assessment',
    --         'prs_report', 'eligibility_decision', 'clinical_note'
    
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,  -- Azure Blob path
    file_size_bytes INT NOT NULL,
    file_mime_type VARCHAR(50),
    
    -- Processing
    extracted_text TEXT,  -- OCR or extraction result
    is_processed BIT DEFAULT 0,
    processing_errors TEXT,
    
    -- Metadata
    description TEXT,
    
    -- Timeline
    uploaded_at DATETIME NOT NULL DEFAULT GETDATE(),
    
    -- Audit
    created_at DATETIME NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME NOT NULL DEFAULT GETDATE(),
    
    -- Soft Delete
    is_deleted BIT NOT NULL DEFAULT 0,
    deleted_at DATETIME,
    
    -- Indexes
    INDEX idx_patient_id (patient_id),
    INDEX idx_type (document_type),
    INDEX idx_uploaded_by (uploaded_by),
    INDEX idx_is_processed (is_processed),
    INDEX idx_is_deleted (is_deleted)
);
```

### Audit Logs Table

```sql
CREATE TABLE audit_logs (
    -- Primary Key
    id VARCHAR(36) PRIMARY KEY DEFAULT NEWID(),
    
    -- Actor
    actor_id VARCHAR(36) NOT NULL,
    FOREIGN KEY (actor_id) REFERENCES users(id),
    
    -- Action
    action VARCHAR(50) NOT NULL,
    -- VALUES: 'CREATE', 'UPDATE', 'DELETE', 'VIEW', 'TRANSITION',
    --         'CALCULATE', 'ASSIGN', 'APPROVE', 'REJECT'
    
    -- Target
    entity_type VARCHAR(50) NOT NULL,
    -- VALUES: 'Patient', 'Assessment', 'User', 'Center', etc.
    entity_id VARCHAR(36) NOT NULL,
    
    -- Changes (JSON, before/after)
    changes TEXT,
    
    -- Context
    metadata TEXT,  -- JSON, additional context
    
    -- Timestamp
    timestamp DATETIME NOT NULL DEFAULT GETDATE(),
    
    -- Audit
    created_at DATETIME NOT NULL DEFAULT GETDATE(),
    
    -- Indexes (for querying)
    INDEX idx_actor (actor_id),
    INDEX idx_action (action),
    INDEX idx_entity (entity_type, entity_id),
    INDEX idx_timestamp (timestamp),
    INDEX idx_created_at (created_at)
);
```

---

## Sample Data Flows

### User Registration Flow
```
POST /users/register
{
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "password": "SecurePass123!",
  "role": "clinician"
}

INSERT INTO users (
  email, first_name, last_name, hashed_password, role, is_active
) VALUES (
  'john@example.com', 'John', 'Doe', '$2b$12$hash...', 'clinician', 1
)

RETURN {
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "john@example.com",
  "role": "clinician",
  "created_at": "2024-02-11T10:00:00Z"
}
```

### Patient Assessment & Scoring Flow
```
1. Create Assessment
   INSERT INTO assessments (patient_id, assessment_type, clinician_id, status) 
   VALUES (patient_id, 'clinical', clinician_id, 'draft')

2. Complete Assessment
   UPDATE assessments 
   SET status = 'completed', completed_at = NOW(), responses = '...'
   WHERE id = assessment_id

3. Calculate Score (Domain Logic)
   PRSScoringEngine.calculate_prs(responses) 
   → Returns PRSScore with score, category, recommendations

4. Store Score
   UPDATE assessments 
   SET normalized_score = 75.5, status = 'reviewed'
   WHERE id = assessment_id
   
   INSERT INTO audit_logs 
   VALUES (actor_id, 'CALCULATE', 'Assessment', assessment_id, {...})

5. Route Patient
   RoutingEngine.route_patient(patient_data, available_centers)
   → Returns RoutingDecision with recommended center

6. Assign to Center
   UPDATE patients 
   SET workflow_state = 'active', center_id = selected_center_id
   WHERE id = patient_id
   
   INSERT INTO audit_logs 
   VALUES (actor_id, 'ASSIGN', 'Patient', patient_id, {assigned_center: center_id})
```

---

## Query Patterns

### Get All Active Patients
```sql
SELECT * FROM patients 
WHERE is_deleted = 0 
  AND workflow_state IN ('active', 'assignment')
ORDER BY updated_at DESC
```

### Get Patient with Complete Profile
```sql
SELECT p.*, u.email, u.first_name, u.last_name, c.name as center_name
FROM patients p
JOIN users u ON p.user_id = u.id
LEFT JOIN centers c ON p.center_id = c.id
WHERE p.id = @patient_id AND p.is_deleted = 0
```

### Get Recent Assessments for Patient
```sql
SELECT * FROM assessments
WHERE patient_id = @patient_id 
  AND is_deleted = 0
  AND status = 'completed'
ORDER BY completed_at DESC
LIMIT 10
```

### Get Audit Trail for Patient Changes
```sql
SELECT * FROM audit_logs
WHERE entity_type = 'Patient' 
  AND entity_id = @patient_id
ORDER BY timestamp DESC
```

### Find Patients by Risk Level (Requires Join with Assessment)
```sql
SELECT DISTINCT p.*
FROM patients p
JOIN assessments a ON p.id = a.patient_id
WHERE a.normalized_score >= 75  -- High risk
  AND a.status = 'reviewed'
  AND p.is_deleted = 0
  AND a.is_deleted = 0
ORDER BY a.normalized_score DESC
```

---

## Performance Considerations

### Indexing Strategy
- **Hot columns**: user_id, patient_id, is_deleted, workflow_state, status
- **Range queries**: created_at, updated_at, timestamp
- **Full-text search**: Consider full-text indexes on notes, description

### Partitioning (Future)
```sql
-- Partition assessments by year
ALTER TABLE assessments 
PARTITION BY RANGE(YEAR(created_at)) (
  PARTITION p2023 VALUES LESS THAN (2024),
  PARTITION p2024 VALUES LESS THAN (2025),
  PARTITION p2025 VALUES LESS THAN (2026)
)
```

### Archive Strategy
- Move completed assessments to history table after 2 years
- Keep active patients for 5 years (HIPAA)
- Archive deleted records separately

---

## Data Types & Ranges

| Column Type | MSSQL | Notes |
|---|---|---|
| ID | VARCHAR(36) | UUID |
| Name | VARCHAR(255) | Person names, center names |
| Email | VARCHAR(255) | Unique per system |
| Password | VARCHAR(255) | Hashed, bcrypt output |
| Score | FLOAT | 0-100, two decimals |
| Timestamp | DATETIME | UTC, indexed |
| JSON | TEXT | Serialized, not native JSON in MSSQL |
| Large Text | TEXT | Notes, extracted text |
| Flag | BIT | 0/1 for boolean |

---

## Backup & Recovery

### Backup Strategy
```
- Daily full backup
- Hourly differential backup
- Azure Backup integration
- 30-day retention
```

### Recovery RTO/RPO
- **RTO** (Recovery Time Objective): 4 hours
- **RPO** (Recovery Point Objective): 1 hour

---

## Compliance & Security Notes

✅ **HIPAA Compliance**:
- Encryption at rest (Azure SQL TDE)
- Encryption in transit (HTTPS/TLS)
- Audit logging for all access
- Data retention policies
- De-identification capability

✅ **PCI Compliance** (if handling payments):
- No payment data stored
- Use third-party providers (Stripe, etc.)

✅ **GDPR Compliance** (if EU users):
- Right to be forgotten via soft delete
- Data portability via exports
- Clear consent trails in audit logs
