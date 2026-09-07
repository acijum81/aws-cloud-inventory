from __future__ import annotations

import os

from infrastructure.aws.session_factory import AwsSessionFactory
from infrastructure.database.repository import ResourceRepository


def repository() -> ResourceRepository:
    url = os.getenv("DATABASE_URL", "sqlite:///./inventory.db")
    repo = ResourceRepository(url)
    repo.create_schema()
    return repo


def session_factory() -> AwsSessionFactory:
    return AwsSessionFactory()
