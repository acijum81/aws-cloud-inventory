from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable
from uuid import uuid4

from application.ports.aws_inventory_provider import ResourceCollector
from domain.entities.aws_resource import AWSResource
from infrastructure.aws.errors import AwsOperationError, build_operation_error
from infrastructure.aws.session_factory import AwsSessionFactory


@dataclass(slots=True)
class InventoryResult:
    resources: list[AWSResource] = field(default_factory=list)
    errors: list[AwsOperationError] = field(default_factory=list)


class InventoryRunner:
    """Runs collectors independently so one AWS failure does not abort the run."""

    def __init__(self, session_factory: AwsSessionFactory, collectors: Iterable[type[ResourceCollector]]) -> None:
        self._session_factory = session_factory
        self._collector_types = tuple(collectors)

    def collect_account_region(self, account_id: str, region: str) -> InventoryResult:
        result = InventoryResult()
        correlation_id = str(uuid4())
        for collector_type in self._collector_types:
            service = getattr(collector_type, "service_name", "unknown")
            try:
                session = self._session_factory.create(region)
                collector = collector_type(session)
                result.resources.extend(collector.collect(account_id, region))
            except Exception as exc:
                result.errors.append(
                    build_operation_error(
                        exc, account_id=account_id, region=region, service=service,
                        operation="collect", correlation_id=correlation_id,
                    )
                )
        return result
