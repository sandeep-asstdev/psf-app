# Comprehensive Legacy 120-Column AppSheet Mapping to PSF SaaS Architecture

This document maps all 120 columns from the legacy dealership AppSheet Google Sheet (`sample_data - Sheet1.csv`) into the modern PostgreSQL database architecture and Dynamic Questionnaire Engine.

---

## 1. Dropped Legacy Columns & Rationale

The following columns from the legacy spreadsheet are explicitly **dropped** during ingestion and not persisted to database tables:

| Column Index | Column Header | Reason for Dropping |
| :--- | :--- | :--- |
| **5** | `Brand Logo` | AppSheet local image asset path (`PSF_Images/...`). Brands manage logos via central media/S3 upload in platform settings. |
| **67** | `Closure Doc` | AppSheet local filesystem image/pdf path (`PSF_Images/...`). Document attachments are managed via MinIO pre-signed S3 URLs. |
| **70** | `Update Changes` | Redundant counter identical to `Total Attempted` tracking legacy formula recalculations. |
| **77** | `Ather Docs` | AppSheet local filesystem asset path for Ather gate pass PDFs. |
| **94** | `Document (TNPS)` | AppSheet local filesystem asset path for TNPS paperwork. |
| **111** | `8` | Empty spreadsheet column with artifact header name `"8"`. |
| **114** | `9` | Empty spreadsheet column with artifact header name `"9"`. |

---

## 2. Exhaustive 120-Column Mapping Table

| Col Index | Legacy Column Header | Target Entity | Target Field / Question Key | Data Type | Notes & Transformation Rules |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **0** | `Unique ID` | `job_cards` | `external_id` / metadata | `VARCHAR(32)` | 8-char hex AppSheet key |
| **1** | `Uploaded By` | `job_cards` / `import_batches` | `uploaded_by` | `UUIDv7` | Resolved against user accounts |
| **2** | `Upload Timestamp` | `import_batches` | `created_at` | `TIMESTAMPTZ` | Parsed as `dd-mm-yyyy HH:MM:SS` (Asia/Kolkata) |
| **3** | `Brand` | `brands` | `id` | `UUIDv7` | FK to OEM brand (Hyundai, Tata, MG, etc.) |
| **4** | `Branch` | `branches` | `id` | `UUIDv7` | Resolved by name or DMS code |
| **5** | `Brand Logo` | *DROPPED* | — | — | Local AppSheet image path dropped |
| **6** | `Job Card No` | `job_cards` | `job_card_no` | `VARCHAR(60)` | Unique per branch; prefix identifies DMS code (S8211=Hubli, S8827=Gadag) |
| **7** | `Job Card Date` | `job_cards` | `job_card_date` | `DATE` | Standardized ISO date `dd-mm-yyyy` -> `YYYY-MM-DD` |
| **8** | `Customer Name` | `customers` | `name` | `VARCHAR(150)` | Title-cased customer name |
| **9** | `Contact Number` | `customers` | `phone` & `phone_hash` | `VARCHAR(255)` | Encrypted at rest (AES-128-CBC) + HMAC-SHA256 search hash |
| **10** | `Vin No` | `vehicles` | `vin` | `VARCHAR(50)` | 17-char Vehicle Identification Number |
| **11** | `Reg No` | `vehicles` | `reg_no` | `VARCHAR(30)` | Cleaned alphanumeric license plate number |
| **12** | `Model` | `vehicles` | `model` | `VARCHAR(100)` | Vehicle model name (e.g. Creta, i20, Nexon) |
| **13** | `Service Advisor` | `job_cards` | `service_advisor_name` | `VARCHAR(120)` | Stored as text and mapped to user account |
| **14** | `Service Type` | `job_cards` | `service_type` | `VARCHAR(80)` | 1st Free, Paid, Periodic Maintenance, Running Repair |
| **15** | `Total Service Amount`| `job_cards` | `total_amount` | `NUMERIC(12,2)` | Invoiced total service amount |
| **16** | `Calling Date` | `followup_queues`| `due_at` | `TIMESTAMPTZ` | Target call scheduling window |
| **17** | `Call Status` | `calls` / `call_attempts` | `call_status` | `VARCHAR(50)` | Connected, Not Connected |
| **18** | `Case Status` | `calls` / `call_attempts` | `case_status` | `VARCHAR(50)` | Derived from rating band or sentiment state |
| **19** | `VOC` | `calls` / `call_attempts` | `voc` | `TEXT` | Voice of Customer verbatim feedback |
| **20** | `Followed By` | `calls` / `call_attempts` | `called_by_id` | `UUIDv7` | Resolved to CRE caller User ID |
| **21** | `Followup Timestamp` | `calls` / `call_attempts` | `called_at` | `TIMESTAMPTZ` | Dial execution timestamp (Asia/Kolkata) |
| **22** | `Name of CRE` | `followup_queues`| `assigned_to_id` | `UUIDv7` | Assigned CRE queue owner |
| **23** | `Maintenance and Repair Work Done on Car` | `survey_responses.answers` | `rating_generic_maintenance_repair` | `INTEGER` | Generic PSF rating (1-10 or 1-5) |
| **24** | `Whether You Have Availed Pick & Drop Facility? (Yes/No)` | `survey_responses.answers` | `availed_pick_drop` | `VARCHAR(10)` | Normalized: "Yes" / "No" |
| **25** | `Were You Offered Pick Up and Drop or Not?` | `survey_responses.answers` | `offered_pick_drop` | `VARCHAR(10)` | Normalized: "Yes" / "No" |
| **26** | `Were You Contacted by the Workshop Staff for Feedback After Delivery of Vehicle? (Yes/No/Not Aware)` | `survey_responses.answers` | `contacted_feedback_post_delivery` | `VARCHAR(20)` | Normalized: "Yes" / "No" / "Not Aware" |
| **27** | `Whether the Service Advisor Has Opened the Repair Order Through Tablet Device?` | `survey_responses.answers` | `opened_ro_via_tablet` | `VARCHAR(10)` | Normalized: "Yes" / "No" |
| **28** | `How Do You Rate Courtesy & Behaviour of the Person Who Came to Pick & Drop Your Vehicle?` | `survey_responses.answers` | `pick_drop_staff_courtesy` | `VARCHAR(10)` | Normalized: "Yes" / "No" |
| **29** | `Whether the Repair Charges Explained to You Were Reasonable With Respect to Work Done on Your Car?` | `survey_responses.answers` | `charges_explained_reasonable` | `VARCHAR(10)` | Normalized: "Yes" / "No" |
| **30** | `Basis Your Last Service Experience, How Strongly Would You Recommend the Dealer to Your Friends, Relatives, or Colleagues?` | `survey_responses.answers` | `recommend_dealer_friends` | `VARCHAR(10)` | Normalized: "Yes" / "No" |
| **31** | `Did the Service Advisor Offer You the Road Test of Your Car Before Opening the Repair Order (Job Card)?` | `survey_responses.answers` | `road_test_before_ro` | `VARCHAR(10)` | Normalized: "Yes" / "No" |
| **32** | `Did the Service Advisor Offer You a Road Test Before Delivery After Getting the Vehicle Serviced?` | `survey_responses.answers` | `road_test_before_delivery` | `VARCHAR(10)` | Normalized: "Yes" / "No" |
| **33** | `Did the Service Advisor Check the Maintenance History of Your Vehicle?` | `survey_responses.answers` | `checked_maintenance_history` | `VARCHAR(10)` | Normalized: "Yes" / "No" |
| **34** | `Did the Service Advisor Conduct the Vehicle Inspection in Front of You?` | `survey_responses.answers` | `inspection_in_front_of_customer` | `VARCHAR(10)` | Normalized: "Yes" / "No" |
| **35** | `Did You Get the Regular Update on WhatsApp Group for Your Vehicle Status?` | `survey_responses.answers` | `whatsapp_status_updates` | `VARCHAR(10)` | Normalized: "Yes" / "No" |
| **36** | `Were You Offered Water Bottle During Your Visit to the Workshop? (Yes/No/Not Aware/NA)` | `survey_responses.answers` | `offered_water_bottle` | `VARCHAR(20)` | Normalized: "Yes" / "No" / "Not Aware" |
| **37** | `Did the Service Advisor Explain the Parts Repaired and Work Performed?` | `survey_responses.answers` | `explained_parts_repaired_work` | `VARCHAR(10)` | Normalized: "Yes" / "No" |
| **38** | `After Completion of the Service or Repair, Did You Receive Your Car Back on the Same Day?` | `survey_responses.answers` | `car_returned_same_day` | `VARCHAR(10)` | Normalized: "Yes" / "No" |
| **39** | `Was the Service Advisor Polite and Courteous During Interaction?` | `survey_responses.answers` | `advisor_polite_courteous` | `VARCHAR(10)` | Normalized: "Yes" / "No" |
| **40** | `Was the Restroom Maintained Neat and Clean?` | `survey_responses.answers` | `restroom_neat_clean` | `VARCHAR(10)` | Normalized: "Yes" / "No" |
| **41** | `How Would You Rate the Workshop Support for Insurance Claim Processing?` | `survey_responses.answers` | `insurance_claim_support_rating` | `VARCHAR(10)` | Normalized: "Yes" / "No" |
| **42** | `Did You Get the Proper Response from Dealer Staff When You Visited the Workshop?` | `survey_responses.answers` | `proper_response_dealer_staff` | `VARCHAR(10)` | Normalized: "Yes" / "No" |
| **43** | `Did the Service Advisor Explain the Parts Replaced and Charges Taken at the Time of Delivery?` | `survey_responses.answers` | `explained_parts_replaced_charges` | `VARCHAR(10)` | Normalized: "Yes" / "No" |
| **44** | `Did the Service Advisor Walk You Out With the Statement Enjoy Your Driving with Hyundai?` | `survey_responses.answers` | `walk_out_hyundai_statement` | `VARCHAR(10)` | Normalized: "Yes" / "No" |
| **45** | `How Would You Rate the Maintenance & Repair Work Done on Your Car?` | `survey_responses.answers` | `rating_maintenance_repair_work` | `INTEGER` | Rating (1-10) |
| **46** | `How Would You Rate the Condition or Cleanliness of Your Car, on Return?` | `survey_responses.answers` | `rating_cleanliness_on_return` | `INTEGER` | Rating (1-10) |
| **47** | `How Would You Rate the Explanation Given by Service Advisor on the Work Done of Your Car?` | `survey_responses.answers` | `rating_explanation_by_advisor` | `INTEGER` | Rating (1-10) |
| **48** | `How Would You Rate Your Overall Interaction & Experience with Workshop?` | `survey_responses.answers` | `rating_overall_interaction_experience` | `INTEGER` | Rating (1-10) |
| **49** | `Whether the Vehicle Was Picked & Dropped as per Committed Time?` | `survey_responses.answers` | `rating_pick_drop_committed_time` | `INTEGER` | Rating (1-10) |
| **50** | `How Would You Rate the Service Delivery Process of Your Car After Servicing?` | `survey_responses.answers` | `rating_service_delivery_process` | `INTEGER` | Rating (1-10) |
| **51** | `How Would You Rate the Overall Cleanliness of Dealer Facility?` | `survey_responses.answers` | `rating_cleanliness_dealer_facility` | `INTEGER` | Rating (1-10) |
| **52** | `How Would You Rate the Quality of Denting, Painting and Finishing of Repairs Carried Out in the Car?` | `survey_responses.answers` | `rating_denting_painting_quality` | `INTEGER` | Rating (1-10) |
| **53** | `How Would You Rate the Ambience and Hygiene of Customer Interaction Area in the Workshop?` | `survey_responses.answers` | `rating_ambience_hygiene_customer_area` | `INTEGER` | Rating (1-10) |
| **54** | `Did the Service Advisor Inform You About the Promised Delivery Date and Time of Your Car?` | `survey_responses.answers` | `rating_informed_promised_delivery_time` | `INTEGER` | Rating (1-10) |
| **55** | `Condition of Cleanliness of the Car` | `survey_responses.answers` | `rating_generic_cleanliness` | `INTEGER` | Generic PSF rating |
| **56** | `Explanation Given by Service Advisor on Work Done and Repair Charges After Servicing` | `survey_responses.answers` | `rating_generic_explanation_charges` | `INTEGER` | Generic PSF rating |
| **57** | `Delivery Process` | `survey_responses.answers` | `rating_generic_delivery_process` | `INTEGER` | Generic PSF rating |
| **58** | `Cleanliness of Dealer Facility` | `survey_responses.answers` | `rating_generic_facility_cleanliness` | `INTEGER` | Generic PSF rating |
| **59** | `Overall Interaction and Experience with Workshop` | `survey_responses.answers` | `rating_generic_overall_experience` | `INTEGER` | Generic PSF rating |
| **60** | `After Service Vehicle Condition` | `survey_responses.answers` | `rating_generic_after_service_condition` | `INTEGER` | Generic PSF rating |
| **61** | `Fairness of Charges` | `survey_responses.answers` | `rating_generic_fairness_charges` | `INTEGER` | Generic PSF rating |
| **62** | `Payment Confirmation` | `survey_responses.answers` | `rating_generic_payment_confirmation` | `INTEGER` | Generic PSF rating |
| **63** | `How Would You Rate or Recommend to Your Family & Friends?` | `survey_responses.answers` | `rating_generic_recommend_family_friends` | `INTEGER` | Generic PSF rating |
| **64** | `Complaints` | `complaints` | `description` | `TEXT` | Customer complaint narrative |
| **65** | `Complaint Categories` | `complaints` | `category_id` | `UUIDv7` | Resolved against 14 clean complaint categories |
| **66** | `Complaint Closure` | `complaints` / `complaint_events` | `resolution_remarks` / `remarks` | `TEXT` | Closer action taken remarks |
| **67** | `Closure Doc` | *DROPPED* | — | — | AppSheet local filesystem path dropped |
| **68** | `Total Attempted` | `followup_queues` / `call_attempts` | `attempts` / attempt reconstruction | `INTEGER` | Reconstructed into individual attempt records |
| **69** | `Total Contacted` | `followup_queues` | `contacted_count` | `INTEGER` | Number of successful contacts |
| **70** | `Update Changes` | *DROPPED* | — | — | Redundant counter identical to attempted |
| **71** | `Updated By` | `complaints` | `resolved_by_id` / `closed_by_id` | `UUIDv7` | Complaint closer user (e.g. Deepa Hiremath) |
| **72** | `Updated Timestamp` | `complaints` | `resolved_at` / `closed_at` | `TIMESTAMPTZ` | Timestamp of complaint resolution |
| **73** | `Alt Contact Number` | `customers` | `alt_phone` | `VARCHAR(255)` | Encrypted at rest (AES-128-CBC) |
| **74** | `Current Status` | `complaints` | `status` | `VARCHAR(40)` | "Closed in Time" / "Closed Late" / "Open" |
| **75** | `Technician` | `job_cards` | `technician_name` | `VARCHAR(120)` | Assigned service technician |
| **76** | `Where all the jobs requested by you done up to your satisfaction?` | `survey_responses.answers` | `ather_jobs_satisfaction` | `VARCHAR(10)` | Brand survey question (Ather) |
| **77** | `Ather Docs` | *DROPPED* | — | — | AppSheet local filesystem asset path |
| **78** | `Taking everything into consideration, how likely are you to recommend JSW MG Brand to your Family or friends?` | `survey_responses.answers` | `mg_recommend_brand_nps` | `INTEGER` | MG OEM NPS rating (0-10) |
| **79** | `How likely are you to recommend MG Workshop from where you got your vehicle serviced, to your Family or friend ?` | `survey_responses.answers` | `mg_recommend_workshop_nps` | `INTEGER` | MG Workshop NPS rating (0-10) |
| **80** | `What specific improvement areas would make you recommend dealer?` | `survey_responses.answers` | `mg_improvement_areas` | `TEXT` | MG feedback text |
| **81** | `How would you rate the Service advisor assigned at the Workshop for your car?` | `survey_responses.answers` | `mg_advisor_rating` | `INTEGER` | MG SA rating (1-5) |
| **82** | `Could you please tell us the specific reasons for this rating` | `survey_responses.answers` | `mg_advisor_reasons` | `TEXT` | Root cause justification text |
| **83** | `How would you rate the overall process of handing over the car for service and taking the delivery` | `survey_responses.answers` | `mg_handover_rating` | `INTEGER` | MG delivery rating (1-5) |
| **84** | `Could you please tell us the specific reasons for this rating?` | `survey_responses.answers` | `mg_handover_reasons` | `TEXT` | Root cause justification text |
| **85** | `Was the work to be done and any applicable charges, explained to you before taking the car in for service` | `survey_responses.answers` | `mg_work_charges_explained_before` | `VARCHAR(10)` | Normalized: "Yes" / "No" |
| **86** | `Could you pls elaborate that what did not happen at the workshop?` | `survey_responses.answers` | `mg_charges_explanation_notes` | `TEXT` | Feedback detail |
| **87** | `Were all the jobs requested or issues informed by you resolved in the 1st attempt itself?` | `survey_responses.answers` | `mg_first_attempt_resolution` | `VARCHAR(10)` | Normalized: "Yes" / "No" |
| **88** | `Could you pls elaborate what did not happen as per expectation at workshop?` | `survey_responses.answers` | `mg_first_attempt_reasons` | `TEXT` | First attempt failure reasons |
| **89** | `TNPS Followed By` | `tnps_calls` | `conducted_by_id` | `UUIDv7` | TNPS caller user |
| **90** | `TNPS Followed Timestamp` | `tnps_calls` | `called_at` | `TIMESTAMPTZ` | TNPS dial timestamp |
| **91** | `TNPS Call Status` | `tnps_calls` | `call_status` | `VARCHAR(50)` | Connected / Not Connected |
| **92** | `TNPS VOC` | `tnps_calls` | `voc` | `TEXT` | TNPS verbatim feedback |
| **93** | `TNPS Ratings` | `tnps_calls` | `brand_recommend_score` | `INTEGER` | TNPS score (0-10) |
| **94** | `Document (TNPS)` | *DROPPED* | — | — | AppSheet local filesystem asset path |
| **95** | `TNPS Date` | `followup_queues`| `scheduled_tnps_date` | `DATE` | Scheduled TNPS date (typically T+7 days after PSF) |
| **96** | `Followed By Advisor` | `advisor_calls` | `advisor_id` | `UUIDv7` | Service Advisor User ID |
| **97** | `Timestamp` | `advisor_calls` | `called_at` | `TIMESTAMPTZ` | Advisor follow-up timestamp |
| **98** | `Adv Call Status` | `advisor_calls` | `adv_call_status` | `VARCHAR(50)` | Connected, Call Later |
| **99** | `Adv Case Status` | `advisor_calls` | `adv_case_status` | `VARCHAR(50)` | Resolved, Vehicle Revisiting |
| **100** | `Adv VOC` | `advisor_calls` | `adv_voc` | `TEXT` | Advisor verbatim notes |
| **101** | `Adv Status` | `advisor_calls` | `adv_status` | `VARCHAR(40)` | CLOSED, IN_PROGRESS |
| **102** | `Reconfirmation Date` | `reconfirmations` | `reconfirmation_date` | `TIMESTAMPTZ` | Date of closure verification call |
| **103** | `Reconfirmation Done By` | `reconfirmations` | `conducted_by_id` | `UUIDv7` | CRE conducting reconfirmation |
| **104** | `Reconfirmation Status` | `reconfirmations` | `status` | `VARCHAR(40)` | SATISFIED_CLOSED / UNSATISFIED_REOPENED |
| **105** | `Reconfirmation Complaint` | `reconfirmations` | `customer_feedback` | `TEXT` | Customer feedback during reconfirmation |
| **106** | `Status` | `reconfirmations` | `status` | `VARCHAR(40)` | Secondary status field |
| **107** | `Reconfirmation Complaint Closure` | `reconfirmations` | `customer_feedback` | `TEXT` | Closure verification confirmation |
| **108** | `Closed By` | `complaints` | `closed_by_id` | `UUIDv7` | Verification closer user |
| **109** | `Closed Timestamp` | `complaints` | `closed_at` | `TIMESTAMPTZ` | Timestamp when complaint verified closed |
| **110** | `Reconfirmation Call Satus` | `reconfirmations` | `call_status` | `VARCHAR(50)` | Connected / Not Connected |
| **111** | `8` | *DROPPED* | — | — | Empty column named "8" |
| **112** | `Overall Experience` | `survey_responses.answers` | `overall_experience_score` | `INTEGER` | Rating (1-10) |
| **113** | `Timely Delivery` | `survey_responses.answers` | `timely_delivery_score` | `INTEGER` | Rating (1-10) |
| **114** | `9` | *DROPPED* | — | — | Empty column named "9" |
| **115** | `Responsiveness of Advisor` | `survey_responses.answers` | `advisor_responsiveness_score` | `INTEGER` | Rating (1-10) |
| **116** | `Quality of Repair` | `survey_responses.answers` | `repair_quality_score` | `INTEGER` | Rating (1-10) |
| **117** | `Vehicle cleanliness & Condition` | `survey_responses.answers` | `cleanliness_condition_score` | `INTEGER` | Rating (1-10) |
| **118** | `Insurance Claim Support (If Applicable  SR Accident)` | `survey_responses.answers` | `insurance_accident_support_score` | `INTEGER` | Rating (1-10) |
| **119** | `Any recommendation` | `survey_responses.answers` | `general_recommendations` | `TEXT` | Verbatim customer comments |

---

## 3. Standard 13-Column Production DMS Import Template

The modern production DMS ingestion interface uses a clean 13-column format representing standard dealership export data from any OEM (Hyundai, Tata Motors, MG, Ather, Mahindra, etc.).

### 3.1 Standard Columns & Entity Mapping

| Column Header | Recognized Header Aliases | Target Entity | Target Database Field | Validation & Normalization Rules | Error / Warning Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Brand** | Make, OEM, Manufacturer | `brands` | `id` (resolved) | Case-insensitive lookup against tenant master brands. | Unknown brand is a **Row Error**. |
| **Branch** | Workshop, Dealership Branch, Location, Outlet | `branches` | `id` (resolved) | Resolved by branch name, code, or DMS code (`S8211`, `S8827`). Branch must belong to the specified brand. | Unknown branch or brand mismatch is a **Row Error**. User must have scope. |
| **Brand Logo** | Logo | *IGNORED* | — | Optional column. Always ignored; logos are loaded dynamically from brand masters. | Safe to include or omit. |
| **Job Card No** | Job Card Number, RO No, RO Number, JC No, Repair Order | `job_cards` | `job_card_no` | Required text identifier. Stripped of extra whitespace. | Missing or blank is a **Row Error**. Existing `(branch_id, job_card_no)` skipped as duplicate. |
| **Job Card Date** | RO Date, JC Date, Bill Date, Invoice Date, Service Date | `job_cards` | `job_card_date` | Supports `DD-MM-YYYY`, `DD/MM/YYYY`, `YYYY-MM-DD`, and Excel serial dates. | Unparseable date is a **Row Error**. Future dates or dates > 90 days old trigger a **Warning**. |
| **Customer Name** | Customer, Cust Name, Client, Owner, Party Name | `customers` | `name` | Trimmed, collapsed spaces, title-cased. Default: "Customer". | Non-fatal. Defaults to "Customer" if blank. |
| **Contact Number** | Mobile No, Mobile Number, Phone, Mobile, Phone Number | `customers` | `phone` (AES-128-CBC) & `phone_hash` (HMAC-SHA256) | Strips spaces, dashes, dots, `+91`, and leading `0`. Safe cell normalizer handles Excel scientific notation (`9.48E+09`). Must be 10 digits starting with 6, 7, 8, or 9. | Invalid phone format or scientific conversion failure is a **Row Error**. |
| **Vin No** | VIN, Chassis, Chassis No, Chassis Number | `vehicles` | `vin` | Uppercase, removed whitespace. Clean alphanumeric text. | Flagged with a **Warning** if length is not 17 characters. |
| **Reg No** | Registration No, Vehicle No, Car No, License Plate | `vehicles` | `reg_no` | Uppercase, spaces/dashes removed. Generated `TEMP-{jc_no}` if missing. | Non-fatal fallback. |
| **Model** | Vehicle Model, Car Model, Model Name | `vehicles` | `model` | Trimmed text string. Default: "Unknown Model". | Non-fatal fallback. |
| **Service Advisor** | Advisor, SA Name, SA, Service Consultant | `job_cards` / `users` | `service_advisor_name` / `service_advisor_id` | Matched against active `SERVICE_ADVISOR` users. If unrecognized, system creates an **inactive placeholder user** (`is_active=False`). | Non-fatal. Creates placeholder user and lists in report. |
| **Service Type** | Type of Service, Job Type, Service Category | `job_cards` | `service_type` | Matched against `service_types` dropdown master (PMS, RR, Bodyshop, General, Warranty). | Unrecognized service type triggers a **Warning** and maps to `Unmapped Service`. |
| **Total Service Amount** | Amount, Total Amount, Bill Amount, Net Amount, Invoice Amount | `job_cards` | `total_amount` | Strips currency symbols (₹, Rs.), commas, spaces. Must be a numeric value $\ge 0$. | Negative amount is a **Row Error**. Empty amounts default to `0.0`. |

### 3.2 System-Generated Audit Fields (Never Read from File)
- **Unique ID**: Auto-generated `UUIDv7` primary key.
- **Uploaded By**: Authenticated user ID extracted from JWT token.
- **Upload Timestamp**: Server-side UTC timestamp (`datetime.now(timezone.utc)`).
- **File Hash**: SHA-256 digest of binary content for idempotent deduplication.

### 3.3 Auto-Generated Follow-Up Campaigns
Upon batch ingestion:
1. **PSF Call Queue**: Created for all OEM brands, scheduled for delivery date + customer calling window.
2. **Hyundai Happiness Calling**: Automatically scheduled for Hyundai vehicles at delivery date + 15 days.
3. **Automatic Equal Allocation**: Unassigned calls are partitioned equally across CREs marked present for the day.
