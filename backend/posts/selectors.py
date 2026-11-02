from datetime import timedelta
from common.exceptions import missing
from .models import Post


def post_queryset():
    return Post.objects.select_related("publisher", "category", "location__campus")


def get_post_for_claim(post_id, lock=False):
    queryset = post_queryset()
    if lock:
        queryset = queryset.select_for_update(of=("self",))
    try:
        post = queryset.filter(pk=post_id).first()
    except (ValueError, OverflowError):
        post = None
    if post is None:
        missing()
    return post


def visible_post(post_id, user):
    post = get_post_for_claim(post_id)
    if post.status == Post.Status.WITHDRAWN and post.publisher_id != user.pk:
        missing()
    return post


def list_match_candidates(source_post):
    lost_source = source_post.post_type == Post.Type.LOST
    lower = source_post.occurred_at if lost_source else source_post.occurred_at - timedelta(days=30)
    upper = source_post.occurred_at + timedelta(days=30) if lost_source else source_post.occurred_at
    return post_queryset().filter(
        post_type=Post.Type.FOUND if lost_source else Post.Type.LOST,
        status=Post.Status.OPEN, category_id=source_post.category_id,
        location__campus_id=source_post.campus_id, occurred_at__gte=lower, occurred_at__lte=upper,
    ).exclude(publisher_id=source_post.publisher_id)
