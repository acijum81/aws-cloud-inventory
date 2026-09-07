from typing import Protocol

from domain.entities.aws_resource import AWSResource


class ResourceCollector(Protocol):
    service_name: str
    is_global: bool

    def collect(self, account_id: str, region: str) -> list[AWSResource]: ...
