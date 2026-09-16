from __future__ import annotations

import os

import boto3

from infrastructure.aws.session_factory import AwsSessionFactory
from infrastructure.database.repository import ResourceRepository


def repository() -> ResourceRepository:
    url = os.getenv("DATABASE_URL", "sqlite:///./inventory.db")
    repo = ResourceRepository(url)
    repo.create_schema()
    return repo


def session_factory() -> AwsSessionFactory:
    return AwsSessionFactory()


def session_factory_from_credentials(
    access_key_id: str,
    secret_access_key: str,
    session_token: str | None,
    region: str | None = None,
) -> AwsSessionFactory:
    session = boto3.Session(
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        aws_session_token=session_token or None,
        region_name=region or os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
    )
    return AwsSessionFactory(session)
