from claims.models import ClaimMessage
from .helpers import ClaimsTestCase


class MessageTests(ClaimsTestCase):
    def test_both_participants_can_send_and_read_in_order(self):
        claim = self.apply()
        for user, content in ((self.applicant, "我的钥匙共有三把"), (self.publisher, "请描述一下挂件")):
            self.login_as(user)
            response = self.client.post(f"/api/v1/claims/{claim.pk}/messages", {"content": content}, format="json")
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.data["data"]["sender_id"], str(user.pk))
        data = self.client.get(f"/api/v1/claims/{claim.pk}/messages").data["data"]
        self.assertEqual([item["content"] for item in data["items"]], ["我的钥匙共有三把", "请描述一下挂件"])
        self.assertFalse(data["has_more"])

    def test_nonparticipant_cannot_read_or_send(self):
        claim = self.apply()
        self.login_as(self.other)
        self.assert_error(self.client.get(f"/api/v1/claims/{claim.pk}/messages"), 404, "NOT_FOUND")
        self.assert_error(self.client.post(f"/api/v1/claims/{claim.pk}/messages", {"content": "非法读取"}, format="json"), 404, "NOT_FOUND")
        self.assertEqual(ClaimMessage.objects.count(), 0)

    def test_message_length_trim_and_readonly_fields(self):
        claim = self.apply()
        for body in ({"content": "  "}, {"content": "字" * 1001}, {"content": 123}, {"content": "正常", "sender_id": str(self.publisher.pk)}):
            self.assert_error(self.client.post(f"/api/v1/claims/{claim.pk}/messages", body, format="json"), 400, "VALIDATION_ERROR")
        result = self.client.post(f"/api/v1/claims/{claim.pk}/messages", {"content": "  <script>alert(1)</script>  "}, format="json")
        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.data["data"]["content"], "<script>alert(1)</script>")

    def test_cursor_batches_empty_and_cross_conversation(self):
        claim = self.apply()
        rows = [ClaimMessage.objects.create(claim=claim, sender=self.applicant, content=f"消息{i}") for i in range(3)]
        other_claim = self.apply(post=self.make_post())
        foreign = ClaimMessage.objects.create(claim=other_claim, sender=self.applicant, content="另一会话")
        url = f"/api/v1/claims/{claim.pk}/messages"
        first = self.client.get(url + "?limit=2").data["data"]
        self.assertEqual([item["id"] for item in first["items"]], [str(row.pk) for row in rows[:2]])
        self.assertTrue(first["has_more"])
        second = self.client.get(url + f"?after_id={first['next_after_id']}&limit=2").data["data"]
        self.assertEqual([item["id"] for item in second["items"]], [str(rows[-1].pk)])
        empty = self.client.get(url + f"?after_id={rows[-1].pk}").data["data"]
        self.assertEqual(empty, {"items": [], "next_after_id": str(rows[-1].pk), "has_more": False})
        for query in (f"after_id={foreign.pk}", "after_id=no-such-message", "limit=0", "limit=101", "limit=1.1", "unknown=1"):
            self.assert_error(self.client.get(url + "?" + query), 400, "VALIDATION_ERROR")
        # BigAutoField 的 19 位合法 ID 也必须支持，不能用浮点数或截位比较。
        big_id = "9007199254740992001"
        ClaimMessage.objects.create(id=int(big_id), claim=claim, sender=self.applicant, content="大 ID 消息")
        self.assertEqual(self.client.get(url + f"?after_id={big_id}").data["data"]["next_after_id"], big_id)
        self.assert_error(self.client.get(url + "?after_id=9223372036854775808"), 400, "VALIDATION_ERROR")

    def test_empty_conversation_cursor_is_null(self):
        claim = self.apply()
        self.assertEqual(self.client.get(f"/api/v1/claims/{claim.pk}/messages").data["data"], {"items": [], "next_after_id": None, "has_more": False})

    def test_terminal_claims_keep_history_but_reject_new_messages(self):
        for status in ("rejected", "cancelled", "closed", "completed"):
            with self.subTest(status=status):
                claim = self.apply(post=self.make_post())
                ClaimMessage.objects.create(claim=claim, sender=self.applicant, content="原有历史")
                if status == "completed":
                    self.action(claim, "accept")
                    self.action(claim, "confirm-handover", self.applicant)
                    self.action(claim, "confirm-handover")
                elif status == "closed":
                    from workflows.post_workflow import withdraw_post
                    withdraw_post(self.publisher, claim.post_id)
                else:
                    self.action(claim, "reject" if status == "rejected" else "cancel", self.publisher if status == "rejected" else self.applicant, {"decision_note": "特征不符合"} if status == "rejected" else {})
                self.login_as(self.applicant)
                url = f"/api/v1/claims/{claim.pk}/messages"
                self.assertEqual(len(self.client.get(url).data["data"]["items"]), 1)
                self.assert_error(self.client.post(url, {"content": "终态新消息"}, format="json"), 409, "STATE_CONFLICT")
