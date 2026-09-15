from __future__ import annotations

import csv
import io
import json
import os

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from presentation.api.dependencies import repository
from presentation.api.security import require_read_access

router = APIRouter(prefix="/api/v1/resources", tags=["resources"])


def _public_resource(item):
    return item.model_dump(mode="json", exclude={"raw_data", "tags"})


def _export_limit() -> int:
    try:
        return max(1, min(int(os.getenv("MAX_EXPORT_ROWS", "10000")), 10000))
    except ValueError:
        return 10_000


def _filters(inventory_run_id, account_id, region, service, resource_type, state, environment, owner, search):
    return {"inventory_run_id": inventory_run_id, "account_id": account_id, "region": region, "service": service,
            "resource_type": resource_type, "state": state, "environment": environment, "owner": owner, "search": search}


@router.get("", dependencies=[Depends(require_read_access)])
def list_resources(inventory_run_id: str | None = None, account_id: str | None = None, region: str | None = None,
                   service: str | None = None, resource_type: str | None = None, state: str | None = None,
                   environment: str | None = None, owner: str | None = None, search: str | None = None,
                   limit: int = Query(default=100, ge=1, le=1000), offset: int = Query(default=0, ge=0)):
    items, total = repository().list_resources(_filters(inventory_run_id, account_id, region, service, resource_type, state, environment, owner, search), limit, offset)
    return {"items": [_public_resource(x) for x in items], "total": total, "limit": limit, "offset": offset}


@router.get("/summary", dependencies=[Depends(require_read_access)])
def resources_summary(inventory_run_id: str | None = None):
    return repository().summary(inventory_run_id)


@router.get("/export.csv", dependencies=[Depends(require_read_access)])
def export_csv(inventory_run_id: str | None = None):
    items, _ = repository().list_resources({"inventory_run_id": inventory_run_id} if inventory_run_id else {}, _export_limit(), 0)
    output = io.StringIO(); writer = csv.DictWriter(output, fieldnames=["resource_id", "resource_name", "resource_type", "service", "account_id", "region", "state", "environment", "owner", "arn", "configuration_hash"])
    writer.writeheader()
    for item in items:
        data = item.model_dump()
        writer.writerow({k: data.get(k) for k in writer.fieldnames})
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=aws-inventory.csv"})


@router.get("/export.json", dependencies=[Depends(require_read_access)])
def export_json(inventory_run_id: str | None = None):
    items, _ = repository().list_resources({"inventory_run_id": inventory_run_id} if inventory_run_id else {}, _export_limit(), 0)
    payload = json.dumps([_public_resource(x) for x in items])
    return StreamingResponse(iter([payload]), media_type="application/json", headers={"Content-Disposition": "attachment; filename=aws-inventory.json"})
