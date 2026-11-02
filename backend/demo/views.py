"""仅 DEBUG + DEMO_MODE 挂载的 A/B 适配接口，正式联调由 A/B 替换。"""
from django.contrib.auth import authenticate
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.views import APIView
from common.responses import ok
from common.serializers import StrictSerializer, StringField, EmptyInput, PageQuery, validated, paginate
from posts.selectors import post_queryset, visible_post
from posts.serializers import post_summary, post_detail, timestamp
from users.services import issue_session, user_summary
from workflows.post_workflow import withdraw_post, restore_post


class LoginInput(StrictSerializer):
    username = StringField(min_length=4, max_length=32)
    password = StringField(min_length=8, max_length=64, trim_whitespace=False)


def user_self(user):
    return {**user_summary(user), "username": user.username, "bio": user.bio,
            "created_at": timestamp(user.date_joined), "updated_at": timestamp(user.updated_at)}


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = validated(LoginInput, request.data)
        user = authenticate(username=data["username"].lower(), password=data["password"])
        if user is None:
            raise AuthenticationFailed("账号或密码错误")
        token, session = issue_session(user)
        return ok({"access_token": token, "token_type": "Bearer", "expires_at": timestamp(session.expires_at), "user": user_self(user)})


class LogoutView(APIView):
    def post(self, request):
        validated(EmptyInput, request.data)
        request.auth.delete()
        return ok()


class MeView(APIView):
    def get(self, request):
        return ok(user_self(request.user))


class DemoPostsView(APIView):
    def get(self, request):
        query = validated(PageQuery, request.query_params)
        # 本演示清单包含本人已撤回记录，第三方看不到这些记录。
        from django.db.models import Q
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
