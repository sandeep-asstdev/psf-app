---
name: psf-app
description: Project knowledge and working rules for the PSF (Post Service Follow-up) multi-tenant dealership app (React + FastAPI + PostgreSQL + Redis + MinIO). Use this skill at the START of every task in this repo, including any change to PSF, CRE calling, call console, DMS import, call allocation, complaints, Ather TNPS, questionnaires, rating scales, roles and permissions, Admin Console, reports, migrations, seeds or tests. Read it BEFORE exploring the codebase so you do not re-read files, and follow its speed rules and non-negotiable rules even when the user does not mention them.
---

# PSF App: project skill

Read this file first. It replaces a lot of exploring. Only open the files a task needs.

## 1. What the product is
PSF = Post Service Follow-up. After a car is serviced, the dealership's CREs (Customer Relationship Executives) call or WhatsApp the customer, record the answers, raise complaints for unhappy customers, and get them closed. Replaces a Google AppSheet app. It will be SOLD to many dealership groups, so everything must be multi-tenant and configurable (config over code).

Flow: DMS job cards imported -> follow-up queue items created -> split equally among PRESENT CREs -> CRE calls (call console) -> survey answers + outcome -> complaint if unhappy -> closure -> reconfirmation -> reports.

## 2. Domain facts (do not re-derive)
- Hierarchy: Tenant (dealership group) > Brand > Branch. Only Super Admin creates brands and branches.
- Roles (rows in DB, not code): L1 SUPER_ADMIN (developers, everything), L2 CRE_ADMIN (all brands/branches, limited), L3 BRANCH_MANAGER, BRANCH_CRE, SERVICE_ADVISOR (scoped to own branch / own calls / own customers). Auditor also exists.
- **TNPS is NOT a generic second survey.** It is the name of the PSF follow-up program of the ATHER ENERGY brand. It is created on import like PSF, allocated the same way, no delayed second call. See docs/TNPS_CORRECTION.md. The Hyundai sheet column "TNPS Date" has unknown meaning: stored raw as legacy only.
- Brands: HYUNDAI, TATA MOTORS, HERO MOTO CORP, MG MOTORS, ATHER ENERGY, CHEVROLET, SWARAJ. Branch-to-brand mapping is explicit (never infer from name prefixes; "ATHER BANGALORE" belongs to ATHER ENERGY). "Haveri TRZ" is needs_review (no brand).
- Job Card No looks like `S8211_R2026xxxxx`; prefix is the branch DMS code (S8211 Hubli, S8827 Gadag).
- Rating scales differ per brand and are configurable: Hyundai 1-5 poor, 6-8 average, 9 satisfied, 10 delight (9 and below should raise a complaint, category "WhatsApp Rating <=9", keep it a setting); Tata 5 good, 4 satisfied, 1-3 dissatisfied; MG 1-8 dissatisfied, 9-10 satisfied.
- Case statuses fall in categories: SENTIMENT (Delight, Satisfied, Non-Delight, Dissatisfied), CONTACT_FAILED (No Response, Not Reachable, Switch Off, Incoming Call Not Available, Call Disconnected), INVALID (Wrong Number, Invalid Number, Vehicle Sold), DEFERRED (Call Later, Vehicle Inside Workshop, Vehicle Not Checked, Parts Order). Behaviour comes from flags (counts_as_contacted, retry_allowed, closes_followup), not from names.
- Survey answers: normalise Yes/YES/yes to Yes; ratings are numeric. Question answer_type is configurable per question (YES_NO, YES_NO_NA, RATING_10, RATING_5, TEXT); legacy data contradicts the old dropdown file for some questions.
- Attempts: every call attempt is a row in call_attempts; totals are derived, never typed.

## 3. Standard DMS import file (13 columns)
Brand, Branch, Brand Logo (ignored), Job Card No, Job Card Date, Customer Name, Contact Number, Vin No, Reg No, Model, Service Advisor, Service Type, Total Service Amount. Unique ID, Uploaded By, Upload Timestamp are system generated. Read cells as text (Excel corrupts phones). Unknown brand/branch = row error; unknown advisor = inactive placeholder user; dedupe on (branch_id, job_card_no). Mapping templates are editable per brand.

## 4. Call allocation (built, in services/allocation_service.py)
Equal split among present CREs (counts differ by at most 1), remainder rotated by a persisted cursor, advisory lock per tenant, sticky customers (same phone together), only untouched calls (attempts == 0, PENDING) can move, undo within a window, unallocated pool when nobody is present. Present = active + call.make + login session today, or manual override (attendance_overrides). Strategies: EQUAL_PRESENT_CRE, ROUND_ROBIN, BY_BRANCH, MANUAL. Settings live in the Admin Console "Allocation Rules" tab.

## 5. Permissions (data-driven, never by role name)
- Backend: `require("resource.action")` dependency + `apply_data_scope` on every query. Scopes: ALL, DEALERSHIP, ASSIGNED_BRANCHES, OWN. Matrix lives in role_permissions; defaults seeded in backend/app/db/seed.py; catalogue in backend/app/core/permissions.py.
- Frontend: `can("key")` from authStore, `<Can do="key">`, ProtectedRoute with `permission=`. Never write `role === "SUPER_ADMIN"` anywhere.
- A user may only create/edit users at or below their own role level. Lockout protection: never delete the last Super Admin.
- Phone numbers are masked unless `contact.unmask`.

## 6. Repo map
```
backend/app/
  api/deps.py, api/v1/api.py, api/v1/endpoints/*.py   (admin_console, allocation, auth, complaints, health, imports, masters, psf, questionnaires, reports, users)
  core/    config, crypto (Fernet + HMAC blind hash), database, permissions, redis, security, storage (MinIO)
  models/  additional (many misc tables), allocation, auth, complaint, customer, followup, questionnaire, service, tenant
  schemas/ one file per area
  services/ allocation, auth, complaint_flow, import, master, psf, questionnaire, rating, report, user
  db/      seed.py, seed_questionnaires.py
  workers/runner.py
backend/alembic/versions/ 0001 .. 0007   (latest: 0007_ather_tnps_model_correction)
backend/tests/            one test file per area, conftest.py
frontend/src/
  components/ allocation, auth (Can, ProtectedRoute), calling (CallConsoleModal, CallAttemptHistoryModal), common, layout
  pages/      admin (AdminConsolePage is huge), advisors, auth, complaints, happiness, imports, psf, reports, settings, users
  services/api.js, store/authStore.js, store/themeStore.js
scripts/ import_legacy.py, seed_data.py, purge_test_data.py
docs/    ADMIN_GUIDE, architecture, er_diagram, legacy_column_mapping, TNPS_CORRECTION
sample_data/ MASKED files only
```
Verify exact paths with a quick `ls` or grep before editing; do not assume.

## 7. Tech stack and commands
Frontend: React 18 + Vite, JavaScript only (.js/.jsx, NO TypeScript), Tailwind with light AND dark theme (class strategy, CSS-variable tokens in index.css, toggle in themeStore), TanStack Query, Zustand, Recharts, Lucide. Keep the design minimal.
Backend: Python 3.12, FastAPI async, SQLAlchemy 2.0 async + Alembic (NOT Prisma), PostgreSQL 16, Redis, MinIO, JWT httpOnly cookies. No cloud services (self-hosted data center).
Host is Windows (`start.bat` / `stop.bat`); containers: psf_api, psf_web, psf_db, redis, minio.
```
Migrate:   docker exec psf_api alembic upgrade head
Backend tests (targeted): docker exec psf_api pytest tests/test_<area>.py -x -q
Backend tests (full, once per task): docker exec psf_api pytest tests -q
Frontend:  npm test --prefix frontend -- --run   |   npm run build --prefix frontend
Deploy build locally: copy frontend/dist into the psf_web container web root
```
Python scripts on Windows: use UTF-8 (`PYTHONIOENCODING=utf-8`), emoji in output breaks otherwise.

## 8. NON-NEGOTIABLE rules
1. Database changes go through Alembic migrations only (with downgrade). No create_all, no manual SQL changes in a running DB. A fresh DB (`alembic upgrade head` + seed) must pass all tests.
2. Config over code: statuses, categories, questions, scales, labels, allocation rules, programs are data edited in the Admin Console. Do not hard-code brand names, question keys, rating thresholds or status names in business logic.
3. Every query is tenant-scoped; every read/write respects `apply_data_scope`.
4. Customer phone numbers: encrypted at rest + blind hash for search; never log or print PII; never commit real customer data. Only the masked CSV lives in sample_data/ and backend/sample_data/. `.env` is never committed.
5. Soft delete, never hard delete business data. Every config or data edit writes an audit log row (who, what, before, after, reason).
6. Do not weaken or delete a test to make it pass. If a test must change because behaviour changed on purpose, say so in the summary.
7. Do not break existing behaviour for Hyundai, MG, Tata, Ather (DMS import, allocation, complaint lifecycle, legacy importer).
8. No new heavy dependencies without a reason. No cloud-only services.

## 9. SPEED RULES (how to work fast here)
- Read this file, then open only files the task touches. Never re-read a file you have already read in the session; never dump whole large files (AdminConsolePage.jsx, allocation_service.py, import_service.py): grep for the symbol, then view a line range.
- Write whole new files in one call. Batch related edits. Do not make 5 tiny edits to the same file.
- Run only tests related to the change while working; run the full suite once at the end.
- Do not write audit reports, long explanations or extra docs unless asked. Final answer: 10 lines or fewer (what changed, files, test result, anything needing my decision).
- Prefer extending existing services over new abstractions. Put new models in new files (e.g. models/config.py), not in models/additional.py.
- If a task is large, split into slices, commit after each, and stop for approval between slices.
- Ask a question only when truly blocked. Otherwise state the assumption in one line and proceed.

## 10. Known gotchas (from past work)
- Tests need realistic fixtures: Vehicle relationships, followup `due_at` populated, AuditLog field names (check the model first), the session factory name in core/database.py.
- Earlier work set tables/defaults outside Alembic once (`is_deleted` on reconfirmations). Make sure every schema change is in a migration.
- Frontend bundle is ~1 MB with no route code-splitting; split by route when touching routing.
- AdminConsolePage.jsx is one very large file; new tabs go into separate files under pages/admin/tabs/.
- The "first CRE to log in gets the whole unallocated pool" behaviour is a known issue; allocation mode (IMMEDIATE / SCHEDULED / WHEN_MIN_PRESENT) should be configurable.

## 11. Definition of done (check before finishing)
- Migration added and a fresh-DB run is fine; seeds updated if masters changed.
- Permission keys used for new endpoints and UI (no role-name checks); scope applied.
- Related tests added/updated and passing; full suite run once.
- No PII in logs, commits or fixtures.
- Short summary given; docs updated only where behaviour for admins changed (docs/ADMIN_GUIDE.md, docs/er_diagram.md).

## 12. Open items (ask the user only if the task depends on them)
Ather TNPS rating scale (default 0-10) and extra Ather questions; meaning of Hyundai "TNPS Date"; who sends WhatsApp rating requests today (real WhatsApp/SMS provider not built, a stub exists or is planned); whether each dealership's CREs are a central pool or per branch (default CRE_POOL, configurable).
