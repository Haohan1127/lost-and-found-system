import hashlib
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from .models import AuthSession


class BearerAuthentication(BaseAuthentication):
    def authenticate(self, request):
        header = get_authorization_header(request).split()
        if not header:
            return None
        if len(header) != 2 or header[0].lower() != b"bearer":
            raise AuthenticationFailed("登录令牌格式错误")
        digest = hashlib.sha256(header[1]).hexdigest()
        session = AuthSession.objects.select_related("user").filter(token_digest=digest, expires_at__gt=timezone.now(), user__is_active=True).first()
        if session is None:
            raise AuthenticationFailed("令牌无效或已过期")
        return session.user, session

    def authenticate_header(self, request):
        return "Bearer"
