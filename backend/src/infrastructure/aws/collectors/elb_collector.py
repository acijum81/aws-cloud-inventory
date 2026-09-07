from __future__ import annotations

from domain.entities.aws_resource import AWSResource
from infrastructure.aws.collectors.base import resource


class ELBCollector:
    service_name = "elbv2"
    is_global = False

    def __init__(self, session) -> None:
        self.client = session.client("elbv2")

    def collect(self, account_id: str, region: str) -> list[AWSResource]:
        resources: list[AWSResource] = []
        for page in self.client.get_paginator("describe_load_balancers").paginate():
            for item in page.get("LoadBalancers", []):
                resources.append(resource(
                    resource_id=item["LoadBalancerArn"], resource_type="elbv2:load-balancer",
                    service=self.service_name, account_id=account_id, region=region, raw_data=item,
                    arn=item.get("LoadBalancerArn"), name=item.get("LoadBalancerName"), state=item.get("State", {}).get("Code"),
                ))
        return resources
