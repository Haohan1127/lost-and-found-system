from django.db import IntegrityError, transaction
from claims.models import Claim
from .helpers import ClaimsTestCase


class ClaimRulesTests(ClaimsTestCase):
    def test_anonymous_requires_login(self):
        self.assert_error(self.client.post("/api/v1/claims", {}, format="json"), 401, "UNAUTHENTICATED")

    def test_unverified_cannot_apply(self):
        self.login_as(self.unverified)
        response = self.client.post("/api/v1/claims", {"post_id": str(self.post.pk), "verification_text": "这是我的蓝色钥匙和小熊挂件"}, format="json")
        self.assert_error(response, 403, "IDENTITY_REQUIRED")
        self.assertEqual(Claim.objects.count(), 0)

    def test_lost_post_cannot_be_claimed(self):
        self.login_as(self.applicant)
        post = self.make_post(post_type="lost", handover_note=None)
        response = self.client.post("/api/v1/claims", {"post_id": str(post.pk), "verification_text": "这是我的蓝色钥匙和小熊挂件"}, format="json")
        self.assert_error(response, 400, "VALIDATION_ERROR")

    def test_owner_cannot_apply(self):
        self.login_as(self.publisher)
        response = self.client.post("/api/v1/claims", {"post_id": str(self.post.pk), "verification_text": "这是我的蓝色钥匙和小熊挂件"}, format="json")
        self.assert_error(response, 403, "FORBIDDEN")

    def test_private_or_absent_post_hidden(self):
        self.login_as(self.applicant)
        self.post.status = "withdrawn"
        self.post.save()
        for post_id in (str(self.post.pk), "no-such-post", "99999999999999999999999999999999"):
            with self.subTest(post_id=post_id):
                response = self.client.post("/api/v1/claims", {"post_id": post_id, "verification_text": "这是我的蓝色钥匙和小熊挂件"}, format="json")
                self.assert_error(response, 404, "NOT_FOUND")

    def test_not_open_post_conflicts(self):
        self.login_as(self.applicant)
        for status in ("completed", "in_handover"):
            self.post.status = status
            self.post.save()
            response = self.client.post("/api/v1/claims", {"post_id": str(self.post.pk), "verification_text": "这是我的蓝色钥匙和小熊挂件"}, format="json")
            self.assert_error(response, 409, "STATE_CONFLICT")

    def test_duplicate_active_claim(self):
        self.apply()
        response = self.client.post("/api/v1/claims", {"post_id": str(self.post.pk), "verification_text": "这是再次提交的认领证明文字"}, format="json")
        self.assert_error(response, 409, "DUPLICATE_RESOURCE")
        self.assertEqual(Claim.objects.count(), 1)

    def test_create_fields_limits_and_readonly(self):
        self.login_as(self.applicant)
        base = {"post_id": str(self.post.pk), "verification_text": "这是我的蓝色钥匙和小熊挂件"}
        for extra in ({"status": "completed"}, {"applicant_id": str(self.other.pk)}, {"publisher_id": "99"},
                      {"verification_text": "  太短  "}, {"verification_text": "字" * 1001}, {"verification_text": 1234567890}, {"post_id": self.post.pk}):
            with self.subTest(extra=extra):
                self.assert_error(self.client.post("/api/v1/claims", {**base, **extra}, format="json"), 400, "VALIDATION_ERROR")
        self.assertEqual(Claim.objects.count(), 0)

    def test_trim_and_string_ids(self):
        self.login_as(self.applicant)
        response = self.client.post("/api/v1/claims", {"post_id": str(self.post.pk), "verification_text": "  钥匙共有三把，挂着小熊挂件。  "}, format="json")
        data = response.data["data"]
        self.assertEqual(response.status_code, 201)
        self.assertEqual(data["verification_text"], "钥匙共有三把，挂着小熊挂件。")
        for field in ("id", "post_id", "applicant_id"):
            self.assertIsInstance(data[field], str)
        self.assertNotIn("username", data["applicant"])
        self.assertNotIn("password", str(data))
        self.assertTrue(data["created_at"].endswith("Z"))

    def test_nonparticipant_cannot_read_or_act(self):
        claim = self.apply()
        self.login_as(self.other)
        self.assert_error(self.client.get(f"/api/v1/claims/{claim.pk}"), 404, "NOT_FOUND")
        for action, body in (("accept", {}), ("reject", {"decision_note": "不符合"}), ("cancel", {}), ("confirm-handover", {})):
            self.assert_error(self.action(claim, action, self.other, body), 404, "NOT_FOUND")

    def test_only_publisher_can_review(self):
        claim = self.apply()
        self.assert_error(self.action(claim, "accept", self.applicant), 403, "FORBIDDEN")
        self.assert_error(self.action(claim, "reject", self.applicant, {"decision_note": "拒绝"}), 403, "FORBIDDEN")

    def test_rejection_requires_reason_and_is_idempotent(self):
        claim = self.apply()
        self.assert_error(self.action(claim, "reject"), 400, "VALIDATION_ERROR")
        self.assert_error(self.action(claim, "reject", body={"decision_note": "  "}), 400, "VALIDATION_ERROR")
        result = self.action(claim, "reject", body={"decision_note": "物品特征不符合"})
        self.assertEqual(result.status_code, 200)
        repeated = self.action(claim, "reject", body={"decision_note": "改写说明"})
        self.assertEqual(repeated.data["data"]["decision_note"], "物品特征不符合")
        self.assert_error(self.action(claim, "accept"), 409, "STATE_CONFLICT")
        self.assertEqual(self.apply().status, "pending")

    def test_pending_cancel_only_applicant_and_reapply(self):
        claim = self.apply()
        self.assert_error(self.action(claim, "cancel"), 403, "FORBIDDEN")
        self.assertEqual(self.action(claim, "cancel", self.applicant).data["data"]["status"], "cancelled")
        self.assertEqual(self.action(claim, "cancel", self.applicant).status_code, 200)
        self.assert_error(self.action(claim, "cancel"), 403, "FORBIDDEN")
        self.assertNotEqual(self.apply().pk, claim.pk)

    def test_my_lists_respect_role_filter_and_pagination(self):
        claim = self.apply()
        other_claim = self.apply(self.other)
        self.login_as(self.applicant)
        data = self.client.get("/api/v1/users/me/claims").data["data"]
        self.assertEqual([item["id"] for item in data["items"]], [str(claim.pk)])
        self.assertEqual(self.client.get("/api/v1/users/me/claims?role=publisher").data["data"]["total"], 0)
        self.login_as(self.publisher)
        data = self.client.get("/api/v1/users/me/claims?role=publisher&page_size=1").data["data"]
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["total_pages"], 2)
        self.assertEqual(data["items"][0]["id"], str(other_claim.pk))
        self.assertEqual(self.client.get("/api/v1/users/me/claims?role=publisher&page=99999999999999999999999").data["data"]["items"], [])

    def test_list_validation_and_empty_filters(self):
        self.login_as(self.applicant)
        for query in ("role=admin", "status=open", "page=0", "page_size=101", "page=1.1", "role=applicant&role=publisher", "unknown=1"):
            self.assert_error(self.client.get(f"/api/v1/users/me/claims?{query}"), 400, "VALIDATION_ERROR")
        for query in ("post_id=no-such-id", "post_id=999999999999999999999999", "status=completed"):
            data = self.client.get(f"/api/v1/users/me/claims?{query}").data["data"]
            self.assertEqual(data["total"], 0)
            self.assertEqual(data["total_pages"], 0)

    def test_db_rejects_duplicate_active_and_accepted(self):
        self.apply()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Claim.objects.create(post=self.post, applicant=self.applicant, verification_text="重复申请")
        Claim.objects.filter(post=self.post).update(status="accepted")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Claim.objects.create(post=self.post, applicant=self.other, verification_text="重复同意", status="accepted")

    def test_unknown_action_and_readonly_update_not_available(self):
        claim = self.apply()
        self.assertEqual(self.client.patch(f"/api/v1/claims/{claim.pk}", {"verification_text": "改写"}, format="json").status_code, 405)
        self.assertEqual(self.client.post(f"/api/v1/claims/{claim.pk}/delete", {}, format="json").status_code, 404)
