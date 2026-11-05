"""A 模块接口视图：只做「权限 → 入参校验 → 调服务 → 统一响应」四件事。

- 成功：from common.responses import ok，ok(data) 或 ok(data, 201)
- 入参校验：validated(Serializer, request.data)，失败自动 400
- 错误：由 common.exceptions.exception_handler 统一包装成 code/message/data/errors
"""
from rest_framework.views import APIView

from common.responses import ok
from common.serializers import EmptyInput, validated
from . import serializers as s
from .permissions import LoginRequired, PublicAccess
from .selectors import current_user, get_campus_binding
from .services import bind_campus, issue_session, login_user, register_user, revoke_session, update_profile
from .throttles import enforce_binding_rate_limit, enforce_login_rate_limit


class RegisterView(APIView):
    permission_classes = [PublicAccess]

    def post(self, request):
        # TODO [D1-03] validated(s.RegisterInput, request.data) → register_user(**data) → ok(s.user_self(user), 201)
        raise NotImplementedError("D1-03 注册接口")


class LoginView(APIView):
    permission_classes = [PublicAccess]

    def post(self, request):
        # TODO [D1-04] 先 enforce_login_rate_limit(request)，再校验入参；
        #   login_user(...) → issue_session(user) → ok({"access_token", "token_type": "Bearer",
        #   "expires_at": s.timestamp(session.expires_at), "user": s.user_self(user)})
        raise NotImplementedError("D1-04 登录接口")


class LogoutView(APIView):
    permission_classes = [LoginRequired]

    def post(self, request):
        # TODO [D1-05] validated(EmptyInput, request.data) → revoke_session(request.auth) → ok()
        raise NotImplementedError("D1-05 登出接口")


class MeView(APIView):
    permission_classes = [LoginRequired]

    def get(self, request):
        # TODO [D1-05] ok(s.user_self(current_user(request.user)))
        raise NotImplementedError("D1-05 查看本人资料")

    def patch(self, request):
        # TODO [D1-06] validated(s.UpdateProfileInput, request.data) → update_profile(...) → ok(s.user_self(...))
        raise NotImplementedError("D1-06 修改本人资料")


class CampusBindingView(APIView):
    permission_classes = [LoginRequired]

    def get(self, request):
        # TODO [D2-02] 已绑定返回 s.binding_view(binding)，未绑定返回 ok(None)
        raise NotImplementedError("D2-02 查询校园绑定")

    def post(self, request):
        # TODO [D2-02] 先 enforce_binding_rate_limit(request)，再校验入参并调用 bind_campus(...)，
        #   成功返回 ok(s.binding_view(binding), 201)
        raise NotImplementedError("D2-02 提交校园绑定")
