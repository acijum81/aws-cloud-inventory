from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError, EndpointConnectionError


class AwsErrorCategory(StrEnum):
    ACCESS_DENIED = "AccessDenied"
    THROTTLING = "Throttling"
    UNSUPPORTED_REGION = "UnsupportedRegion"
    ENDPOINT_CONNECTION = "EndpointConnectionError"
    OPT_IN_REQUIRED = "OptInRequired"
    VALIDATION = "ValidationError"
    UNKNOWN = "UnknownError"


@dataclass(frozen=True, slots=True)
class AwsOperationError:
    account_id: str
    region: str | None
    service: str
    operation: str
    category: AwsErrorCategory
    message: str
    occurred_at: datetime
    attempt: int = 1
    correlation_id: str | None = None


def classify_aws_error(exc: BaseException) -> AwsErrorCategory:
    if isinstance(exc, EndpointConnectionError):
        return AwsErrorCategory.ENDPOINT_CONNECTION
    if isinstance(exc, ClientError):
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if code in {"AccessDenied", "AccessDeniedException", "UnauthorizedOperation"}:
            return AwsErrorCategory.ACCESS_DENIED
        if code in {
            "Throttling",
            "ThrottlingException",
            "TooManyRequestsException",
            "RequestLimitExceeded",
        }:
            return AwsErrorCategory.THROTTLING
        if code in {"OptInRequired", "OptInRequiredException"}:
            return AwsErrorCategory.OPT_IN_REQUIRED
        if code in {"InvalidRegion", "InvalidEndpoint"}:
            return AwsErrorCategory.UNSUPPORTED_REGION
        if code in {"ValidationError", "InvalidParameterValue", "InvalidParameterException"}:
            return AwsErrorCategory.VALIDATION
        return AwsErrorCategory.UNKNOWN
    if isinstance(exc, BotoCoreError):
        return AwsErrorCategory.UNKNOWN
    return AwsErrorCategory.UNKNOWN


def sanitize_error_message(exc: BaseException) -> str:
    if isinstance(exc, ClientError):
        return str(exc.response.get("Error", {}).get("Message", str(exc)))[:2000]
    return str(exc)[:2000]


def build_operation_error(
    exc: BaseException,
    *,
    account_id: str,
    region: str | None,
    service: str,
    operation: str,
    attempt: int = 1,
    correlation_id: str | None = None,
) -> AwsOperationError:
    return AwsOperationError(
        account_id=account_id,
        region=region,
        service=service,
        operation=operation,
        category=classify_aws_error(exc),
        message=sanitize_error_message(exc),
        occurred_at=datetime.now(timezone.utc),
        attempt=attempt,
        correlation_id=correlation_id,
    )
