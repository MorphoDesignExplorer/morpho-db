from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException

def exception_with_code_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    if isinstance(exc, APIException):
        response.data["code"] = exc.get_codes()

    return response
