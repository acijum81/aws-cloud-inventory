from __future__ import annotations

from domain.entities.aws_resource import AWSResource
from infrastructure.aws.collectors.base import resource, tags_from_aws


class EC2Collector:
    service_name = "ec2"
    is_global = False

    def __init__(self, session) -> None:
        self.client = session.client("ec2")

    def collect(self, account_id: str, region: str) -> list[AWSResource]:
        resources: list[AWSResource] = []
        for page in self.client.get_paginator("describe_instances").paginate():
            for reservation in page.get("Reservations", []):
                for item in reservation.get("Instances", []):
                    tags = tags_from_aws(item.get("Tags"))
                    resources.append(resource(
                        resource_id=item["InstanceId"], resource_type="ec2:instance",
                        service=self.service_name, account_id=account_id, region=region,
                        raw_data=item, tags=tags, name=tags.get("Name"),
                        state=(item.get("State") or {}).get("Name"),
                        availability_zone=(item.get("Placement") or {}).get("AvailabilityZone"),
                        creation_time=item.get("LaunchTime"),
                    ))
        return resources
