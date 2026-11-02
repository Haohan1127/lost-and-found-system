"""A 模块（用户管理）出参与入参序列化：UserSelf、绑定视图与严格校验输入。"""
from django.core.validators import RegexValidator
from rest_framework import serializers

from common.serializers import IdField, StrictSerializer, StringField, timestamp

USERNAME_VALIDATOR = RegexValidator(r"^[A-Za-z0-9_]{4,32}$", "账号需为 4～32 位字母、数字或下划线")
STUDENT_NO_VALIDATOR = RegexValidator(r"^[A-Za-z0-9]{6,20}$", "学号需为 6～20 位字母或数字")


class RegisterInput(StrictSerializer):
    username = StringField(min_length=4, max_length=32, validators=[USERNAME_VALIDATOR])
    password = StringField(min_length=8, max_length=64, trim_whitespace=False)
    nickname = StringField(min_length=1, max_length=30)


class LoginInput(StrictSerializer):
    username = StringField(min_length=1, max_length=32)
    password = StringField(min_length=1, max_length=64, trim_whitespace=False)


class UpdateProfileInput(StrictSerializer):
    nickname = StringField(min_length=1, max_length=30, required=False)
    bio = StringField(max_length=200, allow_blank=True, required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError({"non_field_errors": ["至少提交一个可修改字段"]})
        return attrs


class CampusBindingInput(StrictSerializer):
    campus_id = IdField()
    student_no = StringField(min_length=6, max_length=20, validators=[STUDENT_NO_VALIDATOR])
    binding_code = StringField(min_length=6, max_length=64, trim_whitespace=False)


def mask_student_no(student_no):
    """学号脱敏：保留末 4 位，其余替换为 *（20260001 -> ****0001）。"""
    keep = student_no[-4:]
    return "*" * max(0, len(student_no) - 4) + keep


def user_self(user):
    """UserSelf：本人资料，不含密码/哈希。"""
    return {
        "id": str(user.pk), "username": user.username, "nickname": user.nickname, "bio": user.bio,
        "is_campus_verified": user.is_campus_verified, "verification_mode": user.verification_mode,
        "created_at": timestamp(user.date_joined), "updated_at": timestamp(user.updated_at),
    }


def binding_view(binding):
    """校园绑定视图：学号只出脱敏值。"""
    return {
        "campus_id": binding.campus_id, "student_no_masked": mask_student_no(binding.student_no),
        "verification_mode": binding.verification_mode, "verified_at": timestamp(binding.verified_at),
    }
