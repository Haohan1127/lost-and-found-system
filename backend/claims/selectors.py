from common.exceptions import missing
from common.serializers import numeric_id
from .models import Claim, ClaimMessage
from .permissions import require_participant


def claim_queryset():
    return Claim.objects.select_related("applicant", "post__publisher")


def get_claim(claim_id, user):
    try:
        claim = claim_queryset().filter(pk=claim_id).first()
    except (ValueError, OverflowError):
        claim = None
    if claim is None:
        missing()
    require_participant(claim, user)
    return claim


def my_claims(user, query):
    filters = {"applicant_id" if query["role"] == "applicant" else "post__publisher_id": user.pk}
    if "status" in query:
        filters["status"] = query["status"]
    if "post_id" in query:
        post_id = numeric_id(query["post_id"])
        if post_id is None:
            return claim_queryset().none()
        filters["post_id"] = post_id
    return claim_queryset().filter(**filters).order_by("-created_at", "-id")


def message_batch(claim, query):
    after_id = query.get("after_id")
    queryset = ClaimMessage.objects.filter(claim=claim).select_related("sender").order_by("id")
    if after_id is not None:
        from rest_framework.exceptions import ValidationError
        parsed_id = numeric_id(after_id)
        if parsed_id is None or not queryset.filter(pk=parsed_id).exists():
            raise ValidationError({"after_id": ["必须是本会话已有消息的 ID"]})
        queryset = queryset.filter(pk__gt=parsed_id)
    rows = list(queryset[:query["limit"] + 1])
    has_more = len(rows) > query["limit"]
    rows = rows[:query["limit"]]
    return rows, str(rows[-1].pk) if rows else after_id, has_more
