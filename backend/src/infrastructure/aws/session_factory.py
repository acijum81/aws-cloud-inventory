from __future__ import annotations

import re
from dataclasses import dataclass

import boto3
from boto3.session import Session
from botocore.config import Config


_SESSION_NAME_RE = re.compile(r"[^A-Za-z0-9+=,.@_-]")


@dataclass(frozen=True, slots=True)
class RetrySettings:
    mode: str = "standard"
    max_attempts: int = 6

    def to_config(self) -> Config:
        return Config(
            retries={"mode": self.mode, "max_attempts": self.max_attempts},
        )


class AwsSessionFactory:
    """Creates AWS sessions while preserving the SDK credential provider chain.

    Sessions created from AssumeRole use temporary credentials returned by STS.
    No long-lived credentials are persisted by this class.
    """

    def __init__(
        self,
        base_session: Session | None = None,
        retry_settings: RetrySettings | None = None,
    ) -> None:
        self._base_session = base_session or boto3.Session()
        self._retry_settings = retry_settings or RetrySettings()

    @property
    def retry_config(self) -> Config:
        return self._retry_settings.to_config()

    def create(self, region: str | None = None) -> Session:
        return Session(
            region_name=region or self._base_session.region_name,
            botocore_session=self._base_session._session,
        )

    def client(self, service_name: str, region: str | None = None):
        session = self.create(region)
        return session.client(
            service_name,
            region_name=region or session.region_name,
            config=self.retry_config,
        )

    def assume_role(
        self,
        role_arn: str,
        session_name: str,
        region: str | None = None,
        external_id: str | None = None,
    ) -> Session:
        safe_session_name = self._normalize_session_name(session_name)
        sts = self.client("sts", region)
        params: dict[str, str] = {
            "RoleArn": role_arn,
            "RoleSessionName": safe_session_name,
        }
        if external_id:
            params["ExternalId"] = external_id
        response = sts.assume_role(**params)
        credentials = response["Credentials"]
        return Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
            region_name=region or self._base_session.region_name,
        )

    @staticmethod
    def _normalize_session_name(value: str) -> str:
        normalized = _SESSION_NAME_RE.sub("-", value).strip("-")[:64]
        return normalized or "aws-inventory"
