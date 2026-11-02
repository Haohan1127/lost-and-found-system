from django.conf import settings
from django.urls import include, path

# A 的正式用户接口在 claims 之前注册，接管原 demo 中的登录/登出/本人资料适配入口。
urlpatterns = [
    path("api/v1/", include("users.urls")),
    path("api/v1/", include("claims.urls")),
]
if settings.DEMO_MODE:
    urlpatterns += [path("api/v1/", include("demo.urls"))]

handler404 = "common.exceptions.not_found"
handler500 = "common.exceptions.server_error"
