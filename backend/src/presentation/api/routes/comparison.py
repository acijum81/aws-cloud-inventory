from fastapi import APIRouter, Depends, HTTPException
from presentation.api.dependencies import repository
from presentation.api.security import require_read_access

router = APIRouter(prefix="/api/v1/inventory-runs", tags=["comparison"])

@router.get("/{current_run_id}/compare/{baseline_run_id}", dependencies=[Depends(require_read_access)])
def compare_runs(current_run_id: str, baseline_run_id: str):
    repo = repository()
    if not repo.get_run(current_run_id) or not repo.get_run(baseline_run_id):
        raise HTTPException(status_code=404, detail="Inventory run not found")
    comparison = repo.compare_runs(baseline_run_id, current_run_id)
    return {
        key: [{field: value for field, value in item.items() if field not in {"raw_data", "tags"}} for item in items]
        for key, items in comparison.items()
    }
