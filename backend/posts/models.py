from django.conf import settings
from django.db import models


class Post(models.Model):
    class Type(models.TextChoices):
        LOST = "lost", "寻物"
        FOUND = "found", "招领"

    class Status(models.TextChoices):
        OPEN = "open", "进行中"
        IN_HANDOVER = "in_handover", "交接中"
        COMPLETED = "completed", "已完成"
        WITHDRAWN = "withdrawn", "已撤回"

    publisher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    post_type = models.CharField(max_length=8, choices=Type.choices)
    title = models.CharField(max_length=60)
    category = models.ForeignKey("catalog.Category", on_delete=models.PROTECT)
    location = models.ForeignKey("catalog.Location", on_delete=models.PROTECT)
    description = models.TextField(max_length=2000)
    location_detail = models.CharField(max_length=100, blank=True)
    occurred_at = models.DateTimeField()
    handover_note = models.CharField(max_length=200, null=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True)

    @property
    def campus_id(self):
        return self.location.campus_id

    class Meta:
        indexes = [models.Index(fields=["status", "post_type", "category", "occurred_at"])]
        constraints = [
            models.CheckConstraint(condition=models.Q(status__in=["open", "in_handover", "completed", "withdrawn"]), name="post_valid_status"),
            models.CheckConstraint(condition=models.Q(post_type__in=["lost", "found"]), name="post_valid_type"),
        ]
