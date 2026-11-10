import uuid
import asyncio
import pytest
from datetime import date, datetime, timezone, timedelta, time
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from app.main import app
from app.core.database import AsyncSessionLocal
from app.models.tenant import Tenant, Brand, Branch
from app.models.auth import User, Role, LoginLog, UserScope
from app.models.service import JobCard
from app.models.customer import Customer, Vehicle
from app.models.followup import FollowupQueue
from app.models.allocation import AllocationCursor
from app.services.auth_service import cleanup_stale_login_sessions
from app.services.allocation_service import (
    allocate_queue_items,
    get_present_cres,
    set_attendance_override,
    get_allocation_rules,
    update_allocation_rules,
    preview_rebalance,
    confirm_rebalance,
    undo_allocation_run,
    auto_allocate_on_login,
)


async def create_test_queue_item(db, tenant_id, brand_id, branch_id, cust_name, phone, jc_no, shared_cust=None):
    if not shared_cust:
        cust = Customer(
            tenant_id=tenant_id,
            name=cust_name,
            phone=phone,
            phone_hash=f"hash_{uuid.uuid4().hex}",
        )
        db.add(cust)
        await db.flush()
    else:
        cust = shared_cust

    veh = Vehicle(
        tenant_id=tenant_id,
        brand_id=brand_id,
        customer_id=cust.id,
        reg_no=f"REG-{uuid.uuid4().hex[:6]}",
        model="Test Model",
    )
    db.add(veh)
    await db.flush()

    jc = JobCard(
        tenant_id=tenant_id,
        brand_id=brand_id,
        branch_id=branch_id,
        customer_id=cust.id,
        vehicle_id=veh.id,
        job_card_no=jc_no,
        job_card_date=date(2026, 11, 1),
        total_amount=500.0,
    )
    db.add(jc)
    await db.flush()

    q = FollowupQueue(
        tenant_id=tenant_id,
        job_card_id=jc.id,
        queue_type="PSF",
        status="PENDING",
        due_at=datetime.now(timezone.utc),
        attempts=0,
        assigned_to_id=None,
    )
    db.add(q)
    await db.flush()
    q.job_card = jc
    return q


@pytest.mark.asyncio
async def test_allocation_endpoints_and_present_cres():
    """Test allocation API endpoints: present-cres, rules, override."""
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

        # 1. GET /allocation/rules
        rules_res = await client.get("/api/v1/allocation/rules", headers=headers)
        assert rules_res.status_code == 200
        rules = rules_res.json()
        assert "strategy" in rules
        assert "pool_mode" in rules
        assert "sticky_customers" in rules

        # 2. PUT /allocation/rules
        rules["sticky_customers"] = True
        rules["undo_window_minutes"] = 20
        put_rules_res = await client.put("/api/v1/allocation/rules", json=rules, headers=headers)
        assert put_rules_res.status_code == 200
        assert put_rules_res.json()["undo_window_minutes"] == 20

        # 3. GET /allocation/present-cres
        pres_res = await client.get("/api/v1/allocation/present-cres", headers=headers)
        assert pres_res.status_code == 200
        pres_data = pres_res.json()
        assert "total_eligible" in pres_data
        assert "total_present" in pres_data
        assert isinstance(pres_data["cres"], list)

        # 4. GET /allocation/unallocated
        unalloc_res = await client.get("/api/v1/allocation/unallocated", headers=headers)
        assert unalloc_res.status_code == 200
        assert "total_unallocated" in unalloc_res.json()


@pytest.mark.asyncio
async def test_equal_split_29_items_3_cres():
    """
    Business rule requirement:
    29 items split across 3 present CREs gives 10 / 10 / 9 (counts differ by at most 1).
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@apexauto.com", "password": "Admin@12345"},
        )
        tenant_id = uuid.UUID(login_res.json()["tenant_id"])

    async with AsyncSessionLocal() as db:
        # Reset rules to default EQUAL_PRESENT_CRE
        await update_allocation_rules(
            db, tenant_id,
            {"strategy": "EQUAL_PRESENT_CRE", "pool_mode": "CRE_POOL", "sticky_customers": False, "balance_total_pending": False, "weights": {}}
        )

        # Fetch or create 3 test CREs
        role_stmt = select(Role).where(Role.tenant_id == tenant_id, Role.name.in_(["BRANCH_CRE", "CRE"]))
        cre_role = (await db.execute(role_stmt)).scalars().first()

        test_cres = []
        for i in range(1, 4):
            email = f"test_cre_{i}_{uuid.uuid4().hex[:4]}@apexauto.com"
            user = User(
                tenant_id=tenant_id,
                role_id=cre_role.id,
                email=email,
                hashed_password="hashed_dummy_password",
                full_name=f"Test CRE {i}",
                is_active=True,
            )
            db.add(user)
            await db.flush()
            test_cres.append(user)
            await set_attendance_override(db, tenant_id, user.id, "PRESENT")

        # Mark all other users ABSENT for this test to isolate these 3 CREs
        all_other_users = (await db.execute(
            select(User).where(User.tenant_id == tenant_id, User.id.not_in([u.id for u in test_cres]))
        )).scalars().all()
        for ou in all_other_users:
            await set_attendance_override(db, tenant_id, ou.id, "ABSENT")

        # Fetch Brand & Branch
        brand = (await db.execute(select(Brand).where(Brand.tenant_id == tenant_id))).scalars().first()
        branch = (await db.execute(select(Branch).where(Branch.tenant_id == tenant_id))).scalars().first()

        # Create 29 dummy job cards & followup queues
        queue_items = []
        for i in range(29):
            q = await create_test_queue_item(
                db, tenant_id, brand.id, branch.id,
                f"Customer {i}", f"98765{i:05d}", f"JC-TEST-29-{i}-{uuid.uuid4().hex[:6]}"
            )
            queue_items.append(q)

        # Allocate 29 items
        run = await allocate_queue_items(
            db=db,
            tenant_id=tenant_id,
            queue_items=queue_items,
            run_type="IMPORT_BATCH",
        )

        assert run.allocated_items == 29
        assert run.unallocated_items == 0

        # Check counts per CRE
        counts = [len([q for q in queue_items if q.assigned_to_id == u.id]) for u in test_cres]
        counts.sort(reverse=True)
        assert counts == [10, 10, 9]
        assert max(counts) - min(counts) <= 1


@pytest.mark.asyncio
async def test_cursor_rotation_fairness():
    """
    Test cursor rotation:
    Batch 1: A gets 10, B gets 10, C gets 9 (cursor advances by remainder=2 to index 2, CRE C).
    Batch 2: C gets 10, A gets 10, B gets 9 (A=10, B=9, C=10).
    Batch 3: B gets 10, C gets 10, A gets 9 (A=9, B=10, C=10).
    Over 3 imports, cumulative totals: A=29, B=29, C=29!
    """
    async with AsyncSessionLocal() as db:
        tenant = (await db.execute(select(Tenant))).scalars().first()
        tenant_id = tenant.id
        brand = (await db.execute(select(Brand).where(Brand.tenant_id == tenant_id))).scalars().first()
        branch = (await db.execute(select(Branch).where(Branch.tenant_id == tenant_id))).scalars().first()
        cre_role = (await db.execute(select(Role).where(Role.tenant_id == tenant_id, Role.name.in_(["BRANCH_CRE", "CRE"])))).scalars().first()

        # Reset cursor
        cursor = (await db.execute(select(AllocationCursor).where(AllocationCursor.tenant_id == tenant_id))).scalar_one_or_none()
        if cursor:
            cursor.last_cre_index = 0
            await db.commit()

        # Create 3 isolated test CREs
        test_cres = []
        for i in range(1, 4):
            user = User(
                tenant_id=tenant_id,
                role_id=cre_role.id,
                email=f"rot_cre_{i}_{uuid.uuid4().hex[:4]}@apexauto.com",
                hashed_password="pw",
                full_name=f"Rotation CRE {i}",
                is_active=True,
            )
            db.add(user)
            await db.flush()
            test_cres.append(user)
            await set_attendance_override(db, tenant_id, user.id, "PRESENT")

        # Mark all others ABSENT
        all_other = (await db.execute(
            select(User).where(User.tenant_id == tenant_id, User.id.not_in([u.id for u in test_cres]))
        )).scalars().all()
        for ou in all_other:
            await set_attendance_override(db, tenant_id, ou.id, "ABSENT")

        # Helper for batch of items
        async def make_batch(n: int, prefix: str):
            items = []
            for i in range(n):
                q = await create_test_queue_item(
                    db, tenant_id, brand.id, branch.id,
                    f"Cust {prefix}_{i}", f"9777{prefix[:2]}{i:04d}", f"JC-ROT-{prefix}-{i}-{uuid.uuid4().hex[:4]}"
                )
                items.append(q)
            return items

        # Batch 1: 29 items
        batch1 = await make_batch(29, "b1")
        run1 = await allocate_queue_items(db, tenant_id, batch1, run_type="IMPORT_BATCH")
        c1 = [len([q for q in batch1 if q.assigned_to_id == u.id]) for u in test_cres]

        # Batch 2: 29 items
        batch2 = await make_batch(29, "b2")
        run2 = await allocate_queue_items(db, tenant_id, batch2, run_type="IMPORT_BATCH")
        c2 = [len([q for q in batch2 if q.assigned_to_id == u.id]) for u in test_cres]

        # Batch 3: 29 items
        batch3 = await make_batch(29, "b3")
        run3 = await allocate_queue_items(db, tenant_id, batch3, run_type="IMPORT_BATCH")
        c3 = [len([q for q in batch3 if q.assigned_to_id == u.id]) for u in test_cres]

        # Cumulative totals
        total_counts = [c1[i] + c2[i] + c3[i] for i in range(3)]
        # All three CREs receive exactly 29 items across the three runs!
        assert total_counts == [29, 29, 29]


@pytest.mark.asyncio
async def test_equal_split_29_items_2_and_1_cre():
    """Test 29 items with 2 CREs (15/14) and 1 CRE (all 29)."""
    async with AsyncSessionLocal() as db:
        tenant = (await db.execute(select(Tenant))).scalars().first()
        tenant_id = tenant.id
        brand = (await db.execute(select(Brand).where(Brand.tenant_id == tenant_id))).scalars().first()
        branch = (await db.execute(select(Branch).where(Branch.tenant_id == tenant_id))).scalars().first()
        cre_role = (await db.execute(select(Role).where(Role.tenant_id == tenant_id, Role.name.in_(["BRANCH_CRE", "CRE"])))).scalars().first()

        # 2 CREs test
        user_a = User(tenant_id=tenant_id, role_id=cre_role.id, email=f"cre_a_{uuid.uuid4().hex[:4]}@apexauto.com", hashed_password="p", full_name="CRE A", is_active=True)
        user_b = User(tenant_id=tenant_id, role_id=cre_role.id, email=f"cre_b_{uuid.uuid4().hex[:4]}@apexauto.com", hashed_password="p", full_name="CRE B", is_active=True)
        db.add_all([user_a, user_b])
        await db.flush()

        # Mark all others ABSENT, user_a and user_b PRESENT
        all_u = (await db.execute(select(User).where(User.tenant_id == tenant_id))).scalars().all()
        for u in all_u:
            await set_attendance_override(db, tenant_id, u.id, "ABSENT")
        await set_attendance_override(db, tenant_id, user_a.id, "PRESENT")
        await set_attendance_override(db, tenant_id, user_b.id, "PRESENT")

        items_2 = []
        for i in range(29):
            q = await create_test_queue_item(
                db, tenant_id, brand.id, branch.id,
                f"C2_{i}", f"9666{i:06d}", f"JC-2CRE-{i}-{uuid.uuid4().hex[:4]}"
            )
            items_2.append(q)

        run = await allocate_queue_items(db, tenant_id, items_2, run_type="IMPORT_BATCH")
        c_a = len([q for q in items_2 if q.assigned_to_id == user_a.id])
        c_b = len([q for q in items_2 if q.assigned_to_id == user_b.id])
        assert sorted([c_a, c_b]) == [14, 15]

        # 1 CRE test: Mark user_b ABSENT
        await set_attendance_override(db, tenant_id, user_b.id, "ABSENT")
        items_1 = []
        for i in range(29):
            q = await create_test_queue_item(
                db, tenant_id, brand.id, branch.id,
                f"C1_{i}", f"9555{i:06d}", f"JC-1CRE-{i}-{uuid.uuid4().hex[:4]}"
            )
            items_1.append(q)

        run1 = await allocate_queue_items(db, tenant_id, items_1, run_type="IMPORT_BATCH")
        c_a1 = len([q for q in items_1 if q.assigned_to_id == user_a.id])
        assert c_a1 == 29


@pytest.mark.asyncio
async def test_zero_present_cres_and_auto_allocate_on_login():
    """
    Test 0 present CREs -> items stay unallocated.
    When first eligible CRE logs in -> auto_allocate_on_login allocates them!
    """
    async with AsyncSessionLocal() as db:
        tenant = (await db.execute(select(Tenant))).scalars().first()
        tenant_id = tenant.id
        brand = (await db.execute(select(Brand).where(Brand.tenant_id == tenant_id))).scalars().first()
        branch = (await db.execute(select(Branch).where(Branch.tenant_id == tenant_id))).scalars().first()
        cre_role = (await db.execute(select(Role).where(Role.tenant_id == tenant_id, Role.name.in_(["BRANCH_CRE", "CRE"])))).scalars().first()

        # Mark all users ABSENT
        all_u = (await db.execute(select(User).where(User.tenant_id == tenant_id))).scalars().all()
        for u in all_u:
            await set_attendance_override(db, tenant_id, u.id, "ABSENT")

        user_late = User(
            tenant_id=tenant_id,
            role_id=cre_role.id,
            email=f"late_cre_{uuid.uuid4().hex[:4]}@apexauto.com",
            hashed_password="pw",
            full_name="Late CRE",
            is_active=True,
        )
        db.add(user_late)
        await db.flush()
        await set_attendance_override(db, tenant_id, user_late.id, "ABSENT")

        # Create 10 items
        unalloc_items = []
        for i in range(10):
            q = await create_test_queue_item(
                db, tenant_id, brand.id, branch.id,
                f"CZero_{i}", f"9444{i:06d}", f"JC-ZERO-{i}-{uuid.uuid4().hex[:4]}"
            )
            unalloc_items.append(q)

        # Allocate with 0 present CREs
        run = await allocate_queue_items(db, tenant_id, unalloc_items, run_type="IMPORT_BATCH")
        assert run.allocated_items == 0
        assert run.unallocated_items == 10
        for q in unalloc_items:
            assert q.assigned_to_id is None

        # Now mark user_late PRESENT (simulating login shift start)
        await set_attendance_override(db, tenant_id, user_late.id, "PRESENT")

        # Configure IMMEDIATE trigger mode for single-CRE login test
        await update_allocation_rules(
            db, tenant_id,
            {"allocation_trigger_mode": "IMMEDIATE"}
        )

        # Trigger auto_allocate_on_login
        login_run = await auto_allocate_on_login(db, tenant_id, user_late)
        assert login_run is not None
        assert login_run.allocated_items >= 10

        # Verify all 10 items are now assigned to user_late
        for q in unalloc_items:
            await db.refresh(q)
            assert q.assigned_to_id == user_late.id


@pytest.mark.asyncio
async def test_sticky_customers_bundled():
    """
    Test sticky customers:
    Job cards with the same customer phone in the same batch must go to the same CRE.
    """
    async with AsyncSessionLocal() as db:
        tenant = (await db.execute(select(Tenant))).scalars().first()
        tenant_id = tenant.id
        brand = (await db.execute(select(Brand).where(Brand.tenant_id == tenant_id))).scalars().first()
        branch = (await db.execute(select(Branch).where(Branch.tenant_id == tenant_id))).scalars().first()
        cre_role = (await db.execute(select(Role).where(Role.tenant_id == tenant_id, Role.name.in_(["BRANCH_CRE", "CRE"])))).scalars().first()

        # Enable sticky customers
        await update_allocation_rules(db, tenant_id, {"sticky_customers": True})

        cre1 = User(tenant_id=tenant_id, role_id=cre_role.id, email=f"stk1_{uuid.uuid4().hex[:4]}@apexauto.com", hashed_password="p", full_name="Sticky CRE 1", is_active=True)
        cre2 = User(tenant_id=tenant_id, role_id=cre_role.id, email=f"stk2_{uuid.uuid4().hex[:4]}@apexauto.com", hashed_password="p", full_name="Sticky CRE 2", is_active=True)
        db.add_all([cre1, cre2])
        await db.flush()

        all_u = (await db.execute(select(User).where(User.tenant_id == tenant_id))).scalars().all()
        for u in all_u:
            await set_attendance_override(db, tenant_id, u.id, "ABSENT")
        await set_attendance_override(db, tenant_id, cre1.id, "PRESENT")
        await set_attendance_override(db, tenant_id, cre2.id, "PRESENT")

        # Same customer with 3 vehicles/job cards
        shared_phone = "9111222333"
        cust_shared = Customer(tenant_id=tenant_id, name="Shared Cust", phone=shared_phone, phone_hash=f"h_{uuid.uuid4().hex}")
        db.add(cust_shared)
        await db.flush()

        items = []
        for i in range(3):
            q = await create_test_queue_item(
                db, tenant_id, brand.id, branch.id,
                "Shared Cust", shared_phone, f"JC-SHARED-{i}-{uuid.uuid4().hex[:4]}",
                shared_cust=cust_shared
            )
            items.append(q)

        # Plus 3 distinct other customers
        for i in range(3):
            q = await create_test_queue_item(
                db, tenant_id, brand.id, branch.id,
                f"Other Cust {i}", f"922233344{i}", f"JC-OTHER-{i}-{uuid.uuid4().hex[:4]}"
            )
            items.append(q)

        run = await allocate_queue_items(db, tenant_id, items, run_type="IMPORT_BATCH")
        # Check all 3 shared customer job cards
        shared_assigned = [q.assigned_to_id for q in items[:3]]
        # They must ALL be assigned to the same CRE!
        assert len(set(shared_assigned)) == 1
        assert shared_assigned[0] in [cre1.id, cre2.id]


@pytest.mark.asyncio
async def test_rebalance_preview_and_confirm_untouched_only():
    """
    Test Rebalance:
    Only untouched calls (attempts == 0, status == 'PENDING') are moved.
    Calls already attempted or in progress never move!
    """
    async with AsyncSessionLocal() as db:
        tenant = (await db.execute(select(Tenant))).scalars().first()
        tenant_id = tenant.id
        brand = (await db.execute(select(Brand).where(Brand.tenant_id == tenant_id))).scalars().first()
        branch = (await db.execute(select(Branch).where(Branch.tenant_id == tenant_id))).scalars().first()
        cre_role = (await db.execute(select(Role).where(Role.tenant_id == tenant_id, Role.name.in_(["BRANCH_CRE", "CRE"])))).scalars().first()

        cre_early = User(tenant_id=tenant_id, role_id=cre_role.id, email=f"reb_early_{uuid.uuid4().hex[:4]}@apexauto.com", hashed_password="p", full_name="Early CRE", is_active=True)
        cre_late = User(tenant_id=tenant_id, role_id=cre_role.id, email=f"reb_late_{uuid.uuid4().hex[:4]}@apexauto.com", hashed_password="p", full_name="Late CRE", is_active=True)
        db.add_all([cre_early, cre_late])
        await db.flush()

        all_u = (await db.execute(select(User).where(User.tenant_id == tenant_id))).scalars().all()
        for u in all_u:
            await set_attendance_override(db, tenant_id, u.id, "ABSENT")

        # cre_early is present and gets 10 calls
        await set_attendance_override(db, tenant_id, cre_early.id, "PRESENT")

        batch = []
        for i in range(10):
            q = await create_test_queue_item(
                db, tenant_id, brand.id, branch.id,
                f"RebCust_{i}", f"9333{i:06d}", f"JC-REB-{i}-{uuid.uuid4().hex[:4]}"
            )
            batch.append(q)

        await allocate_queue_items(db, tenant_id, batch, run_type="IMPORT_BATCH")
        for q in batch:
            assert q.assigned_to_id == cre_early.id

        # cre_early attempts 2 calls (attempt count = 1, status = 'CONNECTED')
        batch[0].attempts = 1
        batch[0].status = "CONNECTED"
        batch[1].attempts = 1
        batch[1].status = "CONNECTED"
        await db.commit()

        # Now cre_late arrives and is marked PRESENT
        await set_attendance_override(db, tenant_id, cre_late.id, "PRESENT")

        # Preview rebalance: 8 untouched calls should be divided 4 and 4
        preview = await preview_rebalance(db, tenant_id)
        assert preview["total_movable_calls"] == 8
        assert preview["present_cre_count"] == 2

        # Confirm rebalance
        conf = await confirm_rebalance(db, tenant_id, cre_early.id)
        assert conf.run_type == "REBALANCE"
        assert conf.allocated_items == 8

        # The 2 attempted calls MUST remain with cre_early
        await db.refresh(batch[0])
        await db.refresh(batch[1])
        assert batch[0].assigned_to_id == cre_early.id
        assert batch[1].assigned_to_id == cre_early.id

        # Untouched calls divided 4 and 4 between cre_early and cre_late
        cre_early_untouched = [q for q in batch[2:] if (await db.refresh(q) or True) and q.assigned_to_id == cre_early.id]
        cre_late_untouched = [q for q in batch[2:] if q.assigned_to_id == cre_late.id]
        assert len(cre_early_untouched) == 4
        assert len(cre_late_untouched) == 4


@pytest.mark.asyncio
async def test_undo_allocation_run_and_safety():
    """
    Test Undo Allocation:
    1. Undo works within time window if no calls attempted.
    2. Undo fails if any call in batch has an attempt recorded.
    """
    async with AsyncSessionLocal() as db:
        tenant = (await db.execute(select(Tenant))).scalars().first()
        tenant_id = tenant.id
        brand = (await db.execute(select(Brand).where(Brand.tenant_id == tenant_id))).scalars().first()
        branch = (await db.execute(select(Branch).where(Branch.tenant_id == tenant_id))).scalars().first()
        cre_role = (await db.execute(select(Role).where(Role.tenant_id == tenant_id, Role.name.in_(["BRANCH_CRE", "CRE"])))).scalars().first()

        cre_undo = User(tenant_id=tenant_id, role_id=cre_role.id, email=f"undo_{uuid.uuid4().hex[:4]}@apexauto.com", hashed_password="p", full_name="Undo CRE", is_active=True)
        db.add(cre_undo)
        await db.flush()

        all_u = (await db.execute(select(User).where(User.tenant_id == tenant_id))).scalars().all()
        for u in all_u:
            await set_attendance_override(db, tenant_id, u.id, "ABSENT")
        await set_attendance_override(db, tenant_id, cre_undo.id, "PRESENT")

        batch = []
        for i in range(5):
            q = await create_test_queue_item(
                db, tenant_id, brand.id, branch.id,
                f"UndoCust_{i}", f"9000{i:06d}", f"JC-UNDO-{i}-{uuid.uuid4().hex[:4]}"
            )
            batch.append(q)

        run = await allocate_queue_items(db, tenant_id, batch, run_type="IMPORT_BATCH")
        assert run.allocated_items == 5

        # Undo successfully
        undo_result = await undo_allocation_run(db, tenant_id, run.id, cre_undo.id)
        assert undo_result["reverted_count"] == 5
        for q in batch:
            await db.refresh(q)
            assert q.assigned_to_id is None

        # Re-allocate
        run2 = await allocate_queue_items(db, tenant_id, batch, run_type="IMPORT_BATCH")
        # Now mark 1 attempt on one item
        batch[0].attempts = 1
        await db.commit()

        # Trying to undo run2 must raise 400 HTTPException
        with pytest.raises(HTTPException) as excinfo:
            await undo_allocation_run(db, tenant_id, run2.id, cre_undo.id)
        assert excinfo.value.status_code == 400
        assert "already been attempted" in excinfo.value.detail


@pytest.mark.asyncio
async def test_auto_allocation_defers_when_below_min_present_cres():
    """
    Test that when allocation_trigger_mode == 'WHEN_MIN_PRESENT' and min_present_cres == 2,
    if only 1 CRE is present, allocation is deferred (returns None).
    When the 2nd CRE becomes present and logs in, allocation triggers and divides calls!
    """
    async with AsyncSessionLocal() as db:
        tenant = (await db.execute(select(Tenant))).scalars().first()
        tenant_id = tenant.id
        brand = (await db.execute(select(Brand).where(Brand.tenant_id == tenant_id))).scalars().first()
        branch = (await db.execute(select(Branch).where(Branch.tenant_id == tenant_id))).scalars().first()
        cre_role = (await db.execute(select(Role).where(Role.tenant_id == tenant_id, Role.name.in_(["BRANCH_CRE", "CRE"])))).scalars().first()

        # Mark all users ABSENT
        all_u = (await db.execute(select(User).where(User.tenant_id == tenant_id))).scalars().all()
        for u in all_u:
            await set_attendance_override(db, tenant_id, u.id, "ABSENT")

        # Set rules: WHEN_MIN_PRESENT, min_present_cres = 2
        await update_allocation_rules(
            db, tenant_id,
            {
                "strategy": "EQUAL_PRESENT_CRE",
                "pool_mode": "CRE_POOL",
                "allocation_trigger_mode": "WHEN_MIN_PRESENT",
                "min_present_cres": 2,
            }
        )

        cre_1 = User(
            tenant_id=tenant_id,
            role_id=cre_role.id,
            email=f"defer_cre_1_{uuid.uuid4().hex[:4]}@apexauto.com",
            hashed_password="p",
            full_name="Defer CRE 1",
            is_active=True,
        )
        cre_2 = User(
            tenant_id=tenant_id,
            role_id=cre_role.id,
            email=f"defer_cre_2_{uuid.uuid4().hex[:4]}@apexauto.com",
            hashed_password="p",
            full_name="Defer CRE 2",
            is_active=True,
        )
        db.add_all([cre_1, cre_2])
        await db.flush()

        await set_attendance_override(db, tenant_id, cre_1.id, "ABSENT")
        await set_attendance_override(db, tenant_id, cre_2.id, "ABSENT")

        # Create 6 unallocated calls
        items = []
        for i in range(6):
            q = await create_test_queue_item(
                db, tenant_id, brand.id, branch.id,
                f"CustDefer_{i}", f"9333{i:06d}", f"JC-DEFER-{i}-{uuid.uuid4().hex[:4]}"
            )
            items.append(q)

        # CRE 1 logs in (only 1 present CRE, requirement is 2)
        await set_attendance_override(db, tenant_id, cre_1.id, "PRESENT")
        res1 = await auto_allocate_on_login(db, tenant_id, cre_1)
        assert res1 is None, "Allocation must be deferred when present CREs < min_present_cres"

        # CRE 2 logs in (now 2 present CREs -> satisfies min_present_cres)
        await set_attendance_override(db, tenant_id, cre_2.id, "PRESENT")
        res2 = await auto_allocate_on_login(db, tenant_id, cre_2)
        assert res2 is not None, "Allocation must execute when minimum present CREs threshold is met"
        assert res2.allocated_items >= 6

        # Items should be divided fairly
        for q in items:
            await db.refresh(q)
            assert q.assigned_to_id in [cre_1.id, cre_2.id]


@pytest.mark.asyncio
async def test_auto_allocation_defers_when_before_scheduled_time():
    """
    Test that when allocation_trigger_mode == 'SCHEDULED_AT_TIME' and scheduled_time is in the future,
    login does not trigger allocation.
    """
    async with AsyncSessionLocal() as db:
        tenant = (await db.execute(select(Tenant))).scalars().first()
        tenant_id = tenant.id
        cre_role = (await db.execute(select(Role).where(Role.tenant_id == tenant_id, Role.name.in_(["BRANCH_CRE", "CRE"])))).scalars().first()

        cre = User(
            tenant_id=tenant_id,
            role_id=cre_role.id,
            email=f"sched_cre_{uuid.uuid4().hex[:4]}@apexauto.com",
            hashed_password="p",
            full_name="Sched CRE",
            is_active=True,
        )
        db.add(cre)
        await db.flush()
        await set_attendance_override(db, tenant_id, cre.id, "PRESENT")

        # Set scheduled_time to 23:59 (far in future today)
        await update_allocation_rules(
            db, tenant_id,
            {
                "allocation_trigger_mode": "SCHEDULED_AT_TIME",
                "scheduled_time": "23:59",
            }
        )

        res = await auto_allocate_on_login(db, tenant_id, cre)
        assert res is None, "Allocation must be deferred when current time is before scheduled_time"


@pytest.mark.asyncio
async def test_end_of_day_stale_session_cleanup():
    """
    Sessions from previous days without logout must be automatically closed
    and not count as present today.
    """
    async with AsyncSessionLocal() as db:
        tenant = (await db.execute(select(Tenant))).scalars().first()
        tenant_id = tenant.id
        cre_role = (await db.execute(select(Role).where(Role.tenant_id == tenant_id, Role.name.in_(["BRANCH_CRE", "CRE"])))).scalars().first()

        stale_user = User(
            tenant_id=tenant_id,
            role_id=cre_role.id,
            email=f"stale_session_{uuid.uuid4().hex[:4]}@apexauto.com",
            hashed_password="p",
            full_name="Stale Session User",
            is_active=True,
        )
        db.add(stale_user)
        await db.flush()

        # Create a login log from yesterday without logout
        yesterday_dt = datetime.now(timezone.utc) - timedelta(days=1)
        yesterday_log = LoginLog(
            tenant_id=tenant_id,
            user_id=stale_user.id,
            login_at=yesterday_dt.replace(hour=9, minute=0, second=0),
            logout_at=None,
            status="LOGGED_IN",
            ip_address="127.0.0.1",
        )
        db.add(yesterday_log)
        await db.commit()

        # Run cleanup_stale_login_sessions
        closed = await cleanup_stale_login_sessions(db, tenant_id=tenant_id)
        assert closed >= 1

        # Check the log in DB
        await db.refresh(yesterday_log)
        assert yesterday_log.logout_at is not None
        assert yesterday_log.status == "AUTO_LOGGED_OUT_EOD"
        assert yesterday_log.duration_seconds is not None

        # Verify get_present_cres does NOT count this user as present
        cres = await get_present_cres(db, tenant_id=tenant_id)
        stale_entry = next((c for c in cres if c["user_id"] == stale_user.id), None)
        assert stale_entry is not None
        assert stale_entry["is_present"] is False
        assert stale_entry["has_active_login"] is False


@pytest.mark.asyncio
async def test_allocate_now_preview_and_confirm():
    """Test CRE Admin 'Allocate Now' button: preview modal and execution."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login as Admin
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@apexauto.com", "password": "Admin@12345"},
        )
        assert login_res.status_code == 200
        headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

        # 1. Preview
        preview_res = await client.post("/api/v1/allocation/allocate-now/preview", headers=headers)
        assert preview_res.status_code == 200
        p_data = preview_res.json()
        assert "total_unallocated_calls" in p_data
        assert "present_cre_count" in p_data
        assert "items" in p_data

        # 2. Confirm (if there are unallocated items and present CREs)
        if p_data["total_unallocated_calls"] > 0 and p_data["present_cre_count"] > 0:
            confirm_res = await client.post("/api/v1/allocation/allocate-now/confirm", headers=headers)
            assert confirm_res.status_code == 200
            c_data = confirm_res.json()
            assert c_data["run_type"] == "MANUAL_ALLOCATE_NOW"
            assert c_data["allocated_items"] > 0


@pytest.mark.asyncio
async def test_cre_admin_cannot_edit_allocation_rules():
    """
    Requirement 7:
    Confirm that CRE Admin cannot edit allocation rules (Super Admin only: 403 Forbidden).
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login as CRE Admin
        cre_admin_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "cre.admin@apexauto.com", "password": "Password@12345"},
        )
        assert cre_admin_login.status_code == 200
        cre_admin_headers = {"Authorization": f"Bearer {cre_admin_login.json()['access_token']}"}

        # Try to update allocation rules as CRE Admin -> Must receive 403 Forbidden
        put_res = await client.put(
            "/api/v1/allocation/rules",
            json={"strategy": "ROUND_ROBIN", "pool_mode": "CRE_POOL"},
            headers=cre_admin_headers,
        )
        assert put_res.status_code == 403
        assert "permission" in put_res.json()["detail"].lower()

        # Login as Super Admin -> Must succeed with 200 OK
        super_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@apexauto.com", "password": "Password@12345"},
        )
        assert super_login.status_code == 200
        super_headers = {"Authorization": f"Bearer {super_login.json()['access_token']}"}

        put_res_super = await client.put(
            "/api/v1/allocation/rules",
            json={"strategy": "EQUAL_PRESENT_CRE", "pool_mode": "CRE_POOL"},
            headers=super_headers,
        )
        assert put_res_super.status_code == 200


@pytest.mark.asyncio
async def test_branch_scoping_isolation():
    """
    Test that a CRE scoped only to Branch A receives 0 items for Branch B
    under pool_mode = 'BRANCH_ONLY'.
    """
    async with AsyncSessionLocal() as db:
        tenant = (await db.execute(select(Tenant))).scalars().first()
        tenant_id = tenant.id
        brand = (await db.execute(select(Brand).where(Brand.tenant_id == tenant_id))).scalars().first()
        branches = (await db.execute(select(Branch).where(Branch.tenant_id == tenant_id))).scalars().all()
        assert len(branches) >= 2
        branch_1, branch_2 = branches[0], branches[1]
        cre_role = (await db.execute(select(Role).where(Role.tenant_id == tenant_id, Role.name.in_(["BRANCH_CRE", "CRE"])))).scalars().first()

        # Mark all users absent
        all_u = (await db.execute(select(User).where(User.tenant_id == tenant_id))).scalars().all()
        for u in all_u:
            await set_attendance_override(db, tenant_id, u.id, "ABSENT")

        # Set BRANCH_ONLY pool mode
        await update_allocation_rules(
            db, tenant_id,
            {"strategy": "BY_BRANCH", "pool_mode": "BRANCH_ONLY", "sticky_customers": False}
        )

        cre_branch1 = User(
            tenant_id=tenant_id,
            role_id=cre_role.id,
            email=f"cre_b1_{uuid.uuid4().hex[:4]}@apexauto.com",
            hashed_password="p",
            full_name="Branch 1 CRE",
            is_active=True,
        )
        cre_branch2 = User(
            tenant_id=tenant_id,
            role_id=cre_role.id,
            email=f"cre_b2_{uuid.uuid4().hex[:4]}@apexauto.com",
            hashed_password="p",
            full_name="Branch 2 CRE",
            is_active=True,
        )
        db.add_all([cre_branch1, cre_branch2])
        await db.flush()

        # Assign scopes
        scope_1 = UserScope(tenant_id=tenant_id, user_id=cre_branch1.id, brand_id=brand.id, branch_id=branch_1.id)
        scope_2 = UserScope(tenant_id=tenant_id, user_id=cre_branch2.id, brand_id=brand.id, branch_id=branch_2.id)
        db.add_all([scope_1, scope_2])
        await db.flush()

        await set_attendance_override(db, tenant_id, cre_branch1.id, "PRESENT")
        await set_attendance_override(db, tenant_id, cre_branch2.id, "PRESENT")

        # Create 5 calls for Branch 1 and 5 calls for Branch 2
        batch = []
        for i in range(5):
            q1 = await create_test_queue_item(db, tenant_id, brand.id, branch_1.id, f"B1Cust_{i}", f"9222{i:06d}", f"JC-B1-{i}-{uuid.uuid4().hex[:4]}")
            batch.append(q1)
        for i in range(5):
            q2 = await create_test_queue_item(db, tenant_id, brand.id, branch_2.id, f"B2Cust_{i}", f"9111{i:06d}", f"JC-B2-{i}-{uuid.uuid4().hex[:4]}")
            batch.append(q2)

        run = await allocate_queue_items(db, tenant_id, batch, run_type="IMPORT_BATCH")

        # Verify CRE 1 gets all calls for Branch 1, and CRE 2 gets all calls for Branch 2
        for q1 in batch[:5]:
            await db.refresh(q1)
            assert q1.assigned_to_id == cre_branch1.id
        for q2 in batch[5:]:
            await db.refresh(q2)
            assert q2.assigned_to_id == cre_branch2.id


@pytest.mark.asyncio
async def test_idempotent_duplicate_import_allocates_zero_new():
    """
    Test that re-importing already assigned / duplicate items allocates 0 new items.
    """
    async with AsyncSessionLocal() as db:
        tenant = (await db.execute(select(Tenant))).scalars().first()
        tenant_id = tenant.id
        brand = (await db.execute(select(Brand).where(Brand.tenant_id == tenant_id))).scalars().first()
        branch = (await db.execute(select(Branch).where(Branch.tenant_id == tenant_id))).scalars().first()
        cre_role = (await db.execute(select(Role).where(Role.tenant_id == tenant_id, Role.name.in_(["BRANCH_CRE", "CRE"])))).scalars().first()

        cre = User(
            tenant_id=tenant_id,
            role_id=cre_role.id,
            email=f"idemp_cre_{uuid.uuid4().hex[:4]}@apexauto.com",
            hashed_password="p",
            full_name="Idemp CRE",
            is_active=True,
        )
        db.add(cre)
        await db.flush()
        await set_attendance_override(db, tenant_id, cre.id, "PRESENT")

        items = []
        for i in range(3):
            q = await create_test_queue_item(db, tenant_id, brand.id, branch.id, f"IdempCust_{i}", f"9001{i:06d}", f"JC-IDEMP-{i}-{uuid.uuid4().hex[:4]}")
            items.append(q)

        # First run allocates all 3
        run1 = await allocate_queue_items(db, tenant_id, items, run_type="IMPORT_BATCH")
        assert run1.allocated_items == 3

        # Re-running allocation with already allocated items allocates 0
        run2 = await allocate_queue_items(db, tenant_id, items, run_type="IMPORT_BATCH")
        assert run2.allocated_items == 0
        assert run2.unallocated_items == 0


@pytest.mark.asyncio
async def test_inactive_users_never_allocated():
    """
    Test that inactive users (is_active = False) are never returned as present
    and never receive call allocations.
    """
    async with AsyncSessionLocal() as db:
        tenant = (await db.execute(select(Tenant))).scalars().first()
        tenant_id = tenant.id
        brand = (await db.execute(select(Brand).where(Brand.tenant_id == tenant_id))).scalars().first()
        branch = (await db.execute(select(Branch).where(Branch.tenant_id == tenant_id))).scalars().first()
        cre_role = (await db.execute(select(Role).where(Role.tenant_id == tenant_id, Role.name.in_(["BRANCH_CRE", "CRE"])))).scalars().first()

        inactive_user = User(
            tenant_id=tenant_id,
            role_id=cre_role.id,
            email=f"inactive_cre_{uuid.uuid4().hex[:4]}@apexauto.com",
            hashed_password="p",
            full_name="Inactive CRE",
            is_active=False,
        )
        active_user = User(
            tenant_id=tenant_id,
            role_id=cre_role.id,
            email=f"active_cre_{uuid.uuid4().hex[:4]}@apexauto.com",
            hashed_password="p",
            full_name="Active CRE",
            is_active=True,
        )
        db.add_all([inactive_user, active_user])
        await db.flush()

        # Inactive user must not appear in eligible present CREs
        cres = await get_present_cres(db, tenant_id)
        assert all(c["user_id"] != inactive_user.id for c in cres)

        # Set active user present
        all_u = (await db.execute(select(User).where(User.tenant_id == tenant_id))).scalars().all()
        for u in all_u:
            await set_attendance_override(db, tenant_id, u.id, "ABSENT")
        await set_attendance_override(db, tenant_id, active_user.id, "PRESENT")

        items = [await create_test_queue_item(db, tenant_id, brand.id, branch.id, "InactCust", "9888000000", f"JC-INACT-{uuid.uuid4().hex[:4]}")]
        run = await allocate_queue_items(db, tenant_id, items, run_type="IMPORT_BATCH")

        await db.refresh(items[0])
        assert items[0].assigned_to_id == active_user.id
        assert items[0].assigned_to_id != inactive_user.id


@pytest.mark.asyncio
async def test_strategies_round_robin_by_branch_manual():
    """
    Test strategies:
    1) ROUND_ROBIN: Sequential item-by-item rotation across present CREs
    2) BY_BRANCH: Strict routing based on branch scopes
    3) MANUAL: Leaves all items unallocated in the pool
    """
    async with AsyncSessionLocal() as db:
        tenant = (await db.execute(select(Tenant))).scalars().first()
        tenant_id = tenant.id
        brand = (await db.execute(select(Brand).where(Brand.tenant_id == tenant_id))).scalars().first()
        branch = (await db.execute(select(Branch).where(Branch.tenant_id == tenant_id))).scalars().first()
        cre_role = (await db.execute(select(Role).where(Role.tenant_id == tenant_id, Role.name.in_(["BRANCH_CRE", "CRE"])))).scalars().first()

        cre_x = User(tenant_id=tenant_id, role_id=cre_role.id, email=f"strat_x_{uuid.uuid4().hex[:4]}@apexauto.com", hashed_password="p", full_name="Strat X", is_active=True)
        cre_y = User(tenant_id=tenant_id, role_id=cre_role.id, email=f"strat_y_{uuid.uuid4().hex[:4]}@apexauto.com", hashed_password="p", full_name="Strat Y", is_active=True)
        db.add_all([cre_x, cre_y])
        await db.flush()

        all_u = (await db.execute(select(User).where(User.tenant_id == tenant_id))).scalars().all()
        for u in all_u:
            await set_attendance_override(db, tenant_id, u.id, "ABSENT")
        await set_attendance_override(db, tenant_id, cre_x.id, "PRESENT")
        await set_attendance_override(db, tenant_id, cre_y.id, "PRESENT")

        # 1. ROUND_ROBIN Strategy (4 items -> 2 to each)
        await update_allocation_rules(db, tenant_id, {"strategy": "ROUND_ROBIN", "sticky_customers": False})
        items_rr = [await create_test_queue_item(db, tenant_id, brand.id, branch.id, f"RRCust_{i}", f"9777{i:06d}", f"JC-RR-{i}-{uuid.uuid4().hex[:4]}") for i in range(4)]
        run_rr = await allocate_queue_items(db, tenant_id, items_rr, run_type="IMPORT_BATCH")
        assert run_rr.allocated_items == 4
        c_x = len([q for q in items_rr if q.assigned_to_id == cre_x.id])
        c_y = len([q for q in items_rr if q.assigned_to_id == cre_y.id])
        assert c_x == 2 and c_y == 2

        # 2. MANUAL Strategy (items remain unallocated)
        await update_allocation_rules(db, tenant_id, {"strategy": "MANUAL"})
        items_manual = [await create_test_queue_item(db, tenant_id, brand.id, branch.id, f"ManCust_{i}", f"9666{i:06d}", f"JC-MAN-{i}-{uuid.uuid4().hex[:4]}") for i in range(4)]
        run_manual = await allocate_queue_items(db, tenant_id, items_manual, run_type="IMPORT_BATCH")
        assert run_manual.allocated_items == 0
        assert run_manual.unallocated_items == 4
        for q in items_manual:
            assert q.assigned_to_id is None


@pytest.mark.asyncio
async def test_concurrent_imports_single_allocation():
    """
    Test that concurrent allocation runs allocate each item exactly once with zero collisions.
    Uses PostgreSQL transaction isolation and row locking.
    """
    async with AsyncSessionLocal() as db:
        tenant = (await db.execute(select(Tenant))).scalars().first()
        tenant_id = tenant.id
        brand = (await db.execute(select(Brand).where(Brand.tenant_id == tenant_id))).scalars().first()
        branch = (await db.execute(select(Branch).where(Branch.tenant_id == tenant_id))).scalars().first()
        cre_role = (await db.execute(select(Role).where(Role.tenant_id == tenant_id, Role.name.in_(["BRANCH_CRE", "CRE"])))).scalars().first()

        cre = User(tenant_id=tenant_id, role_id=cre_role.id, email=f"conc_cre_{uuid.uuid4().hex[:4]}@apexauto.com", hashed_password="p", full_name="Conc CRE", is_active=True)
        db.add(cre)
        await db.flush()
        await set_attendance_override(db, tenant_id, cre.id, "PRESENT")

        # Explicitly ensure EQUAL_PRESENT_CRE strategy
        await update_allocation_rules(
            db, tenant_id,
            {"strategy": "EQUAL_PRESENT_CRE", "pool_mode": "CRE_POOL", "sticky_customers": False}
        )

        items = [await create_test_queue_item(db, tenant_id, brand.id, branch.id, f"ConcCust_{i}", f"9555{i:06d}", f"JC-CONC-{i}-{uuid.uuid4().hex[:4]}") for i in range(10)]
        await db.commit()
        item_ids = [q.id for q in items]

        # Run two concurrent allocations across separate database sessions on the same items
        async def run_alloc():
            async with AsyncSessionLocal() as session:
                qs = (await session.execute(
                    select(FollowupQueue).options(selectinload(FollowupQueue.job_card)).where(FollowupQueue.id.in_(item_ids))
                )).scalars().all()
                return await allocate_queue_items(session, tenant_id, qs, run_type="IMPORT_BATCH")

        run1, run2 = await asyncio.gather(run_alloc(), run_alloc())

        total_allocated = run1.allocated_items + run2.allocated_items
        assert total_allocated == 10, f"Expected exactly 10 allocated across both runs, got {total_allocated}"
        for q in items:
            await db.refresh(q)
            assert q.assigned_to_id is not None
