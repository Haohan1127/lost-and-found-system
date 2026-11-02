import logging
from django.http import JsonResponse
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.views import exception_handler as drf_handler
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class BusinessError(APIException):
    def __init__(self, code, message, status=409):
        self.status_code = status
        self.business_code = code
        super().__init__(message)


def missing():
    raise BusinessError("NOT_FOUND", "资源不存在", 404)


def forbidden():
    raise BusinessError("FORBIDDEN", "无权执行此操作", 403)


def conflict(message="当前状态不允许此操作"):
    raise BusinessError("STATE_CONFLICT", message)


def exception_handler(exc, context):
    response = drf_handler(exc, context)
    if response is None:
        logger.error("请求处理失败", exc_info=(type(exc), exc, exc.__traceback__))
        return Response({"code": "INTERNAL_ERROR", "message": "服务暂时不可用", "data": None, "errors": {}}, status=500)
    codes = {400: "VALIDATION_ERROR", 401: "UNAUTHENTICATED", 403: "FORBIDDEN",
             404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED", 415: "UNSUPPORTED_MEDIA_TYPE", 429: "RATE_LIMITED"}
    errors = {}
    if isinstance(exc, ValidationError):
        errors = response.data if isinstance(response.data, dict) else {"non_field_errors": response.data}
    response.data = {"code": getattr(exc, "business_code", codes.get(response.status_code, "INTERNAL_ERROR")),
                     "message": "请检查填写内容" if errors else str(getattr(exc, "detail", "请求失败")),
                     "data": None, "errors": errors}
    return response


def not_found(request, exception):
    return JsonResponse({"code": "NOT_FOUND", "message": "资源不存在", "data": None, "errors": {}}, status=404)


def server_error(request):
    return JsonResponse({"code": "INTERNAL_ERROR", "message": "服务暂时不可用", "data": None, "errors": {}}, status=500)
