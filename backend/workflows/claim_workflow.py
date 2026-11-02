from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from common.exceptions import BusinessError, conflict, forbidden, missing
from users.services import require_campus_verified
from posts import services as post_services
from posts.selectors import get_post_for_claim
from claims.models import Claim
from claims.permissions import require_participant, require_publisher
from claims.selectors import get_claim
from claims.services import close_pending_claims


def lock_post_claims(post_id):
    post = get_post_for_claim(post_id, lock=True)
    claims = list(Claim.objects.select_for_update().filter(post_id=post.pk).order_by("id"))
    return post, claims


def lock_claim(claim_id, user):
    # 先检查可见性；不可变的 post_id 用于确定统一的锁顺序。
    hint = get_claim(claim_id, user)
    post, claims = lock_post_claims(hint.post_id)
    claim = next((obj for obj in claims if obj.pk == hint.pk), None)
    if claim is None:
        missing()
    claim.post = post
    require_participant(claim, user)
    return post, claim


@transaction.atomic
def create_claim(user, post_id, verification_text):
    require_campus_verified(user)
    post, claims = lock_post_claims(post_id)
    if post.status == "withdrawn" and post.publisher_id != user.pk:
        missing()
    if post.post_type != "found":
        raise ValidationError({"post_id": ["只能对招领信息申请认领"]})
    if post.publisher_id == user.pk:
        forbidden()
    if post.status != "open":
        conflict("该招领信息当前不能申请")
    if any(c.applicant_id == user.pk and c.status in {"pending", "accepted"} for c in claims):
        raise BusinessError("DUPLICATE_RESOURCE", "已有有效认领申请")
    try:
        return Claim.objects.create(post=post, applicant=user, verification_text=verification_text)
    except IntegrityError:
        raise BusinessError("DUPLICATE_RESOURCE", "已有有效认领申请")


@transaction.atomic
def accept_claim(user, claim_id, decision_note=None):
    post, claim = lock_claim(claim_id, user)
    require_publisher(claim, user)
    if claim.status == "accepted":
        return claim
    if claim.status != "pending" or post.status != "open":
        conflict()
    claim.status = "accepted"
    claim.decision_note = decision_note
    claim.save(update_fields=["status", "decision_note", "updated_at"])
    close_pending_claims(post.pk, "another_claim_accepted", claim.pk)
    claim.post = post_services.set_handover_state(post.pk, "reserve")
    return claim


@transaction.atomic
def reject_claim(user, claim_id, decision_note):
    post, claim = lock_claim(claim_id, user)
    require_publisher(claim, user)
    if claim.status == "rejected":
        return claim
    if claim.status != "pending" or post.status != "open":
        conflict()
    claim.status, claim.decision_note = "rejected", decision_note
    claim.save(update_fields=["status", "decision_note", "updated_at"])
    return claim


@transaction.atomic
def cancel_claim(user, claim_id):
    post, claim = lock_claim(claim_id, user)
    if claim.status == "pending" and user.pk != claim.applicant_id:
        forbidden()
    if claim.status == "cancelled":
        if claim.cancellation_stage == "pending" and user.pk != claim.applicant_id:
            forbidden()
        return claim
    if claim.status not in {"pending", "accepted"}:
        conflict()
    if claim.applicant_confirmed_at or claim.publisher_confirmed_at:
        conflict("已有一方确认交接，不能取消；请由另一方确认")
    claim.cancellation_stage = claim.status
    if claim.status == "accepted":
        claim.post = post_services.set_handover_state(post.pk, "reopen")
    elif post.status != "open":
        conflict()
    claim.status = "cancelled"
    claim.save(update_fields=["status", "cancellation_stage", "updated_at"])
    return claim


@transaction.atomic
def confirm_handover(user, claim_id):
    post, claim = lock_claim(claim_id, user)
    if claim.status == "completed":
        return claim
    if claim.status != "accepted" or post.status != "in_handover":
        conflict()
    field = "applicant_confirmed_at" if user.pk == claim.applicant_id else "publisher_confirmed_at"
    if getattr(claim, field) is not None:
        return claim
    setattr(claim, field, timezone.now())
    if claim.applicant_confirmed_at and claim.publisher_confirmed_at:
        claim.status = "completed"
        claim.post = post_services.set_handover_state(post.pk, "complete")
    claim.save(update_fields=[field, "status", "updated_at"])
    return claim
