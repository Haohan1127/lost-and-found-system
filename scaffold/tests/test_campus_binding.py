"""验收基线：校园身份绑定（TC-A-029～039 的骨架版）。

启用方式：
    Copy-Item scaffold\\tests\\test_campus_binding.py backend\\users\\tests\\test_campus_binding.py
    .\\.venv\\Scripts\\python.exe backend\\manage.py test users.tests.test_campus_binding -v 2

前置：D2-02（bind_campus + binding_view + 视图）、D2-04（seed 命令）完成后应全绿。
"""
import hashlib

from django.test import override_settings

from catalog.models import Campus
from users.models import CampusBinding, DemoIdentity
from . import UserApiTestCase

BINDING = "/api/v1/users/me/campus-binding"
ME = "/api/v1/users/me"
CODE = "demo-binding-0001"


class CampusBindingTests(UserApiTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user()
        self.campus = Campus.objects.create(pk="campus_main", name="主校区")
        self.identity = DemoIdentity.objects.create(
            campus=self.campus, student_no="20260004",
            code_digest=hashlib.sha256(CODE.encode()).hexdigest())
        self.use_token(self.login_token())

    def payload(self, **changes):
        data = {"campus_id": "campus_main", "student_no": "20260004", "binding_code": CODE}
        data.update(changes)
        return data

    def bind(self, **changes):
        return self.client.post(BINDING, self.payload(**changes), format="json")

    def test_get_unbound_returns_null(self):
        response = self.client.get(BINDING)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNone(response.data["data"])

    def test_bind_success(self):
        response = self.bind()
        self.assertEqual(response.status_code, 201, response.data)
        data = response.data["data"]
        self.assertEqual(data["campus_id"], "campus_main")
        self.assertEqual(data["student_no_masked"], "****0004")
        self.assertEqual(data["verification_mode"], "demo")
        self.assertTrue(data["verified_at"])
        # 数据库侧：绑定记录、身份占用、用户认证标记
        self.assertTrue(CampusBinding.objects.filter(user=self.user, campus=self.campus, student_no="20260004").exists())
        self.identity.refresh_from_db()
        self.assertEqual(self.identity.used_by_id, self.user.pk)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_campus_verified)
        self.assertEqual(self.user.verification_mode, "demo")
        # 本人资料接口同步反映认证状态
        self.assertTrue(self.client.get(ME).data["data"]["is_campus_verified"])
        # 再次 GET 返回脱敏绑定
        self.assertEqual(self.client.get(BINDING).data["data"]["student_no_masked"], "****0004")

    def test_bind_wrong_code_returns_400(self):
        response = self.bind(binding_code="wrong-code-0001")
        self.assert_error(response, 400, "VALIDATION_ERROR")
        self.assertIn("binding_code", response.data["errors"])
        self.assertFalse(CampusBinding.objects.exists())

    def test_bind_unknown_identity_returns_400(self):
        response = self.bind(student_no="20269999")
        self.assert_error(response, 400, "VALIDATION_ERROR")
        self.assertIn("binding_code", response.data["errors"])

    def test_bind_unknown_campus_returns_400(self):
        response = self.bind(campus_id="campus_unknown")
        self.assert_error(response, 400, "VALIDATION_ERROR")
        self.assertIn("campus_id", response.data["errors"])

    def test_second_bind_returns_409(self):
        self.assertEqual(self.bind().status_code, 201)
        self.assert_error(self.bind(), 409, "DUPLICATE_RESOURCE")

    def test_identity_taken_by_other_returns_409(self):
        other = self.make_user(username="other")
        CampusBinding.objects.create(user=other, campus=self.campus, student_no="20260004")
        self.identity.used_by = other
        self.identity.save(update_fields=["used_by"])
        self.assert_error(self.bind(), 409, "DUPLICATE_RESOURCE")

    def test_requires_login(self):
        self.client.credentials()
        self.assert_error(self.client.post(BINDING, self.payload(), format="json"), 401, "UNAUTHENTICATED")
        self.assert_error(self.client.get(BINDING), 401, "UNAUTHENTICATED")

    @override_settings(RATE_LIMIT_ENABLED=True, BINDING_RATE_LIMIT=2)
    def test_binding_rate_limited_after_limit(self):
        for _ in range(2):
            self.assertEqual(self.bind(binding_code="wrong-code-0001").status_code, 400)
        blocked = self.bind(binding_code="wrong-code-0001")
        self.assert_error(blocked, 429, "RATE_LIMITED")
        self.assertIn("Retry-After", blocked.headers)
