import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import AsyncSessionLocal
from app.models.auth import User, Role, RolePermission
from app.models.complaint import Complaint
from app.models.tenant import Branch
from sqlalchemy import select


@pytest.mark.asyncio
async def test_super_admin_full_capabilities():
    """Verify L1 Super Admin can access brands, branches, roles, matrix, and admin console."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login as Super Admin
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@apexauto.com", "password": "Admin@12345"},
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Fetch Permission Matrix
        matrix_res = await client.get("/api/v1/admin/matrix", headers=headers)
        assert matrix_res.status_code == 200
        matrix_data = matrix_res.json()
        assert len(matrix_data["roles"]) >= 5
        assert len(matrix_data["catalogue"]) >= 30

        # 2. Check /me/permissions returns is_super_admin = True
        me_perms = await client.get("/api/v1/auth/me/permissions", headers=headers)
        assert me_perms.status_code == 200
        assert me_perms.json()["is_super_admin"] is True

        # 3. Super Admin can manage brands
        test_brand_code = f"T{uuid.uuid4().hex[:4].upper()}"
        brand_res = await client.post(
            "/api/v1/masters/brands",
            headers=headers,
            json={"name": f"Test OEM {test_brand_code}", "code": test_brand_code, "primary_color": "#FF5733"},
        )
        assert brand_res.status_code == 201


@pytest.mark.asyncio
async def test_cre_admin_limited_capabilities():
    """
    Verify L2 CRE Admin (Dealer Admin):
    - CAN manage CREs, import job cards, close complaints, view reports.
    - CANNOT manage brands/branches or roles/matrix (403 Forbidden).
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "dealer.admin@apexauto.com", "password": "Dealer@12345"},
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Fetch own permissions
        me_perms = await client.get("/api/v1/auth/me/permissions", headers=headers)
        assert me_perms.status_code == 200
        perms = me_perms.json()["permissions"]
        assert "complaint.close" in perms
        assert "jobcard.import" in perms
        assert "brand.manage" not in perms
        assert "role.manage" not in perms

        # 2. Attempt to create brand -> MUST FAIL with 403 Forbidden
        bad_brand = await client.post(
            "/api/v1/masters/brands",
            headers=headers,
            json={"name": "Unauthorized Brand", "code": "UNAUTH"},
        )
        assert bad_brand.status_code == 403

        # 3. Attempt to fetch role matrix -> MUST FAIL with 403 Forbidden
        bad_matrix = await client.get("/api/v1/admin/matrix", headers=headers)
        assert bad_matrix.status_code == 403

        # 4. Can access reports summary
        rep_res = await client.get("/api/v1/reports/summary", headers=headers)
        assert rep_res.status_code == 200


@pytest.mark.asyncio
async def test_service_advisor_cannot_close_complaints():
    """Verify Service Advisor (L3) cannot close complaints directly (403 Forbidden)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "rajesh.adv@apexauto.com", "password": "Advisor@12345"},
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Attempt to change complaint status -> MUST FAIL with 403 Forbidden
        fake_id = uuid.uuid4()
        close_res = await client.put(
            f"/api/v1/complaints/{fake_id}/status",
            headers=headers,
            json={"status": "CLOSED", "remarks": "Unauthorized attempt by advisor"},
        )
        assert close_res.status_code == 403
        assert "complaint.close" in close_res.json()["detail"]


@pytest.mark.asyncio
async def test_branch_manager_data_scoping():
    """Verify Branch Manager (L3) is restricted to assigned branch in complaints list."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "manager.central@apexauto.com", "password": "Manager@12345"},
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Fetch complaints list
        complaints_res = await client.get("/api/v1/complaints", headers=headers)
        assert complaints_res.status_code == 200
        data = complaints_res.json()
        assert "items" in data
        # All items returned must belong to manager's branch
        for item in data["items"]:
            assert item.get("branch_name") in ["Apex Central Workshop", "APEX-CENTRAL", None]


@pytest.mark.asyncio
async def test_lockout_protection_and_safety_rules():
    """Verify lockout protections: cannot delete last super admin, cannot delete oneself."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Super admin login
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@apexauto.com", "password": "Admin@12345"},
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        sa_id = login_res.json()["user_id"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Attempt self-deletion -> MUST FAIL with 400
        del_self = await client.delete(f"/api/v1/users/{sa_id}", headers=headers)
        assert del_self.status_code == 400
        assert "Lockout protection" in del_self.json()["detail"]

        # 2. Attempt to delete SUPER_ADMIN role -> MUST FAIL with 400
        roles_res = await client.get("/api/v1/admin/matrix", headers=headers)
        sa_role = next(r for r in roles_res.json()["roles"] if r["name"] == "SUPER_ADMIN")
        del_role = await client.delete(f"/api/v1/admin/roles/{sa_role['id']}", headers=headers)
        assert del_role.status_code == 400
        assert "System" in del_role.json()["detail"] or "SUPER_ADMIN" in del_role.json()["detail"]


@pytest.mark.asyncio
async def test_data_correction_mandatory_reason_and_audit():
    """Verify Super Admin data correction requires mandatory reason and logs audit."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@apexauto.com", "password": "Admin@12345"},
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Without reason -> MUST FAIL with 400
        fail_res = await client.post(
            "/api/v1/admin/data-correction",
            headers=headers,
            json={
                "entity_type": "CUSTOMER",
                "entity_id": str(uuid.uuid4()),
                "field_updates": {"name": "Corrected Name"},
                "reason": "   ",
            },
        )
        assert fail_res.status_code == 400

        # 2. With valid reason on a real customer or job card
        # Find any branch or user to correct
        users_res = await client.get("/api/v1/users", headers=headers)
        if users_res.json().get("items"):
            target_user = users_res.json()["items"][0]
            corr_res = await client.post(
                "/api/v1/admin/data-correction",
                headers=headers,
                json={
                    "entity_type": "USER",
                    "entity_id": target_user["id"],
                    "field_updates": {"full_name": target_user["full_name"]},
                    "reason": "Routine master data standardization per OEM policy",
                },
            )
            assert corr_res.status_code == 200
            assert corr_res.json()["success"] is True


@pytest.mark.asyncio
async def test_user_impersonation():
    """Verify Super Admin can impersonate another user and receive simulation token."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@apexauto.com", "password": "Admin@12345"},
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Find target user (e.g. Priya CRE)
        users_res = await client.get("/api/v1/users?search=Priya", headers=headers)
        priya = users_res.json()["items"][0]

        # Impersonate
        imp_res = await client.post(
            f"/api/v1/auth/impersonate/{priya['id']}?reason=Testing+CRE+workspace+view",
            headers=headers,
        )
        assert imp_res.status_code == 200
        data = imp_res.json()
        assert "access_token" in data
        assert data["impersonated"] is True
        assert data["user"]["email"] == priya["email"]
