"""Playwright 专用隔离数据库；每次测试启动只重置 backend/e2e.sqlite3。

隔离浏览器验收环境关闭限流，避免多账号用例在 1 分钟窗口内累计触发登录/绑定限流；
限流行为由 backend/users/tests 用 @override_settings(RATE_LIMIT_ENABLED=True) 单独覆盖。
正常演示/生产未设置该变量时仍默认开启限流。
"""
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "backend"))
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
os.environ["DJANGO_DB_PATH"] = str(root / "backend" / "e2e.sqlite3")
os.environ["DJANGO_DEBUG"] = "1"
os.environ["DJANGO_DEMO_MODE"] = "1"
os.environ["DEMO_PASSWORD"] = "e2e-test-only-123"
# 浏览器验收关闭限流；后端测试仍覆盖限流逻辑。
os.environ["DJANGO_RATE_LIMIT"] = "0"
# 浏览器验收使用固定一次性绑定码（学号 20260004），失败可复现。
os.environ["DEMO_BINDING_CODE"] = "e2e-binding-0001"

import django
django.setup()
from django.core.management import call_command
call_command("migrate", interactive=False, verbosity=0)
call_command("flush", interactive=False, verbosity=0)
call_command("seed_demo", verbosity=0)
call_command("seed_demo_users", verbosity=0)
call_command("runserver", "127.0.0.1:8001", use_reloader=False)
