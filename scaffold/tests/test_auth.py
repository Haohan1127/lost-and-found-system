"""验收基线：注册 / 登录 / 登出 / 本人资料（TC-A-001～028 的骨架版）。

启用方式（复制到 users/tests/ 后运行）：
    Copy-Item scaffold\\tests\\test_auth.py backend\\users\\tests\\test_auth.py
    .\\.venv\\Scripts\\python.exe backend\\manage.py test users.tests.test_auth -v 2

先红后绿：D1-03 完成后 RegisterTests 转绿；D1-04 完成后 LoginTests 转绿，以此类推。
断言口径来自 docs/共同字段与接口约定.md §4 与 A 的需求规格说明书。
"""
from datetime import timedelta

from django.test import override_settings
from django.utils import timezone

from users.models import AuthSession, User
from users.services import issue_session
from . import UserApiTestCase

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/users/me"


class RegisterTests(UserApiTestCase):
    def test_register_returns_201_user_self_without_password(self):
        response = self.client.post(
            REGISTER, {"username": "Student_1", "password": "pass-1234", "nickname": "新同学"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["code"], "OK")
        data = response.data["data"]
        # 账号统一小写
        self.assertEqual(data["username"], "student_1")
        self.assertEqual(data["nickname"], "新同学")
        self.assertFalse(data["is_campus_verified"])
        self.assertIsNone(data["verification_mode"])
        self.assertEqual(
            set(data), {"id", "username", "nickname", "bio", "is_campus_verified", "verification_mode", "created_at", "updated_at"})
        self.assertNotIn("password", data)
        self.assertEqual(User.objects.get(username="student_1").nickname, "新同学")
        # 密码必须是哈希，不是明文
        user = User.objects.get(username="student_1")
        self.assertNotEqual(user.password, "pass-1234")
        self.assertTrue(user.check_password("pass-1234"))

    def test_register_does_not_auto_login(self):
        self.client.post(REGISTER, {"username": "student_1", "password": "pass-1234", "nickname": "新同学"}, format="json")
        self.assertEqual(AuthSession.objects.count(), 0)

    def test_duplicate_username_returns_409(self):
        self.make_user(username="student_1")
        response = self.client.post(
            REGISTER, {"username": "STUDENT_1", "password": "pass-1234", "nickname": "再来一个"}, format="json")
        self.assert_error(response, 409, "DUPLICATE_RESOURCE")

    def test_invalid_fields_return_400_with_field_errors(self):
        cases = [
            ({"username": "ab", "password": "pass-1234", "nickname": "x"}, "username"),
            ({"username": "bad name", "password": "pass-1234", "nickname": "x"}, "username"),
            ({"username": "student_1", "password": "short", "nickname": "x"}, "password"),
            ({"username": "student_1", "password": "pass-1234", "nickname": ""}, "nickname"),
        ]
        for payload, field in cases:
            with self.subTest(field=field):
                response = self.client.post(REGISTER, payload, format="json")
                self.assert_error(response, 400, "VALIDATION_ERROR")
                self.assertIn(field, response.data["errors"])

    def test_unknown_or_readonly_field_returns_400(self):
        response = self.client.post(
            REGISTER,
            {"username": "student_1", "password": "pass-1234", "nickname": "x", "is_campus_verified": True},
            format="json")
        self.assert_error(response, 400, "VALIDATION_ERROR")
        self.assertIn("is_campus_verified", response.data["errors"])


class LoginTests(UserApiTestCase):
    def test_login_returns_token_and_stores_only_digest(self):
        self.make_user()
        response = self.client.post(LOGIN, {"username": "Member", "password": "member-pass-123"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data["data"]
        self.assertEqual(data["token_type"], "Bearer")
        self.assertTrue(data["access_token"])
        self.assertTrue(data["expires_at"])
        self.assertEqual(data["user"]["username"], "member")
        session = AuthSession.objects.get(user__username="member")
        self.assertNotEqual(session.token_digest, data["access_token"])
        self.assertEqual(len(session.token_digest), 64)

    def test_wrong_password_and_unknown_user_share_same_401(self):
        self.make_user()
        wrong = self.client.post(LOGIN, {"username": "member", "password": "wrong-pass-123"}, format="json")
        unknown = self.client.post(LOGIN, {"username": "nobody", "password": "wrong-pass-123"}, format="json")
        for response in (wrong, unknown):
            self.assert_error(response, 401, "UNAUTHENTICATED")
        self.assertEqual(wrong.data["message"], unknown.data["message"])

    @override_settings(RATE_LIMIT_ENABLED=True, LOGIN_RATE_LIMIT=2)
    def test_login_rate_limited_after_limit(self):
        self.make_user()
        for _ in range(2):
            self.assertEqual(
                self.client.post(LOGIN, {"username": "member", "password": "member-pass-123"}, format="json").status_code,
                200)
        blocked = self.client.post(LOGIN, {"username": "member", "password": "member-pass-123"}, format="json")
        self.assert_error(blocked, 429, "RATE_LIMITED")
        self.assertIn("Retry-After", blocked.headers)


class LogoutTests(UserApiTestCase):
    def test_logout_revokes_only_current_session(self):
        self.make_user()
        first = self.login_token()
        second = self.login_token()
        self.use_token(first)
        self.assertEqual(self.client.post(LOGOUT, {}, format="json").status_code, 200)
        self.use_token(first)
        self.assert_error(self.client.get(ME), 401, "UNAUTHENTICATED")
        self.use_token(second)
        self.assertEqual(self.client.get(ME).status_code, 200)

    def test_logout_requires_login(self):
        self.assert_error(self.client.post(LOGOUT, {}, format="json"), 401, "UNAUTHENTICATED")


class MeTests(UserApiTestCase):
    def test_me_requires_login(self):
        self.assert_error(self.client.get(ME), 401, "UNAUTHENTICATED")

    def test_me_returns_current_profile(self):
        user = self.make_user(nickname="原昵称", bio="原简介")
        self.use_token(self.login_token())
        response = self.client.get(ME)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["id"], str(user.pk))
        self.assertEqual(response.data["data"]["nickname"], "原昵称")
        self.assertNotIn("password", response.data["data"])

    def test_patch_nickname_and_bio_persist(self):
        self.make_user()
        self.use_token(self.login_token())
        response = self.client.patch(ME, {"nickname": "新昵称", "bio": "新简介"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["data"]["nickname"], "新昵称")
        self.assertEqual(self.client.get(ME).data["data"]["bio"], "新简介")

    def test_patch_trims_whitespace(self):
        self.make_user()
        self.use_token(self.login_token())
        response = self.client.patch(ME, {"nickname": "  小 明  "}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["data"]["nickname"], "小 明")

    def test_patch_rejects_readonly_and_unknown_fields(self):
        self.make_user()
        self.use_token(self.login_token())
        for payload in ({"is_campus_verified": True}, {"username": "hacker"}, {"unknown_field": "x"}):
            with self.subTest(payload=payload):
                self.assert_error(self.client.patch(ME, payload, format="json"), 400, "VALIDATION_ERROR")

    def test_patch_empty_body_returns_400(self):
        self.make_user()
        self.use_token(self.login_token())
        self.assert_error(self.client.patch(ME, {}, format="json"), 400, "VALIDATION_ERROR")

    def test_patch_boundaries(self):
        self.make_user()
        self.use_token(self.login_token())
        self.assertEqual(self.client.patch(ME, {"nickname": "名" * 30}, format="json").status_code, 200)
        self.assert_error(self.client.patch(ME, {"nickname": "名" * 31}, format="json"), 400, "VALIDATION_ERROR")
        self.assertEqual(self.client.patch(ME, {"bio": "字" * 200}, format="json").status_code, 200)
        self.assert_error(self.client.patch(ME, {"bio": "字" * 201}, format="json"), 400, "VALIDATION_ERROR")

    def test_expired_token_returns_401(self):
        user = self.make_user()
        token, session = issue_session(user)
        session.expires_at = timezone.now() - timedelta(seconds=1)
        session.save(update_fields=["expires_at"])
        self.use_token(token)
        self.assert_error(self.client.get(ME), 401, "UNAUTHENTICATED")
