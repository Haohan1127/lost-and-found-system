"""FR-A-08/09、NFR-A-05：与成员 C 认领模块的身份集成与回归。"""
import hashlib
import json

from django.core.cache import cache
from django.urls import resolve

from users.models import CampusBinding, DemoIdentity
from users.views import LoginView

from .helpers import ClaimsTestCase


class IdentityIntegrationTests(ClaimsTestCase):
    def setUp(self):
        cache.clear()

    def test_unauthenticated_claim_is_401_fr_a08(self):
        self.client.credentials()
        response = self.client.post(
            "/api/v1/claims", {"post_id": str(self.post.pk), "verification_text": "蓝色钥匙挂着小熊，共三把。"}, format="json")
        self.assert_error(response, 401, "UNAUTHENTICATED")

    def test_unverified_user_gets_403_identity_required_fr_a09(self):
        self.login_as(self.unverified)
        response = self.client.post(
            "/api/v1/claims", {"post_id": str(self.post.pk), "verification_text": "蓝色钥匙挂着小熊，共三把。"}, format="json")
        self.assert_error(response, 403, "IDENTITY_REQUIRED")
        self.assertIn("校园身份", response.data["message"])

    def test_binding_then_claim_succeeds_fr_a09(self):
        code = "integration-code-01"
        DemoIdentity.objects.create(campus=self.campus, student_no="20260004",
                                    code_digest=hashlib.sha256(code.encode()).hexdigest())
        self.login_as(self.unverified)
        response = self.client.post("/api/v1/users/me/campus-binding", {
            "campus_id": self.campus.pk, "student_no": "20260004", "binding_code": code,
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["data"]["student_no_masked"], "****0004")
        self.assertNotIn("20260004", json.dumps(response.data["data"]))
        self.unverified.refresh_from_db()
        self.assertTrue(self.unverified.is_campus_verified)
        self.assertEqual(self.unverified.verification_mode, "demo")
        self.assertTrue(CampusBinding.objects.filter(user=self.unverified).exists())
        self.login_as(self.unverified)
        claim = self.client.post(
            "/api/v1/claims", {"post_id": str(self.post.pk), "verification_text": "蓝色钥匙挂着小熊，共三把。"}, format="json")
        self.assertEqual(claim.status_code, 201, claim.data)

    def test_public_post_user_summary_only_has_public_fields_fr_a09(self):
        self.client.credentials()
        response = self.client.get(f"/api/v1/posts/{self.post.pk}")
        self.assertEqual(response.status_code, 200, response.data)
        publisher = response.data["data"]["publisher"]
        self.assertEqual(set(publisher), {"id", "nickname", "is_campus_verified", "verification_mode"})
        publisher_json = json.dumps(publisher)
        self.assertNotIn(self.publisher.username, publisher_json)
        self.assertNotIn("bio", publisher_json)

    def test_logout_invalidates_token_for_claims_fr_a08(self):
        response = self.client.post(
            "/api/v1/auth/login", {"username": "applicant", "password": "test-only-123"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        token = response.data["data"]["access_token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(self.client.get("/api/v1/users/me/claims").status_code, 200)
        self.assertEqual(self.client.post("/api/v1/auth/logout", {}, format="json").status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assert_error(self.client.get("/api/v1/users/me/claims"), 401, "UNAUTHENTICATED")

    def test_formal_auth_routes_replace_demo_adapters_nfr_a05(self):
        # 路由由 users 正式接口接管，demo 不再挂载登录/登出/本人资料。
        self.assertIs(resolve("/api/v1/auth/login").func.view_class, LoginView)
        self.login_as(self.publisher)
        response = self.client.get("/api/v1/users/me")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["data"]["username"], "publisher")
        # 其余演示接口仍可用（C 的 52 项回归依赖）。
        self.assertEqual(self.client.get("/api/v1/demo/posts").status_code, 200)
