"""初始化演示校园身份（一次性绑定码；只存 SHA-256 摘要，不存明文）。

数据约定（与 docs/共同字段与接口约定.md §3.3、使用说明一致）：
- 校区：campus_main（主校区，不存在则创建）；
- 学号 20260001～20260006，各对应一个一次性绑定码；
- 已认证的演示账号 publisher/applicant/competitor 自动绑定 001～003；
- 剩余未被使用的身份打印明文码（只打印一次）；--reset-codes 只重置“未被使用”身份的码；
- 幂等：重复执行不重复建身份、不改已绑定记录。

自测命令：
  .\.venv\Scripts\python.exe backend\manage.py seed_demo_users
  .\.venv\Scripts\python.exe backend\manage.py seed_demo_users --reset-codes
"""
import hashlib
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from catalog.models import Campus
from users.models import CampusBinding, DemoIdentity, User

STUDENT_NOS = [f"2026000{index}" for index in range(1, 7)]
BOUND_DEMO_ACCOUNTS = [("publisher", 1), ("applicant", 2), ("competitor", 3)]


class Command(BaseCommand):
    help = "初始化演示校区与一次性校园身份，并为既有演示认证账号补绑定（幂等）"

    def add_arguments(self, parser):
        parser.add_argument("--reset-codes", action="store_true", help="重新生成未被使用身份的绑定码并打印")

    @transaction.atomic
    def handle(self, *args, **options):
        # TODO [D2-04] 实现步骤：
        # 1) settings.DEMO_MODE 为 False 时抛 CommandError（演示命令不能用于生产）；
        # 2) Campus.objects.get_or_create(pk="campus_main", defaults={"name": "主校区"})；
        # 3) 遍历 STUDENT_NOS：不存在则生成码（os.environ 的 DEMO_BINDING_CODE 存在时用它，便于 e2e 固定码）
        #    并 hashlib.sha256(code.encode()).hexdigest() 存摘要；存在且 --reset-codes 且 used_by 为空则重置码；
        # 4) 为 BOUND_DEMO_ACCOUNTS 里已认证的账号补 CampusBinding（学号 001/002/003），并置 used_by；
        # 5) 最后统一打印仍 used_by__isnull=True 的身份中“本次生成”的明文码，以及当前可用身份数量。
        #    注意顺序：先补绑定再打印，否则先打印的码可能马上失效。
        raise CommandError("TODO [D2-04] seed_demo_users 尚未实现")
