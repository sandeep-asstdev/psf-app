# Script to add header documentation to backend API endpoints and server entry

import os

DOCS = {
    "backend/app/main.py": {
        "purpose": (
            "FastAPI Application Entry Point & Global Server Configuration.\n"
            "Initializes the FastAPI application, sets up lifespan event hooks (connecting to DB, Redis, and MinIO),\n"
            "configures CORS security rules so the frontend can communicate with the backend,\n"
            "registers all API v1 routers, and provides global exception handlers for database errors."
        ),
        "responsibilities": [
            "Creates the FastAPI application instance (`app`).",
            "Manages application startup and shutdown lifecycle hooks (`lifespan`).",
            "Configures CORS middleware supporting localhost and local IP development.",
            "Attaches global error handlers ensuring clean error JSON and CORS headers.",
            "Mounts all API endpoints under `/api/v1`."
        ],
        "troubleshooting": [
            ("CORS error in browser console: 'No Access-Control-Allow-Origin header is present'",
             "Request was blocked by CORS policy or an unhandled 500 error crashed before headers were added.",
             "Verify `allow_origins` in this file and ensure your frontend URL (e.g. http://localhost:5173) is allowed."),
            ("Server hangs on startup: 'Could not connect to Redis' or DB timeout",
             "Database or Redis container is stopped.",
             "Check container status with `docker ps` and ensure `psf_postgres` and `psf_redis` are healthy.")
        ]
    },

    "backend/app/api/deps.py": {
        "purpose": (
            "FastAPI Route Dependencies & Security Gates.\n"
            "Provides reusable dependency injection functions for FastAPI endpoints:\n"
            "retrieving current database session (`get_db`), extracting authenticated user from JWT token\n"
            "(`get_current_user`), verifying active account status, and enforcing permission checks (`require`)."
        ),
        "responsibilities": [
            "Injects active asynchronous database sessions (`get_db`).",
            "Validates Bearer JWT access tokens and fetches the requesting User from database (`get_current_user`).",
            "Enforces role permission checks (`require(PermissionKey.CALL_VIEW)`).",
            "Enforces multi-permission checks (`require_any`, `require_all`)."
        ],
        "troubleshooting": [
            ("HTTP 401 Unauthorized: 'Not authenticated' or 'Invalid token'",
             "Missing or expired Authorization Bearer token header in the HTTP request.",
             "Log in again at /login or verify the frontend is passing `Authorization: Bearer <token>` in headers."),
            ("HTTP 403 Forbidden: 'Insufficient permissions'",
             "The user's role does not possess the required permission key.",
             "Check the user's role permissions in the Admin Console Role Matrix.")
        ]
    },

    "backend/app/api/v1/api.py": {
        "purpose": (
            "API v1 Central Router Aggregator.\n"
            "Combines all individual endpoint routers (auth, psf, allocation, complaints, imports, masters, users)\n"
            "into a single unified `api_router` mounted under the `/api/v1` URL prefix."
        ),
        "responsibilities": [
            "Mounts authentication routes (`/auth`).",
            "Mounts PSF calling routes (`/psf`).",
            "Mounts call allocation and attendance routes (`/allocation`).",
            "Mounts complaints management routes (`/complaints`).",
            "Mounts DMS import routes (`/imports`).",
            "Mounts master data routes (`/masters`).",
            "Mounts enterprise admin routes (`/admin`).",
            "Mounts reports and analytics routes (`/reports`)."
        ],
        "troubleshooting": [
            ("HTTP 404 Not Found on an API endpoint",
             "The endpoint was not included in this central router or path prefix is mismatched.",
             "Check this file to ensure the sub-router is registered with `api_router.include_router(...)`.")
        ]
    },

    "backend/app/api/v1/endpoints/admin_console.py": {
        "purpose": (
            "Enterprise Admin Console Endpoints (Super Admin Only).\n"
            "Provides restricted endpoints for managing the RBAC Role Permission Matrix,\n"
            "system-wide configuration parameters, and supervisor data corrections with mandatory audit reasons."
        ),
        "responsibilities": [
            "Returns role permissions matrix (`GET /admin/matrix`).",
            "Updates permissions for specific roles (`PUT /admin/matrix`).",
            "Performs supervisor data corrections with mandatory audit trail (`POST /admin/correct-data`)."
        ],
        "troubleshooting": [
            ("HTTP 403 Forbidden: 'Super Admin privileges required'",
             "A non-Super Admin user attempted to modify system security roles.",
             "Log in as Super Admin (`admin@apexauto.com`). Other roles cannot access the Admin Console.")
        ]
    },

    "backend/app/api/v1/endpoints/allocation.py": {
        "purpose": (
            "Call Allocation, Attendance & Notification WebSocket Endpoints.\n"
            "Provides endpoints for viewing present CRE callers, setting manual attendance overrides,\n"
            "configuring allocation rules, triggering mid-shift rebalances, undoing allocation runs,\n"
            "and establishing live WebSocket connections for personal caller assignment notifications."
        ),
        "responsibilities": [
            "Returns present CREs roster with pending call counts (`GET /allocation/present-cres`).",
            "Toggles manual CRE attendance ('Present' or 'On Leave') (`PUT /allocation/attendance/override`).",
            "Retrieves and updates allocation rules (`GET/PUT /allocation/rules`).",
            "Previews and executes manual Allocate Now (`POST /allocation/allocate-now`).",
            "Provides 15-minute undo capability (`POST /allocation/runs/{run_id}/undo`).",
            "Live real-time WebSocket for caller toast notifications (`WebSocket /allocation/ws/notifications/{token}`)."
        ],
        "troubleshooting": [
            ("WebSocket disconnects or fails to connect",
             "Invalid or expired token passed in WebSocket URL.",
             "Frontend should pass fresh access token in ws URL: `/allocation/ws/notifications/${token}`."),
            ("Undo fails with HTTP 400 'Undo window expired'",
             "Attempted to undo an allocation run after the 15-minute grace window.",
             "Use bulk reassignment on the PSF table instead.")
        ]
    },

    "backend/app/api/v1/endpoints/auth.py": {
        "purpose": (
            "Authentication, Token Refresh & Attendance Session Endpoints.\n"
            "Provides endpoints for staff login, logout (punch-out), token refresh,\n"
            "inspecting current user profile, and retrieving shift attendance logs."
        ),
        "responsibilities": [
            "Authenticates credentials and returns JWT access + refresh tokens (`POST /auth/login`).",
            "Records punch-out and revokes session on logout (`POST /auth/logout`).",
            "Returns current logged-in user details and permissions (`GET /auth/me`).",
            "Refreshes expired access tokens using refresh token (`POST /auth/refresh`).",
            "Lists shift attendance records (`GET /auth/attendance/logs`)."
        ],
        "troubleshooting": [
            ("HTTP 401 'Incorrect email or password'",
             "Invalid credentials entered.",
             "Confirm user credentials. Default demo password is `Password@12345`.")
        ]
    },

    "backend/app/api/v1/endpoints/complaints.py": {
        "purpose": (
            "Customer Complaints & SLA Lifecycle Endpoints.\n"
            "Provides endpoints for creating complaints from PSF calls, updating complaint statuses,\n"
            "adding manager action notes, and tracking SLA resolution deadlines."
        ),
        "responsibilities": [
            "Lists complaints with branch and status filters (`GET /complaints`).",
            "Creates a new customer complaint ticket (`POST /complaints`).",
            "Updates complaint status (OPEN, IN_PROGRESS, RESOLVED, CLOSED) (`PUT /complaints/{id}/status`).",
            "Adds manager action log entries to complaint timeline (`POST /complaints/{id}/actions`)."
        ],
        "troubleshooting": [
            ("HTTP 403 Forbidden when closing complaint",
             "User lacks `complaint.close` permission (e.g. Service Advisor).",
             "Only CRE Admin or Super Admin can mark complaints CLOSED.")
        ]
    },

    "backend/app/api/v1/endpoints/health.py": {
        "purpose": (
            "System Health Probes & Readiness Checks.\n"
            "Provides health check endpoints used by Docker healthchecks, Kubernetes liveness probes,\n"
            "and uptime monitors to verify that the API, database, and Redis are running normally."
        ),
        "responsibilities": [
            "Liveness check: returns 200 OK if API server is alive (`GET /health/live`).",
            "Readiness check: tests live connection to PostgreSQL and Redis (`GET /health/ready`)."
        ],
        "troubleshooting": [
            ("Health check returns 503 Service Unavailable",
             "Database or Redis is unreachable from the API container.",
             "Inspect database container with `docker logs psf_postgres` and Redis with `docker logs psf_redis`.")
        ]
    },

    "backend/app/api/v1/endpoints/imports.py": {
        "purpose": (
            "DMS File Upload, Sample Template & Error Report Endpoints.\n"
            "Provides endpoints for uploading dealer management system files (.xlsx, .xls, .csv),\n"
            "downloading standard 13-column sample templates, and downloading Excel row error reports."
        ),
        "responsibilities": [
            "Receives uploaded file, processes job cards, and auto-allocates to CREs (`POST /imports/upload-and-process`).",
            "Downloads standard 13-column sample template in .xlsx or .csv (`GET /imports/template/sample`).",
            "Downloads row error Excel report for failed rows in a batch (`GET /imports/batches/{id}/error-report`).",
            "Lists recent import batch history (`GET /imports/batches`)."
        ],
        "troubleshooting": [
            ("HTTP 400 Bad Request: 'Duplicate file upload'",
             "The exact same file was already imported previously.",
             "Tick 'Confirm duplicate upload' in the UI or upload a new file.")
        ]
    },

    "backend/app/api/v1/endpoints/masters.py": {
        "purpose": (
            "Dealership Master Data Endpoints.\n"
            "Provides endpoints for listing, creating, and updating OEM Brands, Branches,\n"
            "Service Advisors, and column mapping templates."
        ),
        "responsibilities": [
            "Lists and creates Brands (`GET/POST /masters/brands`).",
            "Lists and creates Branches (`GET/POST /masters/branches`).",
            "Lists Service Advisors (`GET /masters/advisors`)."
        ],
        "troubleshooting": [
            ("HTTP 403 Forbidden: 'brand.manage permission required'",
             "Attempted to add or edit a brand without required permissions.",
             "Only Super Admin can create or edit OEM Brands.")
        ]
    },

    "backend/app/api/v1/endpoints/psf.py": {
        "purpose": (
            "PSF Calling Workspace, Dashboard & Call Console Endpoints.\n"
            "Powers the main calling interface: provides dashboard KPI stats, lists calling line items,\n"
            "delivers complete customer dossier to the calling dialer modal, and records submitted call outcomes."
        ),
        "responsibilities": [
            "Returns dashboard KPI counters (`GET /psf/dashboard`).",
            "Returns paginated calling line items with CRE role scoping (`GET /psf/queues`).",
            "Delivers full dossier to Call Console modal (`GET /psf/console/{queue_id}`).",
            "Saves completed call log, updating customer sentiment and queue status (`POST /psf/calls/submit`).",
            "Bulk reassigns calling queue line items (`POST /psf/queues/bulk-assign`)."
        ],
        "troubleshooting": [
            ("Dashboard shows 0 or table says 'Loading line items...'",
             "Network timeout or API error.",
             "Check browser DevTools Network tab. Verify that /psf/dashboard returns HTTP 200.")
        ]
    },

    "backend/app/api/v1/endpoints/questionnaires.py": {
        "purpose": (
            "Dynamic Survey Questionnaire Endpoints.\n"
            "Provides endpoints for retrieving brand survey questions, submitting customer survey responses,\n"
            "and calculating CSAT / NPS scores."
        ),
        "responsibilities": [
            "Returns survey questions for a specific brand and queue (`GET /questionnaires`).",
            "Records survey answer ratings from Call Console (`POST /questionnaires/submit`)."
        ],
        "troubleshooting": [
            ("Empty questions array returned",
             "No active survey template seeded for the requested brand.",
             "Run `docker exec psf_api python -m app.db.seed_questionnaires` to seed survey templates.")
        ]
    },

    "backend/app/api/v1/endpoints/reports.py": {
        "purpose": (
            "Analytical Reports & Excel Export Endpoints.\n"
            "Provides endpoints for viewing aggregated dealership performance metrics\n"
            "and downloading multi-tab Excel analytical workbooks."
        ),
        "responsibilities": [
            "Returns date-range filtered calling performance KPIs (`GET /reports/summary`).",
            "Generates and streams downloadable Excel workbook (`GET /reports/export/excel`)."
        ],
        "troubleshooting": [
            ("HTTP 403 Forbidden on reports",
             "Logged in user does not have `report.view` permission.",
             "CRE callers cannot view executive reports; log in as Super Admin, CRE Admin, or Manager.")
        ]
    },

    "backend/app/api/v1/endpoints/users.py": {
        "purpose": (
            "User Management & Role Assignment Endpoints.\n"
            "Provides endpoints for listing personnel users, creating new accounts, updating roles,\n"
            "activating / deactivating users, and setting branch access scopes."
        ),
        "responsibilities": [
            "Lists dealership personnel users with filters (`GET /users`).",
            "Creates new user account (`POST /users`).",
            "Updates user profile or role (`PUT /users/{id}`).",
            "Configures explicit branch or brand user scopes (`PUT /users/{id}/scopes`)."
        ],
        "troubleshooting": [
            ("HTTP 400 Bad Request: 'Email already registered'",
             "A user with this email address already exists.",
             "Use a unique email address or update the existing user.")
        ]
    },

    "backend/app/db/seed.py": {
        "purpose": (
            "Database Initial Seeding Script.\n"
            "Seeds foundational system data on first installation:\n"
            "default tenant, default OEM Brands (Hyundai, Tata, MG), default Branches,\n"
            "all security Roles with permission mappings, and the initial Super Admin account."
        ),
        "responsibilities": [
            "Creates default Apex Automotive Group tenant.",
            "Seeds standard dealership roles (Super Admin, CRE Admin, CRE, Service Advisor, etc.).",
            "Seeds initial Super Admin account (`admin@apexauto.com` / `Password@12345`).",
            "Seeds default OEM Brands and dealership workshop branches."
        ],
        "troubleshooting": [
            ("Seed script fails with IntegrityError",
             "Data was already seeded previously.",
             "The script is idempotent; re-running it skips records that already exist.")
        ]
    },

    "backend/app/db/seed_questionnaires.py": {
        "purpose": (
            "Survey Questionnaire Seeding Script.\n"
            "Seeds standard manufacturer-compliant survey questionnaires for Hyundai, Tata Motors, and MG Motors,\n"
            "including 1-10 NPS rating questions, service satisfaction ratings, and CSAT calculation logic."
        ),
        "responsibilities": [
            "Seeds Hyundai 4-Question PSF Survey template.",
            "Seeds Tata Motors 7-Question PSF Survey template.",
            "Seeds MG Motors 5-Question PSF Survey template."
        ],
        "troubleshooting": [
            ("Questionnaire seed fails with 'Brand not found'",
             "Brands have not been seeded yet.",
             "Run `seed.py` first to create the OEM Brands before running `seed_questionnaires.py`.")
        ]
    },

    "backend/app/workers/runner.py": {
        "purpose": (
            "Asynchronous Background Worker Runner.\n"
            "Runs asynchronous background processing tasks outside the main web request thread,\n"
            "such as batch DMS file imports, end-of-day session cleanup, and report generation."
        ),
        "responsibilities": [
            "Listens for background jobs in Redis task queues.",
            "Executes long-running file processing jobs without blocking HTTP responses.",
            "Monitors job completion and updates job statuses."
        ],
        "troubleshooting": [
            ("Background worker container psf_worker keeps restarting",
             "Worker could not connect to Redis or PostgreSQL.",
             "Check `docker logs psf_worker` to see the exact connection error.")
        ]
    }
}

def apply_headers():
    count = 0
    for file_rel, doc in DOCS.items():
        if not os.path.exists(file_rel):
            print(f"Skipping (not found): {file_rel}")
            continue

        with open(file_rel, "r", encoding="utf-8") as f:
            content = f.read()

        # Check if already has header
        if "FILE PURPOSE:" in content:
            print(f"Already documented: {file_rel}")
            continue

        header_lines = [
            '"""',
            '================================================================================',
            f'FILE PURPOSE: {doc["purpose"]}',
            '',
            'KEY RESPONSIBILITIES:'
        ]
        for r in doc["responsibilities"]:
            header_lines.append(f'- {r}')
        
        header_lines.append('')
        header_lines.append('COMMON ERRORS & TROUBLESHOOTING GUIDE:')
        for err, cause, fix in doc["troubleshooting"]:
            header_lines.append(f'- Error: {err}')
            header_lines.append(f'  -> Cause: {cause}')
            header_lines.append(f'  -> What should you do: {fix}')
        
        header_lines.extend([
            '================================================================================',
            '"""',
            ''
        ])

        new_content = "\n".join(header_lines) + content
        with open(file_rel, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Added header to: {file_rel}")
        count += 1

    print(f"\nDone Batch 3! Updated {count} files.")

if __name__ == "__main__":
    apply_headers()

