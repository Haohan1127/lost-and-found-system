from datetime import timedelta
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from users.models import User
from catalog.models import Campus, Category, Location
from posts.models import Post
from claims.models import Claim


class DataMixin:
    @classmethod
    def create_data(cls):
        cls.publisher = User.objects.create_user(username="publisher", password="test-only-123", nickname="拾获者", is_campus_verified=True, verification_mode="demo")
        cls.applicant = User.objects.create_user(username="applicant", password="test-only-123", nickname="失主", is_campus_verified=True, verification_mode="demo")
        cls.other = User.objects.create_user(username="competitor", password="test-only-123", nickname="第三人", is_campus_verified=True, verification_mode="demo")
        cls.unverified = User.objects.create_user(username="unverified", password="test-only-123", nickname="未认证")
        cls.campus = Campus.objects.create(id="main", name="主校区")
        cls.category = Category.objects.create(id="keys", name="钥匙")
        cls.location = Location.objects.create(id="library", name="图书馆", campus=cls.campus)
        cls.post = cls.make_post()

    @classmethod
    def make_post(cls, **changes):
        data = dict(publisher=cls.publisher, post_type="found", title="图书馆蓝色钥匙", category=cls.category,
                    location=cls.location, description="蓝色钥匙，更多细节请通过私有申请核实。", occurred_at=timezone.now() - timedelta(hours=2),
                    handover_note="核实后交接")
        data.update(changes)
        return Post.objects.create(**data)

    def login_as(self, user):
        self.client.force_authenticate(user=user)

    def apply(self, user=None, post=None):
        self.login_as(user or self.applicant)
        response = self.client.post("/api/v1/claims", {"post_id": str((post or self.post).pk), "verification_text": "钥匙共有三把，挂着蓝色小熊挂件。"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return Claim.objects.get(pk=response.data["data"]["id"])

    def action(self, claim, action, user=None, body=None):
        self.login_as(user or self.publisher)
        return self.client.post(f"/api/v1/claims/{claim.pk}/{action}", body or {}, format="json")

    def assert_error(self, response, status, code):
        self.assertEqual(response.status_code, status, response.data)
        self.assertEqual(response.data["code"], code)
        self.assertIsNone(response.data["data"])
        self.assertIsInstance(response.data["errors"], dict)


class ClaimsTestCase(DataMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.create_data()
