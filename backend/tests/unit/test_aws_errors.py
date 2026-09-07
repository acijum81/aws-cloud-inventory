from botocore.exceptions import ClientError, EndpointConnectionError

from infrastructure.aws.errors import AwsErrorCategory, classify_aws_error


def client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": "safe"}}, "DescribeInstances")


def test_error_classifier() -> None:
    assert classify_aws_error(client_error("AccessDeniedException")) == AwsErrorCategory.ACCESS_DENIED
    assert classify_aws_error(client_error("ThrottlingException")) == AwsErrorCategory.THROTTLING
    assert classify_aws_error(client_error("OptInRequired")) == AwsErrorCategory.OPT_IN_REQUIRED
    assert classify_aws_error(client_error("ValidationError")) == AwsErrorCategory.VALIDATION


def test_endpoint_error_classifier() -> None:
    error = EndpointConnectionError(endpoint_url="https://example.test")
    assert classify_aws_error(error) == AwsErrorCategory.ENDPOINT_CONNECTION
