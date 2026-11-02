from rest_framework import serializers
from common.serializers import StrictSerializer, StringField, IdField, PageQuery
from users.services import user_summary
from posts.serializers import timestamp
from .models import Claim


class CreateClaimInput(StrictSerializer):
    post_id = IdField()
    verification_text = StringField(min_length=10, max_length=1000)


class AcceptInput(StrictSerializer):
    decision_note = StringField(max_length=500, allow_blank=True, required=False, default=None)


class RejectInput(StrictSerializer):
    decision_note = StringField(min_length=1, max_length=500)


class ClaimListQuery(PageQuery):
    role = serializers.ChoiceField(choices=["applicant", "publisher"], default="applicant")
    status = serializers.ChoiceField(choices=Claim.Status.values, required=False)
    post_id = IdField(required=False)


class MessageInput(StrictSerializer):
    content = StringField(min_length=1, max_length=1000)


class MessageQuery(StrictSerializer):
    after_id = IdField(required=False)
    limit = serializers.IntegerField(min_value=1, max_value=100, default=50)


class MatchQuery(StrictSerializer):
    limit = serializers.IntegerField(min_value=1, max_value=20, default=10)


def claim_view(claim):
    post = claim.post
    return {
        "id": str(claim.pk), "post_id": str(post.pk), "applicant_id": str(claim.applicant_id),
        "verification_text": claim.verification_text, "status": claim.status,
        "decision_note": claim.decision_note, "close_reason": claim.close_reason,
        "applicant_confirmed_at": timestamp(claim.applicant_confirmed_at),
        "publisher_confirmed_at": timestamp(claim.publisher_confirmed_at),
        "created_at": timestamp(claim.created_at), "updated_at": timestamp(claim.updated_at),
        "applicant": user_summary(claim.applicant), "publisher": user_summary(post.publisher),
        "post": {"id": str(post.pk), "title": post.title, "post_type": post.post_type, "status": post.status},
    }


def message_view(message):
    return {"id": str(message.pk), "claim_id": str(message.claim_id), "sender_id": str(message.sender_id),
            "content": message.content, "created_at": timestamp(message.created_at), "sender": user_summary(message.sender)}
