from django.conf import settings
from django.db import models
from django.db.models import Q


class Claim(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "待核实"
        ACCEPTED = "accepted", "等待交接"
        REJECTED = "rejected", "已拒绝"
        CANCELLED = "cancelled", "已取消"
        COMPLETED = "completed", "已完成"
        CLOSED = "closed", "已关闭"

    post = models.ForeignKey("posts.Post", on_delete=models.PROTECT, related_name="claims")
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="claims")
    verification_text = models.TextField(max_length=1000)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    decision_note = models.CharField(max_length=500, null=True)
    close_reason = models.CharField(max_length=32, null=True)
    applicant_confirmed_at = models.DateTimeField(null=True)
    publisher_confirmed_at = models.DateTimeField(null=True)
    # 内部字段，保留取消时的权限语义，不返回 API。
    cancellation_stage = models.CharField(max_length=16, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["post", "status"]), models.Index(fields=["applicant", "status", "created_at"])]
        constraints = [
            models.UniqueConstraint(fields=["post", "applicant"], condition=Q(status__in=["pending", "accepted"]), name="unique_active_applicant"),
            models.UniqueConstraint(fields=["post"], condition=Q(status="accepted"), name="unique_accepted_post"),
            models.CheckConstraint(condition=Q(status__in=["pending", "accepted", "rejected", "cancelled", "completed", "closed"]), name="claim_valid_status"),
            models.CheckConstraint(condition=(Q(status="closed", close_reason__isnull=False, close_reason__in=["post_withdrawn", "another_claim_accepted"]) | (~Q(status="closed") & Q(close_reason__isnull=True))), name="claim_close_reason_consistent"),
            models.CheckConstraint(condition=(
                Q(status="completed", applicant_confirmed_at__isnull=False, publisher_confirmed_at__isnull=False)
                | (Q(status="accepted") & (Q(applicant_confirmed_at__isnull=True) | Q(publisher_confirmed_at__isnull=True)))
                | (~Q(status__in=["accepted", "completed"]) & Q(applicant_confirmed_at__isnull=True, publisher_confirmed_at__isnull=True))
            ), name="claim_confirmation_consistent"),
        ]


class ClaimMessage(models.Model):
    claim = models.ForeignKey(Claim, on_delete=models.PROTECT, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    content = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        indexes = [models.Index(fields=["claim", "id"])]
