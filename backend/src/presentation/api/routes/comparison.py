from fastapi import APIRouter, HTTPException
from presentation.api.dependencies import repository

router = APIRouter(prefix="/api/v1/inventory-runs", tags=["comparison"])

@router.get("/{current_run_id}/compare/{baseline_run_id}")
def compare_runs(current_run_id: str, baseline_run_id: str):
    repo = repository()
    if not repo.get_run(current_run_id) or not repo.get_run(baseline_run_id):
        raise HTTPException(status_code=404, detail="Inventory run not found")
    return repo.compare_runs(baseline_run_id, current_run_id)
