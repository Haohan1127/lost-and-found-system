from django.conf import settings
from django.urls import include, path

urlpatterns = [path("api/v1/", include("claims.urls"))]
if settings.DEMO_MODE:
    urlpatterns += [path("api/v1/", include("demo.urls"))]

handler404 = "common.exceptions.not_found"
handler500 = "common.exceptions.server_error"
