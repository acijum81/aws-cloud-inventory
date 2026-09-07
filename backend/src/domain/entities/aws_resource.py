from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AWSResource(BaseModel):
    model_config = ConfigDict(frozen=True)

    resource_id: str
    arn: str | None = None
    resource_name: str | None = None
    resource_type: str
    service: str
    account_id: str
    account_name: str | None = None
    organization_id: str | None = None
    region: str | None = None
    availability_zone: str | None = None
    state: str | None = None
    environment: str | None = None
    owner: str | None = None
    application: str | None = None
    cost_center: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)
    creation_time: datetime | None = None
    last_seen_at: datetime | None = None
    inventory_run_id: str | None = None
    raw_data: dict[str, Any] = Field(default_factory=dict)
    configuration_hash: str | None = None
