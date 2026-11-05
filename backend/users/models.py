from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """用户主表：在 Django 自带 User 基础上补昵称、简介与认证标记。

    - nickname：1～30 字，必填（注册时写入）
    - bio：0～200 字，可为空
    - is_campus_verified / verification_mode：认证结果只允许服务端写，客户端不可提交
    """
    nickname = models.CharField(max_length=30)
    bio = models.CharField(max_length=200, blank=True)
    is_campus_verified = models.BooleanField(default=False)
    verification_mode = models.CharField(max_length=16, null=True, default=None)
    updated_at = models.DateTimeField(auto_now=True)


class AuthSession(models.Model):
    """一次登录对应一条会话：只存令牌的 SHA-256 摘要，不存明文令牌。"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token_digest = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()


# ==== 以下两个模型由规划表 D2-01/D2-02 使用；结构与 docs/数据库设计.md 一致，可直接沿用。 ====


class CampusBinding(models.Model):
    """校园身份绑定：一个用户最多一条；同一校区内学号唯一。

    迁移已随脚手架提供（0002_campusbinding_demoidentity.py），修改字段前先想清楚迁移影响。
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="campus_binding")
    campus = models.ForeignKey("catalog.Campus", on_delete=models.PROTECT)
    student_no = models.CharField(max_length=20)
    verification_mode = models.CharField(max_length=16, default="demo")
    verified_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["campus", "student_no"], name="uniq_campus_student_no")]
        ordering = ["-verified_at"]


class DemoIdentity(models.Model):
    """演示用一次性校园身份：只存绑定码摘要（SHA-256），used_by 非空表示已被占用。"""
    campus = models.ForeignKey("catalog.Campus", on_delete=models.PROTECT)
    student_no = models.CharField(max_length=20)
    code_digest = models.CharField(max_length=64)
    used_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["campus", "student_no"], name="uniq_demo_identity")]
