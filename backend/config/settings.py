import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
DEMO_MODE = DEBUG and os.environ.get("DJANGO_DEMO_MODE", "1") == "1"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "local-claims-demo-only")
if not DEBUG and SECRET_KEY in {"local-claims-demo-only", "replace-for-deployment"}:
    raise ImproperlyConfigured("非调试环境必须设置 DJANGO_SECRET_KEY")
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
INSTALLED_APPS = [
    "django.contrib.auth", "django.contrib.contenttypes", "rest_framework",
    "users", "catalog", "posts", "claims", "demo",
]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware", "django.middleware.common.CommonMiddleware"]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
AUTH_USER_MODEL = "users.User"
DATABASES = {"default": {
    "ENGINE": "django.db.backends.sqlite3", "NAME": os.environ.get("DJANGO_DB_PATH", str(BASE_DIR / "db.sqlite3")),
    # SQLite 不支持行锁；在任何事务读取前取得写锁，跨进程串行化写事务。
    "OPTIONS": {"timeout": 20, "transaction_mode": "IMMEDIATE"},
    "TEST": {"NAME": BASE_DIR / "test-claims.sqlite3"},
}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_TZ = True
APPEND_SLASH = False
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["users.authentication.BearerAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "EXCEPTION_HANDLER": "common.exceptions.exception_handler",
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%S.%fZ",
}
