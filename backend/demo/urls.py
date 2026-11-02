from django.urls import path
from . import views

urlpatterns = [
    path("auth/login", views.LoginView.as_view()),
    path("auth/logout", views.LogoutView.as_view()),
    path("users/me", views.MeView.as_view()),
    path("demo/posts", views.DemoPostsView.as_view()),
    path("posts/<str:post_id>", views.PostDetailView.as_view()),
]
for action in ("withdraw", "restore"):
    urlpatterns.append(path(f"demo/posts/<str:post_id>/{action}", views.DemoPostActionView.as_view(), {"action": action}))
