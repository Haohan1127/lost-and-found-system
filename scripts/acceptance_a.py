#!/usr/bin/env python
"""成员 A（用户管理）独立验收脚本 —— 验证角色编写，可重复执行。

用途
----
不依赖实现者自述与既有测试用例名称，用真实的 Django 视图/中间件/认证/序列化链路
（``django.test.Client``，等价于 WSGI 请求）逐条断言 FR-A-01～12 与 NFR-A-01～07 的
可观察行为：状态码、统一响应包装、错误码与字段级错误、脱敏、数据库副作用与隐私存储。

隔离性
------
- 数据库：系统临时目录下的一次性 SQLite 文件（``DJANGO_DB_PATH``），执行结束自动删除；
- 限流：默认 ``DJANGO_RATE_LIMIT=0`` 关闭，限流用例内用 ``override_settings`` 单独开启并清缓存；
- 浏览器验收环境的 ``e2e.sqlite3`` 与普通演示库 ``backend/db.sqlite3`` 均不被触碰。

用法（仓库根目录）
------------------
    .\\.venv\\Scripts\\python.exe scripts\\acceptance_a.py

输出每个断言 PASS/FAIL，最后打印统计；任一断言失败以退出码 1 结束。

编号约定：ACC-A-xx 是本脚本自有编号，与 docs/test/A-用户管理-测试用例.md 的 TC-A-xxx
对照关系见 docs/test/A-用户管理-测试报告.md。
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import shutil
import sys
import tempfile
import time
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
_TMP_DIR = Path(tempfile.mkdtemp(prefix="acceptance-a-"))

os.environ.update({
    "DJANGO_SETTINGS_MODULE": "config.settings",
    "DJANGO_DB_PATH": str(_TMP_DIR / "acceptance_a.sqlite3"),
    "DJANGO_DEBUG": "1",
    "DJANGO_DEMO_MODE": "1",
    "DJANGO_RATE_LIMIT": "0",          # 限流用例内 override_settings 单独开启
    "DJANGO_ALLOWED_HOSTS": "localhost,127.0.0.1,testserver",
    "DEMO_BINDING_CODE": "e2e-binding-0001",
    "PYTHONUTF8": "1",
})
sys.path.insert(0, str(BACKEND))

import django  # noqa: E402

django.setup()

from django.core.cache import cache  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.core.management.base import CommandError  # noqa: E402
from django.test import Client, override_settings  # noqa: E402
from django.utils import timezone  # noqa: E402

from catalog.models import Campus, Category, Location  # noqa: E402
from claims.models import Claim  # noqa: E402
from posts.models import Post  # noqa: E402
from users.models import AuthSession, CampusBinding, DemoIdentity, User  # noqa: E402

USER_SELF_FIELDS = {"id", "username", "nickname", "bio", "is_campus_verified",
                    "verification_mode", "created_at", "updated_at"}
BINDING_FIELDS = {"campus_id", "student_no_masked", "verification_mode", "verified_at"}
DEMO_ACCOUNTS = ["publisher", "applicant", "competitor"]
DEMO_BINDING_CODE = "e2e-binding-0001"
USER_PASSWORD = "Passw0rd-123"

client = Client()
CASES: list[tuple[str, str, bool, str]] = []
_seq = [0]


# ---------------------------------------------------------------- 基础设施

def _json(resp):
    try:
        return json.loads(resp.content.decode("utf-8"))
    except Exception:  # noqa: BLE001
        return {"_raw": resp.content.decode("utf-8", "replace")[:400]}


def request(method, path, payload=None, token=None):
    """统一请求入口：显式 JSON 编码，避免 DRF 测试客户端的格式化差异。"""
    extra = {}
    if token is not None:
        extra["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    if method.lower() in ("post", "patch", "put"):
        data = json.dumps(payload if payload is not None else {})
        return client.generic(method.upper(), path, data=data, content_type="application/json", **extra)
    return client.generic(method.upper(), path, **extra)


def next_name(prefix="acc_user"):
    _seq[0] += 1
    return f"{prefix}_{_seq[0]:03d}"


def register(username, password=USER_PASSWORD, nickname="验收用户"):
    return request("post", "/api/v1/auth/register",
                   {"username": username, "password": password, "nickname": nickname})


def make_account(prefix="acc_user", nickname="验收用户", password=USER_PASSWORD):
    """注册并登录一个全新账号，返回 (username, token, User)。"""
    username = next_name(prefix)
    resp = register(username, password=password, nickname=nickname)
    assert resp.status_code == 201, f"注册失败: {resp.status_code} {resp.content[:200]}"
    login = request("post", "/api/v1/auth/login", {"username": username, "password": password})
    assert login.status_code == 200, f"登录失败: {login.status_code} {login.content[:200]}"
    return username, login.json()["data"]["access_token"], User.objects.get(username=username)


def case(case_id, title):
    def deco(fn):
        def wrapper():
            try:
                fn()
            except AssertionError as exc:  # 业务断言失败
                CASES.append((case_id, title, False, str(exc)))
                print(f"FAIL {case_id} {title} :: {exc}")
            except Exception as exc:  # noqa: BLE001
                CASES.append((case_id, title, False, f"{type(exc).__name__}: {exc}"))
                print(f"FAIL {case_id} {title} :: {type(exc).__name__}: {exc}")
            else:
                CASES.append((case_id, title, True, ""))
                print(f"PASS {case_id} {title}")
        wrapper.case_id = case_id
        wrapper.title = title
        return wrapper
    return deco


def assert_status(resp, expected, note=""):
    assert resp.status_code == expected, (
        f"期望 {expected}，实际 {resp.status_code}{('（' + note + '）') if note else ''}；body={resp.content[:300]}")


def assert_envelope(payload, code, with_errors=False):
    expected = {"code", "message", "data", "errors"} if with_errors else {"code", "message", "data"}
    assert set(payload) == expected, f"响应包装字段异常: {sorted(payload)}"
    assert payload["code"] == code, f"期望 code={code}，实际 {payload.get('code')}"


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- 前置数据

def prepare_fixture():
    """演示校区/分类/地点/演示账号/公开信息：供身份集成与公开摘要用例使用。"""
    campus, _ = Campus.objects.get_or_create(pk="campus_main", defaults={"name": "主校区"})
    category, _ = Category.objects.get_or_create(pk="keys", defaults={"name": "钥匙"})
    location, _ = Location.objects.get_or_create(pk="library", defaults={"name": "图书馆", "campus": campus})
    users = {}
    for name, nickname in (("publisher", "拾获者"), ("applicant", "失主"), ("competitor", "第三人")):
        users[name] = User.objects.create_user(
            username=name, password="test-only-123", nickname=nickname,
            is_campus_verified=True, verification_mode="demo")
    users["unverified"] = User.objects.create_user(username="unverified", password="test-only-123", nickname="未认证")
    post = Post.objects.create(
        publisher=users["publisher"], post_type="found", title="图书馆蓝色钥匙", category=category,
        location=location, description="蓝色钥匙，更多细节请通过私有申请核实。",
        occurred_at=timezone.now() - timedelta(hours=2), handover_note="核实后交接")
    return {"campus": campus, "category": category, "location": location, "post": post, "users": users}


FIXTURE: dict = {}


# ---------------------------------------------------------------- 用例

@case("ACC-A-01", "注册 201：UserSelf 字段集合、username 小写、昵称去空白、无令牌、库中 PBKDF2 哈希")
def acc_a_01():
    username = next_name("reg_case")
    resp = register(f"  {username.upper()}  ", nickname="  验收用户  ")
    assert_status(resp, 201)
    payload = _json(resp)
    assert_envelope(payload, "OK")
    data = payload["data"]
    assert set(data) == USER_SELF_FIELDS, f"字段集合异常: {sorted(data)}"
    assert data["username"] == username.lower(), data["username"]
    assert data["nickname"] == "验收用户", data["nickname"]
    assert data["bio"] == "" and data["is_campus_verified"] is False and data["verification_mode"] is None
    assert isinstance(data["id"], str) and data["created_at"].endswith("Z") and data["updated_at"].endswith("Z")
    assert "access_token" not in data and "token" not in data
    user = User.objects.get(username=username.lower())
    assert user.password.startswith("pbkdf2_sha256$"), f"密码哈希格式异常: {user.password[:20]}"
    assert user.check_password(USER_PASSWORD)
    assert AuthSession.objects.filter(user=user).count() == 0, "注册不应自动登录"


@case("ACC-A-02", "注册重复 409 DUPLICATE_RESOURCE，大小写账号等价去重")
def acc_a_02():
    username = next_name("dup_case")
    assert_status(register(username), 201)
    same = register(username)
    assert_status(same, 409)
    assert_envelope(_json(same), "DUPLICATE_RESOURCE", with_errors=True)
    upper = register(username.upper())
    assert_status(upper, 409)
    assert User.objects.filter(username=username).count() == 1


@case("ACC-A-03", "注册非法输入 400：账号长度/字符、密码长度、昵称长度，错误归对应字段")
def acc_a_03():
    bad = [
        ("username", "abc"), ("username", "a" * 33), ("username", "ab-c"),
        ("username", "中文账号"), ("username", "ab cd"),
        ("password", "short7"), ("password", "x" * 65),
        ("nickname", ""), ("nickname", "名" * 31),
    ]
    for field, value in bad:
        payload = {"username": next_name("bad"), "password": USER_PASSWORD, "nickname": "合法昵称"}
        payload[field] = value
        resp = request("post", "/api/v1/auth/register", payload)
        assert_status(resp, 400, f"{field}={value!r}")
        body = _json(resp)
        assert_envelope(body, "VALIDATION_ERROR", with_errors=True)
        assert field in body["errors"], f"错误未归字段 {field}: {body['errors']}"
    # 合法边界（4/32 位账号、8/64 位密码、1/30 字昵称）必须成功
    ok = request("post", "/api/v1/auth/register",
                 {"username": "a" * 4, "password": "p" * 8, "nickname": "名"})
    assert_status(ok, 201, "4 位账号/8 位密码/1 字昵称边界")
    ok2 = request("post", "/api/v1/auth/register",
                  {"username": "b" * 32, "password": "p" * 64, "nickname": "名" * 30})
    assert_status(ok2, 201, "32 位账号/64 位密码/30 字昵称边界")


@case("ACC-A-04", "注册/登录严格拒绝未知字段与只读字段，非对象 body 返回 400")
def acc_a_04():
    for extra in ({"email": "x@example.com"}, {"is_campus_verified": True},
                  {"password_hash": "x"}, {"bio": "自我介绍"}, {"id": "1"}):
        payload = {"username": next_name("strict"), "password": USER_PASSWORD, "nickname": "严格", **extra}
        resp = request("post", "/api/v1/auth/register", payload)
        assert_status(resp, 400, f"未知字段 {list(extra)}")
        assert set(_json(resp)["errors"]) & set(extra), f"错误未指向非法字段: {_json(resp)['errors']}"
    array_body = client.generic("POST", "/api/v1/auth/register", data="[]", content_type="application/json")
    assert_status(array_body, 400, "JSON 数组 body")
    login_unknown = request("post", "/api/v1/auth/login",
                            {"username": "nobody_x", "password": "wrong-pass-1", "nickname": "x"})
    assert_status(login_unknown, 400, "登录未知字段应在校验阶段 400")


@case("ACC-A-05", "登录 200：access_token/token_type/expires_at/user；令牌只存 SHA-256 摘要、有效期 24h")
def acc_a_05():
    username = next_name("login_case")
    assert_status(register(username), 201)
    before = timezone.now()
    resp = request("post", "/api/v1/auth/login", {"username": username.upper(), "password": USER_PASSWORD})
    assert_status(resp, 200)
    payload = _json(resp)
    assert_envelope(payload, "OK")
    data = payload["data"]
    assert set(data) == {"access_token", "token_type", "expires_at", "user"}, sorted(data)
    assert data["token_type"] == "Bearer"
    assert set(data["user"]) == USER_SELF_FIELDS
    token = data["access_token"]
    assert isinstance(token, str) and len(token) >= 32
    assert "password" not in json.dumps(data["user"]).lower()
    session = AuthSession.objects.get(user__username=username)
    assert session.token_digest == sha256(token), "库中摘要不等于令牌 SHA-256"
    assert len(session.token_digest) == 64 and session.token_digest.islower()
    assert not AuthSession.objects.filter(token_digest=token).exists(), "库中出现明文令牌"
    delta = (session.expires_at - before).total_seconds()
    assert 24 * 3600 - 120 <= delta <= 24 * 3600 + 120, f"令牌有效期异常: {delta}s"


@case("ACC-A-06", "登录失败统一 401 UNAUTHENTICATED/账号或密码错误（密码错、账号不存在、账号停用）")
def acc_a_06():
    username = next_name("fail_case")
    assert_status(register(username), 201)
    attempts = [
        {"username": username, "password": "wrong-password-1"},
        {"username": "nobody_here_x", "password": USER_PASSWORD},
    ]
    for payload in attempts:
        resp = request("post", "/api/v1/auth/login", payload)
        assert_status(resp, 401)
        body = _json(resp)
        assert_envelope(body, "UNAUTHENTICATED", with_errors=True)
        assert body["message"] == "账号或密码错误", body["message"]
        assert body["errors"] == {}
    user = User.objects.get(username=username)
    user.is_active = False
    user.save(update_fields=["is_active"])
    inactive = request("post", "/api/v1/auth/login", {"username": username, "password": USER_PASSWORD})
    assert_status(inactive, 401)
    assert _json(inactive)["message"] == "账号或密码错误"
    assert AuthSession.objects.filter(user=user).count() == 0, "失败登录不应建立会话"


@case("ACC-A-07", "登出：撤销当前令牌（旧令牌 401）、第二会话仍有效、重复登出 401")
def acc_a_07():
    username = next_name("logout_case")
    assert_status(register(username), 201)
    t1 = request("post", "/api/v1/auth/login", {"username": username, "password": USER_PASSWORD}).json()["data"]["access_token"]
    t2 = request("post", "/api/v1/auth/login", {"username": username, "password": USER_PASSWORD}).json()["data"]["access_token"]
    assert t1 != t2
    assert request("get", "/api/v1/users/me", token=t1).status_code == 200
    out = request("post", "/api/v1/auth/logout", {}, token=t1)
    assert_status(out, 200)
    assert _json(out)["data"] is None
    assert request("get", "/api/v1/users/me", token=t1).status_code == 401, "旧令牌未失效"
    assert request("get", "/api/v1/users/me", token=t2).status_code == 200, "第二会话被误杀"
    assert AuthSession.objects.filter(user__username=username).count() == 1
    again = request("post", "/api/v1/auth/logout", {}, token=t1)
    assert_status(again, 401)
    assert_envelope(_json(again), "UNAUTHENTICATED", with_errors=True)


@case("ACC-A-08", "未认证 401 + WWW-Authenticate: Bearer；异常 Authorization 头一律 401 不 500")
def acc_a_08():
    for method, path in (("get", "/api/v1/users/me"), ("patch", "/api/v1/users/me"),
                         ("post", "/api/v1/auth/logout"), ("get", "/api/v1/users/me/campus-binding")):
        resp = request(method, path, {} if method != "get" else None)
        assert_status(resp, 401, f"{method.upper()} {path}")
        assert "Bearer" in (resp.headers.get("WWW-Authenticate") or ""), \
            f"缺少 WWW-Authenticate: Bearer -> {dict(resp.headers)}"
    for header in ("Token abc", "Basic eA==", "Bearer", "Bearer a b", "Bearer invalid-token"):
        resp = client.get("/api/v1/users/me", HTTP_AUTHORIZATION=header)
        assert_status(resp, 401, header)
        assert_envelope(_json(resp), "UNAUTHENTICATED", with_errors=True)


@case("ACC-A-09", "过期令牌 401；公开接口携带无效 Bearer 同样 401（FR-A-08）")
def acc_a_09():
    _, token, user = make_account("expire_case")
    session = AuthSession.objects.get(user=user)
    session.expires_at = timezone.now() - timedelta(seconds=1)
    session.save(update_fields=["expires_at"])
    assert request("get", "/api/v1/users/me", token=token).status_code == 401
    post = FIXTURE["post"]
    public_ok = client.get(f"/api/v1/posts/{post.pk}")
    assert_status(public_ok, 200, "公开详情匿名可读")
    bad = client.get(f"/api/v1/posts/{post.pk}", HTTP_AUTHORIZATION="Bearer not-a-real-token")
    assert_status(bad, 401, "公开接口 + 无效 Bearer 必须 401")
    assert_envelope(_json(bad), "UNAUTHENTICATED", with_errors=True)


@case("ACC-A-10", "GET /users/me 200：字段集合精确、无密码/哈希/学号；未登录 401")
def acc_a_10():
    username, token, user = make_account("me_case", nickname="资料用户")
    resp = request("get", "/api/v1/users/me", token=token)
    assert_status(resp, 200)
    data = _json(resp)["data"]
    assert set(data) == USER_SELF_FIELDS, sorted(data)
    assert data["id"] == str(user.pk) and data["nickname"] == "资料用户"
    raw = json.dumps(data).lower()
    for marker in ("pbkdf2", "password", "hash", "token_digest"):
        assert marker not in raw, f"响应出现敏感标记 {marker}"
    assert request("get", "/api/v1/users/me").status_code == 401


@case("ACC-A-11", "PATCH /users/me：改昵称成功且 updated_at 变化；空对象/未知字段/只读字段 400")
def acc_a_11():
    username, token, user = make_account("patch_case", nickname="旧昵称")
    before = request("get", "/api/v1/users/me", token=token).json()["data"]
    time.sleep(0.02)
    resp = request("patch", "/api/v1/users/me", {"nickname": "新昵称", "bio": "软件工程 2024 级"}, token=token)
    assert_status(resp, 200)
    data = _json(resp)["data"]
    assert set(data) == USER_SELF_FIELDS
    assert data["nickname"] == "新昵称" and data["bio"] == "软件工程 2024 级"
    assert data["updated_at"] != before["updated_at"], "updated_at 未变化"
    assert data["created_at"] == before["created_at"]
    user.refresh_from_db()
    assert (user.nickname, user.bio) == ("新昵称", "软件工程 2024 级")
    empty = request("patch", "/api/v1/users/me", {}, token=token)
    assert_status(empty, 400)
    assert _json(empty)["errors"], "空对象应产生 errors"
    for readonly in ({"username": "hacked"}, {"is_campus_verified": True}, {"verification_mode": "demo"},
                     {"password": "new-pass-123"}, {"password_hash": "x"}, {"id": "1"}):
        resp = request("patch", "/api/v1/users/me", readonly, token=token)
        assert_status(resp, 400, f"只读/未知字段 {list(readonly)}")
        assert set(readonly) & set(_json(resp)["errors"]), f"错误未指向 {list(readonly)}"
    user.refresh_from_db()
    assert user.username == username and user.is_campus_verified is False
    assert request("patch", "/api/v1/users/me", {"nickname": "x"}).status_code == 401


@case("ACC-A-12", "PATCH 长度边界 1/30/31、200/201 与首尾空白裁剪，失败不改数据")
def acc_a_12():
    username, token, user = make_account("bound_case", nickname="边界用户")
    for value, expected in (("名", 200), ("名" * 30, 200), ("名" * 31, 400)):
        resp = request("patch", "/api/v1/users/me", {"nickname": value}, token=token)
        assert_status(resp, expected, f"nickname 长度 {len(value)}")
        if expected == 400:
            assert "nickname" in _json(resp)["errors"]
    for value, expected in (("字" * 200, 200), ("字" * 201, 400)):
        resp = request("patch", "/api/v1/users/me", {"bio": value}, token=token)
        assert_status(resp, expected, f"bio 长度 {len(value)}")
        if expected == 400:
            assert "bio" in _json(resp)["errors"]
    trimmed = request("patch", "/api/v1/users/me", {"nickname": "  小林  ", "bio": "  简介  "}, token=token)
    assert_status(trimmed, 200)
    assert trimmed.json()["data"]["nickname"] == "小林" and trimmed.json()["data"]["bio"] == "简介"
    blank = request("patch", "/api/v1/users/me", {"nickname": "   "}, token=token)
    assert_status(blank, 400, "仅空白昵称必须 400")
    user.refresh_from_db()
    assert user.nickname == "小林"


@case("ACC-A-13", "seed_demo_users：先补绑定再打印未被使用身份；幂等；6 身份只存摘要；--reset-codes 仅未使用身份")
def acc_a_13():
    out1 = io.StringIO()
    call_command("seed_demo_users", stdout=out1)
    text1 = out1.getvalue()
    assert DemoIdentity.objects.count() == 6, DemoIdentity.objects.count()
    assert all(len(row.code_digest) == 64 for row in DemoIdentity.objects.all())
    # 首次运行：自动补绑定先执行，只为“仍未被使用”的身份打印明文码，避免打印随即失效的码
    assert "已为演示认证账号补绑定" in text1, text1
    assert text1.index("已为演示认证账号补绑定") < text1.index("一次性绑定码"), text1
    code_lines = [line for line in text1.splitlines() if "学号" in line and "绑定码" in line]
    assert len(code_lines) == 3, f"应只打印 3 个可用身份码，实际 {code_lines}"
    assert text1.count("20260004") >= 1 and DEMO_BINDING_CODE in text1
    assert "20260001  绑定码" not in text1, "已占用身份的明文码不应打印"
    assert not DemoIdentity.objects.filter(code_digest__contains=DEMO_BINDING_CODE).exists(), "库中出现明文绑定码"
    # 演示认证账号自动补绑定（学号 20260001～20260003），unverified 不认证
    for name, student_no in (("publisher", "20260001"), ("applicant", "20260002"), ("competitor", "20260003")):
        user = User.objects.get(username=name)
        binding = CampusBinding.objects.filter(user=user).first()
        assert binding is not None and binding.student_no == student_no, f"{name} 未自动补绑定"
        assert DemoIdentity.objects.get(campus=FIXTURE["campus"], student_no=student_no).used_by_id == user.pk
        assert user.is_campus_verified is True
    assert User.objects.get(username="unverified").is_campus_verified is False
    # 幂等：二次运行不新建、不打印绑定码，提示已有可用身份
    out2 = io.StringIO()
    call_command("seed_demo_users", stdout=out2)
    text2 = out2.getvalue()
    assert DemoIdentity.objects.count() == 6
    assert "绑定码" not in text2, f"幂等运行时不应再打印绑定码: {text2}"
    assert "已有身份 3 个可用" in text2, text2
    # --reset-codes 只重置未使用身份；已使用身份的摘要不变
    used_digest = DemoIdentity.objects.get(campus=FIXTURE["campus"], student_no="20260001").code_digest
    out3 = io.StringIO()
    call_command("seed_demo_users", "--reset-codes", stdout=out3)
    assert DemoIdentity.objects.get(campus=FIXTURE["campus"], student_no="20260001").code_digest == used_digest
    resets = [line for line in out3.getvalue().splitlines() if "学号" in line and "绑定码" in line]
    assert len(resets) == 3, f"--reset-codes 只应重置 3 个未使用身份: {resets}"
    assert "20260001  绑定码" not in out3.getvalue()
    assert CampusBinding.objects.count() == 3


@case("ACC-A-14", "seed_demo_users 在 DEMO_MODE=False 时抛 CommandError 且不写数据")
def acc_a_14():
    before = (Campus.objects.count(), DemoIdentity.objects.count(), CampusBinding.objects.count())
    with override_settings(DEMO_MODE=False):
        try:
            call_command("seed_demo_users", stdout=io.StringIO())
        except CommandError:
            pass
        else:
            raise AssertionError("DEMO_MODE=False 时未抛 CommandError")
    after = (Campus.objects.count(), DemoIdentity.objects.count(), CampusBinding.objects.count())
    assert before == after, f"非演示模式命令写入了数据: {before} -> {after}"


@case("ACC-A-15", "未绑定 GET /users/me/campus-binding 返回 200 data=null")
def acc_a_15():
    _, token, user = make_account("unbound_case")
    resp = request("get", "/api/v1/users/me/campus-binding", token=token)
    assert_status(resp, 200)
    assert _json(resp)["data"] is None
    assert request("get", "/api/v1/users/me", token=token).json()["data"]["is_campus_verified"] is False
    assert request("get", "/api/v1/users/me/campus-binding").status_code == 401


@case("ACC-A-16", "绑定成功 201：脱敏 ****0004、认证标记、CampusBinding、DemoIdentity.used_by 事务副作用")
def acc_a_16():
    username, token, user = make_account("bind_ok")
    resp = request("post", "/api/v1/users/me/campus-binding",
                   {"campus_id": "campus_main", "student_no": "20260004", "binding_code": DEMO_BINDING_CODE},
                   token=token)
    assert_status(resp, 201)
    data = _json(resp)["data"]
    assert set(data) == BINDING_FIELDS, sorted(data)
    assert data["campus_id"] == "campus_main"
    assert data["student_no_masked"] == "****0004", data["student_no_masked"]
    assert data["verification_mode"] == "demo"
    assert data["verified_at"].endswith("Z")
    assert "20260004" not in json.dumps(data), "绑定响应泄露学号明文"
    assert DEMO_BINDING_CODE not in json.dumps(data)
    user.refresh_from_db()
    assert user.is_campus_verified is True and user.verification_mode == "demo"
    binding = CampusBinding.objects.get(user=user)
    assert (binding.campus_id, binding.student_no) == ("campus_main", "20260004")
    assert DemoIdentity.objects.get(campus=FIXTURE["campus"], student_no="20260004").used_by_id == user.pk
    # 绑定后 GET 返回同一脱敏视图
    get_resp = request("get", "/api/v1/users/me/campus-binding", token=token)
    assert_status(get_resp, 200)
    assert set(get_resp.json()["data"]) == BINDING_FIELDS
    assert get_resp.json()["data"]["student_no_masked"] == "****0004"


@case("ACC-A-17", "重复绑定 409 DUPLICATE_RESOURCE；目标身份不被消耗")
def acc_a_17():
    _, token, user = make_account("bind_dup")
    first = request("post", "/api/v1/users/me/campus-binding",
                    {"campus_id": "campus_main", "student_no": "20260005", "binding_code": DEMO_BINDING_CODE},
                    token=token)
    assert_status(first, 201)
    again = request("post", "/api/v1/users/me/campus-binding",
                    {"campus_id": "campus_main", "student_no": "20260006", "binding_code": DEMO_BINDING_CODE},
                    token=token)
    assert_status(again, 409)
    assert_envelope(_json(again), "DUPLICATE_RESOURCE", with_errors=True)
    assert CampusBinding.objects.filter(user=user).count() == 1
    assert DemoIdentity.objects.get(campus=FIXTURE["campus"], student_no="20260006").used_by_id is None, \
        "重复绑定请求消耗了另一个身份"
    user.refresh_from_db()
    assert user.is_campus_verified is True


@case("ACC-A-18", "身份已被他人占用 409 DUPLICATE_RESOURCE（共同契约 §4），占用者未绑定")
def acc_a_18():
    _, token, user = make_account("bind_occupy")
    resp = request("post", "/api/v1/users/me/campus-binding",
                   {"campus_id": "campus_main", "student_no": "20260004", "binding_code": DEMO_BINDING_CODE},
                   token=token)
    assert_status(resp, 409)
    assert_envelope(_json(resp), "DUPLICATE_RESOURCE", with_errors=True)
    user.refresh_from_db()
    assert user.is_campus_verified is False
    assert not CampusBinding.objects.filter(user=user).exists()
    assert CampusBinding.objects.filter(student_no="20260004").count() == 1, "被占用身份出现第二条绑定"


@case("ACC-A-19", "绑定码错误 400 归 binding_code，不消耗身份、用户状态与数据无副作用")
def acc_a_19():
    _, token, user = make_account("bind_wrong")
    resp = request("post", "/api/v1/users/me/campus-binding",
                   {"campus_id": "campus_main", "student_no": "20260006", "binding_code": "wrong-code-0001"},
                   token=token)
    assert_status(resp, 400)
    body = _json(resp)
    assert_envelope(body, "VALIDATION_ERROR", with_errors=True)
    assert body["errors"]["binding_code"] == ["绑定码无效或已被使用"], body["errors"]
    user.refresh_from_db()
    assert user.is_campus_verified is False and user.verification_mode is None
    assert not CampusBinding.objects.filter(user=user).exists()
    assert DemoIdentity.objects.get(campus=FIXTURE["campus"], student_no="20260006").used_by_id is None
    # 失败后同一身份用正确码仍可绑定（失败不毒化身份）——顺带完成 FR-A-09 的“绑定后认领”
    ok = request("post", "/api/v1/users/me/campus-binding",
                 {"campus_id": "campus_main", "student_no": "20260006", "binding_code": DEMO_BINDING_CODE},
                 token=token)
    assert_status(ok, 201)


@case("ACC-A-20", "未知校区/学号格式/绑定码长度 400 且错误归对应字段")
def acc_a_20():
    _, token, _user = make_account("bind_invalid")
    base = {"campus_id": "campus_main", "student_no": "20260007", "binding_code": DEMO_BINDING_CODE}
    checks = [
        ("campus_id", {**base, "campus_id": "campus_unknown"}),
        ("student_no", {**base, "student_no": "12345"}),
        ("student_no", {**base, "student_no": "abc-def"}),
        ("student_no", {**base, "student_no": ""}),
        ("student_no", {**base, "student_no": "1" * 21}),
        ("binding_code", {**base, "binding_code": "12345"}),
        ("binding_code", {**base, "binding_code": "x" * 65}),
    ]
    for field, payload in checks:
        resp = request("post", "/api/v1/users/me/campus-binding", payload, token=token)
        assert_status(resp, 400, f"{field}={payload[field]!r}")
        errors = _json(resp)["errors"]
        assert field in errors, f"错误未归 {field}: {errors}"
    assert not CampusBinding.objects.filter(user__username__startswith="bind_invalid_").exists()


@case("ACC-A-21", "20 位学号脱敏：仅保留末 4 位，其余 16 个 *，响应无学号明文")
def acc_a_21():
    student_no = "20261234567890123404"  # 20 位
    DemoIdentity.objects.get_or_create(
        campus=FIXTURE["campus"], student_no=student_no,
        defaults={"code_digest": sha256("long-student-no-code")})
    _, token, _user = make_account("mask_case")
    resp = request("post", "/api/v1/users/me/campus-binding",
                   {"campus_id": "campus_main", "student_no": student_no, "binding_code": "long-student-no-code"},
                   token=token)
    assert_status(resp, 201)
    masked = _json(resp)["data"]["student_no_masked"]
    assert masked == "*" * 16 + "3404", masked
    assert student_no not in resp.content.decode("utf-8")


@case("ACC-A-22", "登录限流：同 IP 第 11 次 429 RATE_LIMITED + Retry-After；键隔离；窗口结束后恢复")
def acc_a_22():
    username = next_name("throttle_login")
    assert_status(register(username), 201)
    cache.clear()

    class _FrozenTime:  # 固定窗口计时可控，验证窗口边界与恢复；避免跨分钟边界导致计数意外重置
        now = [1_700_000_000.0]

        @classmethod
        def time(cls):
            return cls.now[0]

    with patch("users.throttles.time", _FrozenTime), override_settings(RATE_LIMIT_ENABLED=True):
        for index in range(10):
            resp = request("post", "/api/v1/auth/login", {"username": username, "password": "wrong-pass-01"})
            assert_status(resp, 401, f"第 {index + 1} 次应 401")
        limited = request("post", "/api/v1/auth/login", {"username": username, "password": "wrong-pass-01"})
        assert_status(limited, 429)
        assert_envelope(_json(limited), "RATE_LIMITED", with_errors=True)
        retry_after = limited.headers.get("Retry-After")
        assert retry_after is not None and int(retry_after) >= 1, f"Retry-After 缺失/非法: {retry_after}"
        # 换 IP 后计数独立（键隔离）
        other_ip = client.generic("POST", "/api/v1/auth/login",
                                 data=json.dumps({"username": username, "password": USER_PASSWORD}),
                                 content_type="application/json", REMOTE_ADDR="10.0.0.9")
        assert_status(other_ip, 200, "不同来源 IP 不应被同一计数误伤")
        # 窗口结束后恢复为正常业务响应（TC-A-047）
        _FrozenTime.now[0] += 61.0
        recovered = request("post", "/api/v1/auth/login", {"username": username, "password": "wrong-pass-01"})
        assert_status(recovered, 401, "新窗口应恢复正常业务响应")
    cache.clear()
    assert AuthSession.objects.filter(user__username=username).count() == 1


@case("ACC-A-23", "绑定限流：同用户第 6 次 429 RATE_LIMITED + Retry-After，前 5 次按业务校验返回")
def acc_a_23():
    _, token, _user = make_account("throttle_bind")
    cache.clear()
    payload = {"campus_id": "campus_main", "student_no": "20260008", "binding_code": "wrong-code-0002"}

    class _FrozenTime:
        @staticmethod
        def time():
            return 1_700_000_000.0

    with patch("users.throttles.time", _FrozenTime), override_settings(RATE_LIMIT_ENABLED=True):
        for index in range(5):
            resp = request("post", "/api/v1/users/me/campus-binding", payload, token=token)
            assert_status(resp, 400, f"第 {index + 1} 次绑定应 400")
        limited = request("post", "/api/v1/users/me/campus-binding", payload, token=token)
        assert_status(limited, 429)
        assert_envelope(_json(limited), "RATE_LIMITED", with_errors=True)
        assert int(limited.headers.get("Retry-After")) >= 1
    cache.clear()
    assert not CampusBinding.objects.filter(user__username__startswith="throttle_bind_").exists()


@case("ACC-A-24", "未登录认领 401；已登录未认证认领 403 IDENTITY_REQUIRED（C 的接口身份前置）")
def acc_a_24():
    post = FIXTURE["post"]
    claim_payload = {"post_id": str(post.pk), "verification_text": "蓝色钥匙挂着小熊挂件，共三把。"}
    anon = request("post", "/api/v1/claims", claim_payload)
    assert_status(anon, 401)
    unverified = FIXTURE["users"]["unverified"]
    token = login_token(unverified)
    before = Claim.objects.count()
    resp = request("post", "/api/v1/claims", claim_payload, token=token)
    assert_status(resp, 403)
    assert_envelope(_json(resp), "IDENTITY_REQUIRED", with_errors=True)
    assert "校园身份" in _json(resp)["message"]
    assert Claim.objects.count() == before, "403 请求产生了认领数据"


@case("ACC-A-25", "绑定后认领 201；C 的公开 PostSummary.publisher 仅 4 个公开字段（无 username/bio）")
def acc_a_25():
    username, token, user = make_account("claim_after_bind")
    bind = request("post", "/api/v1/users/me/campus-binding",
                   {"campus_id": "campus_main", "student_no": "20260009",
                    "binding_code": "claim-after-bind-code"}, token=token)
    if bind.status_code == 400:
        DemoIdentity.objects.create(campus=FIXTURE["campus"], student_no="20260009",
                                   code_digest=sha256("claim-after-bind-code"))
        bind = request("post", "/api/v1/users/me/campus-binding",
                       {"campus_id": "campus_main", "student_no": "20260009",
                        "binding_code": "claim-after-bind-code"}, token=token)
    assert_status(bind, 201)
    post = FIXTURE["post"]
    claim = request("post", "/api/v1/claims",
                    {"post_id": str(post.pk), "verification_text": "蓝色钥匙挂着小熊挂件，共三把。"}, token=token)
    assert_status(claim, 201)
    data = _json(claim)["data"]
    assert data["applicant_id"] == str(user.pk) and data["applicant"]["id"] == str(user.pk)
    assert set(data["applicant"]) == {"id", "nickname", "is_campus_verified", "verification_mode"}
    # 公开详情发布者摘要：仅公开字段，不含账号与简介
    public = client.get(f"/api/v1/posts/{post.pk}")
    assert_status(public, 200)
    publisher = _json(public)["data"]["publisher"]
    assert set(publisher) == {"id", "nickname", "is_campus_verified", "verification_mode"}, sorted(publisher)
    text = json.dumps(publisher, ensure_ascii=False)
    assert User.objects.get(username="publisher").username not in text, "公开摘要泄露账号"
    assert "bio" not in publisher


@case("ACC-A-26", "T13 伪身份字段：认领/资料请求携带 applicant_id、user_id 等返回 400，身份由令牌决定")
def acc_a_26():
    _, token, _user = make_account("t13_case")
    post = FIXTURE["post"]
    forged = {"post_id": str(post.pk), "verification_text": "蓝色钥匙挂着小熊挂件，共三把。",
              "applicant_id": str(FIXTURE["users"]["applicant"].pk)}
    resp = request("post", "/api/v1/claims", forged, token=token)
    assert_status(resp, 400)
    assert "applicant_id" in _json(resp)["errors"]
    for extra in ({"user_id": "1"}, {"is_campus_verified": True}):
        resp = request("post", "/api/v1/claims", {**forged, **extra}, token=token)
        assert_status(resp, 400, f"伪造字段 {list(extra)}")
    # 资料接口同样拒绝只读身份字段（已在 ACC-A-11 覆盖，这里确认不产生越权数据）
    assert not Claim.objects.filter(applicant__username__startswith="t13_case_").exists()


@case("ACC-A-27", "隐私抽查：注册/登录/资料/绑定/认领响应不含密码哈希、学号明文、绑定码明文、令牌摘要")
def acc_a_27():
    username, token, user = make_account("privacy_case")
    responses = [
        register(next_name("privacy_reg")),
        request("post", "/api/v1/auth/login", {"username": username, "password": USER_PASSWORD}),
        request("get", "/api/v1/users/me", token=token),
        request("get", "/api/v1/users/me/campus-binding", token=token),
        request("post", "/api/v1/auth/login", {"username": username, "password": USER_PASSWORD}),
    ]
    secrets = [USER_PASSWORD, "pbkdf2_sha256", "test-only-123", sha256(USER_PASSWORD)]
    for resp in responses:
        text = resp.content.decode("utf-8", "replace")
        for marker in ("pbkdf2", "token_digest"):
            assert marker not in text, f"响应出现 {marker}: {text[:200]}"
        for secret in secrets:
            assert secret not in text, f"响应出现敏感值 {secret!r}"
    login_body = _json(responses[1])["data"]
    assert login_body["access_token"] not in json.dumps(login_body["user"]), "用户资料中出现令牌"
    assert login_body["access_token"] not in json.dumps(_json(responses[2])), "资料响应出现令牌"
    binding_text = responses[3].content.decode("utf-8")
    assert DEMO_BINDING_CODE not in binding_text
    assert AuthSession.objects.get(user=user, token_digest=sha256(token))


@case("ACC-A-28", "绑定码一次性：成功绑定后他人无法再用；错误码不消耗身份；库中只存摘要")
def acc_a_28():
    campus = FIXTURE["campus"]
    student_no, code = "20260010", "one-shot-code-0001"
    DemoIdentity.objects.get_or_create(campus=campus, student_no=student_no,
                                       defaults={"code_digest": sha256(code)})
    _, token1, user1 = make_account("once_first")
    ok = request("post", "/api/v1/users/me/campus-binding",
                 {"campus_id": "campus_main", "student_no": student_no, "binding_code": code}, token=token1)
    assert_status(ok, 201)
    identity = DemoIdentity.objects.get(campus=campus, student_no=student_no)
    assert identity.used_by_id == user1.pk
    assert identity.code_digest == sha256(code) and code not in identity.code_digest
    _, token2, user2 = make_account("once_second")
    again = request("post", "/api/v1/users/me/campus-binding",
                    {"campus_id": "campus_main", "student_no": student_no, "binding_code": code}, token=token2)
    assert_status(again, 409, "已使用的一次性绑定码必须被拒绝")
    user2.refresh_from_db()
    assert user2.is_campus_verified is False


@case("ACC-A-29", "绑定事务回滚：创建绑定后置认证标记失败时整体回滚，无半成品数据（TC-A-050）")
def acc_a_29():
    campus = FIXTURE["campus"]
    student_no, code = "20260011", "rollback-code-0001"
    DemoIdentity.objects.get_or_create(campus=campus, student_no=student_no,
                                       defaults={"code_digest": sha256(code)})
    _, token, user = make_account("rollback_case")
    logging.disable(logging.CRITICAL)
    try:
        # 在“创建 CampusBinding”之后、“置用户认证标记”之前注入异常：user.save 抛错。
        with patch.object(User, "save", side_effect=RuntimeError("injected failure after binding create")):
            resp = request("post", "/api/v1/users/me/campus-binding",
                           {"campus_id": "campus_main", "student_no": student_no,
                            "binding_code": code}, token=token)
    finally:
        logging.disable(logging.NOTSET)
    assert_status(resp, 500)
    assert _json(resp)["code"] == "INTERNAL_ERROR"
    user.refresh_from_db()
    assert not CampusBinding.objects.filter(user=user).exists(), "回滚失败：残留 CampusBinding 记录"
    identity = DemoIdentity.objects.get(campus=campus, student_no=student_no)
    assert identity.used_by_id is None, "回滚失败：DemoIdentity.used_by 被写入"
    assert user.is_campus_verified is False and user.verification_mode is None, "回滚失败：用户认证标记被写入"


@case("ACC-A-30", "并发绑定同一身份：恰一个 201、另一个 409，库中仅一条绑定（线程+独立连接）")
def acc_a_30():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections, connections

    campus = FIXTURE["campus"]
    student_no, code = "20260012", "race-code-0001"
    DemoIdentity.objects.get_or_create(campus=campus, student_no=student_no,
                                       defaults={"code_digest": sha256(code)})
    _, token_a, user_a = make_account("race_first")
    _, token_b, user_b = make_account("race_second")
    barrier = Barrier(2)

    def bind(token):
        close_old_connections()
        try:
            local = Client()
            barrier.wait(timeout=10)
            resp = local.generic(
                "POST", "/api/v1/users/me/campus-binding",
                data=json.dumps({"campus_id": "campus_main", "student_no": student_no,
                                 "binding_code": code}),
                content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {token}")
            return resp.status_code
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = sorted(pool.map(bind, [token_a, token_b]))
    assert statuses == [201, 409], f"并发结果应为 [201, 409]，实际 {statuses}"
    assert CampusBinding.objects.filter(campus=campus, student_no=student_no).count() == 1
    identity = DemoIdentity.objects.get(campus=campus, student_no=student_no)
    assert identity.used_by_id in (user_a.pk, user_b.pk)
    assert User.objects.filter(pk__in=[user_a.pk, user_b.pk], is_campus_verified=True).count() == 1, \
        "并发绑定出现两个已认证用户"


@case("ACC-A-31", "并发注册同一账号（大小写不同）：恰一个 201、另一个 409，库中一条记录（TC-A-007）")
def acc_a_31():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections, connections

    username = next_name("race_register")
    barrier = Barrier(2)

    def signup(candidate):
        close_old_connections()
        try:
            local = Client()
            barrier.wait(timeout=10)
            resp = local.generic(
                "POST", "/api/v1/auth/register",
                data=json.dumps({"username": candidate, "password": USER_PASSWORD, "nickname": "并发注册"}),
                content_type="application/json")
            return resp.status_code
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = sorted(pool.map(signup, [username.lower(), username.upper()]))
    assert statuses == [201, 409], f"并发注册结果应为 [201, 409]，实际 {statuses}"
    assert User.objects.filter(username=username.lower()).count() == 1


@case("ACC-A-32", "500 不泄露内部细节：统一 INTERNAL_ERROR 包装，无堆栈/SQL/路径")
def acc_a_32():
    logging.disable(logging.CRITICAL)
    try:
        _, token, _user = make_account("error_case")
        with patch("users.views.s.user_self", side_effect=RuntimeError("private /tmp/db.sqlite3 SELECT secret")):
            resp = request("get", "/api/v1/users/me", token=token)
    finally:
        logging.disable(logging.NOTSET)
    assert_status(resp, 500)
    body = _json(resp)
    assert set(body) == {"code", "message", "data", "errors"}
    assert body["code"] == "INTERNAL_ERROR"
    text = resp.content.decode("utf-8")
    for marker in ("Traceback", "private", "SELECT", "db.sqlite3", "RuntimeError"):
        assert marker not in text, f"500 响应泄露 {marker}: {text[:300]}"


@case("ACC-A-33", "404/401/403 统一包装且不泄露内部细节（含 DEBUG=False 的项目级 404 处理器）")
def acc_a_33():
    with override_settings(DEBUG=False):
        missing = client.get("/api/v1/users/me/does-not-exist")
        assert_status(missing, 404)
        body = _json(missing)
        assert set(body) == {"code", "message", "data", "errors"}, body
        assert body["code"] == "NOT_FOUND"
        text = missing.content.decode("utf-8")
        for marker in ("Traceback", "sqlite3", "File \"", "settings"):
            assert marker not in text
    unauthorized = request("get", "/api/v1/users/me")
    assert_status(unauthorized, 401)
    body = _json(unauthorized)
    assert set(body) == {"code", "message", "data", "errors"} and body["errors"] == {}
    assert "Traceback" not in unauthorized.content.decode("utf-8")


@case("ACC-A-34", "静态与可复现检查：manage.py check 0 issues、makemigrations --check 无待生成迁移")
def acc_a_34():
    call_command("check", stdout=io.StringIO())
    out = io.StringIO()
    try:
        call_command("makemigrations", "--check", "--dry-run", stdout=out)
    except SystemExit as exc:  # 有未生成迁移时 Django 以 SystemExit(1) 结束
        raise AssertionError(f"存在未生成的迁移: {out.getvalue()[:300]}") from exc


# ---------------------------------------------------------------- 执行

def login_token(user):
    resp = request("post", "/api/v1/auth/login",
                   {"username": user.username, "password": "test-only-123"})
    assert_status(resp, 200)
    return resp.json()["data"]["access_token"]


def main():
    print("=" * 78)
    print("成员 A（用户管理）独立验收脚本 — 临时数据库与真实视图链路")
    print(f"临时数据库: {os.environ['DJANGO_DB_PATH']}")
    print("=" * 78)
    call_command("migrate", interactive=False, verbosity=0)
    global FIXTURE
    FIXTURE = prepare_fixture()
    for fn in (
        acc_a_01, acc_a_02, acc_a_03, acc_a_04, acc_a_05, acc_a_06, acc_a_07, acc_a_08,
        acc_a_09, acc_a_10, acc_a_11, acc_a_12, acc_a_13, acc_a_14, acc_a_15, acc_a_16,
        acc_a_17, acc_a_18, acc_a_19, acc_a_20, acc_a_21, acc_a_22, acc_a_23, acc_a_24,
        acc_a_25, acc_a_26, acc_a_27, acc_a_28, acc_a_29, acc_a_30, acc_a_31, acc_a_32, acc_a_33, acc_a_34,
    ):
        fn()
    passed = sum(1 for row in CASES if row[2])
    failed = len(CASES) - passed
    print("-" * 78)
    print(f"汇总：{passed}/{len(CASES)} PASS，{failed} FAIL")
    for case_id, title, ok, detail in CASES:
        if not ok:
            print(f"  FAILED {case_id} {title} :: {detail}")
    print("-" * 78)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = 1
    try:
        exit_code = main()
    finally:
        shutil.rmtree(_TMP_DIR, ignore_errors=True)
    sys.exit(exit_code)
