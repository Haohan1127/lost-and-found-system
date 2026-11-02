from collections.abc import Mapping
from datetime import timezone
from rest_framework import serializers
from rest_framework.fields import DateTimeField


def timestamp(value):
    """统一以 UTC ISO8601 输出时间；users 与 posts 共用同一格式。"""
    return DateTimeField(default_timezone=timezone.utc).to_representation(value) if value else None


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, Mapping):
            raise serializers.ValidationError({"non_field_errors": ["必须是 JSON 对象或查询参数"]})
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError({key: ["未知或只读字段"] for key in sorted(unknown)})
        if hasattr(data, "getlist"):
            repeated = [key for key in data if len(data.getlist(key)) != 1]
            if repeated:
                raise serializers.ValidationError({key: ["参数不能重复"] for key in repeated})
        return super().to_internal_value(data)


class StringField(serializers.CharField):
    def to_internal_value(self, data):
        if not isinstance(data, str):
            self.fail("invalid")
        return super().to_internal_value(data)


class IdField(StringField):
    def __init__(self, **kwargs):
        super().__init__(max_length=64, trim_whitespace=False, **kwargs)


class EmptyInput(StrictSerializer):
    pass


def numeric_id(value):
    """仅供内部 BigAutoField 查询使用；API 仍以字符串收发 ID。"""
    if not isinstance(value, str) or not value.isascii() or not value.isdecimal() or len(value) > 19:
        return None
    number = int(value)
    return number if 0 < number <= 9223372036854775807 else None


def validated(serializer_class, data):
    serializer = serializer_class(data=data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


class PageQuery(StrictSerializer):
    page = serializers.IntegerField(min_value=1, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=100, default=20)


def paginate(queryset, query, serialize):
    page, size = query["page"], query["page_size"]
    total = queryset.count()
    offset = (page - 1) * size
    # 超大页码不向数据库传递超出 SQLite 整数范围的 OFFSET。
    items = [] if offset >= total else [serialize(obj) for obj in queryset[offset:offset + size]]
    return {"items": items, "page": page, "page_size": size, "total": total,
            "total_pages": (total + size - 1) // size}
