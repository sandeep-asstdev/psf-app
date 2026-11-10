# Enterprise Administrator & Governance Guide

This guide details how administrators can configure and manage the PSF CRM platform without modifying backend code or database schemas.

---

## 1. Role Hierarchy & Dynamic Permissions Matrix

### 1.1 Organizational Hierarchy
The platform organizes dealerships across three distinct administrative tiers:
* **L1 - Super Admin (System / Developers)**:
  * Full control across all brands, branches, and masters.
  * Only level permitted to create/edit brands, branches, roles, permissions matrix, and perform emergency data correction.
* **L2 - CRE Admin (Dealership-wide)**:
  * Dealership-wide oversight across all OEM brands and branches.
  * Manages CRE staff (assign, reassign, activate/deactivate), allocates calls, imports DMS job cards, closes complaints, and accesses aggregated analytics.
  * Cannot alter brands, branches, roles, permissions matrix, or core system settings.
* **L3 - Branch Level (Strictly Scoped)**:
  * **Branch Manager**: Scoped to assigned branch(es). Can view branch calls, monitor branch complaints, and reassign callers within branch.
  * **Branch CRE**: Scoped to own assigned calls and survey submissions.
  * **Service Advisor**: Scoped to own customer feedback tickets and corrective action remarks.

### 1.2 Data Scopes
Every permission granted to a role carries a mandatory `data_scope`:
| Data Scope | Description | Query Filtering Applied |
| :--- | :--- | :--- |
| `ALL` | Tenant-wide unrestricted access | No branch or owner restriction |
| `DEALERSHIP` | Dealership-wide visibility | Filtered to tenant |
| `ASSIGNED_BRANCHES` | Branch-restricted | `model.branch_id IN (user_assigned_branches)` |
| `OWN` | Self-assigned records | `model.assigned_to_id == current_user.id` or `service_advisor_id == current_user.id` |

### 1.3 How to Add a New Role
1. Navigate to **Enterprise Admin** > **Roles & Matrix** tab.
2. Click **Add Role** in the top-right header.
3. Enter the role name (e.g. `FLOOR_SUPERVISOR`), choose the hierarchy level (`L2` or `L3`), and provide a description.
4. In the interactive permission grid, click the badge for each resource action to cycle through the desired data scope (`ALL` -> `DEALERSHIP` -> `ASSIGNED_BRANCHES` -> `OWN` -> disabled).
5. Click the green **Save (Floppy Disk)** icon in the role header. Changes immediately invalidate Redis cached permissions.

### 1.4 How to Clone an Existing Role
1. In the **Roles & Matrix** grid, locate the template role header.
2. Click the **Clone (Copy)** icon.
3. Provide the new role name and description. All assigned permissions and data scopes are cloned into the new role.

---

## 2. Managing Brands & Branches

### 2.1 Adding an OEM Brand
1. Navigate to **Enterprise Admin** > **Brands & Branches** (or **Settings** > **Brands & Branches**).
2. Click **Add Brand**.
3. Fill in:
   * **Brand Name**: e.g. `Hyundai`, `Tata Motors`, `MG Motors`.
   * **Brand Code**: e.g. `HYUN`, `TATA`, `MG`.
   * **Primary Color**: Hex color code for UI badging (e.g. `#002C6C`).
   * **Happiness Calling**: Enabled automatically for Hyundai (15-day and 30-day post-delivery calling).

### 2.2 Adding a Workshop Branch & DMS Code
1. In the Branches section, click **Add Branch**.
2. Fill in:
   * **Branch Name**: e.g. `Apex Central Workshop`.
   * **Internal Code**: e.g. `APEX-CENTRAL`.
   * **DMS Code**: Exact prefix code from the dealer management software (e.g., `S8211` for Hubli, `S8827` for Gadag). The DMS importer automatically resolves this code to the correct branch.
   * **Assigned Brand**: Select the OEM brand operating at this workshop.
   * **Contact Number & Email**: Workshop reception details.

---

## 3. Dynamic Questionnaire Builder (Draft -> Publish Flow)

### 3.1 Managing Questionnaires
Questionnaires are versioned per OEM brand and campaign type (`PSF`, `TNPS`, `HAPPINESS`, `RECONFIRMATION`).
1. Navigate to **Settings** > **Questionnaires** tab.
2. Select the target Brand and Campaign Type.
3. Status indicators indicate:
   * `DRAFT`: In design mode. Can add, edit, reorder, or delete questions.
   * `PUBLISHED`: Active in call consoles. Immutable to protect historical response integrity.
   * `ARCHIVED`: Deprecated versions preserved for audit and reports.

### 3.2 Adding Questions
1. Click **Add Question** inside the questionnaire panel.
2. Configure:
   * **Question Key**: Unique machine identifier (e.g., `advisor_politeness`, `cleaning_satisfaction`).
   * **Label**: Customer-facing question text read by the CRE.
   * **Answer Type**:
     * `YES_NO`: Yes / No toggle.
     * `YES_NO_NA`: Yes / No / Not Applicable.
     * `RATING_10`: 1 to 10 numerical rating.
     * `RATING_5`: 1 to 5 numerical rating.
     * `TEXT`: Freeform remarks.
   * **Section**: Grouping header (e.g., "Service Quality", "Washing & Polishing", "Billing Transparency").
   * **Conditional Logic (`show_if`)**: Set conditional rules (e.g. only show root cause question if previous answer was `"No"`).
   * **Scoring Weight**: Weight allocated towards CSAT calculation.
3. Click **Save Question**. When finalized, click **Publish Version** to activate immediately.

---

## 4. Rating Scales, Sentiment Bands & Complaint Triggers

### 4.1 Rating Scales per Brand
Under **Settings** > **Rating Scales**:
* **Hyundai (10-Point Scale)**:
  * `10`: Delight (`is_delight = true`, `is_complaint_trigger = false`)
  * `9`: Satisfied (`is_delight = false`, `is_complaint_trigger = true` -> Triggers `"WATSAPP RATING <=9"` complaint)
  * `6 - 8`: Non-Delight / Average (`is_complaint_trigger = true`)
  * `1 - 5`: Poor / Dissatisfied (`is_complaint_trigger = true`)
* **Tata Motors (5-Point Scale)**:
  * `5`: Delight (`is_delight = true`)
  * `4`: Satisfied
  * `1 - 3`: Dissatisfied (`is_complaint_trigger = true`)
* **MG Motors (10-Point Scale)**:
  * `9 - 10`: Satisfied
  * `1 - 8`: Poor / Dissatisfied (`is_complaint_trigger = true`)
* **Ather Energy (TNPS Follow-up Program)**:
  * Ather Energy uses a brand-scoped follow-up program labeled **TNPS** (`enable_tnps = true`, `tnps_label = "TNPS"`).
  * Ather job cards import directly into `queue_type = "TNPS"` and are allocated equally among present CRE callers upon DMS import (no secondary delayed schedule).
  * Survey consists of `ather_jobs_satisfaction` (Yes/No) and `ather_tnps_rating` (0-10 scale), scoring Promoters (9-10), Passives (7-8), and Detractors (0-6).
  * The dedicated dashboard widget **TNPS Calls** groups calling queues exclusively across Ather branches (Bangalore, Belgaum, Hubballi, Sirsi).

### 4.2 Editing Complaint Triggers
Any rating band can be configured in real-time by toggling the `is_complaint_trigger` switch. When enabled, any WhatsApp rating or phone VOC survey landing in this score band automatically creates a tracked complaint ticket with SLA timer.

---

## 5. Dynamic Custom Fields (JSONB)

To support brand-specific warranty codes, VIP badges, or custom workshop checklists without database migrations:
1. Navigate to **Enterprise Admin** > **Custom Fields** tab.
2. Select target entity: `Job Cards`, `Call Attempts`, or `Complaints`.
3. Click **Add Custom Field**:
   * **Field Name**: Unique JSON key (e.g., `extended_warranty_opted`).
   * **Field Label**: Display label (e.g., `Extended Warranty Opt-in`).
   * **Data Type**: `TEXT`, `NUMBER`, `BOOLEAN`, `DATE`, or `DROPDOWN`.
   * **Required**: Toggle mandatory input enforcement.
4. Values are stored inside the entity's `custom_fields` JSONB column and rendered in forms and tables.

---

## 6. Super Admin Emergency Data Correction

Under strict governance rules, Super Admins can correct erroneous records (e.g., incorrect customer mobile number or wrong assigned advisor):
1. Navigate to **Enterprise Admin** > **Data Correction** tab.
2. Select the **Entity Type** (`JOB_CARD`, `CALL`, `COMPLAINT`, `CUSTOMER`, `USER`).
3. Enter the record's UUID.
4. Provide the updated fields in valid JSON format:
   ```json
   {
     "service_advisor_name": "Rajesh Kumar",
     "total_amount": 14250.00
   }
   ```
5. Enter a **Mandatory Justification Reason** (e.g., *"Customer disputed advisor name; corrected per signed job card copy"*).
6. Click **Apply Audited Correction**.
7. The system records an immutable row in `audit_logs` storing:
   * Operator ID & IP address
   * Old values before update
   * New values applied
   * Justification reason

---

## 7. User Simulation ("View As User")

Super Admins can simulate the app exactly as any specific employee sees it:
1. Navigate to **Enterprise Admin** > **Users & Simulation** tab.
2. Locate the user row and click **View as User**.
3. Enter a mandatory simulation reason (e.g., *"Investigating why Bangalore North CRE cannot see West Hub calls"*).
4. Click **Start Simulation**.
5. The interface switches to a scoped simulation token. A high-visibility amber banner indicates:
   > **SIMULATION MODE: Viewing system as Priya Sharma (CRE). All actions are audited. [Exit Simulation]**
6. Click **Exit Simulation** at any time to return immediately to Super Admin mode.

---

## 8. Audit Logs & 1-Click Rollback

1. Navigate to **Enterprise Admin** > **Audit & Rollback** tab.
2. Review the **System Audit Trail** for user logins, permission edits, data corrections, and impersonation starts.
3. Review **Configuration Change History**:
   * Each matrix update, SLA rule change, and setting update creates a version snapshot (`v1`, `v2`, ...).
   * Click the red **Rollback** button next to any revision, provide a mandatory reason, and the system restores the exact previous state.

---

## 9. Automatic Equal Call Allocation on DMS Import

### 9.1 Overview & Business Rule
When a CRE Admin or Super Admin uploads and processes DMS job cards, the system automatically divides the new follow-up calls **EQUALLY** among all CRE callers who are **PRESENT today**. No manual assignment step is required.
* **Equal Distribution Guarantee**: If $N$ calls are split among $M$ present CREs, each caller receives either $\lfloor N/M \rfloor$ or $\lfloor N/M \rfloor + 1$ calls (e.g. 29 calls split across 3 present CREs gives 10 / 10 / 9). The difference between any two CREs is at most 1.
* **Rotating Remainder Pointer**: A persistent cursor (`allocation_cursors`) advances by the remainder $N \pmod M$ after each import. For example, with 29 calls and 3 CREs:
  - *Import 1*: CRE A gets 10, CRE B gets 10, CRE C gets 9.
  - *Import 2*: CRE C gets 10, CRE A gets 10, CRE B gets 9.
  - *Import 3*: CRE B gets 10, CRE C gets 10, CRE A gets 9.
  - *Cumulative Fairness*: Over 3 imports, each CRE receives exactly 29 calls.

### 9.2 Determining Caller Presence
A caller is considered **PRESENT** if:
1. Their account is active, not deleted, and their role possesses the `call.make` permission (or `SUPER_ADMIN`).
2. They have an open login session today recorded in `login_logs` (`logout_at IS NULL`), **OR**
3. A CRE Admin has manually marked them **PRESENT** via the **CRE Attendance & Live Presence** panel.
* **Manual Overrides Take Precedence**: Marking a user **ABSENT** or **ON_LEAVE** overrides any open login session. Marking an off-duty user **PRESENT** includes them in the distribution even before they log in.

### 9.3 Scoping & Allocation Modes
Configurable in **Enterprise Admin** > **Call Allocation**:
- **CRE_POOL (Default)**: Central dealership CREs receive calls from all branches unless an explicit branch restriction is attached to their profile.
- **BRANCH_ONLY**: Strict branch isolation. Callers only receive job cards belonging to branches explicitly within their scope.
- **Sticky Customers (Default: ON)**: When a single customer has multiple job cards in the same import batch (e.g. multiple vehicles serviced), the entire bundle is assigned to the same CRE so the customer receives a single consolidated call.
- **Balance Total Pending Workload (Default: OFF)**: When enabled, the allocator equalizes total outstanding pending queues across callers rather than splitting only the new import batch.
- **CRE Logout Policy**:
  - `KEEP` (Default): Pending calls stay assigned to the caller for their next shift.
  - `RETURN_TO_POOL`: Untouched calls return to the unallocated pool upon logout.
  - `REDISTRIBUTE_EQUALLY`: Untouched calls are automatically reallocated among other currently present CREs.

### 9.4 Late Joiners & Untouched Call Rebalancing
When a caller arrives late:
1. Mark them **PRESENT** in the CRE Attendance panel.
2. Click **Rebalance Calls**.
3. A modal preview shows current untouched pending counts vs proposed counts per CRE.
4. Click **Confirm Rebalance**.
> **Safety Guarantee**: ONLY untouched calls (`attempts == 0` and `status == 'PENDING'`) are eligible to move. Calls already attempted, in progress, connected, or closed **NEVER MOVE**.

### 9.5 1-Click Allocation Rollback (Safety Window)
Every allocation run records an `AllocationRun` with linked `AllocationAssignment` rows.
* In the Import Result screen, an **Undo Allocation Batch** button is available within a configurable safety window (default 15 minutes).
* Clicking **Undo** restores all assigned calls in that batch back to their previous unassigned state.
* If any call in that batch has already been attempted by a caller, the system strictly rejects the rollback with a safety alert to protect ongoing caller workflows.

---

## 10. How to Import a DMS File and Fix Errors

The PSF platform features a fault-tolerant Standard DMS Ingestion Engine that processes dealership job cards without aborting on erroneous rows.

### 10.1 Standard 13-Column DMS Specification
Dealerships export workshop job cards containing the following 13 columns:
1. `Brand`: OEM brand name (e.g. `Hyundai`, `Tata Motors`, `MG Motors`).
2. `Branch`: Workshop outlet name, code, or DMS code (e.g. `HYUNDAI HUBLI`, `S8211`).
3. `Brand Logo`: *(Optional)* Ignored by the importer as logos load dynamically from masters.
4. `Job Card No`: Unique workshop repair order / invoice identifier (e.g. `S8211_R202600449`).
5. `Job Card Date`: Date of vehicle delivery or invoice (`DD-MM-YYYY`, `DD/MM/YYYY`, or `YYYY-MM-DD`).
6. `Customer Name`: Vehicle owner / customer name.
7. `Contact Number`: 10-digit Indian mobile number starting with 6, 7, 8, or 9.
8. `Vin No`: 17-character vehicle identification number.
9. `Reg No`: Alphanumeric vehicle registration plate (e.g. `KA25M1234`).
10. `Model`: Vehicle model name (e.g. `Creta 1.5`, `Nexon EV`, `Hector Plus`).
11. `Service Advisor`: Name of the service advisor who handled the customer.
12. `Service Type`: Service classification (e.g. `Periodic Maintenance Service`, `Running Repair`).
13. `Total Service Amount`: Final billed invoice amount in rupees (e.g. `4500.00` or `₹12,500.50`).

> **System-Generated Metadata**: Unique ID, Uploaded By, and Upload Timestamp are automatically generated by the server. They must **never** be supplied in the import file.

### 10.2 Downloading the Sample Template
1. Navigate to **Data Import** in the main sidebar.
2. In the top-right header, click:
   * **Download Template (Excel)**: Downloads `standard_dms_template.xlsx` formatted with headers and 2 realistic sample rows.
   * **Download Template (CSV)**: Downloads `standard_dms_template.csv` encoded in UTF-8 with BOM for direct Excel compatibility.

### 10.3 The 3-Step Import Workflow

#### Step 1: Upload & Duplicate Detection
* Drag and drop your `.xlsx`, `.xls`, or `.csv` file into the upload dropzone.
* **SHA-256 File Hash Check**: If the exact file content was uploaded earlier, the system displays an alert showing the previous batch ID, upload timestamp, and uploader name. You can either cancel or toggle **Confirm Duplicate Upload** to proceed.
* Click **Continue to Preview**.

#### Step 2: Interactive Preview & Validation
* The preview screen displays the first 20 rows of your file with real-time validation badges:
  * **VALID (Green)**: Row is verified and ready for ingestion.
  * **WARNING (Yellow)**: Non-blocking issue (e.g. Vin not 17 characters, date > 90 days old, or unmapped service type). Row will import successfully.
  * **ERROR (Red)**: Critical defect (e.g. missing Job Card No, invalid mobile number, unknown branch, or negative amount).
* **Header Mapping Grid**: Displays detected columns vs internal fields with auto-mapped confidence.
* Click **Confirm & Import Calls**.

#### Step 3: Ingestion Results & Allocation Summary
* The result panel displays real-time execution statistics:
  * **Total Rows Processed**
  * **Successfully Created Job Cards**
  * **Follow-up Queues Created** (PSF + Hyundai 15-day Happiness Calling)
  * **Duplicates Skipped** (Differentiates **Identical** vs **Different** duplicate data)
  * **Errors Flagged**
  * **New Inactive Placeholder Advisors Created**: Any advisor name in the file not found in the user directory is automatically provisioned as an inactive user (`is_active=False`) with role `SERVICE_ADVISOR`, ensuring advisor performance reports function without data gaps.
  * **Unmapped Service Types**: Notifies admins of any service type not found in dropdown masters so it can be added to masters.
  * **Per-CRE Call Allocation Breakdown**: Shows exact number of calls assigned to each present CRE.

---

### 10.4 Downloading & Fixing the Excel Error Report

When an uploaded file contains invalid rows, the batch **continues processing valid rows** while isolating failures into a downloadable report.

1. On the Import Result screen, click the red **Download Error Report (.xlsx)** button.
2. The generated spreadsheet contains 6 standardized columns:
   * **Row Number**: The exact Excel row index from your uploaded file.
   * **Job Card No**: Job Card / RO identifier (or `N/A` if missing).
   * **Column**: Defective source column header.
   * **Rejected Value**: The raw invalid cell value extracted from the file.
   * **Reason**: Explanation of the validation rule failure.
   * **Fix Hint**: Concrete instructions on how to correct the data in your source DMS.

#### Sample Error Report Representation:
| Row Number | Job Card No | Column | Rejected Value | Reason | Fix Hint |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **4** | `JC-HYUN-004` | Contact Number | `987654321` | Invalid contact number '987654321': must be 10 digits starting with 6-9 | Enter a valid 10-digit Indian mobile number (e.g. 9876543210) |
| **7** | `JC-HYUN-007` | Branch | `Bangalore South Outlet` | Unknown Branch 'Bangalore South Outlet' | Check branch spelling against dealership masters in Admin Console |
| **12** | `JC-HYUN-012` | Branch | `TATA MOTORS BELLARY` | Branch 'TATA MOTORS BELLARY' does not belong to Brand 'Hyundai' | Ensure branch belongs to the selected OEM brand |
| **15** | *N/A* | Job Card No | `None` | Missing required Job Card Number | Each row must specify a valid Job Card No |
| **19** | `JC-HYUN-019` | Total Service Amount | `-450.00` | Amount cannot be negative ('-450.00') | Enter a positive billed amount or 0.0 for warranty claims |
| **23** | `JC-HYUN-023` | Job Card Date | `32-13-2026` | Unparseable Job Card Date '32-13-2026' | Use date format DD-MM-YYYY (e.g. 01-11-2026) |

#### Common Fix Procedures:
* **Scientific Phone Numbers (`9.48E+09`)**: The importer automatically converts standard Excel exponential floats back into 10-digit strings. If an unrecoverable corrupted string is present, re-type the mobile number as plain text.
* **Missing Brand / Branch in File**: If your DMS export does not include Brand and Branch columns, select the fallback **Brand** and **Workshop Branch** from the dropdowns on Step 1.
* **Duplicate Skip vs Update**: If a Job Card was already imported, it is safely skipped by default to avoid duplicate calling queues. If customer details changed, choose **Update Existing** to refresh phone and customer records.
* **Fix and Re-Upload**: After fixing defects in your source spreadsheet, simply re-upload the file. Any previously imported rows will be identified as duplicates and skipped, while newly corrected rows will import and generate call queues seamlessly.


