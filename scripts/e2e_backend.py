"""Playwright 专用隔离数据库；每次测试启动只重置 backend/e2e.sqlite3。"""
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

import django
django.setup()
from django.core.management import call_command
call_command("migrate", interactive=False, verbosity=0)
call_command("flush", interactive=False, verbosity=0)
call_command("seed_demo", verbosity=0)
call_command("runserver", "127.0.0.1:8001", use_reloader=False)
