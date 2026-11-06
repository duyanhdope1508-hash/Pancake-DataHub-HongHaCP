from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.models import AuditLog, User


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
