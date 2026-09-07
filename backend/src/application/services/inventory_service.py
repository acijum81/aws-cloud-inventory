from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from domain.entities.aws_resource import AWSResource
from infrastructure.aws.collectors import MVP_COLLECTORS
from infrastructure.aws.discovery.organization import OrganizationDiscovery, AwsAccount
from infrastructure.aws.discovery.regions import RegionDiscovery
from infrastructure.aws.inventory_runner import InventoryResult, InventoryRunner
from infrastructure.aws.session_factory import AwsSessionFactory
from infrastructure.database.repository import ResourceRepository
from application.services.cancellation import cancellation_registry


@dataclass(slots=True)
class InventoryExecution:
    run_id: str
    resources: list[AWSResource]
    errors: list


class MVPInventoryService:
    def __init__(self, session_factory: AwsSessionFactory, repository: ResourceRepository | None = None) -> None:
        self.session_factory = session_factory
        self.repository = repository

    def run_accounts(self, account_ids: list[str], regions: list[str] | None = None, persist: bool = True) -> InventoryExecution:
        run_id = str(uuid4())
        selected_regions = regions or RegionDiscovery(self.session_factory).enabled_regions()
        started_at = datetime.now(timezone.utc)
        if persist and self.repository:
            self.repository.create_run({"run_id": run_id, "status": "running", "scope": "accounts", "started_at": started_at,
                                        "finished_at": None, "requested_accounts": account_ids, "requested_regions": regions,
                                        "resource_count": 0, "error_count": 0, "metadata": {}})
        all_resources: list[AWSResource] = []
        all_errors = []
        for account_id in account_ids:
            if cancellation_registry.is_cancelled(run_id):
                break
            result = self.run_account(account_id, selected_regions, persist=False, run_id=run_id)
            all_resources.extend(result.resources)
            all_errors.extend(result.errors)
        cancelled = cancellation_registry.is_cancelled(run_id)
        if persist and self.repository:
            self.repository.save_many(all_resources)
            self.repository.add_errors(all_errors, run_id)
            self.repository.update_run(run_id, status="cancelled" if cancelled else "completed", finished_at=datetime.now(timezone.utc),
                                       resource_count=len(all_resources), error_count=len(all_errors))
        cancellation_registry.clear(run_id)
        return InventoryExecution(run_id=run_id, resources=all_resources, errors=all_errors)

    def run_account(self, account_id: str, regions: list[str] | None = None, persist: bool = True, run_id: str | None = None) -> InventoryExecution:
        run_id = run_id or str(uuid4())
        selected_regions = regions or RegionDiscovery(self.session_factory).enabled_regions()
        all_resources: list[AWSResource] = []
        errors = []
        global_collectors = [c for c in MVP_COLLECTORS if c.is_global]
        regional_collectors = [c for c in MVP_COLLECTORS if not c.is_global]
        global_result = InventoryRunner(self.session_factory, global_collectors).collect_account_region(account_id, "us-east-1")
        all_resources.extend(self._attach_run_id(global_result.resources, run_id)); errors.extend(global_result.errors)
        for region in selected_regions:
            result = InventoryRunner(self.session_factory, regional_collectors).collect_account_region(account_id, region)
            all_resources.extend(self._attach_run_id(result.resources, run_id)); errors.extend(result.errors)
        if persist and self.repository:
            self.repository.save_many(all_resources); self.repository.add_errors(errors, run_id)
        return InventoryExecution(run_id=run_id, resources=all_resources, errors=errors)

    def discover_accounts(self) -> list[AwsAccount]:
        return OrganizationDiscovery(self.session_factory).list_accounts()

    def discover_regions(self) -> list[str]:
        return RegionDiscovery(self.session_factory).enabled_regions()

    @staticmethod
    def _attach_run_id(resources: list[AWSResource], run_id: str) -> list[AWSResource]:
        return [resource.model_copy(update={"inventory_run_id": run_id}) for resource in resources]
