from __future__ import annotations

from domain.entities.aws_resource import AWSResource
from infrastructure.aws.collectors.base import resource


class EKSCollector:
    service_name = "eks"
    is_global = False

    def __init__(self, session) -> None:
        self.client = session.client("eks")

    def collect(self, account_id: str, region: str) -> list[AWSResource]:
        resources: list[AWSResource] = []
        for page in self.client.get_paginator("list_clusters").paginate():
            for name in page.get("clusters", []):
                item = self.client.describe_cluster(name=name)["cluster"]
                resources.append(resource(
                    resource_id=item["arn"], resource_type="eks:cluster", service=self.service_name,
                    account_id=account_id, region=region, raw_data=item, arn=item.get("arn"),
                    name=item.get("name"), state=item.get("status"), creation_time=item.get("createdAt"),
                ))
        return resources
