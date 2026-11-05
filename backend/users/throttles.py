"""固定窗口限流（Django cache 实现，不依赖外部服务）。

规则（settings 已给常量，不用改）：
- 登录：按来源 IP，LOGIN_RATE_LIMIT 次 / RATE_LIMIT_WINDOW_SECONDS 窗口；
- 绑定：按登录用户，BINDING_RATE_LIMIT 次 / 窗口；
- 超限抛 rest_framework.exceptions.Throttled（=HTTP 429，DRF 自动附 Retry-After）；
- settings.RATE_LIMIT_ENABLED = False（测试环境或显式关闭）时直接放行。
"""
import time

from django.conf import settings
from django.core.cache import cache
from rest_framework.exceptions import Throttled

CACHE_PREFIX = "rate-limit"


def _client_ip(request):
    return request.META.get("REMOTE_ADDR") or "unknown"


def _fixed_window(scope, identity, limit):
    """TODO [D1-08] 固定窗口计数：

    - key = f"{CACHE_PREFIX}:{scope}:{identity}:{当前窗口序号}"，timeout 略大于窗口；
    - 用 cache.add 原子建键、cache.incr 原子自增（不要 get 再 set，会并发漏计）；
    - 计数超过 limit 时 raise Throttled(wait=距本窗口结束秒数, detail="请求过于频繁，请 N 秒后重试")；
    - 未超限返回 None。

    未实现前先放行：限流用例会失败，D1-08 完成后应转绿。
    """
    return None


def enforce_login_rate_limit(request):
    _fixed_window("login-ip", _client_ip(request), settings.LOGIN_RATE_LIMIT)


def enforce_binding_rate_limit(request):
    user = getattr(request, "user", None)
    identity = user.pk if user is not None and user.is_authenticated else "anonymous"
    _fixed_window("binding-user", identity, settings.BINDING_RATE_LIMIT)
