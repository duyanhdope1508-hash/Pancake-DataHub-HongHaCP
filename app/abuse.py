from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import UsageQuota


@dataclass(frozen=True)
class QuotaDecision:
    allowed: bool
    used: int
    limit: int
    retry_after: int
    should_log_denial: bool = False
    should_alert: bool = False


def _quota_key(user_id: str, action: str, window_seconds: int) -> str:
    value = f"{user_id}:{action}:{window_seconds}"
    return sha256(value.encode("utf-8")).hexdigest()


def consume_quota(
    session: Session,
    *,
    user_id: str,
    action: str,
    amount: int,
    limit: int,
    window_seconds: int,
    now: datetime | None = None,
) -> QuotaDecision:
    if amount < 1 or limit < 1 or window_seconds < 1:
        raise ValueError("Quota amount, limit, and window must be positive.")

    current_time = now or datetime.now(UTC)
    key_hash = _quota_key(user_id, action, window_seconds)
    session.execute(
        insert(UsageQuota)
        .values(
            key_hash=key_hash,
            user_id=user_id,
            action=action,
            window_started_at=current_time,
            usage_count=0,
        )
        .on_conflict_do_nothing(index_elements=[UsageQuota.key_hash])
    )
    bucket = session.scalar(
        select(UsageQuota)
        .where(UsageQuota.key_hash == key_hash)
        .with_for_update()
    )
    if bucket is None:
        raise RuntimeError("Usage quota bucket could not be created.")

    window_end = bucket.window_started_at + timedelta(seconds=window_seconds)
    if current_time >= window_end:
        bucket.window_started_at = current_time
        bucket.usage_count = 0
        bucket.last_denied_at = None
        window_end = current_time + timedelta(seconds=window_seconds)

    retry_after = max(1, int((window_end - current_time).total_seconds()))
    projected = bucket.usage_count + amount
    if projected > limit:
        should_log = (
            bucket.last_denied_at is None
            or bucket.last_denied_at <= current_time - timedelta(minutes=5)
        )
        if should_log:
            bucket.last_denied_at = current_time
        session.flush()
        return QuotaDecision(
            allowed=False,
            used=bucket.usage_count,
            limit=limit,
            retry_after=retry_after,
            should_log_denial=should_log,
        )

    previous_usage = bucket.usage_count
    bucket.usage_count = projected
    alert_threshold = max(1, (limit * 80 + 99) // 100)
    session.flush()
    return QuotaDecision(
        allowed=True,
        used=bucket.usage_count,
        limit=limit,
        retry_after=retry_after,
        should_alert=previous_usage < alert_threshold <= projected,
    )
