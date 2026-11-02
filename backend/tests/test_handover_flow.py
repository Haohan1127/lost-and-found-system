from unittest.mock import patch
from workflows import claim_workflow, post_workflow
from claims.models import Claim
from posts import services as post_services
from .helpers import ClaimsTestCase


class HandoverTests(ClaimsTestCase):
    def test_accept_closes_other_claims_and_reserves_post(self):
        first = self.apply()
        second = self.apply(self.other)
        result = self.action(first, "accept", body={"decision_note": "请来图书馆交接"})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data["data"]["post"]["status"], "in_handover")
        second.refresh_from_db()
        self.assertEqual((second.status, second.close_reason), ("closed", "another_claim_accepted"))
        self.assert_error(self.action(second, "accept"), 409, "STATE_CONFLICT")

    def test_accept_repeat_does_not_replace_note(self):
        claim = self.apply()
        self.action(claim, "accept", body={"decision_note": "第一次说明"})
        result = self.action(claim, "accept", body={"decision_note": "第二次说明"})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data["data"]["decision_note"], "第一次说明")

    def test_bilateral_confirmation_and_utc_time(self):
        from datetime import datetime
        claim = self.apply()
        self.action(claim, "accept")
        first = self.action(claim, "confirm-handover", self.applicant).data["data"]
        self.assertEqual((first["status"], first["post"]["status"]), ("accepted", "in_handover"))
        self.assertIsNone(first["publisher_confirmed_at"])
        claim.refresh_from_db()
        self.assertEqual(datetime.fromisoformat(first["applicant_confirmed_at"].replace("Z", "+00:00")), claim.applicant_confirmed_at)
        self.assertEqual(self.action(claim, "confirm-handover", self.applicant).data["data"]["applicant_confirmed_at"], first["applicant_confirmed_at"])
        final = self.action(claim, "confirm-handover").data["data"]
        self.assertEqual((final["status"], final["post"]["status"]), ("completed", "completed"))
        self.post.refresh_from_db()
        self.assertIsNotNone(self.post.completed_at)
        self.assertEqual(self.action(claim, "confirm-handover").data["data"], final)
        self.assert_error(self.action(claim, "accept"), 409, "STATE_CONFLICT")

    def test_publisher_can_confirm_first(self):
        claim = self.apply()
        self.action(claim, "accept")
        self.action(claim, "confirm-handover")
        final = self.action(claim, "confirm-handover", self.applicant)
        self.assertEqual(final.data["data"]["status"], "completed")

    def test_pending_confirmation_not_allowed_and_empty_body_enforced(self):
        claim = self.apply()
        self.assert_error(self.action(claim, "confirm-handover", self.applicant), 409, "STATE_CONFLICT")
        self.assert_error(self.action(claim, "confirm-handover", self.applicant, {"publisher_confirmed_at": "2026-01-01"}), 400, "VALIDATION_ERROR")

    def test_cancel_accepted_reopens_without_reviving_competitor(self):
        claim = self.apply()
        rival = self.apply(self.other)
        self.action(claim, "accept")
        response = self.action(claim, "cancel")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["post"]["status"], "open")
        self.assertEqual(self.action(claim, "cancel", self.applicant).status_code, 200)
        rival.refresh_from_db()
        self.assertEqual(rival.status, "closed")
        self.assertEqual(self.apply().status, "pending")

    def test_applicant_can_cancel_accepted(self):
        claim = self.apply()
        self.action(claim, "accept")
        self.assertEqual(self.action(claim, "cancel", self.applicant).data["data"]["status"], "cancelled")

    def test_single_confirmation_blocks_cancel_withdraw_and_restore(self):
        claim = self.apply()
        self.action(claim, "accept")
        self.action(claim, "confirm-handover", self.applicant)
        for actor in (self.applicant, self.publisher):
            self.assert_error(self.action(claim, "cancel", actor), 409, "STATE_CONFLICT")
        for function in (post_workflow.withdraw_post, post_workflow.restore_post):
            with self.assertRaisesMessage(Exception, "当前状态"):
                function(self.publisher, self.post.pk)

    def test_accept_failure_rolls_back_all_three_changes(self):
        claim = self.apply()
        rival = self.apply(self.other)
        original = post_services.set_handover_state
        def fail_after_write(*args):
            original(*args)
            raise RuntimeError("模拟信息状态写入后的失败")
        with patch("workflows.claim_workflow.post_services.set_handover_state", side_effect=fail_after_write):
            with self.assertRaises(RuntimeError):
                claim_workflow.accept_claim(self.publisher, claim.pk)
        claim.refresh_from_db(); rival.refresh_from_db(); self.post.refresh_from_db()
        self.assertEqual((claim.status, rival.status, self.post.status), ("pending", "pending", "open"))
        self.assertIsNone(rival.close_reason)

    def test_confirmation_failure_rolls_back_both_times_and_post(self):
        claim = self.apply()
        self.action(claim, "accept")
        self.action(claim, "confirm-handover", self.applicant)
        original = post_services.set_handover_state
        def fail_after_write(*args):
            original(*args)
            raise RuntimeError("模拟完成后的失败")
        with patch("workflows.claim_workflow.post_services.set_handover_state", side_effect=fail_after_write):
            with self.assertRaises(RuntimeError):
                claim_workflow.confirm_handover(self.publisher, claim.pk)
        claim.refresh_from_db(); self.post.refresh_from_db()
        self.assertEqual((claim.status, self.post.status), ("accepted", "in_handover"))
        self.assertIsNone(claim.publisher_confirmed_at)
        self.assertIsNone(self.post.completed_at)

    def test_withdraw_and_restore_preserve_history(self):
        claim = self.apply()
        rival = self.apply(self.other)
        post_workflow.withdraw_post(self.publisher, self.post.pk)
        self.login_as(self.applicant)
        self.assert_error(self.client.get(f"/api/v1/posts/{self.post.pk}"), 404, "NOT_FOUND")
        data = self.client.get(f"/api/v1/claims/{claim.pk}").data["data"]
        self.assertEqual((data["status"], data["close_reason"], data["post"]["status"]), ("closed", "post_withdrawn", "withdrawn"))
        post_workflow.restore_post(self.publisher, self.post.pk)
        claim.refresh_from_db(); rival.refresh_from_db()
        self.assertEqual((claim.status, rival.status), ("closed", "closed"))
        self.assertEqual(self.apply().status, "pending")

    def test_withdraw_failure_rolls_back_claims_and_post(self):
        claim = self.apply()
        original = post_workflow.close_pending_claims
        def fail_after_write(*args):
            original(*args)
            raise RuntimeError("模拟关闭申请后的失败")
        with patch("workflows.post_workflow.close_pending_claims", side_effect=fail_after_write):
            with self.assertRaises(RuntimeError):
                post_workflow.withdraw_post(self.publisher, self.post.pk)
        claim.refresh_from_db(); self.post.refresh_from_db()
        self.assertEqual((claim.status, self.post.status), ("pending", "open"))
