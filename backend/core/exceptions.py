from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


class ServiceUnavailable(APIException):
    status_code = 503
    default_detail = "Service temporarily unavailable."
    default_code = "service_unavailable"


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    request = context.get("request")
    if response is not None and request is not None:
        rid = getattr(request, "request_id", None)
        if rid:
            response["X-Request-Id"] = rid
    return response
