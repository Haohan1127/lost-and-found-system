"""A 模块查询：本人资料、校园绑定、演示身份；写操作统一走 services。"""
from common.exceptions import BusinessError
from .models import CampusBinding, DemoIdentity, User


def current_user(user):
    """返回数据库中最新的本人资料（认证实例可能滞后于刚发生的资料修改）。"""
    fresh = User.objects.filter(pk=user.pk).first()
    if fresh is None:
        raise BusinessError("UNAUTHENTICATED", "登录状态已失效", 401)
    return fresh


def get_campus_binding(user):
    return CampusBinding.objects.select_related("campus").filter(user=user).first()


def get_campus(campus_id):
    from catalog.models import Campus
    return Campus.objects.filter(pk=campus_id).first()


def get_demo_identity(campus, student_no, lock=False):
    queryset = DemoIdentity.objects.filter(campus=campus, student_no=student_no)
    if lock:
        queryset = queryset.select_for_update()
    return queryset.first()
