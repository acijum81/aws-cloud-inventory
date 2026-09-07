from __future__ import annotations

from boto3.session import Session


class RegionDiscovery:
    service_name = "ec2"
    discovery_region = "us-east-1"

    def __init__(self, session: Session) -> None:
        self._session = session

    def enabled_regions(self) -> list[str]:
        client = self._session.client("ec2", region_name=self.discovery_region)
        response = client.describe_regions(
            AllRegions=True,
            Filters=[
                {"Name": "opt-in-status", "Values": ["opt-in-not-required", "opted-in"]},
            ],
        )
        regions = {
            str(region["RegionName"])
            for region in response.get("Regions", [])
            if str(region.get("OptInStatus", "")) in {"opt-in-not-required", "opted-in"}
        }
        return sorted(regions)
