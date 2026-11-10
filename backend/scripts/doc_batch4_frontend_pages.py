# Script to add header documentation to frontend pages

import os

DOCS = {
    "frontend/src/pages/HomePage.jsx": {
        "purpose": (
            "Dealership PSF Home Landing Page.\n"
            "This is the first screen all dealership users see upon login. It displays their shift greeting,\n"
            "high-level calling KPI cards (Pending Calls, Contacted, Connect Rate, Open Complaints),\n"
            "and an immediate Calling Queue Line Items table with one-click calling and WhatsApp triggers."
        ),
        "responsibilities": [
            "Fetches dashboard KPI counters from `GET /api/v1/psf/dashboard`.",
            "Fetches pending calling queue items from `GET /api/v1/psf/queues?status=PENDING`.",
            "Enforces role scoping: CRE callers only see their assigned customers; Admins see dealership-wide calls.",
            "Provides one-click telephone (`tel:`) and WhatsApp chat links.",
            "Provides quick navigation buttons to Data Import and Full PSF Calling Workspace."
        ],
        "troubleshooting": [
            ("KPI cards show 0 and table shows 'Loading calling queue...' permanently",
             "Backend API server is unreachable, deadlocked, or JWT session expired.",
             "Open browser DevTools Network tab. If requests are timing out, check `docker ps` and restart `psf_api` with `docker restart psf_api`."),
            ("Table says 'No pending calls found in your queue'",
             "For a CRE caller, no customers have been allocated to your account yet today.",
             "Ask the CRE Admin to import today's DMS job cards or click 'Allocate Now' in Shift Attendance.")
        ]
    },

    "frontend/src/pages/NotFoundPage.jsx": {
        "purpose": (
            "404 Not Found Fallback Page.\n"
            "Displayed whenever a user navigates to an invalid or unmapped URL path.\n"
            "Shows a friendly error message with a button to safely return back to the Home page."
        ),
        "responsibilities": [
            "Catches unmatched router paths in React Router (`path='*'`).",
            "Provides a 1-click button to navigate safely back to Home (`/`)."
        ],
        "troubleshooting": [
            ("User repeatedly lands on 404 page when clicking menu links",
             "The clicked route path does not match any Route definition in App.jsx.",
             "Verify the URL path in `frontend/src/components/layout/Sidebar.jsx` matches `App.jsx`.")
        ]
    },

    "frontend/src/pages/PlaceholderPage.jsx": {
        "purpose": (
            "Feature Placeholder Page.\n"
            "Displays a clean 'Under Development' screen for modules scheduled for future phases."
        ),
        "responsibilities": [
            "Provides a placeholder view with breadcrumbs and feature explanation.",
            "Prevents broken page crashes for future menu items."
        ],
        "troubleshooting": [
            ("Feature shows placeholder instead of real screen",
             "The route is pointed to PlaceholderPage instead of the finished page component.",
             "Update the route import in `App.jsx` to point to the actual page component.")
        ]
    },

    "frontend/src/pages/admin/AdminConsolePage.jsx": {
        "purpose": (
            "Enterprise Admin Console (Super Admin Control Center).\n"
            "Provides Super Admins with full control over the dealership system: the RBAC Role Permission Matrix\n"
            "(who can do what and at what data scope level), system-wide allocation rules, and supervisor data corrections."
        ),
        "responsibilities": [
            "Fetches and updates the Role Permission Matrix (`GET/PUT /api/v1/admin/matrix`).",
            "Allows configuring permission scopes: ALL, BRAND, BRANCH, OWN.",
            "Provides supervisor data correction tool with mandatory audit reason logging.",
            "Guarantees lockout protection so the Super Admin role cannot accidentally delete itself."
        ],
        "troubleshooting": [
            ("Page shows 'Access Denied' or redirects to login",
             "Logged in user is not a Super Admin (L1).",
             "Log in using `admin@apexauto.com` / `Password@12345` to access the Admin Console."),
            ("Saving permissions matrix fails with error toast",
             "Network error or constraint violation.",
             "Check the DevTools network tab for specific validation error message.")
        ]
    },

    "frontend/src/pages/advisors/AdvisorPortalPage.jsx": {
        "purpose": (
            "Service Advisor Follow-up Action Portal.\n"
            "Allows Service Advisors to review and take action on dissatisfied customers and complaints\n"
            "assigned to their workshop repair orders."
        ),
        "responsibilities": [
            "Displays customer complaints filtered to the logged-in Service Advisor.",
            "Allows advisors to add root cause analysis notes and proposed corrective actions.",
            "Prevents advisors from closing complaints directly (enforcing dual-authorization)."
        ],
        "troubleshooting": [
            ("Advisor sees 0 complaints even when customer was dissatisfied",
             "Complaint was not assigned to this advisor or job card advisor name did not match.",
             "Verify complaint assignment in the Complaints tab.")
        ]
    },

    "frontend/src/pages/auth/AttendanceLogsPage.jsx": {
        "purpose": (
            "Shift Attendance & Daily Login Logs Page.\n"
            "Displays the chronological history of daily login and logout timestamps for dealership personnel,\n"
            "showing shift start, shift end, duration, IP address, and attendance status."
        ),
        "responsibilities": [
            "Fetches login attendance logs from `GET /api/v1/auth/attendance/logs`.",
            "Displays shift status (Active / Completed) and active shift duration.",
            "Allows CRE Admin to see who punched in today and is eligible for call allocation."
        ],
        "troubleshooting": [
            ("Shift shows 'Active' from 2 days ago",
             "User forgot to click 'End Shift / Log Out' at the end of their shift.",
             "Click 'End Shift & Log Out' in the bottom left sidebar, or let the automatic end-of-day cleanup run.")
        ]
    },

    "frontend/src/pages/auth/LoginPage.jsx": {
        "purpose": (
            "Dealership Staff Authentication & Punch-In Screen.\n"
            "Allows dealership employees to sign into the system using their email and password.\n"
            "Authenticates credentials, starts their shift attendance timer, and stores JWT tokens."
        ),
        "responsibilities": [
            "Submits login credentials to `POST /api/v1/auth/login`.",
            "Stores JWT access token in AuthStore and triggers shift attendance punch-in.",
            "Displays clear error banners if credentials are wrong or account is inactive.",
            "Provides quick-login role chips for fast switching during demo / testing."
        ],
        "troubleshooting": [
            ("Error banner: 'Incorrect email or password'",
             "Wrong password entered.",
             "Default password for all personnel accounts is `Password@12345`."),
            ("Error banner: 'This account has been deactivated'",
             "The user's is_active flag is set to False in the database.",
             "Have a Super Admin reactivate your account in User Management.")
        ]
    },

    "frontend/src/pages/complaints/ComplaintManagementPage.jsx": {
        "purpose": (
            "Customer Complaints, Escalations & SLA Management Page.\n"
            "Tracks customer dissatisfaction issues generated from follow-up calls.\n"
            "Enables dealership managers to assign tickets, track resolution deadlines, and log corrective actions."
        ),
        "responsibilities": [
            "Lists customer complaints with status filters (OPEN, IN_PROGRESS, RESOLVED, CLOSED).",
            "Highlights SLA breached complaints with flashing warning badges.",
            "Allows managers to reassign complaints to Service Advisors or Service Managers.",
            "Provides action modal to record resolution remarks and customer compensation notes."
        ],
        "troubleshooting": [
            ("Resolution button is disabled or fails with HTTP 403",
             "Logged in user does not have `complaint.close` permission.",
             "Only CRE Admin, Dealer Admin, or Super Admin can mark complaints RESOLVED / CLOSED.")
        ]
    },

    "frontend/src/pages/happiness/HappinessCallingPage.jsx": {
        "purpose": (
            "OEM 24-Hour Happiness Calling Queue Page.\n"
            "Dedicated calling queue for immediate next-day post-service follow-up (24-hour happiness check),\n"
            "ensuring customer satisfaction before the official OEM survey period."
        ),
        "responsibilities": [
            "Filters calling queue to `queue_type=HAPPINESS`.",
            "Allows CREs to make quick satisfaction verification calls.",
            "Immediately escalates any customer dissatisfaction into an urgent complaint ticket."
        ],
        "troubleshooting": [
            ("Queue is empty",
             "No job cards have been imported for the Happiness queue or all have been completed.",
             "Check the main PSF Dashboard to see if calling line items are in the PSF queue instead.")
        ]
    },

    "frontend/src/pages/imports/DataImportPage.jsx": {
        "purpose": (
            "DMS Data Import & Automatic Call Allocation Page.\n"
            "Allows CRE Admins and Super Admins to upload dealer management system (DMS) Excel/CSV files.\n"
            "Automatically divides imported customer calls EQUALLY among active present CREs in 1 click."
        ),
        "responsibilities": [
            "Provides drag-and-drop file upload supporting `.xlsx`, `.xls`, and `.csv`.",
            "Provides downloadable 13-column Standard DMS sample templates (Excel and CSV).",
            "Submits file to `POST /api/v1/imports/upload-and-process`.",
            "Displays instant import summary: job cards created, duplicates skipped, and caller allocation breakdown.",
            "Provides downloadable Excel error reports for rows with bad data."
        ],
        "troubleshooting": [
            ("Toast error: 'Unknown Branch [NAME]'",
             "The branch name in the Excel file does not match any branch in the database.",
             "Create the Branch in Enterprise Admin under Masters, or correct the branch spelling in the Excel file."),
            ("Toast error: 'Duplicate file upload'",
             "The exact same file was already imported.",
             "Check the recent import batches table below to see when it was imported.")
        ]
    },

    "frontend/src/pages/psf/PsfDashboardPage.jsx": {
        "purpose": (
            "Main PSF Calling Workspace & Line Items Spreadsheet.\n"
            "The primary operational dashboard for dealership customer follow-up calls.\n"
            "Renders the complete Line Items Spreadsheet Table matching manufacturer DMS format,\n"
            "enforces CRE role scoping, provides search/filters, and launches the Call Console dialer."
        ),
        "responsibilities": [
            "Displays top KPI cards (Due Calls Today, Contacted, Connect Rate %, Open Complaints).",
            "Renders full Line Items table: Job Card No, Date, Customer Name (Call/WhatsApp), Branch, Brand Logo, VIN, Reg No, Model, Service Type, Status, VOC, Followed By (CRE), Service Advisor, Technician.",
            "Enforces CRE role scoping: CRE callers only see their assigned line items.",
            "Allows Admins to filter by Branch, Queue Type, Status, and Assigned CRE.",
            "Provides Bulk Reassignment bar allowing Admins to reassign selected line items.",
            "Opens the CallConsoleModal dialer when a row or 'Call' button is clicked."
        ],
        "troubleshooting": [
            ("Infinite spinner saying 'Loading line items...'",
             "Backend API server was reloading or timed out.",
             "Refresh the browser page (`F5`). If issue persists, check `docker logs --tail 20 psf_api`."),
            ("CRE user sees 'No line items found'",
             "No calls have been allocated to this specific CRE yet.",
             "Ask the CRE Admin to import a DMS file or use 'Allocate Now' in Shift Attendance.")
        ]
    },

    "frontend/src/pages/reports/ReportsDashboardPage.jsx": {
        "purpose": (
            "Dealership Reports & Analytical Insights Page.\n"
            "Displays aggregate calling performance, connect ratios, customer delight percentages,\n"
            "CRE caller productivity comparisons, and provides downloadable Excel analytical workbooks."
        ),
        "responsibilities": [
            "Fetches date-filtered calling statistics from `GET /api/v1/reports/summary`.",
            "Displays visual charts for connect rate and CSAT satisfaction trends.",
            "Provides 1-click download of multi-tab Excel analytical workbooks."
        ],
        "troubleshooting": [
            ("Toast error: 'Failed to download report'",
             "Network timeout or backend error generating Excel file.",
             "Select a shorter date range (e.g. Last 7 Days) and try again.")
        ]
    },

    "frontend/src/pages/settings/BranchContactsTab.jsx": {
        "purpose": (
            "Branch Contacts & Escalation Matrix Settings Tab.\n"
            "Allows configuring contact phone numbers, emails, and escalation managers for each workshop branch."
        ),
        "responsibilities": [
            "Lists workshop branches with phone, email, and manager contact details.",
            "Allows updating branch escalation contact points for unresolved complaints."
        ],
        "troubleshooting": [
            ("Changes not saving",
             "User lacks `settings.manage` permission.",
             "Ensure you are logged in as Super Admin or Dealer Admin.")
        ]
    },

    "frontend/src/pages/settings/RatingScalesTab.jsx": {
        "purpose": (
            "OEM Rating Scales & Satisfaction Bands Settings Tab.\n"
            "Configures brand-specific rating scales (e.g. Hyundai 1-10 NPS, Tata 1-5 Star)\n"
            "and defines score thresholds for Delight, Satisfied, and Dissatisfied classifications."
        ),
        "responsibilities": [
            "Displays rating bands configured for each OEM brand.",
            "Allows adjusting minimum score thresholds for Delight and Dissatisfied."
        ],
        "troubleshooting": [
            ("Rating bands missing for a brand",
             "Brand has not been configured with rating scale rules.",
             "Run the database seed script to restore default manufacturer rating bands.")
        ]
    },

    "frontend/src/pages/settings/SettingsPage.jsx": {
        "purpose": (
            "Dealership Settings Container Page.\n"
            "Houses tabbed configuration panels for Allocation Rules, Branch Contacts, and OEM Rating Scales."
        ),
        "responsibilities": [
            "Switches between Allocation Rules, Branch Contacts, and Rating Scales tabs.",
            "Restricts tab access according to user permissions."
        ],
        "troubleshooting": [
            ("Allocation Rules tab is missing",
             "CRE Admin (L2) is not permitted to edit allocation rules (Super Admin L1 only).",
             "Log in as Super Admin (`admin@apexauto.com`) to edit allocation rules.")
        ]
    },

    "frontend/src/pages/users/UserManagementPage.jsx": {
        "purpose": (
            "Personnel User Roster & Scoping Management Page.\n"
            "Allows Dealership Admins to view all staff accounts, create new employees, assign roles,\n"
            "activate or deactivate accounts, and configure branch access restrictions."
        ),
        "responsibilities": [
            "Fetches all dealership personnel accounts from `GET /api/v1/users`.",
            "Provides user creation modal with role assignment dropdown.",
            "Allows toggling active/inactive status and resetting passwords.",
            "Allows assigning explicit branch or brand access scopes."
        ],
        "troubleshooting": [
            ("Cannot create user: 'Email already exists'",
             "Another staff account already uses this email address.",
             "Use a unique work email address for the new user account.")
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
            '/**',
            ' * ============================================================================',
            f' * FILE PURPOSE: {doc["purpose"].replace(chr(10), chr(10) + " * ")}',
            ' * ',
            ' * KEY RESPONSIBILITIES:'
        ]
        for r in doc["responsibilities"]:
            header_lines.append(f' * - {r}')
        
        header_lines.append(' * ')
        header_lines.append(' * COMMON ERRORS & TROUBLESHOOTING GUIDE:')
        for err, cause, fix in doc["troubleshooting"]:
            header_lines.append(f' * - Error: {err}')
            header_lines.append(f' *   -> Cause: {cause}')
            header_lines.append(f' *   -> What should you do: {fix}')
        
        header_lines.extend([
            ' * ============================================================================',
            ' */',
            ''
        ])

        new_content = "\n".join(header_lines) + content
        with open(file_rel, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Added header to: {file_rel}")
        count += 1

    print(f"\nDone Batch 4! Updated {count} frontend pages.")

if __name__ == "__main__":
    apply_headers()

