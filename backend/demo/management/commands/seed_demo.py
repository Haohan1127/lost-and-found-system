import os
import secrets
from datetime import timedelta
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from catalog.models import Campus, Category, Location
from users.models import User, AuthSession
from posts.models import Post


class Command(BaseCommand):
    help = "初始化成员 C 的演示依赖数据；不清除已有申请或重置物品状态"

    def add_arguments(self, parser):
        parser.add_argument("--reset-passwords", action="store_true", help="重置四个演示账号密码并撤销其旧会话")

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEMO_MODE:
            raise CommandError("仅允许在 DJANGO_DEBUG=1、DJANGO_DEMO_MODE=1 时初始化演示数据")
        password = os.environ.get("DEMO_PASSWORD") or secrets.token_urlsafe(12)
        if not 8 <= len(password) <= 64:
            raise CommandError("DEMO_PASSWORD 长度必须为 8～64")
        campus, _ = Campus.objects.get_or_create(pk="campus_main", defaults={"name": "主校区"})
        category, _ = Category.objects.get_or_create(pk="cat_keys", defaults={"name": "钥匙"})
        Category.objects.get_or_create(pk="cat_books", defaults={"name": "书籍"})
        library, _ = Location.objects.get_or_create(pk="loc_library", defaults={"name": "图书馆", "campus": campus})
        Location.objects.get_or_create(pk="loc_canteen", defaults={"name": "食堂", "campus": campus})
        people, changed = {}, []
        for username, nickname, verified in [("publisher", "拾获者小林", True), ("applicant", "失主小周", True),
                                              ("competitor", "同学小陈", True), ("unverified", "未认证同学", False)]:
            user, created = User.objects.get_or_create(username=username, defaults={"nickname": nickname, "is_campus_verified": verified,
                                                                                  "verification_mode": "demo" if verified else None})
            if created or options["reset_passwords"]:
                user.set_password(password)
                user.save()
                AuthSession.objects.filter(user=user).delete()
                changed.append(username)
            people[username] = user
        now = timezone.now()
        scenarios = [
            ("publisher", "found", "图书馆拾到蓝色钥匙", 2),
            ("publisher", "found", "图书馆拾到钥匙（取消演示）", 3),
            ("publisher", "found", "图书馆拾到钥匙（撤回演示）", 4),
            ("applicant", "lost", "遗失蓝色钥匙", 6),
            ("competitor", "lost", "图书馆遗失一串钥匙", 8),
        ]
        for owner, kind, title, hours in scenarios:
            Post.objects.get_or_create(publisher=people[owner], title=title, defaults={
                "post_type": kind, "category": category, "location": library,
                "description": "课程演示物品，请通过私有认领申请补充可核实的细节。", "location_detail": "二楼自习区",
                "occurred_at": now - timedelta(hours=hours), "handover_note": "核实后约在图书馆服务台交接" if kind == "found" else None,
            })
        self.stdout.write("演示数据就绪（演示认证，不是真实学校认证）。")
        if changed:
            self.stdout.write(f"账号：{', '.join(changed)}\n本次设置的演示密码：{password}")
        else:
            self.stdout.write("已有账号密码保持不变。忘记密码可执行 seed_demo --reset-passwords。")
