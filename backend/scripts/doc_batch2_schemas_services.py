# Script to add header documentation to backend schemas and services

import os

DOCS = {
    # ---------------- SCHEMAS ----------------
    "backend/app/schemas/admin_console.py": {
        "purpose": (
            "Enterprise Admin Console Data Validation Schemas.\n"
            "Defines Pydantic models for the Super Admin RBAC Role Matrix,\n"
            "system-wide configuration toggles, and supervisor data correction workflows."
        ),
        "responsibilities": [
            "Validates Role Matrix grid payload (roles, permissions, data scopes).",
            "Validates supervisor data corrections (mandatory reason, field updates, audit tracking).",
            "Validates tenant allocation and security parameters."
        ],
        "troubleshooting": [
            ("ValidationError: reason field required for data correction",
             "A supervisor attempted to correct a database record without providing an explanatory audit reason.",
             "Prompt the user in the UI to enter a non-empty audit explanation before submitting.")
        ]
    },

    "backend/app/schemas/allocation.py": {
        "purpose": (
            "Call Allocation & Attendance Data Schemas.\n"
            "Defines Pydantic models for automatic call distribution rules,\n"
            "present CRE summaries, manual attendance overrides, rebalance previews, and undo requests."
        ),
        "responsibilities": [
            "Validates allocation rules (strategy, pool mode, sticky customer toggle, cursor pointer).",
            "Formats Present CRE roster items (login status, pending call load, override flags).",
            "Formats Rebalance and Allocate Now preview diffs (current vs proposed calls)."
        ],
        "troubleshooting": [
            ("ValidationError: Input should be a valid strategy ('EQUAL_PRESENT_CRE', 'ROUND_ROBIN', 'BY_BRANCH', 'MANUAL')",
             "An invalid allocation strategy name was submitted to the rules endpoint.",
             "Select one of the valid enum strategies from the Admin Console dropdown.")
        ]
    },

    "backend/app/schemas/auth.py": {
        "purpose": (
            "Authentication, Token & Shift Session Schemas.\n"
            "Defines Pydantic models for staff login requests, JWT token pairs (access + refresh),\n"
            "current user profile responses, and shift attendance logs."
        ),
        "responsibilities": [
            "Validates email and password format on login.",
            "Formats JWT token response with token expiry and role name.",
            "Serializes current user permissions list for frontend access gating."
        ],
        "troubleshooting": [
            ("ValidationError: value is not a valid email address",
             "User entered an invalid email format during login.",
             "Ensure the user enters a standard email format (e.g., name@dealership.com).")
        ]
    },

    "backend/app/schemas/complaint_flow.py": {
        "purpose": (
            "Customer Complaints & SLA Tracking Schemas.\n"
            "Defines Pydantic models for registering customer complaints,\n"
            "updating complaint tickets, recording manager action logs, and viewing SLA timelines."
        ),
        "responsibilities": [
            "Validates new complaint creation payloads (category, description, severity, assigned advisor).",
            "Validates complaint status transitions (OPEN -> IN_PROGRESS -> RESOLVED -> CLOSED).",
            "Formats complaint audit timelines and SLA breach indicators."
        ],
        "troubleshooting": [
            ("ValidationError: status transition not permitted",
             "Attempted an invalid complaint state transition (e.g. going from CLOSED back to OPEN directly).",
             "Follow proper lifecycle progression or verify user permissions.")
        ]
    },

    "backend/app/schemas/import_job.py": {
        "purpose": (
            "DMS File Import, Header Mapping & Batch Report Schemas.\n"
            "Defines Pydantic models for file upload responses, column header mapping templates,\n"
            "row validation previews, and import error reports."
        ),
        "responsibilities": [
            "Validates column mapping aliases (e.g. 'Job Card No' vs 'JC Number').",
            "Formats import batch statistics (success rows, skipped duplicates, errors).",
            "Structures downloadable row error summaries."
        ],
        "troubleshooting": [
            ("ValidationError: Missing required column mapping for 'Job Card No'",
             "The uploaded file is missing mandatory columns.",
             "Download the sample template from the Data Import page and ensure all 13 standard columns are present.")
        ]
    },

    "backend/app/schemas/master.py": {
        "purpose": (
            "Dealership Master Data Schemas (Brands, Branches, Workshops, Service Types).\n"
            "Defines Pydantic validation models for creating and updating dealership master entities."
        ),
        "responsibilities": [
            "Validates Brand creation and updates (name, OEM code, primary color, logo URL).",
            "Validates Branch creation and updates (name, code, brand link, contact phone, city).",
            "Validates Service Type and Technician records."
        ],
        "troubleshooting": [
            ("ValidationError: primary_color must be a valid hex color code",
             "Brand color was entered in an invalid format (e.g. 'blue' instead of '#0052CC').",
             "Use a valid 6-character hex color format like #1E40AF.")
        ]
    },

    "backend/app/schemas/psf.py": {
        "purpose": (
            "PSF Calling Workspace, Dashboard & Call Console Schemas.\n"
            "Defines Pydantic models for high-level calling KPIs, calling queue line items,\n"
            "customer dossiers for the calling dialer modal, and call submission logs."
        ),
        "responsibilities": [
            "Formats dashboard counters (total pending, contacted, connect rate, open complaints).",
            "Formats line items spreadsheet rows with masked phone numbers and assigned caller tags.",
            "Validates call submission logs (call status, sentiment, VOC, survey ratings, complaint escalation)."
        ],
        "troubleshooting": [
            ("ValidationError: call_status is required",
             "Call console modal submitted without selecting a call outcome (e.g. Connected, Busy, Not Connected).",
             "Ensure the caller selects an outcome button before clicking Submit.")
        ]
    },

    "backend/app/schemas/questionnaire.py": {
        "purpose": (
            "Dynamic Survey Questionnaire Schemas.\n"
            "Defines Pydantic models for OEM survey question definitions,\n"
            "answer option structures, and customer survey response payloads."
        ),
        "responsibilities": [
            "Structures questionnaire templates (Hyundai 4-Q, Tata 7-Q, MG 5-Q).",
            "Validates rating scale responses (1-5 stars, 1-10 NPS, Yes/No).",
            "Formats CSAT score and NPS classification results."
        ],
        "troubleshooting": [
            ("ValidationError: Rating score out of bounds",
             "A score of 12 was submitted for a 1-10 rating question.",
             "Frontend dialer modal should restrict rating inputs to the question's configured range.")
        ]
    },

    "backend/app/schemas/reports.py": {
        "purpose": (
            "Analytics, Performance Reports & Export Schemas.\n"
            "Defines Pydantic models for dealership executive reports, CRE calling summaries,\n"
            "branch satisfaction comparisons, and Excel export request filters."
        ),
        "responsibilities": [
            "Formats date-range filtered report summaries.",
            "Structures CRE caller productivity metrics (attempted vs contacted counts).",
            "Defines parameters for generating Excel export reports."
        ],
        "troubleshooting": [
            ("ValidationError: start_date cannot be greater than end_date",
             "Selected date filter has an inverted range.",
             "Verify the date picker values on the Reports page.")
        ]
    },

    "backend/app/schemas/user.py": {
        "purpose": (
            "User Profile, Role Management & Scope Schemas.\n"
            "Defines Pydantic models for creating users, updating profiles, assigning roles,\n"
            "and configuring branch/brand data access restrictions."
        ),
        "responsibilities": [
            "Validates new user creation (full name, email, password strength, role).",
            "Validates user profile updates and status changes (active / inactive).",
            "Validates explicit branch/brand user scope assignments."
        ],
        "troubleshooting": [
            ("ValidationError: password must be at least 8 characters",
             "Weak password provided during user creation.",
             "Provide a strong password with at least 8 characters including uppercase, lowercase, and numbers.")
        ]
    },

    # ---------------- SERVICES ----------------
    "backend/app/services/allocation_service.py": {
        "purpose": (
            "Automatic Equal Call Allocation Engine.\n"
            "This is the core business logic service that divides imported DMS follow-up calls\n"
            "EQUALLY among active, present CRE callers with zero manual work required.\n"
            "It guarantees that call counts differ by at most 1, rotates remainders fairly,\n"
            "bundles sticky customer calls, respects brand/branch scopes, and provides 15-minute undo."
        ),
        "responsibilities": [
            "Calculates CRE presence based on today's active login sessions and manual overrides (`get_present_cres`).",
            "Executes equal split allocation algorithms inside a database transaction (`allocate_queue_items`).",
            "Maintains fair cursor rotation so remainder calls rotate evenly across CREs.",
            "Provides rebalance preview and confirmation for mid-shift late joiners (`rebalance_queues`).",
            "Provides 15-minute safety undo to rollback allocation batches if untouched (`undo_allocation_run`)."
        ],
        "troubleshooting": [
            ("Calls stay unallocated with message 'No present CREs found'",
             "No active CRE has logged in today and no manual presence overrides were set.",
             "Log in with a CRE user or toggle CREs to 'Present' in the CRE Presence panel, then click 'Allocate Now'.",),
            ("Allocation locked / timeout error",
             "Two concurrent imports attempted to allocate simultaneously.",
             "Distributed lock prevents duplicate allocation. Retry after 2 seconds.")
        ]
    },

    "backend/app/services/auth_service.py": {
        "purpose": (
            "Authentication, Password Verification & Attendance Service.\n"
            "Handles verifying user login credentials, issuing JWT tokens,\n"
            "recording punch-in login attendance logs, and handling punch-out shift logouts."
        ),
        "responsibilities": [
            "Authenticates user email and password against stored bcrypt hashes (`authenticate_user`).",
            "Records shift attendance punch-in when user logs in (`record_login`).",
            "Records shift punch-out when user clicks End Shift / Log Out (`record_logout`).",
            "Handles automatic end-of-day cleanup for abandoned login sessions from previous shifts."
        ],
        "troubleshooting": [
            ("Incorrect email or password error during login",
             "Entered wrong password or email.",
             "Check your email and password. Default demo password for all personnel accounts is 'Password@12345'."),
            ("Account deactivated error (HTTP 403)",
             "The user account has is_active set to False in the database.",
             "Have a Super Admin reactivate the user account from the User Management page.")
        ]
    },

    "backend/app/services/complaint_flow_service.py": {
        "purpose": (
            "Complaint Lifecycle & SLA Escalation Service.\n"
            "Manages the end-to-end lifecycle of customer complaints generated from PSF calls.\n"
            "Calculates target resolution deadlines, tracks SLA breaches, and logs manager action notes."
        ),
        "responsibilities": [
            "Creates complaint records with auto-generated ticket numbers (e.g. 'CMP-20261104-001') (`create_complaint`).",
            "Updates complaint statuses and enforces role restrictions (e.g. Service Advisors cannot close complaints) (`update_complaint_status`).",
            "Monitors and flags SLA breaches based on complaint severity (`check_sla_breaches`)."
        ],
        "troubleshooting": [
            ("HTTP 403 Forbidden: Advisor cannot close complaint",
             "Service Advisor attempted to mark a complaint CLOSED.",
             "Only CRE Admin, Dealer Admin, or Super Admin can mark complaints RESOLVED / CLOSED.")
        ]
    },

    "backend/app/services/import_service.py": {
        "purpose": (
            "DMS Data Import & Ingestion Pipeline.\n"
            "Parses uploaded dealer management system (DMS) files (.xlsx, .xls, .csv),\n"
            "normalizes dates, cleans phone numbers, resolves Brands and Branches against masters,\n"
            "creates JobCard and Customer records, and automatically triggers the call allocator."
        ),
        "responsibilities": [
            "Reads every cell as text to prevent Excel data corruption (lost leading zeros, scientific notation).",
            "Normalizes 10-digit Indian phone numbers and encrypts them with blind index hashes.",
            "Validates Brand and Branch against master tables, raising row errors for unknown values.",
            "Detects duplicate job cards and skips them without aborting the batch.",
            "Automatically triggers `allocate_queue_items()` to distribute calls equally among present CREs."
        ],
        "troubleshooting": [
            ("Row error: 'Unknown Branch [NAME]'",
             "The branch name in the file does not match any branch in the database.",
             "Ensure the Branch is created under the Brand in the Admin Console or verify file branch spelling."),
            ("Row error: 'Invalid phone number'",
             "Phone number cell contains less than 10 digits or is unparseable.",
             "Verify phone numbers in the DMS file start with digits 6-9 and have 10 valid digits.")
        ]
    },

    "backend/app/services/master_service.py": {
        "purpose": (
            "Dealership Master Data Management Service.\n"
            "Provides database operations for managing OEM Brands, dealer Branches, workshops,\n"
            "service types, and DMS column mapping templates."
        ),
        "responsibilities": [
            "Lists, creates, and updates Brands and Branches.",
            "Enforces uniqueness rules on Brand codes and Branch codes.",
            "Manages DMS column mapping templates for various dealership software formats."
        ],
        "troubleshooting": [
            ("IntegrityError: Brand code already exists",
             "Attempted to create a brand with a duplicate code.",
             "Use a unique 4-letter brand code (e.g. HYUN, TATA, MGMT).")
        ]
    },

    "backend/app/services/psf_service.py": {
        "purpose": (
            "PSF Follow-up Calling Workspace & Dossier Service.\n"
            "Powers the PSF calling operations: calculates dashboard counters,\n"
            "retrieves calling queue line items with role scoping, builds complete customer dossiers\n"
            "for the calling dialer modal, and records submitted customer call logs."
        ),
        "responsibilities": [
            "Calculates high-level metrics (pending, contacted, connect rate, open complaints) (`get_dashboard_stats`).",
            "Retrieves paginated calling queue records with masked phone numbers (`list_followup_queues`).",
            "Enforces CRE role scoping so CREs only see their assigned customers.",
            "Builds full customer dossier for Call Console dialer (`get_call_console_data`).",
            "Processes submitted call logs, updating sentiments, CSAT scores, and queue statuses (`submit_call_log`).",
            "Handles bulk reassignment of calls between CREs (`bulk_assign_queues`)."
        ],
        "troubleshooting": [
            ("Line items table showing 0 records or spinning",
             "Network request failed or user scope filtered out all records.",
             "Check browser DevTools console for API status. If logged in as CRE, verify calls have been assigned to your user ID.")
        ]
    },

    "backend/app/services/questionnaire_service.py": {
        "purpose": (
            "Customer Survey & Questionnaire Management Service.\n"
            "Loads dynamic survey questions for specific OEM brands (Hyundai, Tata, MG),\n"
            "evaluates customer survey responses, and computes CSAT and NPS scores."
        ),
        "responsibilities": [
            "Fetches active questionnaire templates for a brand and queue type (`get_questionnaire_for_queue`).",
            "Calculates CSAT percentage score from question ratings (`calculate_csat`).",
            "Classifies NPS rating into Promoter (9-10), Passive (7-8), or Detractor (1-6) (`calculate_nps`)."
        ],
        "troubleshooting": [
            ("Survey questions not showing in call console dialer",
             "No active questionnaire found for the vehicle's brand.",
             "Run `docker exec psf_api python -m app.db.seed_questionnaires` to seed brand survey templates.")
        ]
    },

    "backend/app/services/rating_service.py": {
        "purpose": (
            "OEM Rating Scales & Satisfaction Bands Service.\n"
            "Maps raw customer numeric scores into manufacturer satisfaction bands\n"
            "(e.g. Delight, Satisfied, Dissatisfied) according to brand guidelines."
        ),
        "responsibilities": [
            "Defines rating scale rules per OEM (Hyundai 1-10 scale, Tata 1-5 scale).",
            "Derives overall sentiment from customer answers (`derive_sentiment_from_score`)."
        ],
        "troubleshooting": [
            ("Customer marked Dissatisfied when they gave 9/10",
             "Incorrect rating scale configuration in database.",
             "Review rating scale thresholds in Admin Console -> Rating Scales tab.")
        ]
    },

    "backend/app/services/report_service.py": {
        "purpose": (
            "Analytics, Performance Metrics & Excel Reports Service.\n"
            "Aggregates dealership PSF performance data: connect rates, customer delight ratios,\n"
            "CRE caller productivity, and generates downloadable Excel (.xlsx) analytical workbooks."
        ),
        "responsibilities": [
            "Computes date-range filtered calling performance summaries (`get_reports_summary`).",
            "Computes CRE caller productivity and connect conversion metrics.",
            "Generates multi-tab Excel analytical workbooks (`generate_reports_excel_workbook`)."
        ],
        "troubleshooting": [
            ("Excel export download fails with 500 error",
             "openpyxl encountered missing or corrupted data in one of the rows.",
             "Check backend logs to identify the null field and verify date filters.")
        ]
    },

    "backend/app/services/user_service.py": {
        "purpose": (
            "User Accounts & Role Management Service.\n"
            "Provides business logic for creating personnel user accounts, updating passwords,\n"
            "assigning roles, and configuring explicit branch/brand data scopes."
        ),
        "responsibilities": [
            "Creates new dealership personnel users with hashed passwords (`create_user`).",
            "Updates user profiles, active status, and role assignments (`update_user`).",
            "Assigns explicit branch or brand access scopes (`set_user_scopes`)."
        ],
        "troubleshooting": [
            ("User cannot log in after creation",
             "Password was hashed incorrectly or user was marked inactive.",
             "Verify is_active is True and test logging in with the chosen credentials.")
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

    print(f"\nDone Batch 2! Updated {count} files.")

if __name__ == "__main__":
    apply_headers()

