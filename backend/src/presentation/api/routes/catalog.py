from fastapi import APIRouter
from application.services.inventory_service import MVPInventoryService
from presentation.api.dependencies import session_factory

router = APIRouter(prefix="/api/v1", tags=["discovery"])

@router.get("/accounts")
def accounts():
    items = MVPInventoryService(session_factory()).discover_accounts()
    return {"items": [{"account_id": a.account_id, "name": a.name, "status": a.status, "joined_method": a.joined_method, "joined_timestamp": a.joined_timestamp} for a in items]}

@router.get("/regions")
def regions():
    return {"items": MVPInventoryService(session_factory()).discover_regions()}
