from datetime import timedelta
from django.utils import timezone
from catalog.models import Campus, Category, Location
from claims.matching import title_bigrams
from .helpers import ClaimsTestCase


class MatchingTests(ClaimsTestCase):
    def setUp(self):
        self.source = self.make_post(publisher=self.applicant, post_type="lost", title="蓝 色，钥匙！", occurred_at=self.post.occurred_at - timedelta(hours=1), handover_note=None)
        self.login_as(self.applicant)
        self.url = f"/api/v1/posts/{self.source.pk}/matches"

    def test_score_and_reasons_are_exact_and_public(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        item = response.data["data"]["items"][0]
        self.assertEqual(item["score"], 100)
        self.assertEqual(item["reasons"], ["category_same", "location_same", "time_near", "keyword_overlap"])
        self.assertEqual(set(item["post"]), {"id", "post_type", "title", "category", "campus", "location", "occurred_at", "status", "cover_image", "publisher", "created_at", "updated_at"})
        self.assertNotIn("verification_text", str(item))
        self.assertNotIn("username", item["post"]["publisher"])

    def test_hard_filters_exclude_ineligible_candidates(self):
        other_campus = Campus.objects.create(id="other", name="其他校区")
        other_location = Location.objects.create(id="otherloc", name="其他地点", campus=other_campus)
        other_category = Category.objects.create(id="book", name="书籍")
        for changes in ({"status": "withdrawn"}, {"status": "completed"}, {"status": "in_handover"},
                        {"post_type": "lost"}, {"publisher": self.applicant}, {"location": other_location}, {"category": other_category},
                        {"occurred_at": self.source.occurred_at - timedelta(seconds=1)},
                        {"occurred_at": self.source.occurred_at + timedelta(days=30, seconds=1)}):
            self.make_post(**changes)
        items = self.client.get(self.url).data["data"]["items"]
        self.assertEqual([item["post"]["id"] for item in items], [str(self.post.pk)])

    def test_time_boundaries_and_score_components(self):
        location = Location.objects.create(id="canteen", campus=self.campus, name="食堂")
        at_72 = self.make_post(title="完全不同物品", location=location, occurred_at=self.source.occurred_at + timedelta(hours=72))
        at_30 = self.make_post(title="完全不同物品", location=location, occurred_at=self.source.occurred_at + timedelta(days=30))
        rows = {item["post"]["id"]: item for item in self.client.get(self.url).data["data"]["items"]}
        self.assertEqual(rows[str(at_72.pk)]["score"], 60)
        self.assertEqual(rows[str(at_30.pk)]["score"], 40)

    def test_found_source_applies_time_roles_correctly(self):
        self.login_as(self.publisher)
        data = self.client.get(f"/api/v1/posts/{self.post.pk}/matches").data["data"]
        self.assertEqual([row["post"]["id"] for row in data["items"]], [str(self.source.pk)])

    def test_permissions_nonopen_source_and_limit_validation(self):
        self.login_as(self.other)
        self.assert_error(self.client.get(self.url), 403, "FORBIDDEN")
        self.source.status = "withdrawn"
        self.source.save()
        self.assert_error(self.client.get(self.url), 404, "NOT_FOUND")
        self.login_as(self.applicant)
        self.assert_error(self.client.get(self.url), 409, "STATE_CONFLICT")
        self.source.status = "open"; self.source.save()
        for query in ("limit=0", "limit=21", "limit=1.1", "keyword=x"):
            self.assert_error(self.client.get(self.url + "?" + query), 400, "VALIDATION_ERROR")

    def test_sort_ties_and_limit(self):
        newer = self.make_post()
        # 固定同一创建时间，验证 ID 降序打破平局。
        from posts.models import Post
        Post.objects.filter(pk__in=[newer.pk, self.post.pk]).update(created_at=timezone.now())
        data = self.client.get(self.url + "?limit=1").data["data"]
        self.assertEqual(data["items"][0]["post"]["id"], str(newer.pk))

    def test_title_normalization_unicode_punctuation_and_short_titles(self):
        self.assertEqual(title_bigrams(" Blue，钥 匙！"), title_bigrams("blue钥匙"))
        self.assertEqual(title_bigrams("字"), set())
        self.assertEqual(title_bigrams(" ，！ "), set())

    def test_no_candidates_returns_empty_array(self):
        self.post.status = "withdrawn"; self.post.save()
        self.assertEqual(self.client.get(self.url).data["data"], {"source_post_id": str(self.source.pk), "items": []})
