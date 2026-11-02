"""仅 DEBUG + DEMO_MODE 挂载的演示专用接口；登录/登出/本人资料由 users 正式接口接管。"""
from django.db.models import Q
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from common.responses import ok
from common.serializers import EmptyInput, PageQuery, paginate, validated
from posts.selectors import post_queryset, visible_post
from posts.serializers import post_detail, post_summary
from workflows.post_workflow import restore_post, withdraw_post


class DemoPostsView(APIView):
    def get(self, request):
        query = validated(PageQuery, request.query_params)
        # 本演示清单包含本人已撤回记录，第三方看不到这些记录。
        queryset = post_queryset().filter(~Q(status="withdrawn") | Q(publisher=request.user)).order_by("-created_at", "-id")
        return ok(paginate(queryset, query, post_summary))


class PostDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, post_id):
        validated(EmptyInput, request.query_params)
        return ok(post_detail(visible_post(post_id, request.user)))


class DemoPostActionView(APIView):
    def post(self, request, post_id, action):
        validated(EmptyInput, request.data)
        post = (withdraw_post if action == "withdraw" else restore_post)(request.user, post_id)
        return ok(post_detail(post))
