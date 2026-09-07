from __future__ import annotations

from domain.entities.aws_resource import AWSResource
from infrastructure.aws.collectors.base import resource


class IAMCollector:
    service_name = "iam"
    is_global = True

    def __init__(self, session) -> None:
        self.client = session.client("iam")

    def collect(self, account_id: str, region: str = "us-east-1") -> list[AWSResource]:
        resources: list[AWSResource] = []
        for page in self.client.get_paginator("list_users").paginate():
            for item in page.get("Users", []):
                resources.append(resource(
                    resource_id=item["UserId"], resource_type="iam:user", service=self.service_name,
                    account_id=account_id, region=None, raw_data=item, arn=item.get("Arn"), name=item.get("UserName"),
                    creation_time=item.get("CreateDate"),
                ))
        for page in self.client.get_paginator("list_roles").paginate():
            for item in page.get("Roles", []):
                resources.append(resource(
                    resource_id=item["RoleId"], resource_type="iam:role", service=self.service_name,
                    account_id=account_id, region=None, raw_data=item, arn=item.get("Arn"), name=item.get("RoleName"),
                    creation_time=item.get("CreateDate"),
                ))
        return resources
