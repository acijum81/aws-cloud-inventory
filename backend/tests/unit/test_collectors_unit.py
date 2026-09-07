from datetime import datetime, timezone

import boto3
from botocore.stub import Stubber

from infrastructure.aws.collectors import (
    EC2Collector, EBSCollector, ECSCollector, EKSCollector, ELBCollector,
    IAMCollector, LambdaCollector, RDSCollector, S3Collector, VPCCollector,
)


def session(service: str, region: str = "us-east-1"):
    base = boto3.Session(aws_access_key_id="test", aws_secret_access_key="test", region_name=region)
    return base, base.client(service, region_name=region)


def test_ec2_collector_maps_instance():
    s, c = session("ec2")
    st = Stubber(c); st.add_response("describe_instances", {"Reservations": [{"Instances": [{"InstanceId": "i-1", "LaunchTime": datetime.now(timezone.utc), "Placement": {"AvailabilityZone": "us-east-1a"}, "State": {"Name": "running"}, "Tags": [{"Key": "Name", "Value": "web"}]}]}]}, {}); st.activate()
    s.client = lambda *a, **k: c
    out = EC2Collector(s).collect("123456789012", "us-east-1")
    assert out[0].resource_name == "web" and out[0].state == "running"


def test_ebs_collector_maps_volume_snapshot_and_ami():
    s, c = session("ec2")
    st = Stubber(c)
    st.add_response("describe_volumes", {"Volumes": [{"VolumeId": "vol-1", "State": "in-use", "CreateTime": datetime.now(timezone.utc)}]}, {})
    st.add_response("describe_snapshots", {"Snapshots": [{"SnapshotId": "snap-1", "State": "completed", "StartTime": datetime.now(timezone.utc)}]}, {"OwnerIds": ["123456789012"]})
    st.add_response("describe_images", {"Images": [{"ImageId": "ami-1", "Name": "base", "State": "available", "CreationDate": "2026-01-01T00:00:00.000Z"}]}, {"Owners": ["123456789012"]})
    st.activate(); s.client = lambda *a, **k: c
    out = EBSCollector(s).collect("123456789012", "us-east-1")
    assert {r.resource_id for r in out} == {"vol-1", "snap-1", "ami-1"}


def test_vpc_collector_maps_resources():
    s, c = session("ec2")
    st = Stubber(c)
    responses = [
        ("describe_vpcs", "Vpcs", {"VpcId": "vpc-1", "Tags": [{"Key": "Name", "Value": "vpc"}]}),
        ("describe_subnets", "Subnets", {"SubnetId": "subnet-1"}),
        ("describe_route_tables", "RouteTables", {"RouteTableId": "rtb-1"}),
        ("describe_internet_gateways", "InternetGateways", {"InternetGatewayId": "igw-1"}),
        ("describe_nat_gateways", "NatGateways", {"NatGatewayId": "nat-1", "State": "available"}),
        ("describe_security_groups", "SecurityGroups", {"GroupId": "sg-1", "GroupName": "default"}),
        ("describe_network_acls", "NetworkAcls", {"NetworkAclId": "acl-1"}),
        ("describe_addresses", "Addresses", {"AllocationId": "eipalloc-1"}),
    ]
    for op, key, item in responses:
        st.add_response(op, {key: [item]}, {}) if op != "describe_addresses" else st.add_response(op, {key: [item]}, {})
    st.activate(); s.client = lambda *a, **k: c
    out = VPCCollector(s).collect("123456789012", "us-east-1")
    assert len(out) == 8


def test_s3_collector_maps_buckets():
    s, c = session("s3")
    st = Stubber(c); st.add_response("list_buckets", {"Buckets": [{"Name": "bucket-a", "CreationDate": datetime.now(timezone.utc)}]}, {}); st.activate(); s.client = lambda *a, **k: c
    out = S3Collector(s).collect("123456789012")
    assert out[0].arn == "arn:aws:s3:::bucket-a" and out[0].region is None


def test_rds_collector_maps_instance_and_tags():
    s, c = session("rds")
    arn = "arn:aws:rds:us-east-1:123456789012:db:db1"
    st = Stubber(c); st.add_response("describe_db_instances", {"DBInstances": [{"DBInstanceIdentifier": "db1", "DBInstanceArn": arn, "DBInstanceStatus": "available"}]}, {}); st.add_response("list_tags_for_resource", {"TagList": [{"Key": "Owner", "Value": "db-team"}]}, {"ResourceName": arn}); st.activate(); s.client = lambda *a, **k: c
    out = RDSCollector(s).collect("123456789012", "us-east-1")
    assert out[0].owner == "db-team"


def test_lambda_collector_maps_function():
    s, c = session("lambda")
    st = Stubber(c); st.add_response("list_functions", {"Functions": [{"FunctionName": "fn", "FunctionArn": "arn:aws:lambda:us-east-1:123:function:fn", "State": "Active"}]}, {}); st.activate(); s.client = lambda *a, **k: c
    out = LambdaCollector(s).collect("123456789012", "us-east-1")
    assert out[0].resource_name == "fn"


def test_iam_collector_maps_users_and_roles():
    s, c = session("iam")
    st = Stubber(c); st.add_response("list_users", {"Users": [{"UserId": "AIDABCDEFGHIJKLMN", "UserName": "alice", "Arn": "arn:aws:iam::123456789012:user/alice", "Path": "/", "CreateDate": datetime.now(timezone.utc)}]}, {}); st.add_response("list_roles", {"Roles": [{"RoleId": "AROABCDEFGHIJKLMN", "RoleName": "role", "Arn": "arn:aws:iam::123456789012:role/role", "Path": "/", "CreateDate": datetime.now(timezone.utc)}]}, {}); st.activate(); s.client = lambda *a, **k: c
    out = IAMCollector(s).collect("123456789012")
    assert [r.resource_name for r in out] == ["alice", "role"]


def test_elb_collector_maps_load_balancer():
    s, c = session("elbv2")
    st = Stubber(c); st.add_response("describe_load_balancers", {"LoadBalancers": [{"LoadBalancerArn": "arn:aws:elasticloadbalancing:us-east-1:123:loadbalancer/app/x/1", "LoadBalancerName": "x", "State": {"Code": "active"}}]}, {}); st.activate(); s.client = lambda *a, **k: c
    out = ELBCollector(s).collect("123456789012", "us-east-1")
    assert out[0].resource_name == "x"


def test_ecs_collector_maps_cluster():
    s, c = session("ecs")
    arn = "arn:aws:ecs:us-east-1:123:cluster/default"
    st = Stubber(c); st.add_response("list_clusters", {"clusterArns": [arn]}, {}); st.add_response("describe_clusters", {"clusters": [{"clusterArn": arn, "clusterName": "default", "status": "ACTIVE"}]}, {"clusters": [arn]}); st.activate(); s.client = lambda *a, **k: c
    out = ECSCollector(s).collect("123456789012", "us-east-1")
    assert out[0].resource_name == "default"


def test_eks_collector_maps_cluster():
    s, c = session("eks")
    arn = "arn:aws:eks:us-east-1:123:cluster/demo"
    st = Stubber(c); st.add_response("list_clusters", {"clusters": ["demo"]}, {}); st.add_response("describe_cluster", {"cluster": {"name": "demo", "arn": arn, "status": "ACTIVE"}}, {"name": "demo"}); st.activate(); s.client = lambda *a, **k: c
    out = EKSCollector(s).collect("123456789012", "us-east-1")
    assert out[0].resource_name == "demo"
