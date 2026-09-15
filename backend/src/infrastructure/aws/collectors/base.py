from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

from domain.entities.aws_resource import AWSResource


def tags_from_aws(items: list[dict[str, Any]] | None) -> dict[str, str]:
    return {
        str(item.get("Key")): str(item.get("Value", ""))
        for item in (items or [])
        if item.get("Key") is not None
    }


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def config_hash(data: dict[str, Any]) -> str:
    return sha256(repr(sorted((str(k), repr(v)) for k, v in data.items())).encode()).hexdigest()


def resource(
    *,
    resource_id: str,
    resource_type: str,
    service: str,
    account_id: str,
    region: str | None,
    raw_data: dict[str, Any],
    tags: dict[str, str] | None = None,
    arn: str | None = None,
    name: str | None = None,
    state: str | None = None,
    availability_zone: str | None = None,
    creation_time: datetime | None = None,
) -> AWSResource:
    tag_map = tags or {}
    fingerprint = config_hash(raw_data)
    return AWSResource(
        resource_id=resource_id,
        arn=arn,
        resource_name=name or tag_map.get("Name"),
        resource_type=resource_type,
        service=service,
        account_id=account_id,
        region=region,
        availability_zone=availability_zone,
        state=state,
        environment=tag_map.get("Environment") or tag_map.get("environment"),
        owner=tag_map.get("Owner") or tag_map.get("owner"),
        application=tag_map.get("Application") or tag_map.get("application"),
        cost_center=tag_map.get("CostCenter") or tag_map.get("cost-center"),
        tags={},
        creation_time=creation_time,
        last_seen_at=now_utc(),
        raw_data={},
        configuration_hash=fingerprint,
    )
