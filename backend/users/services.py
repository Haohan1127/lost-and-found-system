"""A 模块领域服务：业务规则全部写在这里，视图只做参数校验与响应包装。

约定：
- 业务错误用 common.exceptions.BusinessError(code, message, status) 抛出；
- 数据库写操作放 transaction.atomic()；SQLite 不支持行锁，靠 settings 里的 IMMEDIATE 事务串行化写；
- 成功返回领域对象（User / CampusBinding / AuthSession），由视图转成出参。

下面 4 个函数是成员 C 已依赖的既有实现，签名不要改（C 的 52 项回归用例依赖它们）。
"""
import hashlib
import secrets
from datetime import timedelta
from django.utils import timezone
from common.exceptions import BusinessError
from .models import AuthSession, User


def require_campus_verified(user):
    if not user.is_campus_verified:
        raise BusinessError("IDENTITY_REQUIRED", "发起认领前请完成校园身份绑定（当前为演示认证）", 403)


def user_summary(user):
    return {"id": str(user.pk), "nickname": user.nickname,
            "is_campus_verified": user.is_campus_verified, "verification_mode": user.verification_mode}


def get_user_summaries(user_ids):
    return {str(user.pk): user_summary(user) for user in User.objects.filter(pk__in=user_ids)}


def issue_session(user):
    token = secrets.token_urlsafe(32)
    session = AuthSession.objects.create(user=user, token_digest=hashlib.sha256(token.encode()).hexdigest(),
                                         expires_at=timezone.now() + timedelta(hours=24))
    return token, session


# ==== 以下由你实现（顺序建议按 D1-03 → D2-02，规划表里每一步都有验收命令） ====


def revoke_session(session):
    """TODO [D1-05] 撤销当前令牌：删除传入的 AuthSession 记录即可，其他会话不受影响。"""
    raise NotImplementedError("D1-05 revoke_session")


def register_user(username, password, nickname):
    """TODO [D1-03] 注册新账号：

    - 账号统一转小写后落库；已存在（含并发）返回 409 DUPLICATE_RESOURCE，message 如“该账号已被注册”；
    - 用 user.set_password(password) 存哈希，绝不存明文；
    - 注册不自动登录（不创建会话），返回新建的 User。
    """
    raise NotImplementedError("D1-03 register_user")


def login_user(username, password):
    """TODO [D1-04] 登录校验：

    - 账号不存在 / 密码错误 / 账号停用，统一返回 401 UNAUTHENTICATED、message“账号或密码错误”；
    - 不要返回“账号不存在”这类能枚举账号的提示；成功返回 User。
    """
    raise NotImplementedError("D1-04 login_user")


def update_profile(user, data):
    """TODO [D1-06] 修改本人资料：只写 data 里出现的 nickname / bio，save() 后返回最新 user。"""
    raise NotImplementedError("D1-06 update_profile")


def bind_campus(user, campus_id, student_no, binding_code):
    """TODO [D2-02] 演示校园身份绑定（必须在一个事务内完成），判定顺序：

    限流（视图层）→ 字段格式 → 本人已绑定 → 校区存在 → 锁身份行 → 校验绑定码 → 写入。

    错误口径：
    - 本人已绑定：409 DUPLICATE_RESOURCE（“已完成校园身份绑定”）
    - 校区不存在：400 VALIDATION_ERROR，errors={"campus_id": [...]}
    - 身份不存在或码不匹配：400 VALIDATION_ERROR，errors={"binding_code": [...]}
    - 身份已被他人占用：409 DUPLICATE_RESOURCE
    成功后：创建 CampusBinding、把 DemoIdentity.used_by 置为本用户、
            User.is_campus_verified=True、verification_mode="demo"。
    绑定码比较请用 hmac.compare_digest，不要存明文码。
    """
    raise NotImplementedError("D2-02 bind_campus")
