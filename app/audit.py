from datetime import UTC, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session, aliased

from app.models import AuditLog, User

LOCAL_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")
AUDIT_CLEANUP_ADVISORY_LOCK_ID = 1_735_531_091
SECURITY_ALERT_ACTIONS = ("security.high_usage", "security.rate_limit")


def cleanup_audit_history(
    session: Session,
    *,
    detail_retention_days: int,
    general_retention_days: int,
    now: datetime | None = None,
) -> dict[str, int]:
    if detail_retention_days < 1 or general_retention_days < detail_retention_days:
        raise ValueError("Audit retention periods are invalid.")
    current_time = now or datetime.now(UTC)
    detail_retention_edge = current_time - timedelta(days=detail_retention_days)
    detail_cutoff = datetime.combine(
        detail_retention_edge.astimezone(LOCAL_TIMEZONE).date(),
        time.min,
        tzinfo=LOCAL_TIMEZONE,
    ).astimezone(UTC)
    general_cutoff = current_time - timedelta(days=general_retention_days)

    session.execute(
        text("SELECT pg_advisory_xact_lock(:lock_id)"),
        {"lock_id": AUDIT_CLEANUP_ADVISORY_LOCK_ID},
    )
    aggregate_result = session.execute(
        text(
            """
            INSERT INTO audit_logs (
                id, actor_user_id, action, resource_type, resource_id,
                result, metadata_json, created_at
            )
            SELECT
                'sum-' || substr(
                    md5(
                        COALESCE(actor_user_id, 'system') || ':' ||
                        DATE(timezone('Asia/Ho_Chi_Minh', created_at))::text
                    ),
                    1,
                    32
                ),
                actor_user_id,
                'orders.view_detail.daily',
                'audit_summary',
                DATE(timezone('Asia/Ho_Chi_Minh', created_at))::text || ':' ||
                    COALESCE(actor_user_id, 'system'),
                'success',
                jsonb_build_object(
                    'event_count', COUNT(*),
                    'unique_order_count', COUNT(DISTINCT resource_id),
                    'summary_date',
                        DATE(timezone('Asia/Ho_Chi_Minh', created_at))::text
                ),
                MAX(created_at)
            FROM audit_logs
            WHERE action = 'orders.view_detail'
              AND created_at < :detail_cutoff
            GROUP BY
                actor_user_id,
                DATE(timezone('Asia/Ho_Chi_Minh', created_at))
            ON CONFLICT (id) DO UPDATE SET
                metadata_json = jsonb_build_object(
                    'event_count',
                        COALESCE((audit_logs.metadata_json->>'event_count')::bigint, 0) +
                        COALESCE((EXCLUDED.metadata_json->>'event_count')::bigint, 0),
                    'unique_order_count',
                        COALESCE((audit_logs.metadata_json->>'unique_order_count')::bigint, 0) +
                        COALESCE((EXCLUDED.metadata_json->>'unique_order_count')::bigint, 0),
                    'summary_date', EXCLUDED.metadata_json->>'summary_date'
                ),
                created_at = GREATEST(audit_logs.created_at, EXCLUDED.created_at)
            """
        ),
        {"detail_cutoff": detail_cutoff},
    )
    detail_delete_result = session.execute(
        delete(AuditLog).where(
            AuditLog.action == "orders.view_detail",
            AuditLog.created_at < detail_cutoff,
        )
    )
    general_delete_result = session.execute(
        delete(AuditLog).where(
            AuditLog.action != "orders.view_detail",
            AuditLog.created_at < general_cutoff,
        )
    )
    session.flush()
    return {
        "summaries_upserted": max(aggregate_result.rowcount or 0, 0),
        "detail_events_deleted": max(detail_delete_result.rowcount or 0, 0),
        "general_events_deleted": max(general_delete_result.rowcount or 0, 0),
    }


def add_audit_event(
    session: Session,
    *,
    actor_user_id: str | None,
    action: str,
    resource_type: str | None,
    resource_id: str | None,
    result: str,
    metadata: dict,
    ip_address: str | None,
    user_agent: str | None,
    deduplicate_seconds: int | None = None,
    now: datetime | None = None,
) -> AuditLog | None:
    current_time = now or datetime.now(UTC)
    if deduplicate_seconds is not None:
        if deduplicate_seconds < 1 or not actor_user_id or not resource_id:
            raise ValueError("Deduplicated audit events require actor, resource, and interval.")
        dedupe_key = f"{actor_user_id}:{action}:{resource_id}"
        session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:dedupe_key))"),
            {"dedupe_key": dedupe_key},
        )
        recent_event_id = session.scalar(
            select(AuditLog.id).where(
                AuditLog.actor_user_id == actor_user_id,
                AuditLog.action == action,
                AuditLog.resource_id == resource_id,
                AuditLog.created_at >= current_time - timedelta(seconds=deduplicate_seconds),
            ).limit(1)
        )
        if recent_event_id is not None:
            return None

    event = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        result=result,
        metadata_json=metadata,
        ip_address=ip_address,
        user_agent=user_agent,
        created_at=current_time,
    )
    session.add(event)
    session.flush()
    return event


def list_audit_logs(
    session: Session,
    *,
    page_number: int = 1,
    page_size: int = 50,
    action: str | None = None,
    actor_user_id: str | None = None,
    result: str | None = None,
    ip_address: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    visible_actor_roles: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    actor = aliased(User)
    visibility_filters = []
    if visible_actor_roles is not None:
        visibility_filters.append(
            AuditLog.actor_user_id.in_(
                select(User.id).where(User.role.in_(visible_actor_roles))
            )
        )
    filters = list(visibility_filters)
    if action:
        filters.append(AuditLog.action == action)
    if actor_user_id:
        filters.append(AuditLog.actor_user_id == actor_user_id)
    if result:
        filters.append(AuditLog.result == result)
    if ip_address:
        filters.append(AuditLog.ip_address == ip_address.strip())
    if date_from:
        filters.append(AuditLog.created_at >= date_from)
    if date_to:
        filters.append(AuditLog.created_at <= date_to)

    total = session.scalar(
        select(func.count()).select_from(AuditLog).where(*filters)
    ) or 0
    rows = session.execute(
        select(AuditLog, actor.username, actor.display_name)
        .outerjoin(actor, actor.id == AuditLog.actor_user_id)
        .where(*filters)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((page_number - 1) * page_size)
        .limit(page_size)
    ).all()
    actions = list(
        session.scalars(
            select(AuditLog.action)
            .where(*visibility_filters)
            .distinct()
            .order_by(AuditLog.action)
        ).all()
    )
    actor_filters = [
        select(1).where(AuditLog.actor_user_id == User.id).exists()
    ]
    if visible_actor_roles is not None:
        actor_filters.append(User.role.in_(visible_actor_roles))
    actors = session.execute(
        select(User.id, User.username, User.display_name)
        .where(*actor_filters)
        .order_by(User.display_name, User.username)
    ).all()
    results = list(
        session.scalars(
            select(AuditLog.result)
            .where(*visibility_filters)
            .distinct()
            .order_by(AuditLog.result)
        ).all()
    )

    return {
        "items": [
            {
                "id": audit_log.id,
                "actor_username": username,
                "actor_display_name": display_name,
                "action": audit_log.action,
                "resource_type": audit_log.resource_type,
                "resource_id": audit_log.resource_id,
                "result": audit_log.result,
                "metadata": audit_log.metadata_json,
                "ip_address": audit_log.ip_address,
                "user_agent": audit_log.user_agent,
                "created_at": audit_log.created_at,
            }
            for audit_log, username, display_name in rows
        ],
        "actions": actions,
        "actors": [
            {"user_id": user_id, "username": username, "display_name": display_name}
            for user_id, username, display_name in actors
        ],
        "results": results,
        "pagination": {
            "page_number": page_number,
            "page_size": page_size,
            "total_items": total,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }


def list_security_alerts(
    session: Session,
    *,
    hours: int = 24,
    limit: int = 50,
    now: datetime | None = None,
    visible_actor_roles: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    if hours < 1 or limit < 1:
        raise ValueError("Security alert window and limit must be positive.")
    current_time = now or datetime.now(UTC)
    cutoff = current_time - timedelta(hours=hours)
    actor = aliased(User)
    filters = [
        AuditLog.action.in_(SECURITY_ALERT_ACTIONS),
        AuditLog.created_at >= cutoff,
    ]
    if visible_actor_roles is not None:
        filters.append(
            AuditLog.actor_user_id.in_(
                select(User.id).where(User.role.in_(visible_actor_roles))
            )
        )
    total = session.scalar(
        select(func.count()).select_from(AuditLog).where(*filters)
    ) or 0
    rows = session.execute(
        select(AuditLog, actor.username, actor.display_name)
        .outerjoin(actor, actor.id == AuditLog.actor_user_id)
        .where(*filters)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
    ).all()
    return {
        "items": [
            {
                "id": audit_log.id,
                "actor_username": username,
                "actor_display_name": display_name,
                "action": audit_log.action,
                "result": audit_log.result,
                "metadata": audit_log.metadata_json,
                "ip_address": audit_log.ip_address,
                "user_agent": audit_log.user_agent,
                "created_at": audit_log.created_at,
            }
            for audit_log, username, display_name in rows
        ],
        "total": total,
        "hours": hours,
    }
