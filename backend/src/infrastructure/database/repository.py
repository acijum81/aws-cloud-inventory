from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import create_engine, func, or_, select
from sqlalchemy.orm import sessionmaker

from domain.entities.aws_resource import AWSResource
from infrastructure.database.models import AWSResourceModel, Base, InventoryErrorModel, InventoryRunModel


class ResourceRepository:
    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.session_factory = sessionmaker(self.engine, expire_on_commit=False)

    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)

    def save_many(self, resources: Iterable[AWSResource]) -> int:
        models = [AWSResourceModel(**resource.model_dump()) for resource in resources]
        if not models:
            return 0
        with self.session_factory.begin() as session:
            session.add_all(models)
        return len(models)

    def create_run(self, run: dict[str, Any]) -> None:
        with self.session_factory.begin() as session:
            session.add(InventoryRunModel(**run))

    def update_run(self, run_id: str, **updates: Any) -> None:
        with self.session_factory.begin() as session:
            item = session.get(InventoryRunModel, run_id)
            if item is None:
                return
            for key, value in updates.items():
                setattr(item, key, value)

    def add_errors(self, errors: Iterable[Any], run_id: str) -> int:
        now = datetime.now(timezone.utc)
        models = [
            InventoryErrorModel(
                run_id=run_id,
                account_id=error.account_id,
                region=error.region,
                service=error.service,
                operation=error.operation,
                error_type=error.error_type,
                message="AWS collection error; inspect protected server logs using the correlation ID.",
                occurred_at=now,
                correlation_id=error.correlation_id,
            )
            for error in errors
        ]
        if not models:
            return 0
        with self.session_factory.begin() as session:
            session.add_all(models)
        return len(models)

    def list_runs(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            rows = session.scalars(select(InventoryRunModel).order_by(InventoryRunModel.started_at.desc()).limit(limit).offset(offset)).all()
            return [self._run_dict(row) for row in rows]

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self.session_factory() as session:
            row = session.get(InventoryRunModel, run_id)
            return self._run_dict(row) if row else None

    def list_errors(self, run_id: str, limit: int = 500) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            rows = session.scalars(select(InventoryErrorModel).where(InventoryErrorModel.run_id == run_id).order_by(InventoryErrorModel.occurred_at.desc()).limit(limit)).all()
            return [
                {"account_id": r.account_id, "region": r.region, "service": r.service, "operation": r.operation,
                 "error_type": r.error_type, "message": r.message, "occurred_at": r.occurred_at,
                 "correlation_id": r.correlation_id}
                for r in rows
            ]

    def list_by_run(self, inventory_run_id: str | None = None, limit: int = 100, offset: int = 0) -> list[AWSResource]:
        items, _ = self.list_resources({"inventory_run_id": inventory_run_id} if inventory_run_id else {}, limit, offset)
        return items

    def list_resources(self, filters: dict[str, Any] | None = None, limit: int = 100, offset: int = 0) -> tuple[list[AWSResource], int]:
        filters = filters or {}
        with self.session_factory() as session:
            query = select(AWSResourceModel)
            count_query = select(func.count()).select_from(AWSResourceModel)
            predicates = []
            exact_fields = ["inventory_run_id", "account_id", "region", "service", "resource_type", "state", "environment", "owner"]
            for field in exact_fields:
                value = filters.get(field)
                if value:
                    column = getattr(AWSResourceModel, field)
                    predicates.append(column == value)
            search = filters.get("search")
            if search:
                like = f"%{search}%"
                predicates.append(or_(AWSResourceModel.resource_id.ilike(like), AWSResourceModel.resource_name.ilike(like), AWSResourceModel.arn.ilike(like)))
            for pred in predicates:
                query = query.where(pred)
                count_query = count_query.where(pred)
            total = int(session.scalar(count_query) or 0)
            models = session.scalars(query.order_by(AWSResourceModel.id).limit(limit).offset(offset)).all()
            return [self._to_entity(model) for model in models], total

    def summary(self, inventory_run_id: str | None = None) -> dict[str, Any]:
        resources, _ = self.list_resources({"inventory_run_id": inventory_run_id} if inventory_run_id else {}, limit=100000, offset=0)
        return {
            "resource_count": len(resources),
            "accounts": sorted({r.account_id for r in resources}),
            "services": sorted({r.service for r in resources}),
            "regions": sorted({r.region for r in resources if r.region}),
            "by_service": self._counts(resources, lambda r: r.service),
            "by_region": self._counts(resources, lambda r: r.region or "global"),
            "missing_owner": sum(1 for r in resources if not r.owner),
            "missing_environment": sum(1 for r in resources if not r.environment),
        }

    def compare_runs(self, baseline_run_id: str, current_run_id: str) -> dict[str, list[dict[str, Any]]]:
        base, _ = self.list_resources({"inventory_run_id": baseline_run_id}, limit=100000, offset=0)
        curr, _ = self.list_resources({"inventory_run_id": current_run_id}, limit=100000, offset=0)
        base_map = {(r.account_id, r.resource_type, r.resource_id): r for r in base}
        curr_map = {(r.account_id, r.resource_type, r.resource_id): r for r in curr}
        added = [r.model_dump(mode="json") for k, r in curr_map.items() if k not in base_map]
        removed = [r.model_dump(mode="json") for k, r in base_map.items() if k not in curr_map]
        changed = [r.model_dump(mode="json") for k, r in curr_map.items() if k in base_map and r.configuration_hash != base_map[k].configuration_hash]
        return {"added": added, "removed": removed, "changed": changed}

    @staticmethod
    def _run_dict(row: InventoryRunModel) -> dict[str, Any]:
        return {"run_id": row.run_id, "status": row.status, "scope": row.scope, "started_at": row.started_at,
                "finished_at": row.finished_at, "requested_accounts": row.requested_accounts or [],
                "requested_regions": row.requested_regions, "resource_count": row.resource_count,
                "error_count": row.error_count, "metadata": row.run_metadata or {}}

    @staticmethod
    def _counts(resources: list[AWSResource], key) -> dict[str, int]:
        result: dict[str, int] = {}
        for resource in resources:
            value = key(resource)
            result[value] = result.get(value, 0) + 1
        return dict(sorted(result.items()))

    @staticmethod
    def _to_entity(model: AWSResourceModel) -> AWSResource:
        return AWSResource.model_validate({
            "resource_id": model.resource_id, "arn": model.arn, "resource_name": model.resource_name,
            "resource_type": model.resource_type, "service": model.service, "account_id": model.account_id,
            "account_name": model.account_name, "organization_id": model.organization_id, "region": model.region,
            "availability_zone": model.availability_zone, "state": model.state, "environment": model.environment,
            "owner": model.owner, "application": model.application, "cost_center": model.cost_center,
            "tags": model.tags or {}, "creation_time": model.creation_time, "last_seen_at": model.last_seen_at,
            "inventory_run_id": model.inventory_run_id, "raw_data": model.raw_data or {},
            "configuration_hash": model.configuration_hash,
        })
