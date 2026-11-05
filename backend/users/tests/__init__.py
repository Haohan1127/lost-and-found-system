"""users 接口测试包：共享基类。

- 每个用例前清空限流缓存，避免限流用例互相污染；
- 测试专用弱哈希器只是为了 100+ 用例不必为每次密码校验付真实 PBKDF2 成本，不影响生产配置。
"""
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase

from users.models import User


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class UserApiTestCase(APITestCase):
    def setUp(self):
        cache.clear()

    def make_user(self, username="member", password="member-pass-123", **kwargs):
        kwargs.setdefault("nickname", "成员")
        return User.objects.create_user(username=username, password=password, **kwargs)

    def login_token(self, username="member", password="member-pass-123"):
        response = self.client.post("/api/v1/auth/login", {"username": username, "password": password}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        return response.data["data"]["access_token"]

    def use_token(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
