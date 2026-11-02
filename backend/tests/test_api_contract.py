from datetime import timedelta
from unittest.mock import patch
from django.test import override_settings
from django.urls import clear_url_caches
from django.utils import timezone
from rest_framework.test import APIClient
from users.models import AuthSession
from users.services import issue_session
from .helpers import ClaimsTestCase


class ApiContractTests(ClaimsTestCase):
    def test_bearer_valid_expired_and_revoked_sessions(self):
        token, session = issue_session(self.applicant)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(self.client.get("/api/v1/users/me/claims").status_code, 200)
        self.assertNotEqual(session.token_digest, token)
        session.expires_at = timezone.now() - timedelta(seconds=1); session.save()
        self.assert_error(self.client.get("/api/v1/users/me/claims"), 401, "UNAUTHENTICATED")
        token, session = issue_session(self.applicant)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(self.client.post("/api/v1/auth/logout", {}, format="json").status_code, 200)
        self.assert_error(self.client.get("/api/v1/users/me/claims"), 401, "UNAUTHENTICATED")

    def test_bad_bearer_even_on_public_post_is_rejected(self):
        for header in ("Bearer invalid", "Token invalid", "Bearer x extra"):
            self.client.credentials(HTTP_AUTHORIZATION=header)
            self.assert_error(self.client.get(f"/api/v1/posts/{self.post.pk}"), 401, "UNAUTHENTICATED")

    def test_malformed_json_and_content_type_have_envelopes(self):
        self.login_as(self.applicant)
        response = self.client.post("/api/v1/claims", '{"post_id":', content_type="application/json")
        self.assert_error(response, 400, "VALIDATION_ERROR")
        response = self.client.post("/api/v1/claims", 'post_id=1', content_type="text/plain")
        self.assert_error(response, 415, "UNSUPPORTED_MEDIA_TYPE")

    def test_internal_error_does_not_leak_details(self):
        self.login_as(self.applicant)
        with patch("claims.views.my_claims", side_effect=RuntimeError("private database path and SQL")):
            with self.assertLogs("common.exceptions", level="ERROR"):
                result = self.client.get("/api/v1/users/me/claims")
        self.assert_error(result, 500, "INTERNAL_ERROR")
        self.assertNotIn("private database", str(result.data))

    def test_login_response_and_independent_sessions(self):
        response = self.client.post("/api/v1/auth/login", {"username": "APPLICANT", "password": "test-only-123"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["token_type"], "Bearer")
        self.assertNotIn("password", response.data["data"]["user"])
        second = self.client.post("/api/v1/auth/login", {"username": "applicant", "password": "test-only-123"}, format="json")
        self.assertNotEqual(response.data["data"]["access_token"], second.data["data"]["access_token"])
        self.assertEqual(AuthSession.objects.filter(user=self.applicant).count(), 2)
