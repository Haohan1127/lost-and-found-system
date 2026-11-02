from rest_framework.response import Response


def ok(data=None, status=200):
    return Response({"code": "OK", "message": "操作成功", "data": data}, status=status)
