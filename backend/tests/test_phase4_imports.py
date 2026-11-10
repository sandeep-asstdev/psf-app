import io
import uuid
import pytest
import pandas as pd
from datetime import date
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_dms_import_and_oem_happiness_allocation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Login as Admin
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@apexauto.com", "password": "Admin@12345"},
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Get Brands and Branches
        brands_res = await client.get("/api/v1/masters/brands", headers=headers)
        assert brands_res.status_code == 200
        brands = brands_res.json()
        hyundai = next((b for b in brands if "HYUNDAI" in b["name"].upper()), None)
        mg = next((b for b in brands if "MG" in b["name"].upper()), None)

        branches_res = await client.get("/api/v1/masters/branches", headers=headers)
        assert branches_res.status_code == 200
        branches = branches_res.json()
        branch_id = next(b["id"] for b in branches if b.get("brand_id") == hyundai["id"])
        mg_branch_id = next(b["id"] for b in branches if b.get("brand_id") == mg["id"])

        unique_id = uuid.uuid4().hex[:6]
        hyun_jc = f"JC-HYUN-{unique_id}"
        mg_jc = f"JC-MG-{unique_id}"

        # 3. Create sample CSV data for Hyundai
        csv_content = (
            f"Job Card No,Date,Customer Name,Mobile,Vehicle Reg No,Model,Advisor,Amount\n"
            f"{hyun_jc},2026-11-01,Vikram Mehra,9811223344,DL01AB1234,Creta 1.5,Ramesh SA,4500\n"
        ).encode("utf-8")

        # 4. Test Preview Endpoint
        preview_res = await client.post(
            "/api/v1/imports/preview",
            files={"file": ("hyundai_dms.csv", csv_content, "text/csv")},
            headers=headers,
        )
        assert preview_res.status_code == 200
        preview_data = preview_res.json()
        assert preview_data["total_rows"] == 1
        assert "Job Card No" in preview_data["detected_columns"]
        assert preview_data["suggested_mapping"]["job_card_no"] == "Job Card No"
        assert preview_data["suggested_mapping"]["customer_phone"] == "Mobile"

        # 5. Process Hyundai Import (Expect PSF + 15-day Happiness Calling!)
        column_mapping_json = (
            '{"job_card_no":"Job Card No","job_card_date":"Date","customer_name":"Customer Name",'
            '"customer_phone":"Mobile","reg_no":"Vehicle Reg No","model":"Model",'
            '"service_advisor":"Advisor","total_amount":"Amount"}'
        )

        form_data = {
            "brand_id": hyundai["id"],
            "branch_id": branch_id,
            "column_mapping": column_mapping_json,
            "allocation_mode": "ROUND_ROBIN",
            "duplicate_action": "SKIP",
        }

        process_res = await client.post(
            "/api/v1/imports/upload-and-process",
            data=form_data,
            files={"file": ("hyundai_dms.csv", csv_content, "text/csv")},
            headers=headers,
        )
        assert process_res.status_code == 200
        result = process_res.json()
        assert result["total_rows"] == 1
        assert result["success_rows"] == 1
        assert result["skipped_rows"] == 0
        assert result["queues_created"] == 2  # 1 PSF + 1 Happiness Calling
        assert result["happiness_scheduled"] == 1  # Scheduled exclusively for Hyundai!

        # 6. Test Duplicate Detection (re-upload same row with SKIP)
        dup_form = dict(form_data)
        dup_form["confirm_duplicate_hash"] = "true"
        dup_res = await client.post(
            "/api/v1/imports/upload-and-process",
            data=dup_form,
            files={"file": ("hyundai_dms.csv", csv_content, "text/csv")},
            headers=headers,
        )
        assert dup_res.status_code == 200
        dup_result = dup_res.json()
        assert dup_result["success_rows"] == 0
        assert dup_result["skipped_rows"] == 1

        # 7. Test Non-Hyundai Import (MG Motors: Happiness Calling should be 0!)
        mg_csv_content = (
            f"Job Card No,Date,Customer Name,Mobile,Vehicle Reg No,Model,Advisor,Amount\n"
            f"{mg_jc},2026-11-01,Anil Kapur,9822334455,DL02CD5678,Hector Plus,Kapil SA,6200\n"
        ).encode("utf-8")

        mg_form_data = {
            "brand_id": mg["id"],
            "branch_id": mg_branch_id,
            "column_mapping": column_mapping_json,
            "allocation_mode": "ROUND_ROBIN",
            "duplicate_action": "SKIP",
        }

        mg_res = await client.post(
            "/api/v1/imports/upload-and-process",
            data=mg_form_data,
            files={"file": ("mg_dms.csv", mg_csv_content, "text/csv")},
            headers=headers,
        )
        assert mg_res.status_code == 200
        mg_result = mg_res.json()
        assert mg_result["success_rows"] == 1
        assert mg_result["queues_created"] == 1  # PSF ONLY!
        assert mg_result["happiness_scheduled"] == 0  # NOT scheduled for MG Motors!


@pytest.mark.asyncio
async def test_dms_realtime_webhook():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@apexauto.com", "password": "Admin@12345"},
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        webhook_jc = f"JC-WEBHOOK-{uuid.uuid4().hex[:6]}"

        # Send webhook from DMS
        payload = {
            "brand_code": "HYUN",
            "branch_code": "APEX-CENTRAL",
            "job_card_no": webhook_jc,
            "job_card_date": str(date.today()),
            "customer_name": "Siddharth Malhotra",
            "customer_phone": "9819998877",
            "reg_no": f"HR26EV{uuid.uuid4().hex[:4].upper()}",
            "model": "Ioniq 5 EV",
            "service_advisor": "Vikas Advisor",
            "technician": "Rajesh Technician",
            "service_type": "Periodic Maintenance",
            "total_amount": 12500.0,
            "odometer": 15200,
        }

        webhook_res = await client.post("/api/v1/imports/webhook", json=payload, headers=headers)
        assert webhook_res.status_code == 201
        data = webhook_res.json()
        assert data["status"] == "success"
        assert data["job_card_no"] == webhook_jc
        assert data["happiness_scheduled"] is True
