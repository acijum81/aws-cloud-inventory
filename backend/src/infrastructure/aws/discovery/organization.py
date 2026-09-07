from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from boto3.session import Session


@dataclass(frozen=True, slots=True)
class AwsAccount:
    account_id: str
    name: str
    status: str
    joined_method: str | None = None
    joined_timestamp: Any | None = None


class OrganizationDiscovery:
    service_name = "organizations"
    region = "us-east-1"
    is_global = True

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_accounts(self) -> list[AwsAccount]:
        client = self._session.client("organizations", region_name=self.region)
        paginator = client.get_paginator("list_accounts")
        accounts: list[AwsAccount] = []
        for page in paginator.paginate():
            for account in page.get("Accounts", []):
                accounts.append(
                    AwsAccount(
                        account_id=str(account["Id"]),
                        name=str(account["Name"]),
                        status=str(account["Status"]),
                        joined_method=account.get("JoinedMethod"),
                        joined_timestamp=account.get("JoinedTimestamp"),
                    )
                )
        return accounts

    def organization_id(self) -> str | None:
        client = self._session.client("organizations", region_name=self.region)
        try:
            response = client.describe_organization()
        except client.exceptions.AWSOrganizationsNotInUseException:
            return None
        return response.get("Organization", {}).get("Id")
