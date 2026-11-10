# Script to add header documentation to frontend components, store, services, and root files

import os

DOCS = {
    "frontend/src/main.jsx": {
        "purpose": (
            "React Application Root Entry Point.\n"
            "Initializes the React virtual DOM tree, mounts the root React component into index.html,\n"
            "and sets up global CSS stylesheets and fonts."
        ),
        "responsibilities": [
            "Imports React and ReactDOM Client (`createRoot`).",
            "Mounts the `<App />` component into the DOM element with ID `root`.",
            "Imports global styles (`./index.css`)."
        ],
        "troubleshooting": [
            ("Blank white screen in browser on load",
             "JavaScript runtime crash before React mounts, or missing #root div in index.html.",
             "Open browser DevTools Console (F12) to inspect the initial error trace.")
        ]
    },

    "frontend/src/App.jsx": {
        "purpose": (
            "Top-Level Application Router & Toast Notification Shell.\n"
            "Configures all client-side page routes using React Router, wraps authenticated pages\n"
            "inside ProtectedRoute and AppLayout, and mounts the global Toast notification container."
        ),
        "responsibilities": [
            "Defines application URL routing hierarchy (Home, PSF, Import, Complaints, Admin, Users, Settings).",
            "Guards private routes using `<ProtectedRoute />`.",
            "Mounts `<LiveNotificationListener />` for real-time WebSocket toast alerts.",
            "Configures `<Toaster />` for notification banners."
        ],
        "troubleshooting": [
            ("User navigates to a URL and sees nothing or 404",
             "Route path was not added to the `<Routes>` list in this file.",
             "Add the `<Route path='/your-path' element={<YourComponent />} />` inside `<Routes>`.")
        ]
    },

    "frontend/src/services/api.js": {
        "purpose": (
            "Axios HTTP Client with Automatic Token Injection & Interceptors.\n"
            "Handles all HTTP network calls between the React frontend and the FastAPI backend.\n"
            "Automatically attaches the user's JWT Bearer token to outgoing requests and handles 401 token expiration."
        ),
        "responsibilities": [
            "Configures base URL (`http://localhost:8000/api/v1` or environment variable).",
            "Request Interceptor: Automatically injects `Authorization: Bearer <token>` from AuthStore.",
            "Response Interceptor: Automatically clears token and redirects to `/login` if server returns 401 Unauthorized."
        ],
        "troubleshooting": [
            ("Network Error or net::ERR_CONNECTION_REFUSED",
             "Backend API server on port 8000 is not running or unreachable.",
             "Verify that `psf_api` container is running using `docker ps`. Restart it with `docker restart psf_api`."),
            ("Repeated redirect to /login",
             "Stored JWT access token has expired and could not be refreshed.",
             "Log in again with valid credentials.")
        ]
    },

    "frontend/src/store/authStore.js": {
        "purpose": (
            "Zustand Authentication State & RBAC Permission Checking Store.\n"
            "Maintains the currently logged-in user's profile, JWT access token, and list of permissions.\n"
            "Provides easy permission checking helpers (`can('call.make')`, `canAny(...)`) used across all UI components."
        ),
        "responsibilities": [
            "Stores authenticated user profile object and JWT token string in localStorage.",
            "Provides `can(permissionKey)` helper to check if the user has a specific permission.",
            "Provides `canAny(...permissionKeys)` helper for multi-permission UI checks.",
            "Handles login state hydration and logout cleanup (`logout`)."
        ],
        "troubleshooting": [
            ("User permissions do not update after role change in Admin Console",
             "Permissions are cached in the user's active session token.",
             "Log out and log back in to refresh the JWT token with the newly assigned permissions.")
        ]
    },

    "frontend/src/store/themeStore.js": {
        "purpose": (
            "Zustand Theme Management Store (Light / Dark Mode).\n"
            "Stores the user's color scheme preference in localStorage and toggles the `dark` class\n"
            "on the root HTML document element."
        ),
        "responsibilities": [
            "Toggles between 'light' and 'dark' display modes.",
            "Persists user theme choice in browser localStorage.",
            "Applies or removes the `dark` class on the HTML `document.documentElement`."
        ],
        "troubleshooting": [
            ("Dark mode styles not applying to a component",
             "Component missing Tailwind dark mode classes (e.g. `dark:bg-slate-900`).",
             "Add explicit `dark:` prefix variants to the component's JSX className.")
        ]
    },

    "frontend/src/i18n/index.js": {
        "purpose": (
            "Internationalization & Localization Configuration.\n"
            "Configures multi-language translation strings and formatting helpers."
        ),
        "responsibilities": [
            "Provides language dictionary mapping.",
            "Supports localized date and currency formatting."
        ],
        "troubleshooting": [
            ("Translation key shows instead of text",
             "The translation key was not defined in the active language dictionary.",
             "Add the translation string to the dictionary.")
        ]
    },

    "frontend/src/tests/smoke.test.jsx": {
        "purpose": (
            "Frontend Smoke & Render Test Suite.\n"
            "Verifies that core React components render successfully without throwing unhandled exceptions."
        ),
        "responsibilities": [
            "Tests that the application mounts without runtime syntax errors.",
            "Tests that basic UI controls render properly."
        ],
        "troubleshooting": [
            ("Smoke test fails with ReferenceError or TypeError",
             "A component has an unhandled null check or missing import.",
             "Check the test error output for the component name and line number.")
        ]
    },

    "frontend/src/components/allocation/AllocationRulesTab.jsx": {
        "purpose": (
            "Allocation Strategy & Rules Configuration Component.\n"
            "Allows Super Admins to configure how DMS job card follow-ups are distributed:\n"
            "strategy (Equal Present CRE, Round Robin, By Branch), sticky customer grouping, and logout policies."
        ),
        "responsibilities": [
            "Fetches current allocation rules from `GET /api/v1/allocation/rules`.",
            "Saves updated rules to `PUT /api/v1/allocation/rules`.",
            "Restricted to Super Admin (L1) only."
        ],
        "troubleshooting": [
            ("Save button fails with HTTP 403 Forbidden",
             "Logged in user is not a Super Admin.",
             "CRE Admin (L2) cannot edit allocation rules; log in as `admin@apexauto.com`.")
        ]
    },

    "frontend/src/components/allocation/PresentCresPanel.jsx": {
        "purpose": (
            "Present CRE Roster & Attendance Slide-out Panel.\n"
            "Shows the CRE Admin which CREs are currently Present or Absent/On Leave today,\n"
            "their active pending call workloads, and provides toggle buttons to manually mark attendance."
        ),
        "responsibilities": [
            "Fetches present CRE list from `GET /api/v1/allocation/present-cres`.",
            "Provides toggle buttons to override attendance to 'Present' or 'On Leave'.",
            "Provides 'Allocate Now' button to immediately distribute unallocated calls.",
            "Provides 'Rebalance' button to re-equalize calls when a CRE joins mid-shift."
        ],
        "troubleshooting": [
            ("CRE shows 'Absent' even though they are working",
             "CRE has not logged in today or was marked absent.",
             "Click the 'Mark Present' toggle button in this panel to manually include them in call distribution.")
        ]
    },

    "frontend/src/components/auth/Can.jsx": {
        "purpose": (
            "Declarative Permission-Gated Wrapper Component.\n"
            "Wraps UI elements (like buttons, links, or sections) and conditionally renders them\n"
            "ONLY if the current user has the required permission key."
        ),
        "responsibilities": [
            "Checks `can(permission)` from AuthStore.",
            "Renders `children` if authorized; otherwise renders `fallback` or null."
        ],
        "troubleshooting": [
            ("A button wrapped in <Can> is invisible",
             "The user's role does not have the specified permission key.",
             "Verify the permission key name or check the user's role in the Admin Console.")
        ]
    },

    "frontend/src/components/auth/ProtectedRoute.jsx": {
        "purpose": (
            "Client-Side Route Authentication Guard.\n"
            "Protects private dashboard pages: if the user is not authenticated, it immediately\n"
            "redirects them to `/login` while preserving their attempted destination URL."
        ),
        "responsibilities": [
            "Checks if an active user session exists in AuthStore.",
            "Redirects unauthenticated visitors to `/login`.",
            "Renders protected route content (`<Outlet />` or children) for logged-in users."
        ],
        "troubleshooting": [
            ("User repeatedly kicked back to login page",
             "JWT token is missing, corrupted, or expired in localStorage.",
             "Clear browser localStorage and log in again at `/login`.")
        ]
    },

    "frontend/src/components/calling/CallAttemptHistoryModal.jsx": {
        "purpose": (
            "Call Attempt History Modal Popup.\n"
            "Displays the chronological audit trail of all previous phone call attempts made to a customer,\n"
            "including timestamps, who called, call outcomes (Connected, Busy, Switched Off), and past VOC feedback."
        ),
        "responsibilities": [
            "Displays past calling attempts for a specific follow-up queue item.",
            "Shows caller name, date/time, customer rating, and recorded remarks."
        ],
        "troubleshooting": [
            ("Modal opens empty",
             "No previous attempts have been made on this queue item (first attempt).",
             "The modal displays 'No previous call attempts recorded' in this scenario.")
        ]
    },

    "frontend/src/components/calling/CallConsoleModal.jsx": {
        "purpose": (
            "Interactive Call Console & Customer Dossier Dialer Modal.\n"
            "The primary caller interface: opens when a CRE clicks 'Call' on a line item.\n"
            "Displays complete customer vehicle snapshot, repair invoice details, brand-specific survey questions,\n"
            "sentiment selectors (Delight, Satisfied, Dissatisfied), VOC notes, and one-click complaint escalation."
        ),
        "responsibilities": [
            "Fetches full customer dossier from `GET /api/v1/psf/console/{queue_id}`.",
            "Renders dynamic OEM survey questions (Hyundai 4-Q, Tata 7-Q, MG 5-Q).",
            "Allows setting call outcome (Connected, Not Connected, Busy, Callback Requested).",
            "Submits call log to `POST /api/v1/psf/calls/submit`.",
            "Supports 'Save & Next' to immediately advance to the next assigned customer without closing the dialer."
        ],
        "troubleshooting": [
            ("Submit button disabled",
             "Mandatory call outcome (e.g. Connected / Not Connected) or survey rating was not selected.",
             "Select a call status outcome button before submitting."),
            ("Call submission fails with error toast",
             "Validation error on the submission payload.",
             "Inspect DevTools network tab to see which field was missing or invalid.")
        ]
    },

    "frontend/src/components/common/LiveNotificationListener.jsx": {
        "purpose": (
            "Real-Time WebSocket Allocation Notification Listener.\n"
            "Maintains an active WebSocket connection to the backend Redis pub/sub channel\n"
            "and immediately displays a bouncing toast alert whenever new calls are assigned to the logged-in CRE."
        ),
        "responsibilities": [
            "Connects to `ws://localhost:8000/api/v1/allocation/ws/notifications/{token}`.",
            "Listens for `CALLS_ALLOCATED` broadcast events.",
            "Displays a toast notification with a 1-click button to open the PSF calling workspace.",
            "Re-establishes connection automatically if network drops."
        ],
        "troubleshooting": [
            ("Console warning: 'WebSocket connection failed'",
             "API server is down or token is invalid.",
             "Listener automatically backs off and retries after 5 seconds.")
        ]
    },

    "frontend/src/components/layout/AppLayout.jsx": {
        "purpose": (
            "Master Dashboard Shell Layout.\n"
            "Provides the persistent layout surrounding all dashboard pages:\n"
            "renders the responsive Sidebar on the left, Header at the top, and scrollable content area."
        ),
        "responsibilities": [
            "Houses `<Sidebar />` and `<Header />`.",
            "Manages mobile menu drawer open/close state.",
            "Renders active page component inside `<main>` via `<Outlet />`."
        ],
        "troubleshooting": [
            ("Page content hidden under header or off-screen",
             "CSS layout overflow or z-index issue.",
             "Check responsive Tailwind classes in `AppLayout.jsx`.")
        ]
    },

    "frontend/src/components/layout/Header.jsx": {
        "purpose": (
            "Top Navigation & Header Bar.\n"
            "Displays dealership branding, global search input, light/dark theme toggle,\n"
            "logged-in user role badge, and quick logout button."
        ),
        "responsibilities": [
            "Displays dealership logo and name.",
            "Provides quick search bar for Job Cards, Customers, and VIN numbers.",
            "Theme switch button (Sun / Moon) calling ThemeStore.",
            "Displays logged-in user name and role badge (e.g. Super Admin, CRE).",
            "Provides End Shift & Log Out button."
        ],
        "troubleshooting": [
            ("User avatar shows 'Guest'",
             "User profile failed to load into AuthStore.",
             "Refresh the page or log in again to populate user details.")
        ]
    },

    "frontend/src/components/layout/Sidebar.jsx": {
        "purpose": (
            "Left Navigation Sidebar with Permission Filtering.\n"
            "Renders the primary navigation menu links, filtering each link based on the user's role permissions,\n"
            "and displays the real-time active shift timer in the footer."
        ),
        "responsibilities": [
            "Filters menu items according to user permissions (`can`, `canAny`).",
            "Highlights the active navigation route.",
            "Displays active shift elapsed timer (e.g. 'Shift Active: 2 hours active').",
            "Provides End Shift & Log Out button at the bottom."
        ],
        "troubleshooting": [
            ("A menu link (e.g. Enterprise Admin) is missing for a user",
             "The user's role lacks the required permission for that menu item.",
             "This is by design (RBAC). Super Admin has access to all links; CRE only sees calling screens.")
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

    print(f"\nDone Batch 5! Updated {count} frontend components/services.")

if __name__ == "__main__":
    apply_headers()

