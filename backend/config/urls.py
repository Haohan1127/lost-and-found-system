from django.conf import settings
from django.urls import include, path

# A 的正式用户接口（auth/*、users/me*）在 claims 之前注册：
# 路径不与 C 的认领/匹配冲突，但保持“A 先接管登录与本人资料”的既有顺序约定。
urlpatterns = [
    path("api/v1/", include("users.urls")),
    path("api/v1/", include("claims.urls")),
]
if settings.DEMO_MODE:
    urlpatterns += [path("api/v1/", include("demo.urls"))]

handler404 = "common.exceptions.not_found"
handler500 = "common.exceptions.server_error"
