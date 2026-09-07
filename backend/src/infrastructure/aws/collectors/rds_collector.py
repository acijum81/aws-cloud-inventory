from __future__ import annotations

from domain.entities.aws_resource import AWSResource
from infrastructure.aws.collectors.base import resource, tags_from_aws


class RDSCollector:
    service_name = "rds"
    is_global = False

    def __init__(self, session) -> None:
        self.client = session.client("rds")

    def collect(self, account_id: str, region: str) -> list[AWSResource]:
        resources: list[AWSResource] = []
        for page in self.client.get_paginator("describe_db_instances").paginate():
            for item in page.get("DBInstances", []):
                arn = item.get("DBInstanceArn")
                tags = tags_from_aws(self.client.list_tags_for_resource(ResourceName=arn).get("TagList")) if arn else {}
                resources.append(resource(
                    resource_id=item["DBInstanceIdentifier"], resource_type="rds:db-instance",
                    service=self.service_name, account_id=account_id, region=region, raw_data=item,
                    tags=tags, arn=arn, name=item.get("DBInstanceIdentifier"),
                    state=item.get("DBInstanceStatus"), creation_time=item.get("InstanceCreateTime"),
                ))
        return resources
