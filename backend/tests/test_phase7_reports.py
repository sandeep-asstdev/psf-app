import pytest
import io
import openpyxl
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_reports_summary_and_excel_export():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Login as Admin
        login_res = await ac.post(
            "/api/v1/auth/login",
            json={"email": "admin@apexauto.com", "password": "Admin@12345"},
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Test Reports Summary Endpoint
        summary_res = await ac.get("/api/v1/reports/summary", headers=headers)
        assert summary_res.status_code == 200
        data = summary_res.json()

        # Verify key sections
        assert "kpis" in data
        assert "trends" in data
        assert "cre_productivity" in data
        assert "advisor_scorecards" in data
        assert "complaint_breakdown" in data
        assert "branch_leaderboard" in data
        assert "funnel" in data

        # Verify KPI structure
        kpis = data["kpis"]
        assert "total_job_cards" in kpis
        assert "average_csat" in kpis
        assert "net_promoter_score" in kpis
        assert "sla_compliance_rate" in kpis

        # Verify Trends
        trends = data["trends"]
        assert len(trends) == 7
        assert "csat_score" in trends[0]
        assert "date_label" in trends[0]

        # Verify Funnel
        assert len(data["funnel"]) == 5
        assert data["funnel"][0]["stage"].startswith("1. DMS")

        # 3. Test Excel Export Endpoint
        excel_res = await ac.get("/api/v1/reports/export/excel", headers=headers)
        assert excel_res.status_code == 200
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in excel_res.headers.get("content-type", "")

        # Verify openpyxl can read the returned workbook
        content_stream = io.BytesIO(excel_res.content)
        wb = openpyxl.load_workbook(content_stream)
        sheet_names = wb.sheetnames
        assert "Executive Summary" in sheet_names
        assert "CRE Productivity" in sheet_names
        assert "Advisor Scorecards" in sheet_names
        assert "Complaint Breakdown" in sheet_names
        assert "Branch Leaderboard" in sheet_names

        ws1 = wb["Executive Summary"]
        assert ws1["A1"].value.startswith("PSF SaaS Platform")
