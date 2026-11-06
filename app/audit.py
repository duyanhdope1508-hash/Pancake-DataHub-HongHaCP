from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, aliased

from app.models import AuditLog, User


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
) -> dict[str, Any]:
    actor = aliased(User)
    filters = []
    if action:
        filters.append(AuditLog.action == action)

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
            select(AuditLog.action).distinct().order_by(AuditLog.action)
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
        "pagination": {
            "page_number": page_number,
            "page_size": page_size,
            "total_items": total,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }
