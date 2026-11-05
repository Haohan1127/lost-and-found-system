"""A 模块（用户管理）入参严格校验与出参视图。

契约来源：docs/共同字段与接口约定.md §4；字段长度/错误码不要自行改。
分工边界：入参字段声明已给出（照契约抄写即可）；标注 TODO 的校验与出参函数由你自己实现。
"""
from datetime import timezone

from django.core.validators import RegexValidator
from rest_framework import serializers
from rest_framework.fields import DateTimeField

from common.serializers import IdField, StrictSerializer, StringField


def timestamp(value):
    """统一按 UTC 输出 ISO8601（与 posts 模块格式一致，见共同契约 2.1；空值返回 None）。"""
    return DateTimeField(default_timezone=timezone.utc).to_representation(value) if value else None


USERNAME_VALIDATOR = RegexValidator(r"^[A-Za-z0-9_]{4,32}$", "账号需为 4～32 位字母、数字或下划线")
STUDENT_NO_VALIDATOR = RegexValidator(r"^[A-Za-z0-9]{6,20}$", "学号需为 6～20 位字母或数字")


class RegisterInput(StrictSerializer):
    """POST /auth/register 入参：三个字段都必填。StrictSerializer 已负责“未知字段 400”。"""
    username = StringField(min_length=4, max_length=32, validators=[USERNAME_VALIDATOR])
    password = StringField(min_length=8, max_length=64, trim_whitespace=False)
    nickname = StringField(min_length=1, max_length=30)


class LoginInput(StrictSerializer):
    """POST /auth/login 入参。密码不裁剪空白（按原值校验）。"""
    username = StringField(min_length=1, max_length=32)
    password = StringField(min_length=1, max_length=64, trim_whitespace=False)


class UpdateProfileInput(StrictSerializer):
    """PATCH /users/me 入参：只允许 nickname、bio，至少提交一个字段。"""
    nickname = StringField(min_length=1, max_length=30, required=False)
    bio = StringField(max_length=200, allow_blank=True, required=False)

    def validate(self, attrs):
        # TODO [D1-06] 一个字段都没提交时抛 400：
        #   raise serializers.ValidationError({"non_field_errors": ["至少提交一个可修改字段"]})
        raise NotImplementedError("D1-06 UpdateProfileInput.validate")


class CampusBindingInput(StrictSerializer):
    """POST /users/me/campus-binding 入参：校区 ID、学号、一次性绑定码。"""
    campus_id = IdField()
    student_no = StringField(min_length=6, max_length=20, validators=[STUDENT_NO_VALIDATOR])
    binding_code = StringField(min_length=6, max_length=64, trim_whitespace=False)


def mask_student_no(student_no):
    """TODO [D2-01] 学号脱敏：保留末 4 位，其余替换为 *。示例：20260004 -> ****0004。"""
    raise NotImplementedError("D2-01 mask_student_no")


def user_self(user):
    """TODO [D1-03] UserSelf 出参：id/username/nickname/bio/is_campus_verified/verification_mode/created_at/updated_at。

    - id 用字符串（str(user.pk)）；时间用本文件 timestamp（UTC ISO8601）
    - created_at 取 user.date_joined，updated_at 取 user.updated_at
    - 绝不能出现 password、密码哈希等敏感字段
    """
    raise NotImplementedError("D1-05 user_self")


def binding_view(binding):
    """TODO [D2-02] 绑定出参：campus_id/student_no_masked/verification_mode/verified_at（学号只给脱敏值）。"""
    raise NotImplementedError("D2-02 binding_view")
