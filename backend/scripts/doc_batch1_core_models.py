# Script to add header documentation to backend core and models

import os

DOCS = {
    # ---------------- CORE ----------------
    "backend/app/core/config.py": {
        "purpose": (
            "Application Configuration & Environment Settings.\n"
            "This file reads environment variables from your system and the .env file,\n"
            "validates them using Pydantic Settings, and provides a single global 'settings'\n"
            "object used everywhere in the backend (DB URLs, Redis, MinIO keys, JWT secrets)."
        ),
        "responsibilities": [
            "Loads database connection strings (Postgres asyncpg & sync psycopg2).",
            "Configures Redis URL and worker concurrency limits.",
            "Stores security keys: SECRET_KEY for JWT tokens and FIELD_ENCRYPTION_KEY for phone numbers.",
            "Defines CORS allowed origins so the frontend at localhost:5173 can call the API.",
            "Sets storage bucket names for MinIO S3 document storage."
        ],
        "troubleshooting": [
            ("ValidationError: 1 validation error for Settings -> FIELD_ENCRYPTION_KEY / SECRET_KEY",
             "Required security keys are missing or not 32 URL-safe base64 characters in your .env file.",
             "Open .env and ensure SECRET_KEY and FIELD_ENCRYPTION_KEY are set properly. You can generate a 32-byte key using `python -c 'import secrets, base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())'`."),
            ("ValidationError: DATABASE_URL not found or invalid format",
             "Database connection URL is missing in environment variables.",
             "Check your .env file and ensure POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, and DATABASE_URL are present.")
        ]
    },

    "backend/app/core/crypto.py": {
        "purpose": (
            "Customer Data Encryption & Privacy Protection (DPDP Act Compliance).\n"
            "This file handles encrypting and decrypting sensitive customer data (especially phone numbers)\n"
            "using AES-256-GCM authenticated encryption, and generating deterministic HMAC-SHA256 blind hashes\n"
            "so you can search for a customer by phone number in the database without storing raw numbers in plain text."
        ),
        "responsibilities": [
            "Encrypts raw 10-digit phone numbers into secure ciphertext before saving to the database.",
            "Decrypts stored ciphertext back into human-readable phone numbers for authorized users.",
            "Generates blind index hashes (HMAC-SHA256) for fast indexed searching.",
            "Provides mask_phone helper (e.g. '+91 ******3456') to protect customer privacy on screens."
        ],
        "troubleshooting": [
            ("InvalidTag error or cryptography.exceptions.InvalidSignature",
             "Attempted to decrypt data with a different encryption key than the one used during encryption.",
             "Do not change FIELD_ENCRYPTION_KEY in .env after data is imported. If you did, restore the original key or re-import the test data."),
            ("ValueError: Phone number must be at least 10 digits",
             "A phone number passed to encrypt_phone or mask_phone was malformed or empty.",
             "Verify phone normalization in the import pipeline before calling encryption routines.")
        ]
    },

    "backend/app/core/database.py": {
        "purpose": (
            "PostgreSQL Database Engine & Session Management.\n"
            "This file sets up the SQLAlchemy async database connection engine, creates the session\n"
            "factory (AsyncSessionLocal) for handling database queries asynchronously, and defines\n"
            "the Base class for all database models. It also provides the `get_db` dependency for FastAPI."
        ),
        "responsibilities": [
            "Initializes SQLAlchemy async engine using asyncpg connection driver.",
            "Provides `get_db()` async generator dependency to inject DB sessions into FastAPI routes.",
            "Defines DeclarativeBase `Base` with shared UUID primary keys and timestamp mixins.",
            "Provides `check_db_health()` to verify PostgreSQL availability during startup."
        ],
        "troubleshooting": [
            ("asyncpg.exceptions.CannotConnectNowError or ConnectionRefusedError: [Errno 111] Connection refused",
             "The PostgreSQL database container (psf_postgres) is stopped or not ready to accept connections.",
             "Run `docker ps` to verify psf_postgres is running. Run `docker logs psf_postgres` to check for DB errors. If stopped, run `docker compose up -d postgres`."),
            ("TimeoutError: QueuePool limit of size 20 overflow 10 reached",
             "Too many database connections opened without being closed (connection leak).",
             "Ensure every endpoint uses `Depends(get_db)` so FastAPI automatically closes sessions after the request completes.")
        ]
    },

    "backend/app/core/permissions.py": {
        "purpose": (
            "Role-Based Access Control (RBAC) & Data Scoping Engine.\n"
            "This file defines all system permission keys (like `call.view`, `jobcard.import`, `complaint.close`)\n"
            "and handles multi-level data scoping (ALL, BRAND, BRANCH, OWN).\n"
            "It controls which rows a user is allowed to see in SQL queries (e.g., CRE only sees OWN calls)."
        ),
        "responsibilities": [
            "Declares PermissionKey constants for all system actions.",
            "Declares DataScope levels: ALL (L1/Super Admin), BRAND (L2/Brand Manager), BRANCH (L3/Branch Manager), OWN (L4/CRE).",
            "Computes effective permissions for a user including tenant roles and custom user scopes.",
            "Provides `apply_data_scope()` which dynamically filters SQLAlchemy queries based on the user's role."
        ],
        "troubleshooting": [
            ("HTTP 403 Forbidden: 'Insufficient permissions'",
             "The logged-in user's role lacks the required permission key for that endpoint.",
             "Check the user's role in the Enterprise Admin Console (Role Matrix) or log in with an account having appropriate privileges (e.g. Super Admin or CRE Admin)."),
            ("A CRE user sees other CREs' calls or an Admin sees zero calls",
             "Data scoping logic filter was incorrectly applied or user scopes are missing.",
             "Inspect `apply_data_scope` and confirm the user's role_name in `get_user_effective_permissions`.")
        ]
    },

    "backend/app/core/redis.py": {
        "purpose": (
            "Redis In-Memory Cache & Pub/Sub Connection Pool.\n"
            "This file provides an asynchronous Redis client connection used for distributed locking\n"
            "(preventing duplicate file imports), real-time WebSocket notifications, and transient caching."
        ),
        "responsibilities": [
            "Manages Redis connection pool and async client lifecycle.",
            "Provides `get_redis()` helper function to get an active Redis client.",
            "Provides `close_redis()` helper called during app shutdown to clean up connections."
        ],
        "troubleshooting": [
            ("redis.exceptions.ConnectionError: Error connecting to redis:6379",
             "The Redis container (psf_redis) is down or port is blocked.",
             "Run `docker ps` to verify psf_redis is running. Run `docker restart psf_redis` if needed. Check REDIS_URL in .env."),
            ("WebSocket notifications not reaching CREs",
             "Redis pub/sub channel communication failed.",
             "Test Redis by running `docker exec psf_redis redis-cli ping`. Expected response is `PONG`.")
        ]
    },

    "backend/app/core/security.py": {
        "purpose": (
            "Password Hashing & JWT Authentication Tokens.\n"
            "This file handles securing passwords with Passlib Bcrypt hashing and creating / decoding\n"
            "JSON Web Tokens (JWT) for user authentication sessions."
        ),
        "responsibilities": [
            "Hashes plain-text passwords securely using bcrypt with automatic salting (`get_password_hash`).",
            "Verifies entered login passwords against stored database hashes (`verify_password`).",
            "Generates JWT Access Tokens (short-lived) and Refresh Tokens (long-lived) (`create_access_token`).",
            "Decodes and validates JWT signatures (`decode_token`)."
        ],
        "troubleshooting": [
            ("jwt.exceptions.ExpiredSignatureError: Signature has expired",
             "The user's access token has timed out (default 60 minutes).",
             "The frontend should automatically refresh the token using /auth/refresh or redirect the user to /login to log in again."),
            ("jwt.exceptions.InvalidTokenError: Could not validate credentials",
             "The token is malformed or signed with a different SECRET_KEY.",
             "Ensure SECRET_KEY has not changed in .env. Log out and log in again with valid credentials.")
        ]
    },

    "backend/app/core/storage.py": {
        "purpose": (
            "MinIO / S3 Object Storage File Management.\n"
            "This file handles uploading, downloading, and managing physical files (DMS import files,\n"
            "error Excel reports, audio recordings, customer survey attachments) in MinIO S3 object storage."
        ),
        "responsibilities": [
            "Initializes default S3 buckets (`psf-documents`, `psf-exports`) during app startup (`init_storage_buckets`).",
            "Uploads file byte streams to S3 with content-type detection (`upload_file`).",
            "Downloads file bytes from S3 (`download_file`).",
            "Generates secure presigned download URLs."
        ],
        "troubleshooting": [
            ("botocore.exceptions.EndpointConnectionError: Could not connect to the endpoint URL http://minio:9000",
             "The MinIO storage container (psf_minio) is stopped or not reachable.",
             "Run `docker ps` to verify psf_minio is running. Run `docker compose up -d minio` to restart it."),
            ("botocore.exceptions.ClientError: NoSuchBucket",
             "The target S3 bucket does not exist.",
             "Restart psf_api (`docker restart psf_api`) to trigger `init_storage_buckets()` which auto-creates required buckets.")
        ]
    },

    # ---------------- MODELS ----------------
    "backend/app/models/__init__.py": {
        "purpose": (
            "SQLAlchemy Models Package Registry.\n"
            "This file imports and registers every database model class so that SQLAlchemy and Alembic\n"
            "migrations can discover all database tables, foreign keys, and relationships in one central place."
        ),
        "responsibilities": [
            "Imports tenant models (Tenant, Brand, Branch).",
            "Imports auth models (User, Role, RolePermission, LoginLog).",
            "Imports customer & vehicle models (Customer, Vehicle).",
            "Imports service models (JobCard, ServiceAdvisor).",
            "Imports followup & call models (FollowupQueue, Call, CallAttempt).",
            "Imports complaint models (Complaint, ComplaintCategory).",
            "Imports questionnaire models (Questionnaire, Question).",
            "Imports allocation models (AllocationRun, AllocationAssignment)."
        ],
        "troubleshooting": [
            ("sqlalchemy.exc.InvalidRequestError: When initializing mapper ..., expression ... refers to an unknown class",
             "A relationship was added referencing a model that was not imported in __init__.py.",
             "Add the missing model import to this file so SQLAlchemy knows about it before building foreign key mappings.")
        ]
    },

    "backend/app/models/tenant.py": {
        "purpose": (
            "Multi-Tenant Hierarchy & Dealership Masters (Tenant, Brand, Branch, Workshop).\n"
            "Defines database tables representing dealership organizations, automobile manufacturer brands\n"
            "(e.g. Hyundai, Tata, MG), and individual dealer branch workshop locations."
        ),
        "responsibilities": [
            "Tenant model: Represents the dealership group (multi-tenant boundary).",
            "Brand model: Represents OEM brands with OEM codes, colors, and logos.",
            "Branch model: Represents dealership physical service centers with phone, address, and brand link."
        ],
        "troubleshooting": [
            ("IntegrityError: duplicate key value violates unique constraint 'uq_branch_code'",
             "Attempted to create a branch with a code that already exists.",
             "Choose a unique branch code in the Admin Console or verify existing branch codes.")
        ]
    },

    "backend/app/models/auth.py": {
        "purpose": (
            "Authentication, Roles, Shift Attendance & User Scopes.\n"
            "Defines database tables for User accounts, security Roles (Super Admin, CRE Admin, CRE),\n"
            "RolePermissions (action + data scope), LoginLogs (attendance shift tracking), and UserScopes."
        ),
        "responsibilities": [
            "User: personnel details, email, hashed password, role link, active shift status.",
            "Role & RolePermission: granular permission definitions and max scopes.",
            "LoginLog: daily punch-in / punch-out attendance records with duration tracking.",
            "UserScope: explicit brand or branch restrictions assigned to specific users."
        ],
        "troubleshooting": [
            ("User not showing as 'Present' on attendance screen",
             "The user does not have an open LoginLog session for today (logout_at is not NULL or session is from previous day).",
             "Log in with that user to start an active shift session, or manually mark them Present in the CRE Presence panel.")
        ]
    },

    "backend/app/models/customer.py": {
        "purpose": (
            "Customer Records & Vehicle Database Models.\n"
            "Defines database tables for vehicle owners (Customer) and the vehicles they own (Vehicle).\n"
            "Stores masked and encrypted contact numbers compliant with data privacy regulations."
        ),
        "responsibilities": [
            "Customer: customer name, encrypted phone number, blind phone index hash, email, city.",
            "Vehicle: registration number (Reg No), VIN number, model, variant, engine number, sale date."
        ],
        "troubleshooting": [
            ("IntegrityError: duplicate key violates 'uq_vehicle_vin'",
             "A vehicle with the same 17-character VIN already exists.",
             "Use existing vehicle record or verify duplicate handling options during DMS import.")
        ]
    },

    "backend/app/models/service.py": {
        "purpose": (
            "Workshop Service Job Cards & Service Advisor Records.\n"
            "Defines database tables representing real workshop service visits (JobCard),\n"
            "assigned Service Advisors, and technicians who worked on the customer's vehicle."
        ),
        "responsibilities": [
            "JobCard: job card number, service date, invoice amount, service type, advisor link, vehicle link.",
            "ServiceAdvisor: advisor name, employee code, active status, branch link."
        ],
        "troubleshooting": [
            ("Job card not linking to branch or brand",
             "The branch_id or brand_id foreign key in JobCard was passed as NULL.",
             "Ensure the DMS import template correctly resolves Brand and Branch before creating the job card.")
        ]
    },

    "backend/app/models/followup.py": {
        "purpose": (
            "Follow-up Calling Queues, Call Records & Customer Sentiments.\n"
            "Defines database tables for calling queue tasks (FollowupQueue), individual phone call records (Call),\n"
            "call attempts history (CallAttempt), scheduled customer call-back reminders (Reminder),\n"
            "and post-service sentiment logs."
        ),
        "responsibilities": [
            "FollowupQueue: tracks calling status (PENDING, CONTACTED, CALLBACK_REQUESTED), assigned CRE caller, and due dates.",
            "Call & CallAttempt: logs each call timestamp, duration, sentiment (Delight, Satisfied, Dissatisfied), and VOC (Voice of Customer).",
            "Reminder: stores callback notifications requested by customers."
        ],
        "troubleshooting": [
            ("Call queue item stuck in PENDING status after submitting call",
             "The call submission did not update queue.status to CONTACTED or NOT_CONTACTED.",
             "Check the call submission payload in the Call Console modal to ensure a valid call_status was provided.")
        ]
    },

    "backend/app/models/complaint.py": {
        "purpose": (
            "Customer Complaints, Escalations & SLA Tracking.\n"
            "Defines database tables for customer grievances (Complaint), complaint categories,\n"
            "and resolution action history (ComplaintAction). Enforces dealership SLA deadlines."
        ),
        "responsibilities": [
            "Complaint: ticket number, description, category, severity, status (OPEN, IN_PROGRESS, RESOLVED, CLOSED).",
            "ComplaintAction: audit history of comments, status changes, and root causes added by managers.",
            "ComplaintCategory: category taxonomy (e.g. Wash Quality, Overcharging, Delay, Advisor Rude)."
        ],
        "troubleshooting": [
            ("Complaint status stuck on SLA Breached",
             "The complaint was not resolved before target_resolution_at timestamp.",
             "Assign the complaint to a Service Advisor or Service Manager and record a resolution action in the Complaints tab.")
        ]
    },

    "backend/app/models/questionnaire.py": {
        "purpose": (
            "Dynamic Customer Survey Questionnaires & OEM Rating Scales.\n"
            "Defines database tables for brand-specific survey templates (Questionnaire), survey questions,\n"
            "answer choices, and recorded customer responses (SurveyResponse)."
        ),
        "responsibilities": [
            "Questionnaire: OEM survey template (e.g. Hyundai 4-Question Survey, Tata 7-Question Survey).",
            "Question: question text, answer type (RATING_5, RATING_10, YES_NO, TEXT), mandatory flag.",
            "SurveyResponse: stores the customer's actual ratings, CSAT score, and NPS classification (Promoter, Passive, Detractor)."
        ],
        "troubleshooting": [
            ("Questionnaire not showing in Call Console",
             "No active questionnaire exists for the job card's brand and queue type.",
             "Run `docker exec psf_api python -m app.db.seed_questionnaires` to seed default OEM survey templates.")
        ]
    },

    "backend/app/models/allocation.py": {
        "purpose": (
            "Automatic Call Allocation Runs, Attendance Overrides & Audit Records.\n"
            "Defines database tables tracking every automatic allocation batch (AllocationRun),\n"
            "item-by-item caller assignments (AllocationAssignment), attendance overrides (AttendanceOverride),\n"
            "and fair-rotation cursor pointers (AllocationCursor)."
        ),
        "responsibilities": [
            "AllocationRun: logs who triggered the allocation, strategy used, present CRE count, and total items.",
            "AllocationAssignment: maps each queue item to the CRE it was assigned to, enabling 15-minute undo.",
            "AttendanceOverride: stores manual 'Present' or 'On Leave' marks set by the CRE Admin.",
            "AllocationCursor: remembers the last CRE who received an extra remainder item to ensure long-term fairness."
        ],
        "troubleshooting": [
            ("Allocation undo button fails with 'Undo window expired' or 'Already attempted'",
             "Undo was clicked after the 15-minute grace window or a CRE already placed a call to one of the customers.",
             "Untouched calls can still be manually reassigned in bulk using the bulk reassignment tool on the PSF table.")
        ]
    },

    "backend/app/models/additional.py": {
        "purpose": (
            "System Audit Logs & Enterprise Data Correction Records.\n"
            "Defines database tables for tracking every sensitive action taken in the system (AuditLog),\n"
            "such as user role changes, supervisor data corrections, and allocation modifications."
        ),
        "responsibilities": [
            "AuditLog: captures actor_id, IP address, action name, before_state JSON, and after_state JSON.",
            "Ensures tamper-evident compliance for dealership audits and Super Admin security reviews."
        ],
        "troubleshooting": [
            ("AuditLog table growing large in production",
             "High transaction volume creating thousands of audit entries.",
             "Set up automated archival for audit records older than 180 days.")
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

    print(f"\nDone Batch 1! Updated {count} files.")

if __name__ == "__main__":
    apply_headers()

