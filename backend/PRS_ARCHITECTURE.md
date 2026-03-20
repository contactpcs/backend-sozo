# NeuroWellness PRS — Production Architecture
## Patient Rating System · Complete Technical Design Document

**Version:** 1.0
**Date:** March 2026
**Status:** Architecture Design (Pre-Development)
**Audience:** Engineering Team (3 Developers), Investors, Technical Stakeholders

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Decision: Shared vs Independent Backend](#2-architecture-decision)
3. [System Overview](#3-system-overview)
4. [Tech Stack](#4-tech-stack)
5. [User Roles & Application Flows](#5-user-roles--application-flows)
6. [Backend Module Design](#6-backend-module-design)
7. [Database Schema — 7 New PRS Tables](#7-database-schema)
8. [API Endpoint Design](#8-api-endpoint-design)
9. [Scale Engine — Python Port](#9-scale-engine--python-port)
10. [Frontend Architecture](#10-frontend-architecture)
11. [Infrastructure & Deployment](#11-infrastructure--deployment)
12. [Security & Compliance](#12-security--compliance)
13. [Developer Work Split](#13-developer-work-split)
14. [Phased Development Roadmap](#14-phased-development-roadmap)

---

## 1. Executive Summary

The **NeuroWellness PRS (Patient Rating System)** is a clinical assessment platform built for neurologists and psychiatrists to assign, administer, and interpret validated psychometric scales for 16 neurological and psychiatric conditions. It currently exists as a functional frontend prototype with 47 clinical scales and a rich scoring engine.

This document defines the architecture to build a **production-grade, fully functional PRS application** that:
- Operates **independently** for investor demonstrations and standalone marketing
- Integrates **seamlessly** into the main NeuroWellness platform via shared auth, database, and API
- Is **scalable globally** — multi-tenant, multi-language, multi-region ready
- Is **clinically compliant** — HIPAA, DISHA (India), GDPR audit trails

---

## 2. Architecture Decision

### Decision: Shared Backend · Independent Frontend

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT TOPOLOGY                               │
│                                                                     │
│   prs.neurowellness.com          app.neurowellness.com              │
│   ┌──────────────────────┐       ┌─────────────────────────────┐   │
│   │  PRS Frontend App    │       │  NeuroWellness Main App     │   │
│   │  (Next.js — NEW)     │       │  (Next.js — existing)       │   │
│   │  Independent Deploy  │       │  Doctor/Admin Portal        │   │
│   └──────────┬───────────┘       └────────────┬────────────────┘   │
│              │                                │                     │
│              └────────────┬───────────────────┘                     │
│                           │  Shared JWT Auth                        │
│                           ▼                                         │
│              ┌────────────────────────────┐                        │
│              │  api.neurowellness.com      │                        │
│              │  NeuroWellness Backend API  │                        │
│              │  (FastAPI — EXTENDED)       │                        │
│              │  /api/v1/prs/*  ← NEW       │                        │
│              └─────────────┬──────────────┘                        │
│                            │                                        │
│              ┌─────────────▼──────────────┐                        │
│              │  PostgreSQL (Supabase)      │                        │
│              │  Existing tables + 7 new   │                        │
│              │  PRS tables                │                        │
│              └────────────────────────────┘                        │
└─────────────────────────────────────────────────────────────────────┘
```

### Why Share the Backend?

| Factor | Shared Backend | Independent Backend |
|--------|---------------|---------------------|
| **Auth/RBAC** | Already exists — doctor, patient, admin roles ready | Must rebuild from scratch |
| **Patient Records** | `patients` table already has MRN, demographics, clinician assignment | Duplicate data, sync complexity |
| **Infrastructure** | Azure, Supabase, Key Vault already provisioned | +$600–900/month duplicate infra |
| **PRS Stub** | `prs_engine` module stub + `prs_router` commented-out already exist | N/A |
| **Compliance** | HIPAA/DISHA compliance already implemented | Must re-implement |
| **Time to market** | ~60% faster — build on existing foundation | Full greenfield build |
| **Integration later** | Already integrated from Day 1 | Complex SSO + data migration |

### Why Independent Frontend?

| Reason | Detail |
|--------|--------|
| **Investor demos** | `prs.neurowellness.com` — standalone, branded independently |
| **Market independently** | Can be licensed to clinics/hospitals without the full NeuroWellness platform |
| **Role-focused UX** | PRS has a very different UX from the main app (patient-facing questionnaire flow) |
| **Separate branding** | NeuroWellness PRS as a product in its own right |
| **Shared tokens** | Same JWT works on both — patients/doctors log in once, access both |

---

## 3. System Overview

### Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        PRS APPLICATION                                  │
│                                                                         │
│  ┌──────────────┐  ┌─────────────────────┐  ┌──────────────────────┐  │
│  │ ADMIN PORTAL │  │ CLINICIAN PORTAL     │  │  PATIENT PORTAL      │  │
│  │              │  │ (Doctor + Clin.Asst) │  │                      │  │
│  │ Manage:      │  │                      │  │ - View assignments   │  │
│  │ · Scales     │  │ - Patient list       │  │ - Take assessments   │  │
│  │ · Conditions │  │ - Assign batteries   │  │ - Save progress      │  │
│  │ · Users      │  │ - View reports       │  │ - View own results   │  │
│  │ · Analytics  │  │ - Risk alerts        │  │ - Download report    │  │
│  │ · Orgs       │  │ - PDF download       │  │                      │  │
│  └──────┬───────┘  └──────────┬──────────┘  └──────────┬───────────┘  │
│         │                     │                         │              │
│         └─────────────────────┴─────────────────────────┘              │
│                               │                                         │
│                   ┌───────────▼────────────┐                           │
│                   │   PRS Frontend App      │                           │
│                   │   Next.js 14 + TypeScript│                          │
│                   │   Redux Toolkit         │                           │
│                   └───────────┬────────────┘                           │
│                               │ HTTPS + JWT                             │
│                               │                                         │
│  ┌────────────────────────────▼────────────────────────────────────┐   │
│  │                  NeuroWellness Backend API                       │   │
│  │                  FastAPI + Python 3.11                           │   │
│  │                                                                  │   │
│  │  ┌──────────────────────────────────────────────────────────┐   │   │
│  │  │                    PRS MODULE                            │   │   │
│  │  │  app/modules/prs/                                        │   │   │
│  │  │                                                          │   │   │
│  │  │  router.py          → REST API endpoints                 │   │   │
│  │  │  service.py         → Business logic orchestration       │   │   │
│  │  │  repository.py      → Database queries (SQLAlchemy)      │   │   │
│  │  │  models.py          → 7 new SQLAlchemy ORM models        │   │   │
│  │  │  schemas.py         → Pydantic request/response schemas  │   │   │
│  │  │  scale_engine.py    → Python port of scaleEngine.js      │   │   │
│  │  │  risk_detector.py   → Risk flag detection + alerting     │   │   │
│  │  │  pdf_generator.py   → Clinical report PDF generation     │   │   │
│  │  │  tasks.py           → Celery async tasks                 │   │   │
│  │  │  seed_scales.py     → Import 47 JSON scales on startup   │   │   │
│  │  └──────────────────────────────────────────────────────────┘   │   │
│  │                                                                  │   │
│  │  Existing modules: users, patients, auth, documents, audit      │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                               │                                         │
│         ┌─────────────────────┼───────────────────────┐                │
│         │                     │                       │                │
│  ┌──────▼───────┐   ┌─────────▼──────┐    ┌──────────▼──────┐        │
│  │  PostgreSQL  │   │  Redis Cache   │    │  Azure Blob     │        │
│  │  (Supabase)  │   │  · Scale JSONB │    │  · PDF reports  │        │
│  │  · 7 new PRS │   │  · Sessions    │    │  · Exports      │        │
│  │    tables    │   │  · WS pub/sub  │    │                 │        │
│  └──────────────┘   └────────────────┘    └─────────────────┘        │
└─────────────────────────────────────────────────────────────────────────┘
```

### Data Flow: Patient Takes an Assessment

```
1. Doctor logs in → assigns "Depression/Anxiety" battery to patient
   POST /api/v1/prs/sessions
   → Creates prs_assessment_session record
   → Creates prs_scale_responses stubs for each scale

2. Patient logs in → sees assigned session
   GET /api/v1/prs/sessions/my
   → Returns sessions with scale list + status

3. Patient starts PHQ-9
   GET /api/v1/prs/scales/PHQ-9
   → Returns scale definition JSONB from Redis (or DB)

4. Patient answers questions → saves progress
   PATCH /api/v1/prs/sessions/{session_id}/responses/{scale_id}
   → Saves partial responses, marks in_progress

5. Patient completes PHQ-9
   POST /api/v1/prs/sessions/{session_id}/responses/{scale_id}/complete
   → ScaleEngine.calculate_score() runs
   → RiskDetector.check_flags() runs
   → Score + severity stored in prs_scale_responses
   → Risk flags stored in prs_risk_alerts
   → prs_score_history updated
   → WebSocket push to doctor if risk flag

6. Patient completes all scales
   → session status → 'completed'
   → Celery task: generate_pdf_report(session_id)
   → PDF uploaded to Azure Blob
   → Doctor notified

7. Doctor reviews
   GET /api/v1/prs/sessions/{session_id}/report
   → Returns full report with scores, severity, risk alerts, trends
   GET /api/v1/prs/sessions/{session_id}/report/pdf
   → Pre-signed Azure Blob URL for download
```

---

## 4. Tech Stack

### Backend (Extending existing backend-neurowellness)

| Component | Technology | Reason |
|-----------|-----------|--------|
| Framework | FastAPI 0.111 | Already in use, async, high performance |
| Language | Python 3.11 | Already in use |
| ORM | SQLAlchemy 2.0 | Already in use |
| Database | PostgreSQL via Supabase | Already provisioned |
| Cache | Redis 7 | Celery broker + scale JSONB cache + WS pub/sub |
| Async tasks | Celery 5 | PDF generation, notifications, score processing |
| PDF | WeasyPrint or ReportLab | Clinical report generation |
| Auth | JWT (existing) | Already implemented |
| Validation | Pydantic v2 | Already in use |
| Storage | Azure Blob Storage | Already configured |

### Frontend (New PRS Frontend App)

| Component | Technology | Reason |
|-----------|-----------|--------|
| Framework | Next.js 14 (App Router) | Matches main app, SSR for SEO |
| Language | TypeScript | Type safety for clinical data |
| State | Redux Toolkit + RTK Query | Matches main app pattern |
| Styling | Tailwind CSS | Matches main app |
| Forms | React Hook Form + Zod | Validation at form level |
| Charts | Recharts | Trend charts for score history |
| PDF viewer | React-PDF | View reports in-browser |
| Real-time | Socket.IO client | Risk alert notifications |
| Testing | Jest + Playwright | Unit + E2E |

### Infrastructure

| Component | Technology |
|-----------|-----------|
| Cloud | Microsoft Azure (India — Central India / Pune) |
| Container orchestration | Azure Kubernetes Service (AKS) |
| Database | Supabase PostgreSQL (existing) |
| CDN / Edge | Azure Front Door |
| Secrets | Azure Key Vault (existing) |
| Monitoring | Azure Monitor + Application Insights |
| CI/CD | GitHub Actions |
| Compliance | DISHA (India), HIPAA, GDPR-ready |

---

## 5. User Roles & Application Flows

The PRS application uses the **existing RBAC roles** already defined in the NeuroWellness backend:

| Role | Access Level | PRS Capabilities |
|------|-------------|-----------------|
| `super_admin` | Full system | All capabilities + system config |
| `platform_admin` | Platform-wide | Manage scales library, conditions, orgs, users |
| `clinical_admin` | Org-wide | Manage org users, view all org assessments |
| `doctor` | Patient-level | Assign batteries, view/interpret results, receive alerts |
| `clinical_assistant` | Patient-level | Assign batteries, monitor completion, view scores |
| `patient` | Self-only | Take assigned assessments, view own results |

### Role: Admin (platform_admin / super_admin)

```
Admin Dashboard
├── Scale Library
│   ├── View all 47 scales (paginated, filterable by category)
│   ├── View scale definition (JSON preview, questions, scoring)
│   ├── Enable / Disable scales
│   ├── Edit scale metadata (name, estimated time, instructions)
│   └── Upload new scale JSON
├── Condition Batteries
│   ├── View all 16 condition batteries
│   ├── Create new battery (condition + scale set)
│   ├── Edit battery (add/remove scales, reorder)
│   └── Enable / Disable battery
├── User Management
│   ├── View all users (filter by role, org, status)
│   ├── Create / Edit / Deactivate users
│   └── Reset passwords
├── Analytics Dashboard
│   ├── Assessment completion rates by condition
│   ├── Scale usage frequency
│   ├── Risk alert statistics
│   ├── Active sessions
│   └── Export CSV reports
└── Organization Management
    ├── Create / Edit organizations (clinics, hospitals)
    ├── Assign doctors to organizations
    └── Set org-level settings (default language, report branding)
```

### Role: Doctor

```
Doctor Dashboard
├── My Patients
│   ├── Patient list (active assignments, recent sessions)
│   ├── Patient profile
│   │   ├── Demographics (from existing patients table)
│   │   ├── Assessment history (all PRS sessions)
│   │   ├── Score trend charts per scale
│   │   └── Risk alert history
│   └── Search / Filter patients
├── Assign Assessment
│   ├── Select patient
│   ├── Choose: Condition Battery OR Custom Scale Set
│   ├── Set due date
│   ├── Add clinical notes / instructions
│   └── Confirm assignment → patient notified
├── Active Sessions
│   ├── List of in-progress sessions
│   ├── Completion status per scale
│   └── Click to view partial results
├── Completed Reports
│   ├── Full report view (scores, severity, subscales, risk flags)
│   ├── Download PDF
│   ├── Add clinical notes to session
│   └── Compare with previous session (trend)
├── Risk Alerts
│   ├── Real-time alert feed (WebSocket)
│   ├── Acknowledge / Resolve alerts
│   └── Escalate to super_admin if needed
└── Clinician-Rated Scales
    ├── List of sessions awaiting clinician input (EDSS, MADRS, etc.)
    ├── Enter clinician observations
    └── Submit clinician rating
```

### Role: Clinical Assistant

```
Clinical Assistant Dashboard
├── My Patients (same as doctor but filtered to assigned patients)
├── Assign Assessment (same as doctor)
├── Monitor Sessions
│   ├── Completion status per patient
│   └── Send reminder to patient
├── View Completed Scores (read-only, no clinical interpretation)
└── Risk Alerts (view + acknowledge, cannot resolve)
```

### Role: Patient

```
Patient Portal
├── Dashboard
│   ├── Welcome message
│   ├── Pending assessments (with due dates)
│   ├── In-progress assessments (resume)
│   └── Completed assessments
├── Take Assessment
│   ├── Assessment overview (condition, scales list, estimated time)
│   ├── Consent screen (digital consent recorded)
│   ├── Scale-by-scale questionnaire
│   │   ├── One scale at a time
│   │   ├── Progress indicator (scale X of Y)
│   │   ├── Question navigation (prev/next)
│   │   ├── Auto-save progress every question
│   │   ├── Resume from last answer if interrupted
│   │   └── Submit scale
│   └── Completion screen
├── My Results
│   ├── Summary view (severity levels per scale)
│   ├── No raw score shown by default (clinician can enable)
│   └── Download report (if doctor enables for patient)
└── Profile
    ├── Personal info
    ├── Preferred language
    └── Notification preferences
```

---

## 6. Backend Module Design

### Module Structure

```
backend/app/modules/prs/
├── __init__.py
├── models.py          # SQLAlchemy ORM models (7 tables)
├── schemas.py         # Pydantic schemas (request + response)
├── repository.py      # All database queries
├── service.py         # Business logic, orchestration
├── router.py          # FastAPI route definitions
├── scale_engine.py    # Python port of scaleEngine.js
├── risk_detector.py   # Risk flag detection
├── pdf_generator.py   # Clinical PDF report generation
├── tasks.py           # Celery async tasks
└── seed_scales.py     # Seed 47 scales from JSON files on startup
```

### Service Layer — Key Methods

```python
# service.py — orchestrates all PRS business logic

class PRSService:

    # ── SCALE MANAGEMENT ──────────────────────────────────────────────
    async def get_all_scales(filters) -> List[ScaleResponse]
    async def get_scale_definition(scale_id) -> ScaleDefinition  # from Redis cache
    async def seed_scales_from_json(scales_dir) -> None  # on startup
    async def update_scale_metadata(scale_id, metadata) -> ScaleResponse

    # ── CONDITION BATTERIES ───────────────────────────────────────────
    async def get_all_batteries() -> List[BatteryResponse]
    async def create_battery(data: BatteryCreate) -> BatteryResponse
    async def update_battery(battery_id, data) -> BatteryResponse

    # ── SESSION MANAGEMENT ────────────────────────────────────────────
    async def assign_session(
        patient_id, assigned_by, condition_id=None,
        custom_scale_ids=None, due_date=None, notes=None
    ) -> SessionResponse
    # Creates session + stub scale_response records

    async def get_sessions_for_patient(patient_id) -> List[SessionResponse]
    async def get_sessions_for_clinician(clinician_id) -> List[SessionResponse]
    async def get_session_detail(session_id) -> SessionDetailResponse

    # ── RESPONSE HANDLING ─────────────────────────────────────────────
    async def save_partial_response(
        session_id, scale_id, responses: dict
    ) -> ScaleResponseRecord
    # Auto-saves progress, marks in_progress

    async def complete_scale_response(
        session_id, scale_id, responses: dict
    ) -> ScaleResponseResult
    # 1. Validate all required questions answered
    # 2. ScaleEngine.calculate_score()
    # 3. RiskDetector.check_flags()
    # 4. Store score + risk flags
    # 5. Update score_history
    # 6. Check if session fully complete → trigger report

    async def submit_clinician_rating(
        session_id, scale_id, responses, clinician_id, notes
    ) -> ScaleResponseResult

    # ── REPORT GENERATION ─────────────────────────────────────────────
    async def get_session_report(session_id) -> FullReportResponse
    async def get_pdf_url(session_id) -> str  # Azure Blob pre-signed URL
    async def generate_pdf_report(session_id) -> str  # Celery task

    # ── RISK ALERTS ───────────────────────────────────────────────────
    async def get_active_alerts(clinician_id) -> List[RiskAlertResponse]
    async def acknowledge_alert(alert_id, user_id) -> RiskAlertResponse
    async def resolve_alert(alert_id, user_id, notes) -> RiskAlertResponse

    # ── ANALYTICS ─────────────────────────────────────────────────────
    async def get_score_history(patient_id, scale_id) -> List[ScoreHistoryPoint]
    async def get_analytics_overview(org_id=None) -> AnalyticsResponse
```

---

## 7. Database Schema

### Overview — 7 New PRS Tables

```
prs_scales              → Library of 47+ validated clinical scales
prs_condition_batteries → 16 condition → scale set mappings
prs_assessment_sessions → A session assigned by clinician to patient
prs_scale_responses     → Per-scale responses + computed scores
prs_risk_alerts         → Auto-detected risk flags needing attention
prs_score_history       → Trend tracking for longitudinal analysis
prs_patient_consents    → HIPAA/DISHA digital consent records
```

### Relationship Diagram

```
users (existing)
  │
  ├── 1:N ──── prs_assessment_sessions (assigned_by)
  │                      │
  │                      ├── 1:N ──── prs_scale_responses
  │                      │                  │
  │                      │                  └── 1:N ── prs_risk_alerts
  │                      │
  │                      └── 1:N ──── prs_patient_consents
  │
patients (existing)
  │
  ├── 1:N ──── prs_assessment_sessions (patient_id)
  │
  └── 1:N ──── prs_score_history (patient_id)

prs_scales
  │
  └── referenced by prs_condition_batteries.scale_ids (JSONB array)
      referenced by prs_scale_responses.scale_id

prs_condition_batteries
  └── referenced by prs_assessment_sessions.condition_id
```

### Table: prs_scales

```sql
CREATE TABLE prs_scales (
    -- Identity
    id              VARCHAR(36)   PRIMARY KEY DEFAULT gen_random_uuid(),
    scale_id        VARCHAR(50)   UNIQUE NOT NULL,   -- 'PHQ-9', 'DASS-21', etc.
    short_name      VARCHAR(100)  NOT NULL,
    full_name       VARCHAR(255)  NOT NULL,

    -- Classification
    category        VARCHAR(50)   NOT NULL,   -- 'depression','anxiety','pain','sleep',...
    subcategory     VARCHAR(50),
    version         VARCHAR(20)   DEFAULT '1.0',

    -- Scoring metadata
    scoring_type    VARCHAR(50)   NOT NULL,
    -- VALUES: 'sum','sum-numeric','subscale-sum','subscale-severity',
    --         'weighted-binary','weighted-domain-sum','fiqr-weighted',
    --         'component-sum','profile-and-vas','reverse-scored',
    --         'clinician','average'

    max_score       FLOAT,
    estimated_minutes INT         DEFAULT 5,

    -- Full scale definition (questions, options, severity bands, risk rules)
    definition      JSONB         NOT NULL,

    -- Flags
    is_active             BOOLEAN DEFAULT TRUE,
    is_clinician_rated    BOOLEAN DEFAULT FALSE,
    requires_consent      BOOLEAN DEFAULT FALSE,

    -- Localization
    languages       JSONB         DEFAULT '["en"]',
    translations    JSONB,   -- { "hi": { shortName: "...", questions: [...] } }

    -- Audit
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    is_deleted      BOOLEAN       DEFAULT FALSE
);

CREATE INDEX idx_prs_scales_category    ON prs_scales(category);
CREATE INDEX idx_prs_scales_is_active   ON prs_scales(is_active);
CREATE INDEX idx_prs_scales_scale_id    ON prs_scales(scale_id);
```

### Table: prs_condition_batteries

```sql
CREATE TABLE prs_condition_batteries (
    id              VARCHAR(36)   PRIMARY KEY DEFAULT gen_random_uuid(),
    condition_id    VARCHAR(100)  UNIQUE NOT NULL, -- 'depression-anxiety', 'migraine', etc.
    label           VARCHAR(255)  NOT NULL,         -- 'Depression/Anxiety'
    description     TEXT,

    -- Ordered list of scale_ids for this condition
    scale_ids       JSONB         NOT NULL,          -- ["EQ-5D-5L","PHQ-9","GAD-7","PSQI"]

    -- Optional: clinician-only scales within this battery
    clinician_scale_ids  JSONB   DEFAULT '[]',       -- scales requiring clinician input

    -- Status
    is_active       BOOLEAN       DEFAULT TRUE,
    display_order   INT           DEFAULT 0,

    -- Audit
    created_by      VARCHAR(36)   REFERENCES users(id),
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    is_deleted      BOOLEAN       DEFAULT FALSE
);

CREATE INDEX idx_prs_batteries_condition_id ON prs_condition_batteries(condition_id);
CREATE INDEX idx_prs_batteries_is_active    ON prs_condition_batteries(is_active);
```

### Table: prs_assessment_sessions

```sql
CREATE TABLE prs_assessment_sessions (
    id              VARCHAR(36)   PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Core relationships
    patient_id      VARCHAR(36)   NOT NULL REFERENCES patients(id),
    assigned_by     VARCHAR(36)   NOT NULL REFERENCES users(id),

    -- What is being assessed
    condition_id    VARCHAR(100),    -- FK to prs_condition_batteries.condition_id
                                     -- NULL if custom scale set
    custom_scale_ids JSONB,          -- non-null when custom, e.g. ["PHQ-9","PSQI"]

    -- Resolved scale list (computed at assignment time, frozen)
    resolved_scale_ids JSONB  NOT NULL,   -- ordered list, never changes after assignment

    -- Session metadata
    title           VARCHAR(255),
    -- e.g. "Depression/Anxiety Assessment — March 2026"
    clinical_notes  TEXT,
    patient_instructions TEXT,

    -- Status lifecycle
    status          VARCHAR(50)   DEFAULT 'assigned',
    -- VALUES: 'assigned' → 'in_progress' → 'completed'
    --         'expired' (past due_date, not started)
    --         'cancelled' (clinician cancelled)
    --         'clinician_review' (awaiting clinician-rated scales)

    -- Timeline
    assigned_at     TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    due_date        TIMESTAMPTZ,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    last_activity_at TIMESTAMPTZ,

    -- Summary results (computed on completion)
    overall_severity        VARCHAR(50),   -- 'minimal','mild','moderate','severe'
    risk_flag_count         INT     DEFAULT 0,
    critical_alert_count    INT     DEFAULT 0,
    scales_completed        INT     DEFAULT 0,
    scales_total            INT     DEFAULT 0,

    -- Report
    report_blob_path        VARCHAR(500),  -- Azure Blob: orgs/{org}/sessions/{id}/report.pdf
    report_generated_at     TIMESTAMPTZ,

    -- Audit
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    is_deleted      BOOLEAN       DEFAULT FALSE,
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX idx_prs_sessions_patient_id   ON prs_assessment_sessions(patient_id);
CREATE INDEX idx_prs_sessions_assigned_by  ON prs_assessment_sessions(assigned_by);
CREATE INDEX idx_prs_sessions_status       ON prs_assessment_sessions(status);
CREATE INDEX idx_prs_sessions_due_date     ON prs_assessment_sessions(due_date);
CREATE INDEX idx_prs_sessions_condition_id ON prs_assessment_sessions(condition_id);
```

### Table: prs_scale_responses

```sql
CREATE TABLE prs_scale_responses (
    id              VARCHAR(36)   PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Relationships
    session_id      VARCHAR(36)   NOT NULL REFERENCES prs_assessment_sessions(id),
    scale_id        VARCHAR(50)   NOT NULL,

    -- Raw responses: { "0": 2, "1": 1, "2": 3, ... }
    -- Key = question index, Value = selected option value
    responses       JSONB,

    -- Computed results (populated on completion)
    total_score         FLOAT,
    max_possible_score  FLOAT,
    percentage          FLOAT,

    severity_level      VARCHAR(50),    -- 'minimal','mild','moderate','moderately-severe','severe'
    severity_label      VARCHAR(100),   -- human-readable label from scale config

    -- Detailed scoring breakdown (depends on scoring type)
    subscale_scores     JSONB,   -- for subscale-sum scales (e.g. DASS-21)
    domain_scores       JSONB,   -- for domain-based scales (e.g. COMPASS-31, FIQR)
    component_scores    JSONB,   -- for component-sum scales (e.g. PSQI)
    dimension_scores    JSONB,   -- for profile scales (e.g. EQ-5D-5L)
    health_state_profile VARCHAR(20),  -- EQ-5D profile string e.g. "11122"
    is_positive         BOOLEAN, -- for cutoff-based scales (LANSS, DN4)
    vas_score           FLOAT,   -- for VAS scales

    -- Status
    status              VARCHAR(50)   DEFAULT 'pending',
    -- VALUES: 'pending'             (assigned, not started)
    --         'in_progress'         (started, partial)
    --         'completed'           (patient submitted)
    --         'clinician_pending'   (clinician-rated, awaiting clinician)
    --         'clinician_completed' (clinician submitted)
    --         'skipped'             (clinician skipped with reason)

    -- Clinician-rated data
    rated_by            VARCHAR(36)   REFERENCES users(id),
    rated_at            TIMESTAMPTZ,
    clinician_notes     TEXT,

    -- Patient timing data
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    time_taken_seconds  INT,
    answer_count        INT     DEFAULT 0,  -- how many questions answered

    -- Scale order in session (for display)
    display_order       INT     DEFAULT 0,

    -- Audit
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    is_deleted          BOOLEAN       DEFAULT FALSE,

    -- Constraints
    UNIQUE (session_id, scale_id)
);

CREATE INDEX idx_prs_responses_session_id ON prs_scale_responses(session_id);
CREATE INDEX idx_prs_responses_scale_id   ON prs_scale_responses(scale_id);
CREATE INDEX idx_prs_responses_status     ON prs_scale_responses(status);
```

### Table: prs_risk_alerts

```sql
CREATE TABLE prs_risk_alerts (
    id                  VARCHAR(36)   PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Context
    session_id          VARCHAR(36)   NOT NULL REFERENCES prs_assessment_sessions(id),
    scale_response_id   VARCHAR(36)   REFERENCES prs_scale_responses(id),
    patient_id          VARCHAR(36)   NOT NULL REFERENCES patients(id),
    assigned_clinician_id VARCHAR(36) REFERENCES users(id),

    -- Alert content
    alert_type          VARCHAR(100)  NOT NULL,
    -- e.g. 'suicide_ideation','severe_depression','critical_pain',
    --      'severe_cognitive_decline','dangerous_alcohol_use'

    severity            VARCHAR(20)   NOT NULL,
    -- VALUES: 'critical','high','medium','low'

    message             TEXT          NOT NULL,
    source_scale_id     VARCHAR(50),
    source_question_index INT,
    source_value        FLOAT,

    -- Status lifecycle
    status              VARCHAR(50)   DEFAULT 'active',
    -- VALUES: 'active' → 'acknowledged' → 'resolved'
    --         'escalated' (forwarded to clinical admin)

    -- Resolution tracking
    acknowledged_by     VARCHAR(36)   REFERENCES users(id),
    acknowledged_at     TIMESTAMPTZ,
    resolved_by         VARCHAR(36)   REFERENCES users(id),
    resolved_at         TIMESTAMPTZ,
    resolution_notes    TEXT,
    escalated_to        VARCHAR(36)   REFERENCES users(id),
    escalated_at        TIMESTAMPTZ,

    -- Notification tracking
    notified_user_ids   JSONB         DEFAULT '[]',
    notification_sent_at TIMESTAMPTZ,
    notification_channel VARCHAR(50), -- 'websocket','email','sms'

    -- Audit
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_prs_alerts_patient_id   ON prs_risk_alerts(patient_id);
CREATE INDEX idx_prs_alerts_session_id   ON prs_risk_alerts(session_id);
CREATE INDEX idx_prs_alerts_status       ON prs_risk_alerts(status);
CREATE INDEX idx_prs_alerts_severity     ON prs_risk_alerts(severity);
CREATE INDEX idx_prs_alerts_clinician    ON prs_risk_alerts(assigned_clinician_id);
```

### Table: prs_score_history

```sql
CREATE TABLE prs_score_history (
    id                  VARCHAR(36)   PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Relationships
    patient_id          VARCHAR(36)   NOT NULL REFERENCES patients(id),
    scale_id            VARCHAR(50)   NOT NULL,
    session_id          VARCHAR(36)   NOT NULL REFERENCES prs_assessment_sessions(id),
    scale_response_id   VARCHAR(36)   NOT NULL REFERENCES prs_scale_responses(id),

    -- Score snapshot (immutable — never updated, only inserted)
    total_score         FLOAT         NOT NULL,
    max_possible_score  FLOAT,
    percentage          FLOAT,
    severity_level      VARCHAR(50),
    severity_label      VARCHAR(100),

    -- When was this recorded
    recorded_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

    -- Audit
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_prs_history_patient_scale ON prs_score_history(patient_id, scale_id);
CREATE INDEX idx_prs_history_recorded_at   ON prs_score_history(recorded_at);
CREATE INDEX idx_prs_history_session_id    ON prs_score_history(session_id);
```

### Table: prs_patient_consents

```sql
CREATE TABLE prs_patient_consents (
    id              VARCHAR(36)   PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Context
    patient_id      VARCHAR(36)   NOT NULL REFERENCES patients(id),
    session_id      VARCHAR(36)   REFERENCES prs_assessment_sessions(id),

    -- Consent details
    consent_type    VARCHAR(100)  NOT NULL,
    -- VALUES: 'assessment_participation', 'data_storage',
    --         'report_sharing', 'anonymized_research'

    consented       BOOLEAN       NOT NULL,
    consent_text    TEXT,        -- exact text shown to patient at consent time

    -- Digital signature / audit trail
    ip_address      VARCHAR(45),
    user_agent      TEXT,
    session_token_hash VARCHAR(64), -- hash of JWT used to consent

    -- Timeline
    consented_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,
    revoked_at      TIMESTAMPTZ,

    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_prs_consents_patient_id ON prs_patient_consents(patient_id);
CREATE INDEX idx_prs_consents_session_id ON prs_patient_consents(session_id);
```

### Alembic Migration

This will be created as migration **009_prs_tables.py** (continuing from the existing migration numbering in `backend/alembic/`).

---

## 8. API Endpoint Design

All endpoints under prefix: **`/api/v1/prs`**

### Scales

```
GET    /api/v1/prs/scales                     → List all scales (admin/doctor/clin_asst)
GET    /api/v1/prs/scales/{scale_id}           → Get full scale definition (any auth)
PATCH  /api/v1/prs/scales/{scale_id}           → Update scale metadata (admin only)
POST   /api/v1/prs/scales/{scale_id}/toggle    → Enable/disable scale (admin only)
```

### Condition Batteries

```
GET    /api/v1/prs/batteries                  → List all condition batteries
GET    /api/v1/prs/batteries/{condition_id}   → Get battery with scale list
POST   /api/v1/prs/batteries                  → Create battery (admin only)
PUT    /api/v1/prs/batteries/{condition_id}   → Update battery (admin only)
DELETE /api/v1/prs/batteries/{condition_id}   → Soft delete (admin only)
```

### Assessment Sessions

```
POST   /api/v1/prs/sessions                          → Assign session to patient
GET    /api/v1/prs/sessions                          → List sessions (clinician: their patients)
GET    /api/v1/prs/sessions/my                       → Patient: my assigned sessions
GET    /api/v1/prs/sessions/{session_id}             → Get session detail
PATCH  /api/v1/prs/sessions/{session_id}             → Update notes/due_date
DELETE /api/v1/prs/sessions/{session_id}             → Cancel session
GET    /api/v1/prs/sessions/{session_id}/report      → Full report JSON
GET    /api/v1/prs/sessions/{session_id}/report/pdf  → Pre-signed Azure Blob URL
```

### Scale Responses

```
GET    /api/v1/prs/sessions/{session_id}/responses
       → List scale response stubs for this session (with status)

GET    /api/v1/prs/sessions/{session_id}/responses/{scale_id}
       → Get scale response (with saved partial answers if in_progress)

PATCH  /api/v1/prs/sessions/{session_id}/responses/{scale_id}
       → Save partial progress (auto-save)

POST   /api/v1/prs/sessions/{session_id}/responses/{scale_id}/complete
       → Submit scale (runs scoring engine + risk detection)

POST   /api/v1/prs/sessions/{session_id}/responses/{scale_id}/clinician
       → Submit clinician rating (doctor only)
```

### Risk Alerts

```
GET    /api/v1/prs/alerts                     → My active alerts (clinician)
GET    /api/v1/prs/alerts/{alert_id}           → Alert detail
POST   /api/v1/prs/alerts/{alert_id}/acknowledge
POST   /api/v1/prs/alerts/{alert_id}/resolve
POST   /api/v1/prs/alerts/{alert_id}/escalate
```

### Score History / Analytics

```
GET    /api/v1/prs/patients/{patient_id}/history
       → All score history (all scales, all sessions)

GET    /api/v1/prs/patients/{patient_id}/history/{scale_id}
       → Score history for specific scale (for trend chart)

GET    /api/v1/prs/analytics/overview         → Platform analytics (admin)
GET    /api/v1/prs/analytics/export           → CSV export (admin)
```

### WebSocket (Real-time Risk Alerts)

```
WS     /api/v1/prs/ws/alerts?token={jwt}
       → Doctor subscribes to real-time alert stream
       → Server pushes alert events when new risk flags detected
```

---

## 9. Scale Engine — Python Port

The existing `scaleEngine.js` in the prototype contains all scoring logic. It must be ported to Python as `scale_engine.py`:

```python
# backend/app/modules/prs/scale_engine.py

class ScaleEngine:
    """
    Python port of prs-frontend-app/js/scaleEngine.js
    Supports all 10+ scoring methods used across 47 clinical scales.
    """

    SCORING_HANDLERS = {
        'sum':                  '_score_sum',
        'sum-numeric':          '_score_sum',            # same as sum
        'subscale-sum':         '_score_subscale_sum',
        'subscale-severity':    '_score_subscale_severity',
        'weighted-binary':      '_score_weighted_binary',
        'weighted-domain-sum':  '_score_weighted_domain_sum',
        'fiqr-weighted':        '_score_fiqr_weighted',
        'component-sum':        '_score_component_sum',
        'profile-and-vas':      '_score_profile_and_vas',
        'reverse-scored':       '_score_reverse_scored',
        'clinician':            '_score_clinician',
        'average':              '_score_average',
    }

    @classmethod
    def calculate_score(cls, scale_id: str, responses: dict, scale_config: dict) -> dict:
        """
        Main entry point. Takes responses {question_index: value}
        and scale_config JSONB, returns complete score result.
        """
        scoring_type = scale_config.get('scoringType') or scale_config.get('scoringMethod', 'sum')
        handler_name = cls.SCORING_HANDLERS.get(scoring_type, '_score_sum')
        handler = getattr(cls, handler_name)

        score_result = handler(responses, scale_config)
        severity = cls._get_severity(score_result['total'], scale_config.get('severityBands', []))
        risk_flags = cls._check_risk_flags(scale_id, responses, scale_config)

        return {
            'scale_id': scale_id,
            'total': score_result['total'],
            'max_possible': score_result.get('maxPossible'),
            'percentage': round(score_result['total'] / score_result['maxPossible'] * 100)
                          if score_result.get('maxPossible') else 0,
            'severity': severity,
            'risk_flags': risk_flags,
            **score_result
        }

    @classmethod
    def validate_responses(cls, responses: dict, scale_config: dict) -> dict:
        """Validate all required questions are answered."""
        missing = []
        for idx, question in enumerate(scale_config.get('questions', [])):
            if question.get('required', True) and str(idx) not in responses:
                missing.append({'index': idx, 'label': question.get('question', f'Question {idx+1}')})
        return {'is_valid': len(missing) == 0, 'missing_questions': missing}
```

---

## 10. Frontend Architecture

### Application Structure

```
prs-frontend-app/  (NEW — Next.js 14 App Router)
├── src/
│   ├── app/
│   │   ├── (auth)/
│   │   │   ├── login/page.tsx          → Shared with NeuroWellness (same JWT)
│   │   │   └── layout.tsx
│   │   ├── (admin)/
│   │   │   ├── dashboard/page.tsx      → Analytics overview
│   │   │   ├── scales/
│   │   │   │   ├── page.tsx            → Scale library list
│   │   │   │   └── [scaleId]/page.tsx  → Scale detail + edit
│   │   │   ├── batteries/
│   │   │   │   ├── page.tsx            → Condition battery list
│   │   │   │   └── [conditionId]/page.tsx
│   │   │   └── users/page.tsx
│   │   ├── (clinician)/               → Doctor + Clinical Assistant
│   │   │   ├── dashboard/page.tsx      → My patients + alerts feed
│   │   │   ├── patients/
│   │   │   │   ├── page.tsx            → Patient list
│   │   │   │   └── [patientId]/
│   │   │   │       ├── page.tsx        → Patient profile + session history
│   │   │   │       ├── assign/page.tsx → Assign new session
│   │   │   │       └── sessions/
│   │   │   │           └── [sessionId]/
│   │   │   │               ├── page.tsx       → Session detail + report
│   │   │   │               └── clinician/page.tsx → Clinician rating form
│   │   │   └── alerts/page.tsx         → Risk alert management
│   │   └── (patient)/
│   │       ├── dashboard/page.tsx      → My pending/completed assessments
│   │       ├── sessions/
│   │       │   └── [sessionId]/
│   │       │       ├── page.tsx        → Session overview + consent
│   │       │       ├── take/
│   │       │       │   └── [scaleId]/page.tsx → Questionnaire UI
│   │       │       └── complete/page.tsx
│   │       └── results/
│   │           └── [sessionId]/page.tsx → Patient-facing results view
│   │
│   ├── components/
│   │   ├── ui/                     → Base components (Button, Input, Card, Badge, Tabs)
│   │   ├── layout/
│   │   │   ├── AdminSidebar.tsx
│   │   │   ├── ClinicianSidebar.tsx
│   │   │   └── PatientHeader.tsx
│   │   ├── prs/
│   │   │   ├── ScaleCard.tsx           → Scale summary card
│   │   │   ├── ScaleQuestionnaire.tsx  → Main questionnaire renderer
│   │   │   ├── QuestionRenderer.tsx    → Renders a single question (likert/VAS/numeric)
│   │   │   ├── ScoreResultCard.tsx     → Shows score + severity for one scale
│   │   │   ├── SeverityBadge.tsx       → Color-coded severity indicator
│   │   │   ├── ScoreTrendChart.tsx     → Recharts line chart for history
│   │   │   ├── RiskAlertBanner.tsx     → Prominent risk alert display
│   │   │   ├── RiskAlertFeed.tsx       → Real-time alerts sidebar
│   │   │   ├── SessionStatusTracker.tsx → Scale completion tracker
│   │   │   ├── BatterySelector.tsx     → Condition/custom battery chooser
│   │   │   ├── ReportViewer.tsx        → Full report with all scale results
│   │   │   └── ConsentModal.tsx        → HIPAA/DISHA consent screen
│   │   └── providers/
│   │       ├── AuthInitializer.tsx     → JWT init (reuse from main app)
│   │       └── WebSocketProvider.tsx   → Risk alert WS connection
│   │
│   ├── features/                   → RTK slices per domain
│   │   ├── auth/authSlice.ts       → Reuse/copy from main app
│   │   ├── scales/scalesSlice.ts
│   │   ├── sessions/sessionsSlice.ts
│   │   ├── responses/responsesSlice.ts  → Per-scale response state + autosave
│   │   ├── alerts/alertsSlice.ts        → Risk alerts state
│   │   └── analytics/analyticsSlice.ts
│   │
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts           → Axios with JWT interceptors
│   │   │   └── endpoints/
│   │   │       ├── scales.ts
│   │   │       ├── sessions.ts
│   │   │       ├── responses.ts
│   │   │       └── alerts.ts
│   │   ├── hooks/
│   │   │   ├── useAuth.ts
│   │   │   ├── useScaleAutoSave.ts   → Debounced auto-save hook
│   │   │   └── useRiskAlerts.ts      → WS subscription hook
│   │   └── utils/
│   │       ├── scoreFormatter.ts     → Format scores for display
│   │       └── severityColors.ts     → Severity → Tailwind color map
│   │
│   └── store/
│       └── index.ts                → Redux store config
│
├── public/
│   └── logo-neurowellness-prs.svg
├── .env.example
├── next.config.ts
├── tailwind.config.ts
└── package.json
```

### Key UX Flows

#### Questionnaire Flow (Patient)

```
Scale Questionnaire Page
┌───────────────────────────────────────────────────────────┐
│  PHQ-9 · Patient Health Questionnaire               3/9   │
│  ████████████░░░░░░░░░░░░░░░  33%                         │
├───────────────────────────────────────────────────────────┤
│                                                           │
│  Over the last 2 weeks, how often have you been          │
│  bothered by the following problem?                       │
│                                                           │
│  Little interest or pleasure in doing things             │
│                                                           │
│  ○  Not at all (0)                                        │
│  ○  Several days (1)                                      │
│  ●  More than half the days (2)  ← selected              │
│  ○  Nearly every day (3)                                  │
│                                                           │
├───────────────────────────────────────────────────────────┤
│  [← Previous]                      [Save & Next →]       │
└───────────────────────────────────────────────────────────┘

Auto-save triggered on every selection (debounced 500ms).
Progress preserved in DB — patient can close and resume.
```

#### Score Result Card (Clinician View)

```
┌─────────────────────────────────────────────────────────┐
│  PHQ-9 · Patient Health Questionnaire-9           ✓     │
│                                                         │
│  Score: 17 / 27                    ████████████░░  63%  │
│                                                         │
│  Severity: ┌─────────────────────────┐                  │
│            │  MODERATELY SEVERE      │  🟠              │
│            └─────────────────────────┘                  │
│                                                         │
│  ⚠️  RISK FLAG: Q9 (Suicidal ideation) — Score: 2       │
│     Requires immediate clinical attention               │
│                                                         │
│  Completed: 20 Mar 2026 · 8 min 42 sec                 │
└─────────────────────────────────────────────────────────┘
```

---

## 11. Infrastructure & Deployment

### Azure Architecture (India-primary, DISHA compliant)

```
                    ┌────────────────────────────────┐
                    │      Azure Front Door           │
                    │  (CDN + WAF + Global LB)        │
                    └──────────────┬─────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
   ┌──────────▼──────┐  ┌──────────▼───────┐  ┌────────▼────────┐
   │  AKS Cluster    │  │  AKS Cluster     │  │  Static Web     │
   │  Central India  │  │  Southeast Asia  │  │  App (Azure)    │
   │  (Primary)      │  │  (DR/Failover)   │  │  PRS Frontend   │
   │                 │  │                  │  │                 │
   │  · API pods     │  │  · API pods      │  └─────────────────┘
   │  · Celery pods  │  │  · Read replica  │
   └────────┬────────┘  └──────────────────┘
            │
   ┌────────▼────────────────────────────────────────────┐
   │               Data Tier                             │
   │                                                     │
   │  Supabase PostgreSQL      Redis (Azure Cache)       │
   │  (Primary DB)             · Scale JSONB cache       │
   │                           · Celery broker           │
   │  Azure Blob Storage       · WS pub/sub              │
   │  · PDF reports                                      │
   │  · Exports                Azure Key Vault           │
   │                           · Secrets                 │
   └─────────────────────────────────────────────────────┘
```

### Docker Compose (Local Dev)

```yaml
# Extension to existing docker-compose.yml
services:
  prs-api:           # Same FastAPI container, just with PRS routes enabled
    extends: api
    environment:
      - PRS_MODULE_ENABLED=true

  redis:             # New — needed for Celery + WS
    image: redis:7-alpine
    ports: ["6379:6379"]

  celery-worker:     # New — async tasks (PDF gen, notifications)
    build: ./backend
    command: celery -A app.tasks worker --loglevel=info

  prs-frontend:      # New Next.js app
    build: ./prs-frontend-app-new
    ports: ["3001:3000"]  # Main app on 3000, PRS on 3001
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
```

### CI/CD Pipeline (GitHub Actions)

```
Push to main branch:
  1. Lint + type check (mypy, ESLint)
  2. Unit tests (pytest, Jest)
  3. Build Docker images
  4. Run integration tests (TestClient + Playwright)
  5. Build Alembic migration check
  6. Deploy to staging (auto)
  7. Manual approval gate
  8. Deploy to production (Azure AKS)
  9. Run smoke tests
 10. Notify team (Slack/Teams)
```

---

## 12. Security & Compliance

### Authentication & Authorization

| Requirement | Implementation |
|-------------|---------------|
| JWT tokens | Existing JWTManager — shared across PRS and main app |
| RBAC enforcement | `require_role()` decorator on every PRS endpoint |
| Patient data isolation | Every query filters by `patient_id` — patients only see own data |
| Clinician data isolation | Clinicians only see patients assigned to them |
| Token expiry | Access: 60min · Refresh: 7 days |

### Data Security

| Requirement | Implementation |
|-------------|---------------|
| Encryption at rest | Supabase PostgreSQL TDE + Azure Blob encryption |
| Encryption in transit | TLS 1.3 enforced by Azure Front Door |
| Secrets management | Azure Key Vault — no secrets in code or env files in production |
| JSONB responses | Responses stored encrypted-at-rest, never logged |
| Audit trail | Every action (assign, complete, view, download) logged to `audit_logs` |
| Soft deletes | No patient data ever hard-deleted |

### Compliance

| Standard | Status |
|----------|--------|
| **DISHA** (India Digital Health) | Azure Pune datacenter — data residency in India ✅ |
| **HIPAA** | Encryption, audit logs, access controls, BAA via Azure ✅ |
| **GDPR** | Soft delete = right to erasure, data export, consent records ✅ |
| **ISO 27001** | Azure compliance inheritance + our audit logging ✅ |

### Clinical Safety

| Risk | Mitigation |
|------|-----------|
| Suicide ideation flag | PHQ-9 Q9, MADRS Q10 → immediate `critical` alert → WebSocket push to clinician |
| Missed assessments | Celery scheduled task: check overdue sessions daily → notify clinician |
| Clinician-rated scales | EDSS, MADRS, MAS, MRC, KPS, ALSFRS-R → locked until clinician submits |
| Score accuracy | ScaleEngine is a direct 1:1 Python port of the validated JS engine |

---

## 13. Developer Work Split

The team of 3 developers splits as follows:

---

### Developer 1 — Backend Engineer

**Scope:** Full PRS backend module

**Deliverables:**

1. **Database** (`models.py` + Alembic migration `009_prs_tables.py`)
   - Create all 7 SQLAlchemy models
   - Write migration
   - Seed 47 scales from JSON files

2. **Scale Engine** (`scale_engine.py`)
   - Port all 11 scoring methods from `scaleEngine.js` to Python
   - Port `getSeverityClassification()` and `checkRiskFlags()`
   - Write unit tests for every scoring type against known expected values

3. **Repository + Service + Router** (`repository.py`, `service.py`, `router.py`)
   - All CRUD for sessions, scale responses, alerts, history
   - Complete service orchestration (assign → respond → complete → score → alert)
   - All 25+ API endpoints

4. **Risk Detection** (`risk_detector.py`)
   - Trigger on scale completion
   - WebSocket push (Redis pub/sub → connected clients)

5. **Async Tasks** (`tasks.py`)
   - PDF report generation (WeasyPrint)
   - Overdue session notifications
   - Redis setup for Celery

6. **Wire into `main.py`**
   - Uncomment `prs_router` line
   - Register `/api/v1/prs` prefix

**Key files to reference:**
- `backend/app/modules/patients/` — canonical module pattern to follow
- `prs-frontend-app/js/scaleEngine.js` — source of truth for scoring logic
- `prs-frontend-app/data/scales/*.json` — 47 scale definitions to seed
- `prs-frontend-app/data/conditionMap.json` — 16 condition batteries to seed

---

### Developer 2 — Frontend Engineer (Clinician + Admin side)

**Scope:** PRS Frontend App — Admin Portal + Clinician Portal

**Deliverables:**

1. **Project setup**
   - Scaffold new Next.js 14 app (`prs-frontend-app-new/`)
   - Copy/adapt auth, Redux store, API client from `frontend-sozo`
   - Tailwind config, brand tokens, NeuroWellness PRS theme

2. **Admin Portal** (`/admin/*`)
   - Scale Library page (table, search, enable/disable)
   - Scale detail page (view JSONB definition, metadata edit)
   - Condition Battery management (CRUD)
   - User management
   - Analytics dashboard (Recharts: completion rates, usage charts)

3. **Clinician Portal** (`/clinician/*`)
   - Dashboard with patient list + alerts feed sidebar
   - Patient profile page + session history
   - Assign session flow (battery selector + custom scale picker + due date)
   - Session detail + full report viewer
   - Clinician rating form (for EDSS, MADRS etc.)
   - Risk alert list + acknowledge/resolve UI

4. **Shared components**
   - `ReportViewer.tsx` — full multi-scale report
   - `ScoreResultCard.tsx` — individual scale result
   - `ScoreTrendChart.tsx` — Recharts longitudinal chart
   - `RiskAlertFeed.tsx` — real-time WS alert sidebar
   - `SeverityBadge.tsx` — color-coded severity

5. **API integration**
   - All RTK Query slices for clinician/admin endpoints
   - WebSocket hook for real-time alerts

---

### Developer 3 — Frontend Engineer (Patient side) + Database

**Scope:** PRS Frontend App — Patient Portal + DB schema finalization

**Deliverables:**

1. **Database Schema Finalization** (coordinate with Dev 1)
   - Review and finalize all 7 table schemas
   - Write seed scripts for scales + conditions
   - Test migration on local Supabase
   - Document query patterns and indexes

2. **Patient Portal** (`/patient/*`)
   - Dashboard — pending/in-progress/completed sessions
   - Session overview page — condition, scale list, estimated time, consent
   - **Consent screen** — DISHA/HIPAA compliant, recorded to DB
   - **Core questionnaire renderer** (`ScaleQuestionnaire.tsx`)
     - One scale at a time
     - All question types: likert, numeric, VAS slider, time picker
     - Auto-save (debounced 500ms) via PATCH endpoint
     - Progress indicator (scale X/Y, question X/Y)
     - Resume capability (load saved partial responses on load)
     - Validation before submit
   - Scale completion screen (with brief result summary if enabled)
   - Session completion screen
   - Patient-facing results page (summary view, download PDF if enabled)

3. **Scale rendering engine** (frontend)
   - Port the question renderer from the existing HTML/JS prototype
   - Handle all question types from the 47 scale JSONs:
     - `likert` — radio options
     - `numeric` — number input
     - `visual-analogue-scale` — range slider
     - `time` — time picker
     - `text` — free text
     - `conditional` — show/hide based on prior answer

**Key reference file:** `prs-frontend-app/index.html` + `prs-frontend-app/js/app.js` — existing prototype UI/UX to port.

---

## 14. Phased Development Roadmap

### Phase 1 — Foundation (Weeks 1–3)
**Goal: Backend running with core scale/session/response flow**

- [ ] DB migration 009 — 7 PRS tables created
- [ ] Seed 47 scales from JSON into `prs_scales`
- [ ] Seed 16 conditions into `prs_condition_batteries`
- [ ] `scale_engine.py` ported + unit tested
- [ ] Session assignment API (`POST /prs/sessions`)
- [ ] Scale response save/complete API
- [ ] Basic scoring + severity working end-to-end
- [ ] PRS module wired into `main.py`

**Milestone:** Postman can: assign a session → submit PHQ-9 responses → get back score + severity

---

### Phase 2 — Risk + Reports (Weeks 4–5)
**Goal: Risk detection, PDF reports, async tasks**

- [ ] `risk_detector.py` — all scales' `riskRules` implemented
- [ ] Redis + Celery setup
- [ ] `pdf_generator.py` — clinical report PDF
- [ ] Azure Blob upload for PDFs
- [ ] WebSocket endpoint for real-time alerts
- [ ] Score history tracking (`prs_score_history`)
- [ ] Analytics API

**Milestone:** Completing PHQ-9 Q9 with score ≥1 triggers critical alert, clinician receives WebSocket push

---

### Phase 3 — Clinician Frontend (Weeks 6–8)
**Goal: Doctors can assign and view reports**

- [ ] PRS Frontend App scaffolded
- [ ] Auth shared with main app (same JWT)
- [ ] Clinician dashboard
- [ ] Patient list + profile
- [ ] Assign session flow
- [ ] Session detail + report viewer
- [ ] Risk alert management
- [ ] Score trend charts

**Milestone:** Doctor can assign "Depression/Anxiety" battery to patient and view completed scores

---

### Phase 4 — Patient Frontend (Weeks 9–11)
**Goal: Patients can take assessments end-to-end**

- [ ] Patient dashboard
- [ ] Consent screen
- [ ] Questionnaire renderer for all question types
- [ ] Auto-save + resume
- [ ] All 47 scale types render correctly
- [ ] Completion flow
- [ ] Patient results view

**Milestone:** Patient logs in, takes all 7 PSQI questions, submits, sees severity, doctor sees report

---

### Phase 5 — Admin + Polish (Weeks 12–13)
**Goal: Admin portal + production readiness**

- [ ] Admin scale library management
- [ ] Admin condition battery management
- [ ] Analytics dashboard
- [ ] Multi-language groundwork (Hindi)
- [ ] Mobile responsive audit
- [ ] E2E test suite (Playwright)
- [ ] Performance testing
- [ ] Security audit

**Milestone:** Investor demo ready — prs.neurowellness.com fully functional

---

### Phase 6 — Production Deploy (Week 14)
**Goal: Live on Azure**

- [ ] AKS deployment config
- [ ] Azure Front Door + WAF
- [ ] Monitoring + alerting (Azure Monitor)
- [ ] Backup verification
- [ ] DISHA compliance sign-off
- [ ] Team training

---

## Summary: What Gets Built

| Component | Status | Who Builds It |
|-----------|--------|---------------|
| 7 PRS DB tables + migration | New | Dev 1 + Dev 3 |
| 47 scale seed scripts | New (data exists) | Dev 1 |
| Python ScaleEngine | New (port from JS) | Dev 1 |
| PRS backend module (25+ APIs) | New | Dev 1 |
| Risk detection + alerts | New | Dev 1 |
| PDF report generation | New | Dev 1 |
| Celery async tasks | New | Dev 1 |
| Admin portal frontend | New | Dev 2 |
| Clinician portal frontend | New | Dev 2 |
| Risk alert WS frontend | New | Dev 2 |
| Patient questionnaire UI | New (port from prototype) | Dev 3 |
| Patient dashboard + results | New | Dev 3 |
| Auto-save + resume logic | New | Dev 3 |

**Existing infrastructure reused:** Auth, JWT, RBAC, PostgreSQL, Azure, `patients` table, `users` table, audit logs, Azure Blob, Key Vault, Docker, AKS config, DISHA compliance.

---

*Document authored by: NeuroWellness Engineering*
*Architecture version: 1.0 — March 2026*
*Next review: After Phase 1 completion*
