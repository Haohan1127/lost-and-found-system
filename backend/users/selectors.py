"""A 模块只读查询：视图/服务都从这里取数据；写操作统一放 services.py。

注意：查询函数只负责“查到什么”，不负责业务判定（例外：用户已失效时抛 401）。
"""
from common.exceptions import BusinessError
from .models import CampusBinding, DemoIdentity, User


def current_user(user):
    """TODO [D1-06] 返回数据库中最新的本人对象（登录认证实例里的 nickname/bio 可能已过期）。"""
    raise NotImplementedError("D1-06 current_user")


def get_campus_binding(user):
    """TODO [D2-02] 返回本人绑定记录（带上 campus），未绑定返回 None。"""
    raise NotImplementedError("D2-02 get_campus_binding")


def get_campus(campus_id):
    """TODO [D2-02] 按 ID 查校区字典；不存在返回 None（是否 400 由 service 决定）。"""
    raise NotImplementedError("D2-02 get_campus")


def get_demo_identity(campus, student_no, lock=False):
    """TODO [D2-02] 查演示校园身份；lock=True 时用 select_for_update() 锁住这一行。"""
    raise NotImplementedError("D2-02 get_demo_identity")
