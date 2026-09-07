from __future__ import annotations

from domain.entities.aws_resource import AWSResource
from infrastructure.aws.collectors.base import resource


class S3Collector:
    service_name = "s3"
    is_global = True

    def __init__(self, session) -> None:
        self.client = session.client("s3")

    def collect(self, account_id: str, region: str = "us-east-1") -> list[AWSResource]:
        response = self.client.list_buckets()
        return [
            resource(
                resource_id=bucket["Name"], resource_type="s3:bucket", service=self.service_name,
                account_id=account_id, region=None, raw_data=bucket, creation_time=bucket.get("CreationDate"),
                arn=f"arn:aws:s3:::{bucket['Name']}", name=bucket["Name"],
            )
            for bucket in response.get("Buckets", [])
        ]
