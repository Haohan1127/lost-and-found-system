from django.db import connection
from django.utils import timezone
from .models import Claim


def close_pending_claims(post_id, reason, except_claim_id=None):
    """调用方已先锁信息、再按 ID 锁申请；不独立开启或提交事务。"""
    if not connection.in_atomic_block:
        raise RuntimeError("关闭申请必须包含在上层事务中")
    if reason not in {"post_withdrawn", "another_claim_accepted"}:
        raise ValueError("未知关闭原因")
    queryset = Claim.objects.filter(post_id=post_id, status=Claim.Status.PENDING)
    if except_claim_id is not None:
        queryset = queryset.exclude(pk=except_claim_id)
    return queryset.update(status=Claim.Status.CLOSED, close_reason=reason, updated_at=timezone.now())
