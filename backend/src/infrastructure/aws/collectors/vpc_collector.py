from __future__ import annotations

from domain.entities.aws_resource import AWSResource
from infrastructure.aws.collectors.base import resource, tags_from_aws


class VPCCollector:
    service_name = "vpc"
    is_global = False
    operations = (
        ("describe_vpcs", "Vpcs", "vpc:network"),
        ("describe_subnets", "Subnets", "vpc:subnet"),
        ("describe_route_tables", "RouteTables", "vpc:route-table"),
        ("describe_internet_gateways", "InternetGateways", "vpc:internet-gateway"),
        ("describe_nat_gateways", "NatGateways", "vpc:nat-gateway"),
        ("describe_security_groups", "SecurityGroups", "vpc:security-group"),
        ("describe_network_acls", "NetworkAcls", "vpc:network-acl"),
        ("describe_addresses", "Addresses", "vpc:elastic-ip"),
    )

    def __init__(self, session) -> None:
        self.client = session.client("ec2")

    def collect(self, account_id: str, region: str) -> list[AWSResource]:
        resources: list[AWSResource] = []
        id_keys = ("VpcId", "SubnetId", "RouteTableId", "InternetGatewayId", "NatGatewayId", "GroupId", "NetworkAclId", "AllocationId")
        for operation, result_key, resource_type in self.operations:
            if operation == "describe_addresses":
                pages = [{result_key: self.client.describe_addresses().get(result_key, [])}]
            else:
                pages = self.client.get_paginator(operation).paginate()
            for page in pages:
                for item in page.get(result_key, []):
                    rid = next((item[k] for k in id_keys if k in item), None)
                    if not rid:
                        continue
                    tags = tags_from_aws(item.get("Tags"))
                    resources.append(resource(
                        resource_id=rid, resource_type=resource_type, service=self.service_name,
                        account_id=account_id, region=region, raw_data=item, tags=tags,
                        state=item.get("State") or item.get("Domain"), name=tags.get("Name"),
                        availability_zone=item.get("AvailabilityZone"),
                    ))
        return resources
