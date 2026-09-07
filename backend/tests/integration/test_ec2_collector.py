from datetime import datetime, timezone

import boto3
from botocore.stub import Stubber

from infrastructure.aws.collectors.ec2_collector import EC2Collector


def test_collect_ec2_instance() -> None:
    session = boto3.Session(
        aws_access_key_id="test",
        aws_secret_access_key="test",
        aws_session_token="test",
        region_name="us-east-1",
    )
    client = session.client("ec2", region_name="us-east-1")
    response = {
        "Reservations": [{"Instances": [{
            "InstanceId": "i-1234567890abcdef0",
            "ImageId": "ami-12345678",
            "InstanceType": "t3.micro",
            "LaunchTime": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "Placement": {"AvailabilityZone": "us-east-1a"},
            "State": {"Code": 16, "Name": "running"},
            "Tags": [{"Key": "Name", "Value": "web-1"}, {"Key": "Owner", "Value": "platform"}],
        }]}]
    }
    stubber = Stubber(client)
    stubber.add_response("describe_instances", response, {})
    stubber.activate()
    session.client = lambda *args, **kwargs: client  # type: ignore[method-assign]

    resources = EC2Collector(session).collect("123456789012", "us-east-1")

    assert len(resources) == 1
    assert resources[0].resource_name == "web-1"
    assert resources[0].owner == "platform"
    stubber.assert_no_pending_responses()
