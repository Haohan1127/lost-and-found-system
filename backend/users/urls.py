from django.urls import path

from . import views

# 路径不带结尾斜杠（settings.APPEND_SLASH = False）；前缀在 config/urls.py 统一挂 /api/v1/
urlpatterns = [
    path("auth/register", views.RegisterView.as_view()),
    path("auth/login", views.LoginView.as_view()),
    path("auth/logout", views.LogoutView.as_view()),
    path("users/me", views.MeView.as_view()),
    path("users/me/campus-binding", views.CampusBindingView.as_view()),
]
