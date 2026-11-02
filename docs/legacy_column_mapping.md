# Legacy Google AppSheet to PSF SaaS Platform Column Mapping

This document provides an exhaustive, column-by-column migration mapping from the legacy flat Google AppSheet spreadsheet (~130 columns) to the new normalized PostgreSQL database architecture and the Dynamic Questionnaire Engine.

---

## 1. Architectural Transformation Summary

In the legacy Google AppSheet setup, every question from every automotive brand (Hyundai, MG, Ather, etc.) was appended as a flat spreadsheet column. This resulted in:
1. Massive horizontal sparsity (~80% of question columns were empty for any given record).
2. Schema lock-in: modifying or adding a question required editing production table columns and broken AppSheet formula views.
3. Hardcoded formula columns for computing CSAT, NPS, and string labels.

**Modern Architecture Solution**:
- **Normalized Master & Transactional Data**: Core customer, vehicle, branch, job card, and call lifecycle fields are stored in strongly typed, partitioned PostgreSQL tables (`job_cards`, `calls`, `complaints`, etc.).
- **Dynamic Questionnaire Engine**: Brand questions are defined in `questionnaires` and `questions` tables. Captured answers are stored in `survey_responses.answers` as JSONB with GIN indexing and denormalized scores (`csat_score`, `nps_score`, `nps_category`).
- **Encrypted Phone Numbers**: All contact numbers are encrypted with AES/Fernet at rest, with indexed HMAC-SHA256 hashes (`phone_hash`) for O(1) searches.

---

## 2. Exhaustive Column Mapping Table

### 2.1 DMS Ingestion & Vehicle / Customer Metadata

| Legacy AppSheet Column Header | Target Table | Target Field | Data Type | Notes / Transformation |
| :--- | :--- | :--- | :--- | :--- |
| `Job Card No` / `JC_NO` | `job_cards` | `job_card_no` | `VARCHAR(60)` | Unique per branch |
| `Job Card Date` / `JC_DATE` | `job_cards` | `job_card_date` | `DATE` | Standardized ISO-8601 |
| `Customer Name` | `customers` | `name` | `VARCHAR(150)` | Title-cased |
| `Contact No` / `Mobile` | `customers` | `phone` & `phone_hash` | `VARCHAR(255)` | Encrypted at rest; deterministic hash generated |
| `Alternate Mobile` | `customers` | `alt_phone` | `VARCHAR(255)` | Encrypted at rest |
| `Customer Email` | `customers` | `email` | `VARCHAR(150)` | Normalized lowercase |
| `Customer Address` | `customers` | `address` | `VARCHAR(500)` | Address line |
| `City` | `customers` | `city` | `VARCHAR(100)` | Dealership city |
| `Registration No` / `Reg_No` | `vehicles` | `reg_no` | `VARCHAR(30)` | Cleaned alphanumeric (e.g. DL01AB1234) |
| `VIN` / `Chassis No` | `vehicles` | `vin` | `VARCHAR(50)` | Standard 17-char VIN format |
| `Model` | `vehicles` | `model` | `VARCHAR(100)` | Vehicle model (e.g. Creta, ZS EV) |
| `Variant` / `Fuel Type` | `vehicles` | `variant` / `fuel_type`| `VARCHAR(100)` | EV, Petrol, Diesel, CNG |
| `Delivery Date` | `vehicles` | `delivery_date` | `DATE` | Original vehicle purchase date |
| `Service Advisor Name` | `job_cards` | `service_advisor_name`| `VARCHAR(120)` | Stored as text + linked to `service_advisor_id` |
| `Technician Name` | `job_cards` | `technician_name` | `VARCHAR(120)` | Assigned bay technician |
| `Service Type` | `job_cards` | `service_type` | `VARCHAR(80)` | Paid, Free 1/2/3, Running Repair |
| `Total Bill Amount` / `Amount`| `job_cards` | `total_amount` | `NUMERIC(12,2)` | Invoiced total |
| `Odometer Reading` / `KMs` | `job_cards` | `odometer_reading` | `INTEGER` | Current vehicle mileage |
| `Promised Delivery Time` | `job_cards` | `promised_delivery_time`| `TIMESTAMPTZ`| Promised handover slot |
| `Actual Delivery Time` | `job_cards` | `actual_delivery_time`| `TIMESTAMPTZ` | Actual billing/gate pass release |
| `Branch Code` / `Branch Name` | `branches` | `id` (FK in `job_cards`) | `UUIDv7` | Resolved against tenant branch master |
| `Brand` (Hyundai, MG, Ather) | `brands` | `id` (FK in `job_cards`) | `UUIDv7` | Resolved against tenant brand master |
| `DMS Upload Batch ID` | `job_cards` | `import_batch_id` | `UUIDv7` | Links to `import_batches.id` |
| `Uploaded By` | `job_cards` | `uploaded_by_id` | `UUIDv7` | User who ran the Excel import |

---

### 2.2 Calling Queue & Call Execution

| Legacy AppSheet Column Header | Target Table | Target Field | Data Type | Notes / Transformation |
| :--- | :--- | :--- | :--- | :--- |
| `Queue Type` (PSF/Happiness/etc)| `followup_queues`| `queue_type` | `VARCHAR(40)` | Enum: PSF, TNPS, HAPPINESS, RECONFIRMATION |
| `Assigned CRE` | `followup_queues`| `assigned_to_id` | `UUIDv7` | User ID of caller |
| `Queue Due Date` | `followup_queues`| `due_at` | `TIMESTAMPTZ` | Target calling window (e.g. T+2 days) |
| `Call Status` | `calls` | `call_status` | `VARCHAR(50)` | Connected, Not Connected, Busy, Switched Off... |
| `Case Status` | `calls` | `case_status` | `VARCHAR(50)` | Satisfied, Dissatisfied, Complaint Registered... |
| `Customer VOC` / `Remarks` | `calls` | `voc` | `TEXT` | Verbatim customer feedback |
| `Call Attempt Count` | `followup_queues`| `attempts` | `INTEGER` | Incremented automatically on each call log |
| `Contacted Flag` | `followup_queues`| `contacted_count`| `INTEGER` | Incremented when call_status == 'Connected' |
| `Last Call Timestamp` | `followup_queues`| `last_attempt_at`| `TIMESTAMPTZ` | Timestamp of latest dial |
| `Next Followup Date/Time` | `followup_queues`| `next_followup_at`| `TIMESTAMPTZ` | Scheduled callback slot |
| `Call Duration (Seconds)` | `calls` | `duration_seconds`| `INTEGER` | Clocked via Call Console timer |
| `Called Phone Number` | `calls` | `phone_dialed` | `VARCHAR(255)` | Encrypted at rest |
| `Alt Contact Used Flag` | `calls` | `alt_contact_used`| `BOOLEAN` | True if alternate phone was dialed |
| `Call Recording URL` | `calls` | `recording_url` | `VARCHAR(500)` | MinIO/S3 audio file path |

---

### 2.3 Brand-Specific Questionnaire Questions (Dynamic JSONB)

All brand-specific flat columns are transformed into versioned records in `questions` and collected in `survey_responses.answers` (JSONB):

#### Hyundai PSF Survey Columns:
| Legacy AppSheet Column | Questionnaire Key | Target Question Type | Options / Scale |
| :--- | :--- | :--- | :--- |
| `H_Pickup_Drop_Offered` | `hyundai_pickup_drop_offered` | `yes_no_na` | Yes, No, N/A |
| `H_Pickup_Person_Courtesy` | `hyundai_pickup_courtesy` | `rating_5` | 1 (Poor) to 5 (Excellent) |
| `H_Tablet_Repair_Order` | `hyundai_tablet_repair_order` | `yes_no` | Yes, No |
| `H_Maintenance_History_Checked` | `hyundai_history_checked` | `yes_no` | Yes, No |
| `H_Inspection_In_Front` | `hyundai_inspection_in_front` | `yes_no` | Yes, No |
| `H_Road_Test_Before_Repair` | `hyundai_road_test_before` | `yes_no` | Yes, No |
| `H_WhatsApp_Updates_Received` | `hyundai_whatsapp_updates` | `yes_no` | Yes, No |
| `H_Water_Bottle_Offered` | `hyundai_water_bottle_offered`| `yes_no` | Yes, No |
| `H_Parts_Explained_Beforehand` | `hyundai_parts_explained` | `yes_no` | Yes, No |
| `H_Same_Day_Delivery_Achieved` | `hyundai_sameday_delivery` | `yes_no_na` | Yes, No, N/A |
| `H_Advisor_Politeness` | `hyundai_advisor_politeness` | `rating_5` | 1 to 5 stars |
| `H_Restroom_Cleanliness` | `hyundai_restroom_cleanliness`| `rating_5` | 1 to 5 stars |
| `H_Customer_Area_Ambience` | `hyundai_customer_ambience` | `rating_5` | 1 to 5 stars |
| `H_Facility_Cleanliness` | `hyundai_facility_cleanliness`| `rating_5` | 1 to 5 stars |
| `H_Repair_Charges_Reasonable` | `hyundai_repair_charges_reasonable` | `yes_no` | Yes, No |
| `H_Charges_Explained_At_Delivery`| `hyundai_charges_explained_delivery`| `yes_no` | Yes, No |
| `H_Work_Quality` | `hyundai_work_quality` | `rating_5` | 1 to 5 stars |
| `H_Denting_Painting_Quality` | `hyundai_denting_painting_quality` | `rating_5` | 1 to 5 stars (conditional) |
| `H_Car_Cleanliness_Washing` | `hyundai_car_cleanliness` | `rating_5` | 1 to 5 stars |
| `H_Advisor_Explanation_Delivery` | `hyundai_advisor_explanation_delivery`| `yes_no` | Yes, No |
| `H_Road_Test_After_Repair` | `hyundai_road_test_after` | `yes_no` | Yes, No |
| `H_Walkout_Greeting_Enjoy_Driving`| `hyundai_walkout_greeting` | `yes_no` | Yes, No |
| `H_Promised_Delivery_Date_Met` | `hyundai_promised_delivery_met`| `yes_no` | Yes, No |
| `H_Contacted_After_Delivery` | `hyundai_contacted_after_delivery` | `yes_no` | Yes, No |
| `H_Insurance_Claim_Support` | `hyundai_insurance_claim_support` | `rating_5` | 1 to 5 stars (conditional) |
| `H_Dealer_Staff_Response` | `hyundai_dealer_staff_response` | `rating_5` | 1 to 5 stars |
| `H_Recommend_Hyundai_Dealer` | `hyundai_recommend_dealer` | `nps_10` | 0 (Not likely) to 10 (Very likely) |
| `H_Overall_Experience` | `hyundai_overall_experience` | `rating_5` | 1 (Poor) to 5 (Delighted) |

#### MG Motors PSF & TNPS Survey Columns:
| Legacy AppSheet Column | Questionnaire Key | Target Question Type | Options / Scale |
| :--- | :--- | :--- | :--- |
| `MG_Recommend_Brand_NPS` | `mg_recommend_brand_nps` | `nps_10` | 0–10 Net Promoter score |
| `MG_Recommend_Workshop_NPS` | `mg_recommend_workshop_nps`| `nps_10` | 0–10 Net Promoter score |
| `MG_Handover_Delivery_Rating` | `mg_handover_rating` | `rating_5` | 1–5 stars |
| `MG_Handover_Improvement_Reason`| `mg_handover_reasons` | `text` | Shown if handover <= 3 |
| `MG_Advisor_Rating` | `mg_advisor_rating` | `rating_5` | 1–5 stars |
| `MG_Advisor_Rating_Reason` | `mg_advisor_reasons` | `text` | Shown if advisor <= 3 |
| `MG_Work_Charges_Explained_Prior`| `mg_work_charges_explained_before` | `yes_no` | Yes, No |
| `MG_Jobs_Resolved_First_Attempt` | `mg_first_attempt_resolution` | `yes_no` | Yes, No |
| `MG_First_Attempt_Reasons` | `mg_first_attempt_reasons` | `text` | Shown if resolved == No |
| `MG_Improvement_Areas` | `mg_improvement_areas` | `multi_select` | Cleanliness, Time, Billing, Quality |

#### Ather Energy PSF Survey Columns:
| Legacy AppSheet Column | Questionnaire Key | Target Question Type | Options / Scale |
| :--- | :--- | :--- | :--- |
| `Ather_Jobs_Satisfaction` | `ather_jobs_satisfaction` | `yes_no` | Yes, No |
| `Ather_Charging_Status_Handover`| `ather_charging_status` | `rating_5` | Min 80% State of Charge |
| `Ather_OTA_Update_Explained` | `ather_ota_explained` | `yes_no_na` | Yes, No, N/A |
| `Ather_Gate_Pass_Doc_Upload` | `ather_doc_uploaded` | `text` | S3 document attachment reference |
| `Ather_Workshop_Experience` | `ather_workshop_experience` | `nps_10` | 0–10 scale |

#### Reconfirmation Survey Columns:
| Legacy AppSheet Column | Target Table / Key | Target Field / Question Key | Notes |
| :--- | :--- | :--- | :--- |
| `Reconf_Conducted_Date` | `reconfirmations` | `reconfirmation_date` | Date of verification call |
| `Reconf_Done_By` | `reconfirmations` | `conducted_by_id` | User FK |
| `Reconf_Call_Status` | `reconfirmations` | `call_status` | Connected, Callback... |
| `Reconf_Overall_Experience` | `reconfirmations` | `customer_feedback` | Summary text |
| `Reconf_Closure_Status` | `reconfirmations` | `status` | SATISFIED_CLOSED / UNSATISFIED_REOPENED |
| `Reconf_Closure_Verified` | `reconfirmations` | `closure_verified` | True/False |

---

### 2.4 Complaints, Escalation & Service Advisor Workflows

| Legacy AppSheet Column Header | Target Table | Target Field | Data Type | Notes / Transformation |
| :--- | :--- | :--- | :--- | :--- |
| `Complaint_Flag` (Yes/No) | `complaints` | Row existence in table | `ROW` | Complaint created if customer is dissatisfied |
| `Complaint_Ticket_No` | `complaints` | `complaint_no` | `VARCHAR(50)` | Unique format (e.g. CMP-2026-0001) |
| `Complaint_Category` | `complaints` | `category_id` | `UUIDv7` | Foreign key to `complaint_categories` |
| `Complaint_Severity` | `complaints` | `severity` | `VARCHAR(30)` | LOW, MEDIUM, HIGH, CRITICAL |
| `Complaint_Status` | `complaints` | `status` | `VARCHAR(40)` | OPEN, ASSIGNED, IN_PROGRESS, RESOLVED, CLOSED |
| `Complaint_Description` | `complaints` | `description` | `TEXT` | Customer issue details |
| `Assigned_Manager_Advisor` | `complaints` | `assigned_to_id` | `UUIDv7` | Assigned resolver User ID |
| `SLA_Due_Timestamp` | `complaints` | `sla_due_at` | `TIMESTAMPTZ` | SLA deadline |
| `SLA_Breach_Flag` | `complaints` | `is_sla_breached` | `BOOLEAN` | Auto-set by background timer |
| `Resolution_Remarks` | `complaints` | `resolution_remarks` | `TEXT` | Workshop action taken |
| `Resolved_By` | `complaints` | `resolved_by_id` | `UUIDv7` | Resolver User ID |
| `Resolved_Timestamp` | `complaints` | `resolved_at` | `TIMESTAMPTZ` | Resolution date/time |
| `Closure_Document_Link` | `documents` | `file_url` | `VARCHAR(500)` | Attached photo/invoice in `documents` |
| `Adv_Followed_By` | `advisor_calls` | `advisor_id` | `UUIDv7` | Service Advisor User ID |
| `Adv_Call_Status` | `advisor_calls` | `adv_call_status` | `VARCHAR(50)` | Advisor follow-up call status |
| `Adv_Case_Status` | `advisor_calls` | `adv_case_status` | `VARCHAR(50)` | Case status according to advisor |
| `Adv_VOC` | `advisor_calls` | `adv_voc` | `TEXT` | Advisor notes |
| `Adv_Status` | `advisor_calls` | `adv_status` | `VARCHAR(40)` | Advisor progress state |

---

## 3. Explicitly Dropped Legacy Columns & Justification

The following columns from the legacy Google AppSheet sheet are intentionally **dropped** from the database schema:

| Dropped Legacy Column | Type in AppSheet | Reason for Dropping & Modern Replacement |
| :--- | :--- | :--- |
| `_RowNumber` | AppSheet System | Ephemeral spreadsheet row position; replaced by persistent `UUIDv7` primary keys. |
| `_Computed_Key` / `Key_ID` | Formula Concatenation | Redundant formula combining `[JC_NO]&"-"&[Reg_No]`; replaced by relational FKs and unique composite index `(tenant_id, branch_id, job_card_no)`. |
| `Display_Status_Color` | AppSheet Enum / Color | UI presentation logic hardcoded in data; replaced by Tailwind CSS design tokens in frontend components. |
| `Status_Icon_Formula` | Emoji Formula | E.g. `IF([Status]="Connected", "🟢", "🔴")`; replaced by Lucide SVG icon components in React. |
| `CSAT_Formula_Column` | Virtual Column Formula | Spreadsheets calculated CSAT via unwieldy nested IF statements; replaced by dynamic score calculation in `survey_responses.csat_score` on submission. |
| `NPS_Promoter_Flag` | Formula Column | Replaced by indexed `nps_category` ('PROMOTER', 'PASSIVE', 'DETRACTOR') computed directly from `nps_score`. |
| `Full_Customer_Summary_Label`| Formula Text | Virtual concatenated string used for AppSheet dropdown lists; replaced by TanStack Table customizable cell formatters. |
| `CRE_Shift_Date_Embedded` | Data Redundancy | In AppSheet, CRE shift dates were redundantly pasted across each row; replaced by normalized `login_logs` table tracking actual shift durations. |
| `Google_Drive_Folder_ID` | File Path String | AppSheet Google Drive folder hierarchy; replaced by S3/MinIO bucket keys and CDN pre-signed URLs stored in `documents`. |
