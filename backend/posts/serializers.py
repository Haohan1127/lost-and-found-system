from common.serializers import timestamp
from users.services import user_summary


def post_summary(post):
    return {
        "id": str(post.pk), "post_type": post.post_type, "title": post.title,
        "category": {"id": str(post.category_id), "name": post.category.name},
        "campus": {"id": str(post.campus_id), "name": post.location.campus.name},
        "location": {"id": str(post.location_id), "name": post.location.name},
        "occurred_at": timestamp(post.occurred_at), "status": post.status, "cover_image": None,
        "publisher": user_summary(post.publisher), "created_at": timestamp(post.created_at), "updated_at": timestamp(post.updated_at),
    }


def post_detail(post):
    return {**post_summary(post), "description": post.description, "location_detail": post.location_detail,
            "handover_note": post.handover_note, "images": [], "completed_at": timestamp(post.completed_at)}
