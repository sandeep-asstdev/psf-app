# PSF – Post Service Follow-up SaaS Platform

A production-grade, multi-tenant enterprise SaaS web application engineered for automobile dealership groups to manage Post Service Follow-up (PSF), customer complaints lifecycle, NPS/TNPS scoring, 15/30-day Happiness Calling (**strictly exclusive to Hyundai**), service advisor feedback resolution, and post-resolution customer reconfirmations.

---

## 1. Architectural Highlights & Tech Stack

### Frontend
- **Framework**: React 18+ with Vite (Pure JavaScript / JSX only, zero TypeScript).
- **Styling**: Tailwind CSS with persistent **Light AND Dark theme** (HTML class strategy, localStorage persistence, CSS custom property design tokens, respects OS preference).
- **State & Data**: TanStack Query (server state), Zustand (auth, UI, and theme state), React Hook Form + Zod validation.
- **Visuals & Tables**: Recharts (CSAT/NPS trend areas, category donut, CRE bar charts, funnel stages), Lucide Icons, date-fns, react-hot-toast.
- **Compliance**: PWA-ready, mobile-first responsive layout tailored for CREs on smartphones and tablets.

### Backend
- **Framework**: Python 3.11+, FastAPI (async), Pydantic v2, Uvicorn ASGI.
- **Database & ORM**: PostgreSQL 18 with **SQLAlchemy 2.0 (async)** + **Alembic** migrations.
- **Keys & Indexing**: UUIDv7 time-sortable primary keys, JSONB GIN indexes for dynamic questionnaire survey answers, composite indexes on tenant and queue states.
- **Cache & Rate Limiting**: Redis 7 for dashboard aggregate caching, rate limiting (35 attempts/min on login), token blacklist, and background queue broker.
- **Storage**: MinIO S3-compatible object storage for document uploads, gate passes, and call audio recordings.
- **Background Worker**: Python asyncio background worker processing queue allocation, SLA breach monitors, and reminder dispatch.

---

## 2. Multi-Tenancy, Scoping & Security

- **Strict Multi-Tenancy**: Hierarchy is structured as `Tenant (Dealer Group)` $\rightarrow$ `Brands (Hyundai, MG, Ather)` $\rightarrow$ `Branches (Workshops)`. Every relational table carries `tenant_id` with row-level scoping.
- **Role-Based Access Control (RBAC)**: Configured with granular permissions for:
  - `SUPER_ADMIN` (Platform owner)
  - `DEALER_ADMIN` (Dealership group management)
  - `BRAND_MANAGER` (Brand-specific queue & questionnaire oversight)
  - `BRANCH_MANAGER` (Workshop operations & complaint assignment)
  - `CRE` (Customer Relationship Executive / follow-up callers)
  - `SERVICE_ADVISOR` (Workshop technical advisors for dissatisfaction resolution)
  - `AUDITOR` (Read-only compliance officer)
- **Data Privacy & Encryption**: Customer phone numbers are stored encrypted at rest using **Fernet AES-128-CBC** (`phone`) alongside HMAC-SHA256 blind hashes (`phone_hash`) for fast deduplication. All UI representations are masked by default (`+91 98*****455`) with one-click `tel:` and WhatsApp links.
- **Production Hardening**: Enforced HTTP security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security`, `Referrer-Policy`) and Redis rate limiting.

---

## 3. Core Modules & Functionality

### 3.1 Home Dashboard
- Welcome greeting with active shift timer and quick KPI stats pills.
- Role-gated module navigation tiles (PSF Dashboard, Happiness Calling, Complaints, Reports, Data Import, User Management, Settings).

### 3.2 PSF Calling Workspace & Split-Layout Call Console
- Grouped filterable queue cards (By Brand $\rightarrow$ Branch, Call Status, Today's Reminders).
- Split-screen **Call Console**:
  - *Left*: Comprehensive customer, vehicle (VIN, Reg, Model), job card invoice, service advisor, and prior call timeline.
  - *Right*: Dynamic questionnaires, call status select (`Connected`, `Busy`, `No Answer`, `Callback`), case status (`Satisfied`, `Dissatisfied`), live call duration timer, and complaint escalation toggle.

### 3.3 Dynamic Questionnaire Engine
- Versioned questionnaires configured per brand and queue type.
- Supports `rating_5`, `nps_10`, `yes_no`, `yes_no_na`, `single_select`, `multi_select`, and conditional `text` fields (`show_if`).
- Automatic score computation calculating CSAT percentage and NPS Promoter/Passive/Detractor categories.

### 3.4 DMS Data Import & Real-time Webhook
- Interactive Excel/CSV column mapper with preset templates per brand.
- Duplicate detection on `(tenant_id, branch_id, job_card_no)` with `SKIP` or `UPDATE` strategies.
- Round-robin auto-allocation to active CRE callers.
- Direct REST API Webhook (`POST /api/v1/imports/webhook`) for real-time DMS invoice integration.

### 3.5 Complaint Management Lifecycle & SLAs
- Full status flow: `OPEN` $\rightarrow$ `ASSIGNED` $\rightarrow$ `IN_PROGRESS` $\rightarrow$ `RESOLVED` $\rightarrow$ `RECONFIRMATION` $\rightarrow$ `CLOSED` / `REOPENED`.
- Configurable SLA thresholds per category with real-time breach detection.
- Complete audit trail logging every status change, remark, and assignee modification.

### 3.6 Hyundai-Exclusive Happiness Calling
- **OEM Exclusivity Rule**: Strictly restricted to Hyundai Motor India customers (`brand.code == 'HYUN'`).
- Dedicated 15-day and 30-day post-delivery quality tracking queue with the Hyundai Happiness questionnaire.

### 3.7 Service Advisor Follow-Up Portal
- Restricted portal (`/advisor`) for Service Advisors to review dissatisfied customer feedback and Detractor ratings.
- Advisor callback resolution modal to log call status, case outcome (`Customer Convinced`, `Part Ordered`, `Inspection Scheduled`), and submit corrective remarks (`adv_voc`).

### 3.8 Post-Resolution Reconfirmations
- Automatically schedules a `RECONFIRMATION` calling queue 24 hours after a complaint is marked `RESOLVED`.
- Reconfirming satisfaction transitions the ticket to `CLOSED`; unresolved customer sentiment transitions it to `REOPENED` with an urgent 12-hour SLA.

### 3.9 Executive Reports & Analytics Dashboard
- KPI summary cards (Job Cards, Connect Rate, CSAT, NPS, Complaints, SLA Compliance).
- Recharts visualizations: 7-day CSAT & volume trends, complaints donut, CRE productivity comparisons, and retention funnel.
- Branch leaderboard and Service Advisor performance scorecards.
- Streaming multi-tab Excel export (`.xlsx`) generated via `openpyxl`.

---

## 4. Quick Start & Operation

### Easy Start via Windows Batch Files
- **To Start Platform**: Double-click [`start.bat`](file:///c:/Users/User/Desktop/PSF/start.bat)  
  *Checks Docker engine, boots all 6 containers in detached mode, runs health checks, and displays URLs.*
- **To Stop Platform**: Double-click [`stop.bat`](file:///c:/Users/User/Desktop/PSF/stop.bat)  
  *Gracefully stops all containers while preserving database and MinIO volumes.*

### Service URLs
| Service | URL | Description |
|---|---|---|
| **Web Application** | `http://localhost:5173` | React Single Page Application |
| **FastAPI Swagger Docs** | `http://localhost:8000/api/v1/docs` | OpenAPI Interactive Documentation |
| **API Health Endpoint** | `http://localhost:8000/health` | System & DB health check |
| **MinIO S3 Console** | `http://localhost:9001` | Object Storage UI (`admin` / `admin12345`) |
| **PostgreSQL 18** | `localhost:5434` | Database (`psf_db` / `postgres` / `postgres123`) |
| **Redis Cache** | `localhost:6380` | Redis 7 cache & queue |

---

## 5. Seeded Demo Accounts & Real Data Masters

All demo accounts belong to the seeded tenant **Apex Automotive Group**:

| Role | Email | Password | Scope |
|---|---|---|---|
| **Super Admin** | `admin@apexauto.com` | `Admin@12345` | Global Tenant Scope |
| **Dealer Admin** | `dealer.admin@apexauto.com` | `Dealer@12345` | Dealership Group Scope |
| **Service Manager / Closer** | `deepa.hiremath@apexauto.com` | `Closer@12345` | Hyundai Hubli (Complaint Closer) |
| **Branch Manager** | `manager.central@apexauto.com` | `Manager@12345` | Apex Central (Hyundai) |
| **CRE Caller** | `priya.cre@apexauto.com` | `Priya@12345` | Apex Central Workshop |
| **CRE Caller** | `pooja.cre@apexauto.com` | `Cre@12345` | Hyundai Hubli |
| **CRE Caller** | `arpita.cre@apexauto.com` | `Cre@12345` | Hyundai Hubli |
| **Service Advisor** | `rajesh.adv@apexauto.com` | `Advisor@12345` | Service Advisor Portal |
| **Auditor** | `audit@apexauto.com` | `Auditor@12345` | Read-only Auditing |

---

## 6. Real Data Migration & Legacy 120-Column Importer

The PSF platform is fully aligned with real dealership operational data from the legacy AppSheet and WhatsApp system:
- **7 OEM Brands**: Hyundai, Tata Motors, MG Motors, Ather Energy, Hero Moto Corp, Chevrolet, Swaraj.
- **27 Workshop Branches**: Explicit branch-to-brand mapping with DMS codes (e.g. `S8211` for Hubli, `S8827` for Gadag) and `Haveri TRZ` unassigned review branch.
- **16 Branch Contacts**: Service Manager escalation phone numbers stored encrypted with blind HMAC-SHA256 search hashes.
- **Brand Rating Scales & Bands**:
  - *Hyundai* (10-point): 1–5 Poor (Dissatisfied), 6–8 Average (Non-Delight), 9 Satisfied, 10 Delight.
  - *Tata Motors* (5-point): 1–3 Dissatisfied, 4 Satisfied, 5 Good (Delight).
  - *MG Motors* (10-point): 1–8 Dissatisfied/Poor, 9–10 Satisfied.
- **14 Cleaned Complaint Categories** with icons and legacy labels.
- **Per-Attempt Call Logs (`call_attempts`)**: Replaces spreadsheet counters with sequential dial records.

### Running Comprehensive Real Data Seeds:
```bash
docker exec psf_api python /app/scripts/seed_real_data.py
```

### Running the 120-Column Legacy Importer:
```bash
# Dry-run validation report:
docker exec psf_api python /app/scripts/import_legacy.py --file /app/sample_data/sample_data_Sheet1_masked.csv --dry-run

# Live commit:
docker exec psf_api python /app/scripts/import_legacy.py --file /app/sample_data/sample_data_Sheet1_masked.csv
```

---

## 7. Running Automated Tests

### Backend Test Suite (Pytest inside Docker)
Run all 15 automated test suites across all build phases and real data import:
```bash
docker exec psf_api pytest -v
```
Output:
```text
tests/test_api_endpoints.py::test_health_endpoints PASSED
tests/test_api_endpoints.py::test_auth_and_questionnaire_oem_restriction PASSED
tests/test_phase3_questionnaires.py::test_calculate_survey_score_csat_and_nps PASSED
tests/test_phase4_imports.py::test_dms_import_and_oem_happiness_allocation PASSED
tests/test_phase4_imports.py::test_dms_realtime_webhook PASSED
tests/test_phase5_psf_console.py::test_psf_dashboard_and_call_console PASSED
tests/test_phase6_complaint_lifecycle.py::test_complaint_lifecycle_and_reconfirmation PASSED
tests/test_phase7_reports.py::test_reports_summary_and_excel_export PASSED
tests/test_phase8_hardening_and_e2e.py::test_security_headers_and_production_hardening PASSED
tests/test_phase8_hardening_and_e2e.py::test_end_to_end_full_psf_lifecycle PASSED
tests/test_real_data_import.py::test_rating_band_derivation_hyundai PASSED
tests/test_real_data_import.py::test_rating_band_derivation_tata PASSED
tests/test_real_data_import.py::test_rating_band_derivation_mg PASSED
tests/test_real_data_import.py::test_db_rating_scale_bands PASSED
tests/test_real_data_import.py::test_imported_legacy_data_assertions PASSED

============================== 15 passed in 5.70s ==============================
```

### Frontend Test Suite (Vitest)
Run the frontend unit & smoke test suite:
```bash
cd frontend
npm test
```
Output:
```text
 ✓ src/tests/smoke.test.jsx (3 tests passed)
```

### Compiling Production Frontend Bundle
```bash
cd frontend
npm run build
docker cp dist/. psf_web:/usr/share/nginx/html/
```
