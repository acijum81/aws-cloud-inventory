from __future__ import annotations

from domain.entities.aws_resource import AWSResource
from infrastructure.aws.collectors.base import resource


class ECSCollector:
    service_name = "ecs"
    is_global = False

    def __init__(self, session) -> None:
        self.client = session.client("ecs")

    def collect(self, account_id: str, region: str) -> list[AWSResource]:
        resources: list[AWSResource] = []
        for page in self.client.get_paginator("list_clusters").paginate():
            arns = page.get("clusterArns", [])
            if not arns:
                continue
            details = self.client.describe_clusters(clusters=arns).get("clusters", [])
            resources.extend(resource(
                resource_id=item["clusterArn"], resource_type="ecs:cluster", service=self.service_name,
                account_id=account_id, region=region, raw_data=item, arn=item.get("clusterArn"),
                name=item.get("clusterName"), state=item.get("status"),
            ) for item in details)
        return resources
