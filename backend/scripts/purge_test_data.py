import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def purge():
    async with AsyncSessionLocal() as db:
        print("Starting test data purge...")

        # 1. Delete complaints on test job cards
        await db.execute(text("""
            DELETE FROM complaint_events WHERE complaint_id IN (
                SELECT id FROM complaints WHERE job_card_id IN (
                    SELECT id FROM job_cards WHERE job_card_no LIKE 'JC-%' OR job_card_no = 'nan'
                )
            )
        """))
        await db.execute(text("""
            DELETE FROM reconfirmations WHERE complaint_id IN (
                SELECT id FROM complaints WHERE job_card_id IN (
                    SELECT id FROM job_cards WHERE job_card_no LIKE 'JC-%' OR job_card_no = 'nan'
                )
            )
        """))
        await db.execute(text("""
            DELETE FROM complaints WHERE job_card_id IN (
                SELECT id FROM job_cards WHERE job_card_no LIKE 'JC-%' OR job_card_no = 'nan'
            )
        """))
        await db.execute(text("""
            UPDATE complaints SET call_id = NULL WHERE call_id IN (
                SELECT id FROM calls WHERE job_card_id IN (
                    SELECT id FROM job_cards WHERE job_card_no LIKE 'JC-%' OR job_card_no = 'nan'
                )
            )
        """))

        # 2. Delete test job cards (e.g. JC-TEST%, JC-1CRE%, nan) and their queues/calls
        test_jc_res = await db.execute(text("SELECT id FROM job_cards WHERE job_card_no LIKE 'JC-%' OR job_card_no = 'nan'"))
        test_jc_ids = [str(r[0]) for r in test_jc_res.fetchall()]
        print(f"Found {len(test_jc_ids)} test job cards to remove.")

        if test_jc_ids:
            await db.execute(text("""
                DELETE FROM allocation_assignments WHERE queue_item_id IN (
                    SELECT id FROM followup_queues WHERE job_card_id IN (
                        SELECT id FROM job_cards WHERE job_card_no LIKE 'JC-%' OR job_card_no = 'nan'
                    )
                )
            """))
            await db.execute(text("""
                DELETE FROM survey_responses WHERE job_card_id IN (
                    SELECT id FROM job_cards WHERE job_card_no LIKE 'JC-%' OR job_card_no = 'nan'
                )
            """))
            await db.execute(text("""
                DELETE FROM calls WHERE job_card_id IN (
                    SELECT id FROM job_cards WHERE job_card_no LIKE 'JC-%' OR job_card_no = 'nan'
                )
            """))
            await db.execute(text("""
                DELETE FROM call_attempts WHERE followup_queue_id IN (
                    SELECT id FROM followup_queues WHERE job_card_id IN (
                        SELECT id FROM job_cards WHERE job_card_no LIKE 'JC-%' OR job_card_no = 'nan'
                    )
                )
            """))
            await db.execute(text("""
                DELETE FROM reminders WHERE followup_queue_id IN (
                    SELECT id FROM followup_queues WHERE job_card_id IN (
                        SELECT id FROM job_cards WHERE job_card_no LIKE 'JC-%' OR job_card_no = 'nan'
                    )
                )
            """))
            await db.execute(text("""
                DELETE FROM followup_queues WHERE job_card_id IN (
                    SELECT id FROM job_cards WHERE job_card_no LIKE 'JC-%' OR job_card_no = 'nan'
                )
            """))
            await db.execute(text("DELETE FROM job_cards WHERE job_card_no LIKE 'JC-%' OR job_card_no = 'nan'"))
            await db.commit()
            print("Purged test job cards and associated queues.")

        # 3. Find all junk test users
        junk_users_res = await db.execute(text("""
            SELECT id, email FROM users
            WHERE email LIKE 'test_cre_%'
               OR email LIKE 'cre_a_%'
               OR email LIKE 'cre_b_%'
               OR email LIKE 'cre_b1_%'
               OR email LIKE 'cre_b2_%'
               OR email LIKE 'strat_x_%'
               OR email LIKE 'strat_y_%'
               OR email LIKE 'conc_cre_%'
               OR email LIKE 'rot_cre_%'
               OR email LIKE 'stk1_%'
               OR email LIKE 'stk2_%'
               OR email LIKE 'defer_cre_%'
               OR email LIKE 'undo_%'
               OR email LIKE 'reb_%'
               OR email LIKE 'late_cre_%'
               OR email LIKE 'sched_cre_%'
               OR email LIKE 'stale_session_%'
               OR email LIKE 'idemp_cre_%'
               OR email LIKE 'inactive_cre_%'
               OR email LIKE 'active_cre_%'
               OR email LIKE 'scoped.%'
               OR email LIKE 'placeholder.advisor.%'
        """))
        junk_users = junk_users_res.fetchall()
        print(f"Found {len(junk_users)} junk test users to purge.")

        if junk_users:
            junk_ids = [f"'{r.id}'" for r in junk_users]
            in_clause = f"({', '.join(junk_ids)})"

            # Remove references to junk users
            await db.execute(text(f"DELETE FROM audit_logs WHERE user_id IN {in_clause}"))
            await db.execute(text(f"DELETE FROM complaint_events WHERE performed_by_id IN {in_clause}"))
            await db.execute(text(f"DELETE FROM reconfirmations WHERE conducted_by_id IN {in_clause}"))
            await db.execute(text(f"UPDATE complaints SET assigned_to_id = NULL WHERE assigned_to_id IN {in_clause}"))
            await db.execute(text(f"UPDATE complaints SET resolved_by_id = NULL WHERE resolved_by_id IN {in_clause}"))
            await db.execute(text(f"UPDATE complaints SET closed_by_id = NULL WHERE closed_by_id IN {in_clause}"))
            await db.execute(text(f"DELETE FROM user_scopes WHERE user_id IN {in_clause}"))
            await db.execute(text(f"DELETE FROM attendance_overrides WHERE user_id IN {in_clause} OR marked_by_id IN {in_clause}"))
            await db.execute(text(f"DELETE FROM login_logs WHERE user_id IN {in_clause}"))
            await db.execute(text(f"DELETE FROM allocation_assignments WHERE from_user_id IN {in_clause} OR to_user_id IN {in_clause}"))
            await db.execute(text(f"DELETE FROM allocation_runs WHERE started_by_id IN {in_clause} OR undone_by_id IN {in_clause}"))
            await db.execute(text(f"DELETE FROM reminders WHERE assigned_to_id IN {in_clause}"))
            await db.execute(text(f"DELETE FROM call_attempts WHERE called_by_id IN {in_clause}"))
            await db.execute(text(f"DELETE FROM survey_responses WHERE call_id IN (SELECT id FROM calls WHERE called_by_id IN {in_clause})"))
            await db.execute(text(f"DELETE FROM calls WHERE called_by_id IN {in_clause}"))
            await db.execute(text(f"UPDATE followup_queues SET assigned_to_id = NULL WHERE assigned_to_id IN {in_clause}"))
            await db.execute(text(f"UPDATE job_cards SET service_advisor_id = NULL WHERE service_advisor_id IN {in_clause}"))
            await db.execute(text(f"UPDATE job_cards SET uploaded_by_id = NULL WHERE uploaded_by_id IN {in_clause}"))
            await db.execute(text(f"UPDATE import_batches SET uploaded_by = (SELECT id FROM users WHERE email = 'admin@apexauto.com' LIMIT 1) WHERE uploaded_by IN {in_clause}"))
            await db.execute(text(f"DELETE FROM users WHERE id IN {in_clause}"))
            await db.commit()
            print(f"Successfully deleted {len(junk_users)} junk test users.")

        # Check remaining users
        res = await db.execute(text("SELECT email, full_name FROM users ORDER BY email"))
        remaining = res.fetchall()
        print(f"Remaining legitimate users ({len(remaining)}):")
        for u in remaining:
            print(f"  {u.email} -> {u.full_name}")

        # Check remaining job cards
        res_jc = await db.execute(text("SELECT count(*) FROM job_cards"))
        print(f"Remaining real job cards: {res_jc.scalar()}")

        # Check remaining followup queues
        res_fq = await db.execute(text("SELECT count(*) FROM followup_queues"))
        print(f"Remaining followup queues: {res_fq.scalar()}")

if __name__ == "__main__":
    asyncio.run(purge())
