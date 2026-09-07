from unittest.mock import MagicMock

import boto3

from infrastructure.aws.session_factory import AwsSessionFactory, RetrySettings


def test_create_preserves_base_botocore_session() -> None:
    base = boto3.Session(profile_name=None, region_name="us-west-2")
    factory = AwsSessionFactory(base)

    child = factory.create("eu-west-1")

    assert child.region_name == "eu-west-1"
    assert child._session is base._session


def test_retry_config_uses_standard_mode_and_bounded_attempts() -> None:
    factory = AwsSessionFactory(retry_settings=RetrySettings(max_attempts=4))
    config = factory.retry_config

    assert config.retries == {"mode": "standard", "max_attempts": 4}


def test_assume_role_sanitizes_session_name_and_external_id() -> None:
    base = boto3.Session(region_name="us-east-1")
    factory = AwsSessionFactory(base)
    sts = MagicMock()
    sts.assume_role.return_value = {
        "Credentials": {
            "AccessKeyId": "ASIAEXAMPLE",
            "SecretAccessKey": "secret",
            "SessionToken": "token",
        }
    }
    factory.client = MagicMock(return_value=sts)  # type: ignore[method-assign]

    session = factory.assume_role(
        "arn:aws:iam::123456789012:role/AWSInventoryReadOnlyRole",
        "inventory/run:bad name/very-long-name",
        external_id="external",
        region="us-west-2",
    )

    sts.assume_role.assert_called_once()
    call = sts.assume_role.call_args.kwargs
    assert call["RoleSessionName"].isalnum() or "-" in call["RoleSessionName"]
    assert call["ExternalId"] == "external"
    assert session.region_name == "us-west-2"
