from django.urls import path

from . import views

# auth/login、auth/logout、users/me 已由 users 正式接口接管（FR-A-02/03/04）。
urlpatterns = [
    path("demo/posts", views.DemoPostsView.as_view()),
    path("posts/<str:post_id>", views.PostDetailView.as_view()),
]
for action in ("withdraw", "restore"):
    urlpatterns.append(path(f"demo/posts/<str:post_id>/{action}", views.DemoPostActionView.as_view(), {"action": action}))
