import abc
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, cast

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.signals import got_request_exception
from django.db.models import ProtectedError
from django.http import Http404
from exceptions_hog.exceptions import ProtectedObjectException
from exceptions_hog.handler import ErrorTypes, _get_error_type, _get_http_status
from exceptions_hog.settings import api_settings
from rest_framework import exceptions
from rest_framework.exceptions import ErrorDetail
from rest_framework.response import Response
from rest_framework.settings import api_settings as drf_api_settings
from rest_framework.views import set_rollback

DEFAULT_ERROR_DETAIL = ErrorDetail("A server error occurred.", code="error")


class ExceptionKeyContentType(Enum):
    single = "single"
    flat = "flat"
    nested = "nested"
    many_flat = "many_flat"
    many_nested = "many_nested"
    index = "index"


@dataclass
class ExceptionKey:
    value: str | int
    details_type: ExceptionKeyContentType


class NormalizedException:
    def __init__(self, keys: list[ExceptionKey], error_details: list[ErrorDetail]):
        self.keys = keys
        self.error_details = error_details

    @property
    def attr(self) -> str | None:
        """
        Returns the offending attribute name. Handles special case
            of __all__ (used for instance in UniqueTogetherValidator) to return `None`.
        """

        def override_or_return(key: str | None) -> str | None:
            """
            Returns overridden code if it needs to change or provided code.
            """
            if key in ["__all__", drf_api_settings.NON_FIELD_ERRORS_KEY]:
                return None

            return key if key else None

        # Do not append `non_field_errors` to the attribute name. For example:
        # if the error of the form {"key": {"non_field_errors": "some error"}} occurs,
        # it should return: {"key": "some error"} and not {"key__non_field_errors": "some error"}
        key_values_for_attr = [value for value in self.key_values if value != "non_field_errors"]
        return override_or_return(
            api_settings.NESTED_KEY_SEPARATOR.join(key_values_for_attr)
        )

    @property
    def code(self) -> str | None:
        """Always returns the first error code"""
        code = self.error_details[0].code
        if code == "invalid":
            # Special handling for validation errors. Use `invalid_input` instead
            # of `invalid` to provide more clarity.
            return "invalid_input"
        return self.error_details[0].code

    @property
    def detail(self) -> str:
        """Always returns the first error detail"""
        return str(self.error_details[0])

    @property
    def key_values(self) -> list[str]:
        # We do str(key.value) to get the actual error value on the ErrorDetail instance
        return [str(key.value) for key in self.keys]


class ExceptionParser:
    @abc.abstractmethod
    def match(self, exception: BaseException) -> bool:
        pass

    @abc.abstractmethod
    def parse(self, exception: Any) -> dict[str, Any]:
        pass


class ValidationErrorParser(ExceptionParser):
    def match(self, exception: BaseException) -> bool:
        return isinstance(exception, exceptions.ValidationError)

    def parse(self, exception: exceptions.ValidationError) -> dict[str, Any]:
        detail = exception.detail
        return {"": detail} if isinstance(detail, list) else detail


class APIExceptionParser(ExceptionParser):
    def match(self, exception: BaseException) -> bool:
        return hasattr(exception, "detail") and isinstance(exception.detail, ErrorDetail)

    def parse(self, exception: exceptions.APIException) -> dict:
        return {"": exception.detail}


class ProtectedObjectExceptionParser(ExceptionParser):
    def match(self, exception: BaseException) -> bool:
        return isinstance(exception, ProtectedObjectException)

    def parse(self, exception: ProtectedObjectException) -> dict[str, ErrorDetail | list[ErrorDetail]]:
        return {"": ErrorDetail(string=exception.detail, code="protected_error")}


class TokenErrorParser(ExceptionParser):
    def match(self, exception: BaseException) -> bool:
        return hasattr(exception, "detail") and isinstance(exception.detail, dict)

    def parse(self, exception: exceptions.APIException) -> dict[str, Any]:
        exception_detail = cast(dict, exception.detail)
        return {"": exception_detail["detail"]}


EXCEPTION_PARSERS = (
    ValidationErrorParser(),
    APIExceptionParser(),
    ProtectedObjectExceptionParser(),
    TokenErrorParser(),
)


def exception_handler(
    exc: BaseException, context: dict | None = None
) -> Response | None:
    # Special handling for Django base exceptions first
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()
    elif isinstance(exc, ProtectedError):
        exc = ProtectedObjectException(
            "",
            protected_objects=exc.protected_objects,
        )

    if (
        getattr(settings, "DEBUG", False)
        and not api_settings.ENABLE_IN_DEBUG
        and not isinstance(exc, exceptions.APIException)
    ):
        # By default don't handle non-DRF errors in DEBUG mode, i.e. Django will treat
        # unhandled exceptions regularly (very evident yellow error page)

        # NOTE: to make sure we get exception tracebacks in test responses, we need
        # to make sure this signal is called. The django test client uses this to
        # pull out the exception traceback.
        #
        # See https://github.com/django/django/blob/3.2.9/django/test/client.py#L712
        got_request_exception.send(
            sender=None,
            request=context["request"] if context and "request" in context else None,
        )
        return None

    api_settings.EXCEPTION_REPORTING(exc, context)
    set_rollback()

    error_details = _get_error_details(exc)
    normalized_exceptions = _get_normalized_exceptions(error_details)

    if api_settings.SUPPORT_MULTIPLE_EXCEPTIONS and len(normalized_exceptions) > 1:
        response = dict(
            type=ErrorTypes.multiple_exceptions.value,
            code=ErrorTypes.multiple_exceptions.value,
            detail="Multiple exceptions occurred. Please check list for details.",
            attr=None,
            list=[
                _assemble_error(exc, error, False) for error in normalized_exceptions
            ],
            **_get_extra(exc)
        )
    else:
        response = _assemble_error(exc, normalized_exceptions[0])

    return Response(response, status=_get_http_status(exc))


def _get_error_details(exc: Any) -> dict | None:
    for parser in EXCEPTION_PARSERS:
        if parser.match(exc):
            return parser.parse(exc)
    return None


def _get_normalized_exceptions(
    error_details: dict | None, parent_keys: list[ExceptionKey] | None = None,
) -> list[NormalizedException]:
    """
    Returns a normalized one-level list of exception attributes and codes. Used to
    standardize multiple exceptions and complex nested exceptions.

    Example:

    Input => {
        "update": [
             ErrorDetail(
                value="This field is required.",
                code="required",
            ),
        ]
        "form": {
             "email": [
                ErrorDetail(
                    value="This field is required.",
                    code="required",
                ),
            ],
            "password": [
                ErrorDetail(
                    value="This password is unsafe.",
                    code="unsafe_password",
                )
            ],
        }
    }

    Output => [
         NormalizedException(
             "keys": [
                ExceptionKey(value="update", type="flat")
             ],
             "error_details": [
                ErrorDetail(
                    value="This field is required.",
                    code="required",
                ),
            ]
         ),
         NormalizedException(
             "keys": [
                ExceptionKey(value="form", type="nested")
                ExceptionKey(value="email", type="flat")
             ],
             "error_details": [
                ErrorDetail(
                    value="This field is required.",
                    code="required",
                ),
            ]
         ),
         NormalizedException(
             "keys": [
                ExceptionKey(value="form", type="nested")
                ExceptionKey(value="password", type="flat")
             ],
             "error_details": [
                ErrorDetail(
                    value="This password is unsafe.",
                    code="unsafe_password",
                )
            ]
         ),
    ]
    """

    if error_details is None:
        return [NormalizedException(keys=[], error_details=[DEFAULT_ERROR_DETAIL])]

    items: list[NormalizedException] = []

    def get_details_type(
        _details: list | dict | ErrorDetail
    ) -> ExceptionKeyContentType:
        if isinstance(_details, list):
            if isinstance(_details[0], list):
                # Output Example: [[ErrorDetail(value="Error", code="error")]]
                return ExceptionKeyContentType.many_flat
            elif isinstance(_details[0], dict):
                # Output Example: {"error": ErrorDetail(value="Error", code="error"})
                return ExceptionKeyContentType.many_nested
            else:
                # Output Example: [ErrorDetail(value="Error", code="error")]
                return ExceptionKeyContentType.flat
        elif isinstance(_details, dict):
            # Output Example: [{"error": [ErrorDetail(value="Error", code="error")]}]
            return ExceptionKeyContentType.nested
        # Output Example: ErrorDetail(value="Error", code="error")
        return ExceptionKeyContentType.single

    def normalize_single_details(
        _keys: list[ExceptionKey], _details: ErrorDetail
    ) -> list[NormalizedException]:
        return [NormalizedException(keys=_keys, error_details=[_details])]

    def normalize_flat_details(
        _keys: list[ExceptionKey], _details: list[ErrorDetail]
    ) -> list[NormalizedException]:
        return [NormalizedException(keys=_keys, error_details=_details)]

    def normalize_nested_details(
        _keys: list[ExceptionKey], _details: dict
    ) -> list[NormalizedException]:
        return _get_normalized_exceptions(
            error_details=_details.copy(), parent_keys=_keys
        )

    def normalize_many_flat_details(
        _keys: list[ExceptionKey], _details: list[list[ErrorDetail]]
    ) -> list[NormalizedException]:
        return [
            NormalizedException(
                keys=[
                    *_keys,
                    ExceptionKey(
                        value=index, details_type=ExceptionKeyContentType.index
                    ),
                ],
                error_details=error_details,
            )
            for index, error_details in enumerate(_details)
        ]

    def normalize_many_nested_details(
        _keys: list[ExceptionKey], _details: list[dict]
    ) -> list[NormalizedException]:
        result: list[NormalizedException] = []
        for index, nested_error_details in enumerate(_details):
            result.extend(
                _get_normalized_exceptions(
                    error_details=nested_error_details.copy(),
                    parent_keys=[
                        *_keys,
                        ExceptionKey(
                            value=index,
                            details_type=ExceptionKeyContentType.index,
                        ),
                    ],
                )
            )
        return result

    switcher = {
        ExceptionKeyContentType.single: normalize_single_details,
        ExceptionKeyContentType.flat: normalize_flat_details,
        ExceptionKeyContentType.nested: normalize_nested_details,
        ExceptionKeyContentType.many_flat: normalize_many_flat_details,
        ExceptionKeyContentType.many_nested: normalize_many_nested_details,
    }

    for key, details in error_details.items():
        parsed_key = ExceptionKey(value=key, details_type=get_details_type(details))
        parsed_keys: list[ExceptionKey] = (parent_keys or []) + [parsed_key]
        # Due to this issue, we can't fix it for now:
        # https://github.com/python/mypy/issues/10740
        normalizer: Callable[[list[ExceptionKey], Any], Any] = switcher[parsed_key.details_type]  # type: ignore
        items.extend(normalizer(parsed_keys, details))

    return items


def _assemble_error(
    exc: BaseException, normalized_exc: NormalizedException, with_extra=True
) -> dict:
    return dict(
        type=_get_error_type(exc),
        code=normalized_exc.code,
        detail=normalized_exc.detail,
        attr=normalized_exc.attr,
        **(_get_extra(exc) if with_extra else {})
    )


def _get_extra(exc: BaseException) -> dict:
    return {"extra": exc.extra} if hasattr(exc, "extra") else {}
