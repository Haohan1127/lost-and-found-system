import hashlib
import secrets
from datetime import timedelta
from django.utils import timezone
from common.exceptions import BusinessError
from .models import AuthSession, User


def require_campus_verified(user):
    if not user.is_campus_verified:
        raise BusinessError("IDENTITY_REQUIRED", "发起认领前请完成校园身份绑定（当前为演示认证）", 403)


def user_summary(user):
    return {"id": str(user.pk), "nickname": user.nickname,
            "is_campus_verified": user.is_campus_verified, "verification_mode": user.verification_mode}


def get_user_summaries(user_ids):
    return {str(user.pk): user_summary(user) for user in User.objects.filter(pk__in=user_ids)}


def issue_session(user):
    token = secrets.token_urlsafe(32)
    session = AuthSession.objects.create(user=user, token_digest=hashlib.sha256(token.encode()).hexdigest(),
                                         expires_at=timezone.now() + timedelta(hours=24))
    return token, session
