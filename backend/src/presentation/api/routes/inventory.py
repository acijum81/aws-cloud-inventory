from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field, SecretStr

from application.services.inventory_service import MVPInventoryService
from application.services.cancellation import cancellation_registry
from presentation.api.dependencies import repository, session_factory_from_credentials
from presentation.api.security import (
    acquire_inventory_slot,
    release_inventory_slot,
    require_allowed_accounts,
    require_read_access,
    require_write_access,
)

router = APIRouter(prefix="/api/v1/inventory-runs", tags=["inventory"])


AwsRegion = Annotated[str, Field(pattern=r"^[a-z]{2}-[a-z]+-\d$")]


class AwsCredentialsRequest(BaseModel):
    access_key_id: SecretStr = Field(min_length=16, max_length=128)
    secret_access_key: SecretStr = Field(min_length=16, max_length=256)
    session_token: SecretStr | None = Field(default=None, max_length=4096)


class InventoryStartRequest(BaseModel):
    credentials: AwsCredentialsRequest
    regions: list[AwsRegion] | None = Field(default=None, max_length=30)

@router.post("", dependencies=[Depends(require_write_access)])
def start_inventory(request: InventoryStartRequest, background: BackgroundTasks) -> dict[str, str]:
    credentials = request.credentials
    factory = session_factory_from_credentials(
        credentials.access_key_id.get_secret_value(),
        credentials.secret_access_key.get_secret_value(),
        credentials.session_token.get_secret_value() if credentials.session_token else None,
    )
    try:
        account_id = factory.client("sts").get_caller_identity()["Account"]
    except (BotoCoreError, ClientError, KeyError):
        raise HTTPException(status_code=400, detail="AWS credentials could not be validated") from None
    require_allowed_accounts([account_id])
    repo = repository()
    acquire_inventory_slot()
    from uuid import uuid4
    run_id = str(uuid4())
    repo.create_run({"run_id": run_id, "status": "queued", "scope": "account", "started_at": datetime.now(timezone.utc),
                     "finished_at": None, "requested_accounts": [account_id], "requested_regions": request.regions,
                     "resource_count": 0, "error_count": 0, "metadata": {"queued_by": "api"}})
    def execute() -> None:
        service = MVPInventoryService(factory, repo)
        repo.update_run(run_id, status="running")
        all_resources = []; all_errors = []
        try:
            if cancellation_registry.is_cancelled(run_id):
                repo.update_run(run_id, status="cancelled", finished_at=datetime.now(timezone.utc))
                return
            result = service.run_account(account_id, request.regions, persist=False, run_id=run_id)
            all_resources.extend(result.resources); all_errors.extend(result.errors)
            repo.save_many(all_resources); repo.add_errors(all_errors, run_id)
            repo.update_run(run_id, status="completed", finished_at=datetime.now(timezone.utc), resource_count=len(all_resources), error_count=len(all_errors))
        except Exception:
            repo.update_run(run_id, status="failed", finished_at=datetime.now(timezone.utc), metadata={"error": "Inventory execution failed"})
        finally:
            cancellation_registry.clear(run_id)
            release_inventory_slot()
    background.add_task(execute)
    return {"run_id": run_id, "status": "queued"}


@router.get("", dependencies=[Depends(require_read_access)])
def list_inventory_runs(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    return {"items": repository().list_runs(limit, offset), "limit": limit, "offset": offset}


@router.get("/{run_id}", dependencies=[Depends(require_read_access)])
def get_inventory_run(run_id: str):
    item = repository().get_run(run_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory run not found")
    return item


@router.post("/{run_id}/cancel", dependencies=[Depends(require_write_access)])
def cancel_inventory_run(run_id: str):
    item = repository().get_run(run_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory run not found")
    if item["status"] in {"completed", "failed", "cancelled"}:
        return item
    cancellation_registry.cancel(run_id)
    return {"run_id": run_id, "status": "cancellation_requested"}


@router.get("/{run_id}/errors", dependencies=[Depends(require_read_access)])
def inventory_errors(run_id: str, limit: int = Query(500, ge=1, le=2000)):
    if not repository().get_run(run_id):
        raise HTTPException(status_code=404, detail="Inventory run not found")
    items = repository().list_errors(run_id, limit)
    return {"items": [{key: value for key, value in item.items() if key != "message"} for item in items]}
