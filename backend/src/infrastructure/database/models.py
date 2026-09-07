from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class InventoryRunModel(Base):
    __tablename__ = "inventory_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    scope: Mapped[str] = mapped_column(String(32), default="account")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    requested_accounts: Mapped[list[str]] = mapped_column(JSON, default=list)
    requested_regions: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    resource_count: Mapped[int] = mapped_column(default=0)
    error_count: Mapped[int] = mapped_column(default=0)
    run_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class InventoryErrorModel(Base):
    __tablename__ = "inventory_errors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    account_id: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    region: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    service: Mapped[str] = mapped_column(String(128), index=True)
    operation: Mapped[str] = mapped_column(String(128))
    error_type: Mapped[str] = mapped_column(String(64), index=True)
    message: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    correlation_id: Mapped[str] = mapped_column(String(64))


class AWSResourceModel(Base):
    __tablename__ = "aws_resources"
    __table_args__ = (
        UniqueConstraint("inventory_run_id", "resource_id", "resource_type", name="uq_run_resource"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    resource_id: Mapped[str] = mapped_column(String(512), index=True)
    arn: Mapped[str | None] = mapped_column(String(1024), nullable=True, index=True)
    resource_name: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    resource_type: Mapped[str] = mapped_column(String(255), index=True)
    service: Mapped[str] = mapped_column(String(128), index=True)
    account_id: Mapped[str] = mapped_column(String(32), index=True)
    account_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    organization_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    region: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    availability_zone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    state: Mapped[str | None] = mapped_column(String(128), nullable=True)
    environment: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    application: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cost_center: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tags: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    creation_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    inventory_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    configuration_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
