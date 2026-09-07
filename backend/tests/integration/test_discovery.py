from datetime import datetime, timezone

import boto3
from botocore.stub import Stubber

from infrastructure.aws.discovery.organization import OrganizationDiscovery
from infrastructure.aws.discovery.regions import RegionDiscovery


def test_organization_list_accounts_is_paginated() -> None:
    session = boto3.Session(aws_access_key_id="test", aws_secret_access_key="test", region_name="us-east-1")
    client = session.client("organizations", region_name="us-east-1")
    stubber = Stubber(client)
    stubber.add_response("list_accounts", {
        "Accounts": [{
            "Id": "111111111111",
            "Name": "prod",
            "Status": "ACTIVE",
            "JoinedMethod": "CREATED",
            "JoinedTimestamp": datetime(2026, 1, 1, tzinfo=timezone.utc),
        }],
        "NextToken": "token",
    }, {})
    stubber.add_response("list_accounts", {
        "Accounts": [{
            "Id": "222222222222",
            "Name": "dev",
            "Status": "ACTIVE",
        }],
    }, {"NextToken": "token"})
    stubber.activate()
    session.client = lambda *args, **kwargs: client  # type: ignore[method-assign]

    accounts = OrganizationDiscovery(session).list_accounts()

    assert [account.account_id for account in accounts] == ["111111111111", "222222222222"]
    assert accounts[0].name == "prod"
    stubber.assert_no_pending_responses()


def test_region_discovery_filters_enabled_regions() -> None:
    session = boto3.Session(aws_access_key_id="test", aws_secret_access_key="test", region_name="us-east-1")
    client = session.client("ec2", region_name="us-east-1")
    stubber = Stubber(client)
    stubber.add_response("describe_regions", {
        "Regions": [
            {"RegionName": "us-east-1", "OptInStatus": "opt-in-not-required"},
            {"RegionName": "eu-west-1", "OptInStatus": "opted-in"},
            {"RegionName": "ap-south-2", "OptInStatus": "not-opted-in"},
        ]
    }, {
        "AllRegions": True,
        "Filters": [{"Name": "opt-in-status", "Values": ["opt-in-not-required", "opted-in"]}],
    })
    stubber.activate()
    session.client = lambda *args, **kwargs: client  # type: ignore[method-assign]

    assert RegionDiscovery(session).enabled_regions() == ["eu-west-1", "us-east-1"]
    stubber.assert_no_pending_responses()
