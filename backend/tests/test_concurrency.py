from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.db import close_old_connections, connections
from django.test import TransactionTestCase
from rest_framework.test import APIClient
from claims.models import Claim, ClaimMessage
from .helpers import DataMixin


class ConcurrencyTests(DataMixin, TransactionTestCase):
    def setUp(self):
        self.create_data()

    def race(self, operations):
        barrier = Barrier(len(operations))
        def run(operation):
            close_old_connections()
            client = APIClient()
            user, path, body = operation
            client.force_authenticate(user)
            try:
                barrier.wait(timeout=10)
                response = client.post(path, body, format="json")
                return response.status_code, response.data
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=len(operations)) as pool:
            return list(pool.map(run, operations))

    def test_same_user_concurrent_create_has_one_winner(self):
        body = {"post_id": str(self.post.pk), "verification_text": "这是我的蓝色钥匙和小熊挂件"}
        responses = self.race([(self.applicant, "/api/v1/claims", body)] * 2)
        self.assertEqual(sorted(code for code, _ in responses), [201, 409], responses)
        self.assertEqual(Claim.objects.filter(status="pending").count(), 1)

    def test_concurrent_accept_has_only_one_winner(self):
        first = Claim.objects.create(post=self.post, applicant=self.applicant, verification_text="原申请")
        second = Claim.objects.create(post=self.post, applicant=self.other, verification_text="竞争申请")
        responses = self.race([(self.publisher, f"/api/v1/claims/{claim.pk}/accept", {}) for claim in (first, second)])
        self.assertEqual(sorted(code for code, _ in responses), [200, 409], responses)
        self.assertEqual(Claim.objects.filter(post=self.post, status="accepted").count(), 1)
        self.assertEqual(Claim.objects.filter(post=self.post, status="closed").count(), 1)
        self.post.refresh_from_db()
        self.assertEqual(self.post.status, "in_handover")

    def test_concurrent_confirm_completes_both_records(self):
        claim = Claim.objects.create(post=self.post, applicant=self.applicant, verification_text="证明", status="accepted")
        self.post.status = "in_handover"; self.post.save()
        path = f"/api/v1/claims/{claim.pk}/confirm-handover"
        responses = self.race([(self.publisher, path, {}), (self.applicant, path, {})])
        self.assertEqual([code for code, _ in responses], [200, 200], responses)
        claim.refresh_from_db(); self.post.refresh_from_db()
        self.assertEqual((claim.status, self.post.status), ("completed", "completed"))
        self.assertIsNotNone(claim.applicant_confirmed_at)
        self.assertIsNotNone(claim.publisher_confirmed_at)

    def test_withdraw_racing_send_never_writes_after_closure(self):
        claim = Claim.objects.create(post=self.post, applicant=self.applicant, verification_text="证明")
        responses = self.race([
            (self.publisher, f"/api/v1/demo/posts/{self.post.pk}/withdraw", {}),
            (self.applicant, f"/api/v1/claims/{claim.pk}/messages", {"content": "交接时间？"}),
        ])
        self.assertEqual(responses[0][0], 200, responses)
        self.assertIn(responses[1][0], [201, 409], responses)
        claim.refresh_from_db()
        self.assertEqual(claim.status, "closed")
        messages = ClaimMessage.objects.filter(claim=claim)
        self.assertEqual(messages.count(), int(responses[1][0] == 201))
        if messages.exists():
            self.assertLessEqual(messages.first().created_at, claim.updated_at)
