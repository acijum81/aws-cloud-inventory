from __future__ import annotations

from domain.entities.aws_resource import AWSResource
from infrastructure.aws.collectors.base import resource, tags_from_aws


class EBSCollector:
    service_name = "ebs"
    is_global = False

    def __init__(self, session) -> None:
        self.client = session.client("ec2")

    def collect(self, account_id: str, region: str) -> list[AWSResource]:
        resources: list[AWSResource] = []
        for page in self.client.get_paginator("describe_volumes").paginate():
            for item in page.get("Volumes", []):
                tags = tags_from_aws(item.get("Tags"))
                resources.append(resource(
                    resource_id=item["VolumeId"], resource_type="ebs:volume",
                    service=self.service_name, account_id=account_id, region=region,
                    raw_data=item, tags=tags, state=item.get("State"),
                    availability_zone=item.get("AvailabilityZone"), creation_time=item.get("CreateTime"),
                ))
        for page in self.client.get_paginator("describe_snapshots").paginate(OwnerIds=[account_id]):
            for item in page.get("Snapshots", []):
                tags = tags_from_aws(item.get("Tags"))
                resources.append(resource(
                    resource_id=item["SnapshotId"], resource_type="ebs:snapshot",
                    service=self.service_name, account_id=account_id, region=region,
                    raw_data=item, tags=tags, state=item.get("State"), creation_time=item.get("StartTime"),
                ))
        for page in self.client.get_paginator("describe_images").paginate(Owners=[account_id]):
            for item in page.get("Images", []):
                tags = tags_from_aws(item.get("Tags"))
                resources.append(resource(
                    resource_id=item["ImageId"], resource_type="ec2:ami", service=self.service_name,
                    account_id=account_id, region=region, raw_data=item, tags=tags,
                    name=item.get("Name"), state=item.get("State"), creation_time=item.get("CreationDate"),
                ))
        return resources
