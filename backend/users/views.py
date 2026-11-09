from rest_framework.views import APIView

from common.responses import ok
from common.serializers import EmptyInput, paginate, timestamp, validated
from . import serializers as s
from .permissions import LoginRequired, PublicAccess
from .selectors import current_user, get_campus_binding, my_posts
from .services import bind_campus, issue_session, login_user, register_user, revoke_session, update_profile
from .throttles import enforce_binding_rate_limit, enforce_login_rate_limit


class RegisterView(APIView):
    permission_classes = [PublicAccess]

    def post(self, request):
        data = validated(s.RegisterInput, request.data)
        return ok(s.user_self(register_user(**data)), 201)


class LoginView(APIView):
    permission_classes = [PublicAccess]

    def post(self, request):
        enforce_login_rate_limit(request)
        data = validated(s.LoginInput, request.data)
        user = login_user(data["username"], data["password"])
        token, session = issue_session(user)
        return ok({"access_token": token, "token_type": "Bearer",
                   "expires_at": timestamp(session.expires_at), "user": s.user_self(user)})


class LogoutView(APIView):
    permission_classes = [LoginRequired]

    def post(self, request):
        validated(EmptyInput, request.data)
        revoke_session(request.auth)
        return ok()


class MeView(APIView):
    permission_classes = [LoginRequired]

    def get(self, request):
        return ok(s.user_self(current_user(request.user)))

    def patch(self, request):
        data = validated(s.UpdateProfileInput, request.data)
        return ok(s.user_self(update_profile(current_user(request.user), data)))


class CampusBindingView(APIView):
    permission_classes = [LoginRequired]

    def get(self, request):
        binding = get_campus_binding(request.user)
        return ok(s.binding_view(binding) if binding else None)

    def post(self, request):
        enforce_binding_rate_limit(request)
        data = validated(s.CampusBindingInput, request.data)
        return ok(s.binding_view(bind_campus(request.user, **data)), 201)


class MyPostsView(APIView):
    """我的发布（契约 v0.3）：A 直接查询 B 的 Post 表，默认包含本人全部状态。"""
    permission_classes = [LoginRequired]

    def get(self, request):
        query = validated(s.MyPostsQuery, request.query_params)
        return ok(paginate(my_posts(request.user, query), query, s.my_post_summary))
