from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """A 的最小身份适配模型；演示认证标记仅由 seed_demo 写入。"""
    nickname = models.CharField(max_length=30)
    bio = models.CharField(max_length=200, blank=True)
    is_campus_verified = models.BooleanField(default=False)
    verification_mode = models.CharField(max_length=16, null=True, default=None)
    updated_at = models.DateTimeField(auto_now=True)


class AuthSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token_digest = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
