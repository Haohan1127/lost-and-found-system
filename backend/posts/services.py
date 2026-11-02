from django.db import connection
from django.utils import timezone
from common.exceptions import conflict
from .selectors import get_post_for_claim


def set_handover_state(post_id, transition):
    """调用方先锁 Post，再锁相关 Claim；不能在事务外使用。"""
    if not connection.in_atomic_block:
        raise RuntimeError("信息状态变更必须包含在上层事务中")
    post = get_post_for_claim(post_id, lock=True)
    transitions = {"reserve": ("open", "in_handover"), "complete": ("in_handover", "completed"), "reopen": ("in_handover", "open")}
    if transition not in transitions or post.post_type != "found":
        conflict()
    before, after = transitions[transition]
    if post.status != before:
        conflict()
    post.status = after
    post.completed_at = timezone.now() if after == "completed" else None
    post.save(update_fields=["status", "completed_at", "updated_at"])
    return post
