"""验收基线：个人资料边界（TC-A-021～028 的骨架版）。

启用方式：
    Copy-Item scaffold\\tests\\test_profile.py backend\\users\\tests\\test_profile.py
    .\\.venv\\Scripts\\python.exe backend\\manage.py test users.tests.test_profile -v 2

test_auth.py 已覆盖主流程，这里只补“边界与只读字段”，避免重复用例。
"""
from . import UserApiTestCase

ME = "/api/v1/users/me"


class ProfileBoundaryTests(UserApiTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user(nickname="原名", bio="原简介")
        self.use_token(self.login_token())

    def test_nickname_length_boundaries(self):
        self.assertEqual(self.client.patch(ME, {"nickname": "名"}, format="json").status_code, 200)
        self.assertEqual(self.client.patch(ME, {"nickname": "名" * 30}, format="json").status_code, 200)
        self.assert_error(self.client.patch(ME, {"nickname": "名" * 31}, format="json"), 400, "VALIDATION_ERROR")
        self.assert_error(self.client.patch(ME, {"nickname": ""}, format="json"), 400, "VALIDATION_ERROR")

    def test_bio_allow_blank_and_length_boundaries(self):
        self.assertEqual(self.client.patch(ME, {"bio": ""}, format="json").status_code, 200)
        self.assertEqual(self.client.patch(ME, {"bio": "字" * 200}, format="json").status_code, 200)
        self.assert_error(self.client.patch(ME, {"bio": "字" * 201}, format="json"), 400, "VALIDATION_ERROR")

    def test_partial_update_keeps_other_field(self):
        response = self.client.patch(ME, {"nickname": "只改昵称"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["data"]["bio"], "原简介")

    def test_client_cannot_write_readonly_fields(self):
        for field, value in (("is_campus_verified", True), ("verification_mode", "demo"),
                             ("username", "hacker"), ("password", "new-pass-123")):
            with self.subTest(field=field):
                response = self.client.patch(ME, {field: value}, format="json")
                self.assert_error(response, 400, "VALIDATION_ERROR")
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_campus_verified)

    def test_unknown_field_is_rejected(self):
        self.assert_error(self.client.patch(ME, {"age": 20}, format="json"), 400, "VALIDATION_ERROR")

    def test_empty_patch_is_rejected(self):
        self.assert_error(self.client.patch(ME, {}, format="json"), 400, "VALIDATION_ERROR")

    def test_profile_requires_token(self):
        self.client.credentials()
        self.assert_error(self.client.patch(ME, {"nickname": "x"}, format="json"), 401, "UNAUTHENTICATED")
