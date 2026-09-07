from __future__ import annotations

from domain.entities.aws_resource import AWSResource
from infrastructure.aws.collectors.base import resource


class LambdaCollector:
    service_name = "lambda"
    is_global = False

    def __init__(self, session) -> None:
        self.client = session.client("lambda")

    def collect(self, account_id: str, region: str) -> list[AWSResource]:
        resources: list[AWSResource] = []
        for page in self.client.get_paginator("list_functions").paginate():
            for item in page.get("Functions", []):
                resources.append(resource(
                    resource_id=item["FunctionArn"], resource_type="lambda:function", service=self.service_name,
                    account_id=account_id, region=region, raw_data=item, arn=item.get("FunctionArn"),
                    name=item.get("FunctionName"), state=item.get("State"), creation_time=item.get("LastModified") and None,
                ))
        return resources
