from django.db import transaction
from common.exceptions import conflict
from workflows.claim_workflow import lock_claim
from .models import ClaimMessage


@transaction.atomic
def send_message(user, claim_id, content):
    post, claim = lock_claim(claim_id, user)
    if claim.status not in {"pending", "accepted"} or post.status not in {"open", "in_handover"}:
        conflict("申请已结束，仅可阅读历史消息")
    return ClaimMessage.objects.create(claim=claim, sender=user, content=content)
