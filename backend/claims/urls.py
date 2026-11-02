from django.urls import path
from . import views

urlpatterns = [
    path("claims", views.ClaimCreateView.as_view()),
    path("claims/<str:claim_id>", views.ClaimDetailView.as_view()),
    path("users/me/claims", views.MyClaimsView.as_view()),
    path("claims/<str:claim_id>/messages", views.ClaimMessagesView.as_view()),
    path("posts/<str:post_id>/matches", views.MatchesView.as_view()),
]
for action in ("accept", "reject", "cancel", "confirm-handover"):
    urlpatterns.append(path(f"claims/<str:claim_id>/{action}", views.ClaimActionView.as_view(), {"action": action}))
