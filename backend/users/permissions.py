"""A 模块视图权限：公开入口与需登录入口。

令牌无效/过期的 401 由 users.authentication.BearerAuthentication 负责；
公开接口携带无效令牌同样返回 401（见共同契约 2.2）。
"""
from rest_framework.permissions import AllowAny, IsAuthenticated


class PublicAccess(AllowAny):
    """注册/登录：匿名可访问。"""


class LoginRequired(IsAuthenticated):
    """本人资料与校园绑定：必须携带有效 Bearer 令牌。"""
