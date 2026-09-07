from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from application.ports.aws_inventory_provider import ResourceCollector

CollectorType: TypeAlias = type[ResourceCollector]


@dataclass(frozen=True, slots=True)
class CollectorDefinition:
    name: str
    collector: CollectorType
    is_global: bool
