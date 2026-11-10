"""
================================================================================
FILE PURPOSE: Configuration Resolver Service.
Resolves hierarchical configuration (Brand overrides Dealership default),
manages Redis-backed caching with automatic cache invalidation on publish,
and enforces Draft -> Publish -> Rollback lifecycles with strict payload validation
and comprehensive audit logging.
================================================================================
"""
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Union

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import ConfigVersion, FollowUpProgram
from app.models.additional import AuditLog
from app.core.redis import get_redis

logger = logging.getLogger("psf.config_resolver")

# In-memory fallback dictionary if Redis is down/unreachable
_MEMORY_CACHE: Dict[str, Any] = {}


class ConfigResolverService:
    @staticmethod
    def _build_cache_key(tenant_id: Union[uuid.UUID, str], config_type: str, scope_key: str) -> str:
        return f"cfg:{tenant_id}:{config_type}:{scope_key}"

    @classmethod
    async def get_cached(cls, key: str) -> Optional[Any]:
        try:
            r = await get_redis()
            val = await r.get(key)
            if val is not None:
                return json.loads(val)
        except Exception as e:
            logger.warning(f"Redis get failed for key {key}, falling back to memory: {e}")
        return _MEMORY_CACHE.get(key)

    @classmethod
    async def set_cached(cls, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        try:
            r = await get_redis()
            await r.set(key, json.dumps(value, default=str), ex=ttl_seconds)
        except Exception as e:
            logger.warning(f"Redis set failed for key {key}: {e}")
        _MEMORY_CACHE[key] = value

    @classmethod
    async def invalidate_cache(cls, tenant_id: Union[uuid.UUID, str], config_type: Optional[str] = None) -> None:
        prefix = f"cfg:{tenant_id}:"
        if config_type:
            prefix += f"{config_type}:"

        try:
            r = await get_redis()
            keys = await r.keys(f"{prefix}*")
            if keys:
                await r.delete(*keys)
        except Exception as e:
            logger.warning(f"Redis cache invalidation failed: {e}")

        # Clear in-memory cache matching prefix
        keys_to_del = [k for k in _MEMORY_CACHE.keys() if k.startswith(prefix)]
        for k in keys_to_del:
            _MEMORY_CACHE.pop(k, None)

    # -------------------------------------------------------------------------
    # Payload Validation
    # -------------------------------------------------------------------------
    @classmethod
    def validate_payload(cls, config_type: str, payload: Any) -> None:
        if not payload or not isinstance(payload, (dict, list)):
            raise ValueError(f"Payload for {config_type} must be a non-empty JSON object or array")

        if config_type == "PROGRAMS":
            programs = payload if isinstance(payload, list) else payload.get("programs", [])
            if not isinstance(programs, list) or len(programs) == 0:
                raise ValueError("PROGRAMS payload must contain a non-empty list of programs")

            valid_triggers = {"ON_IMPORT", "AFTER_COMPLAINT_CLOSURE"}
            valid_channels = {"PHONE", "WHATSAPP", "BOTH"}

            for p in programs:
                if not isinstance(p, dict):
                    raise ValueError("Each program entry must be a dictionary")
                code = p.get("code")
                label = p.get("label")
                trigger = p.get("trigger", "")
                channel = p.get("channel", "PHONE")

                if not code or not isinstance(code, str) or len(code.strip()) == 0:
                    raise ValueError("Program 'code' is required and cannot be empty")
                if not label or not isinstance(label, str) or len(label.strip()) == 0:
                    raise ValueError("Program 'label' is required and cannot be empty")
                if channel not in valid_channels:
                    raise ValueError(f"Invalid channel '{channel}'. Must be one of {valid_channels}")

                is_after_days = bool(re.match(r"^AFTER_DAYS\(\d+\)$", trigger))
                if trigger not in valid_triggers and not is_after_days:
                    raise ValueError(f"Invalid trigger '{trigger}'. Must be ON_IMPORT, AFTER_DAYS(n), or AFTER_COMPLAINT_CLOSURE")

    # -------------------------------------------------------------------------
    # Version Management: Draft -> Publish -> Rollback
    # -------------------------------------------------------------------------
    @classmethod
    async def create_draft(
        cls,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        scope: str,
        scope_id: Optional[uuid.UUID],
        config_type: str,
        payload: Dict[str, Any],
        user_id: Optional[uuid.UUID] = None,
        note: Optional[str] = None,
    ) -> ConfigVersion:
        cls.validate_payload(config_type, payload)

        # Determine next version
        v_stmt = select(func.coalesce(func.max(ConfigVersion.version), 0)).where(
            ConfigVersion.tenant_id == tenant_id,
            ConfigVersion.scope == scope,
            ConfigVersion.scope_id == scope_id,
            ConfigVersion.config_type == config_type,
        )
        current_max = (await db.execute(v_stmt)).scalar() or 0
        next_ver = current_max + 1

        draft = ConfigVersion(
            tenant_id=tenant_id,
            scope=scope,
            scope_id=scope_id,
            config_type=config_type,
            version=next_ver,
            status="DRAFT",
            payload=payload,
            created_by=user_id,
            note=note,
        )
        db.add(draft)
        await db.flush()

        audit = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action="CONFIG_DRAFT_CREATED",
            entity_type="CONFIG_VERSION",
            entity_id=str(draft.id),
            new_values={"scope": scope, "config_type": config_type, "version": next_ver, "note": note},
            reason=note or f"Created DRAFT config v{next_ver} for {config_type}",
        )
        db.add(audit)
        await db.commit()
        await db.refresh(draft)
        return draft

    @classmethod
    async def publish_version(
        cls,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        version_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        note: Optional[str] = None,
    ) -> ConfigVersion:
        v_stmt = select(ConfigVersion).where(
            ConfigVersion.id == version_id,
            ConfigVersion.tenant_id == tenant_id,
        )
        target = (await db.execute(v_stmt)).scalar_one_or_none()
        if not target:
            raise ValueError(f"Config version {version_id} not found")

        # Strictly validate payload
        cls.validate_payload(target.config_type, target.payload)

        # Archive currently published version
        await db.execute(
            update(ConfigVersion)
            .where(
                ConfigVersion.tenant_id == tenant_id,
                ConfigVersion.scope == target.scope,
                ConfigVersion.scope_id == target.scope_id,
                ConfigVersion.config_type == target.config_type,
                ConfigVersion.status == "PUBLISHED",
            )
            .values(status="ARCHIVED")
        )

        target.status = "PUBLISHED"
        target.published_at = datetime.now(timezone.utc)
        if note:
            target.note = note

        # Sync payload to entity tables if applicable
        if target.config_type == "PROGRAMS":
            await cls._sync_programs_from_payload(db, tenant_id, target.scope, target.scope_id, target.payload)

        audit = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action="CONFIG_PUBLISHED",
            entity_type="CONFIG_VERSION",
            entity_id=str(target.id),
            new_values={"status": "PUBLISHED", "version": target.version, "note": target.note},
            reason=note or f"Published config v{target.version} for {target.config_type}",
        )
        db.add(audit)
        await db.commit()
        await db.refresh(target)

        # Invalidate Redis cache
        await cls.invalidate_cache(tenant_id, target.config_type)
        return target

    @classmethod
    async def rollback_config(
        cls,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        target_version_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        reason: Optional[str] = None,
    ) -> ConfigVersion:
        if not reason or len(reason.strip()) < 5:
            raise ValueError("Mandatory reason (min 5 chars) is required for config rollback")

        v_stmt = select(ConfigVersion).where(
            ConfigVersion.id == target_version_id,
            ConfigVersion.tenant_id == tenant_id,
        )
        target = (await db.execute(v_stmt)).scalar_one_or_none()
        if not target:
            raise ValueError(f"Target config version {target_version_id} not found")

        # Determine next version number
        max_stmt = select(func.coalesce(func.max(ConfigVersion.version), 0)).where(
            ConfigVersion.tenant_id == tenant_id,
            ConfigVersion.scope == target.scope,
            ConfigVersion.scope_id == target.scope_id,
            ConfigVersion.config_type == target.config_type,
        )
        current_max = (await db.execute(max_stmt)).scalar() or 0
        new_version_num = current_max + 1

        # Archive existing published version
        await db.execute(
            update(ConfigVersion)
            .where(
                ConfigVersion.tenant_id == tenant_id,
                ConfigVersion.scope == target.scope,
                ConfigVersion.scope_id == target.scope_id,
                ConfigVersion.config_type == target.config_type,
                ConfigVersion.status == "PUBLISHED",
            )
            .values(status="ARCHIVED")
        )

        rollback_ver = ConfigVersion(
            tenant_id=tenant_id,
            scope=target.scope,
            scope_id=target.scope_id,
            config_type=target.config_type,
            version=new_version_num,
            status="PUBLISHED",
            payload=target.payload,
            created_by=user_id,
            published_at=datetime.now(timezone.utc),
            note=f"Rolled back to v{target.version}: {reason}",
        )
        db.add(rollback_ver)

        if target.config_type == "PROGRAMS":
            await cls._sync_programs_from_payload(db, tenant_id, target.scope, target.scope_id, target.payload)

        audit = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action="CONFIG_ROLLBACK",
            entity_type="CONFIG_VERSION",
            entity_id=str(rollback_ver.id),
            old_values={"restored_from_version": target.version},
            new_values={"new_version": new_version_num, "status": "PUBLISHED"},
            reason=reason,
        )
        db.add(audit)
        await db.commit()
        await db.refresh(rollback_ver)

        # Invalidate cache
        await cls.invalidate_cache(tenant_id, target.config_type)
        return rollback_ver

    # -------------------------------------------------------------------------
    # Resolve Config (Brand overrides Dealership, Redis-cached)
    # -------------------------------------------------------------------------
    @classmethod
    async def resolve_config(
        cls,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        config_type: str,
        brand_id: Optional[uuid.UUID] = None,
    ) -> Optional[Any]:
        scope_key = str(brand_id) if brand_id else "default"
        cache_key = cls._build_cache_key(tenant_id, config_type, scope_key)

        cached = await cls.get_cached(cache_key)
        if cached is not None:
            return cached

        # 1. If brand_id provided, look for BRAND-scoped published config
        if brand_id:
            b_stmt = (
                select(ConfigVersion)
                .where(
                    ConfigVersion.tenant_id == tenant_id,
                    ConfigVersion.scope == "BRAND",
                    ConfigVersion.scope_id == brand_id,
                    ConfigVersion.config_type == config_type,
                    ConfigVersion.status == "PUBLISHED",
                )
                .order_by(ConfigVersion.version.desc())
                .limit(1)
            )
            b_ver = (await db.execute(b_stmt)).scalar_one_or_none()
            if b_ver:
                await cls.set_cached(cache_key, b_ver.payload)
                return b_ver.payload

        # 2. Look for DEALERSHIP-scoped published config
        d_stmt = (
            select(ConfigVersion)
            .where(
                ConfigVersion.tenant_id == tenant_id,
                ConfigVersion.scope == "DEALERSHIP",
                ConfigVersion.config_type == config_type,
                ConfigVersion.status == "PUBLISHED",
            )
            .order_by(ConfigVersion.version.desc())
            .limit(1)
        )
        d_ver = (await db.execute(d_stmt)).scalar_one_or_none()
        if d_ver:
            await cls.set_cached(cache_key, d_ver.payload)
            return d_ver.payload

        return None

    # -------------------------------------------------------------------------
    # Active Follow-Up Programs Resolution for Job Cards
    # -------------------------------------------------------------------------
    @classmethod
    async def get_active_programs_for_brand(
        cls,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        brand_id: Optional[uuid.UUID] = None,
    ) -> List[FollowUpProgram]:
        """
        Resolves enabled FollowUpProgram records for a given brand.
        If the brand has programs configured (brand_id == brand_id), those are returned.
        Otherwise falls back to Dealership-wide programs (brand_id is None).
        """
        if brand_id:
            brand_stmt = (
                select(FollowUpProgram)
                .where(
                    FollowUpProgram.tenant_id == tenant_id,
                    FollowUpProgram.brand_id == brand_id,
                    FollowUpProgram.is_deleted.is_(False),
                    FollowUpProgram.enabled.is_(True),
                )
                .order_by(FollowUpProgram.sort_order.asc(), FollowUpProgram.created_at.asc())
            )
            brand_programs = (await db.execute(brand_stmt)).scalars().all()
            if len(brand_programs) > 0:
                return list(brand_programs)

        # Fallback to dealership default programs
        default_stmt = (
            select(FollowUpProgram)
            .where(
                FollowUpProgram.tenant_id == tenant_id,
                FollowUpProgram.brand_id.is_(None),
                FollowUpProgram.is_deleted.is_(False),
                FollowUpProgram.enabled.is_(True),
            )
            .order_by(FollowUpProgram.sort_order.asc(), FollowUpProgram.created_at.asc())
        )
        return list((await db.execute(default_stmt)).scalars().all())

    @classmethod
    async def _sync_programs_from_payload(
        cls,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        scope: str,
        scope_id: Optional[uuid.UUID],
        payload: Any,
    ) -> None:
        """Syncs published payload to follow_up_programs table."""
        programs_list = payload if isinstance(payload, list) else payload.get("programs", [])
        brand_id = scope_id if scope == "BRAND" else None

        # Mark existing programs for this scope as deleted
        await db.execute(
            update(FollowUpProgram)
            .where(
                FollowUpProgram.tenant_id == tenant_id,
                FollowUpProgram.brand_id == brand_id,
            )
            .values(is_deleted=True)
        )

        for idx, item in enumerate(programs_list):
            prog = FollowUpProgram(
                tenant_id=tenant_id,
                brand_id=brand_id,
                code=item["code"].upper().strip(),
                label=item["label"].strip(),
                enabled=item.get("enabled", True),
                trigger=item.get("trigger", "ON_IMPORT"),
                channel=item.get("channel", "PHONE"),
                questionnaire_id=uuid.UUID(item["questionnaire_id"]) if item.get("questionnaire_id") else None,
                rating_scale_id=uuid.UUID(item["rating_scale_id"]) if item.get("rating_scale_id") else None,
                max_attempts=item.get("max_attempts", 3),
                retry_gap_hours=item.get("retry_gap_hours", 24),
                sla_hours=item.get("sla_hours", 48),
                sort_order=item.get("sort_order", idx),
                is_deleted=False,
            )
            db.add(prog)
        await db.flush()
