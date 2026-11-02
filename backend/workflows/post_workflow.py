"""B/C 联调适配：B 接入正式撤回/恢复入口时复用此事务流程。"""
from django.db import transaction
from common.exceptions import conflict, forbidden
from claims.services import close_pending_claims
from .claim_workflow import lock_post_claims


@transaction.atomic
def withdraw_post(user, post_id):
    post, _ = lock_post_claims(post_id)
    if post.publisher_id != user.pk:
        forbidden()
    if post.status == "withdrawn":
        return post
    if post.status != "open":
        conflict()
    post.status = "withdrawn"
    post.save(update_fields=["status", "updated_at"])
    close_pending_claims(post.pk, "post_withdrawn")
    return post


@transaction.atomic
def restore_post(user, post_id):
    post, _ = lock_post_claims(post_id)
    if post.publisher_id != user.pk:
        forbidden()
    if post.status == "open":
        return post
    if post.status != "withdrawn":
        conflict()
    post.status = "open"
    post.save(update_fields=["status", "updated_at"])
    return post
