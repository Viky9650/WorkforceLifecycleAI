import json
from pathlib import Path
from fastapi import APIRouter, HTTPException

router = APIRouter()

RUNS_DIR = Path("store/runs")

@router.get("/runs")
def list_runs():
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted([p.name for p in RUNS_DIR.glob("*.json")], reverse=True)
    return {"runs": files}

@router.get("/runs/{filename}")
def get_run(filename: str):
    path = RUNS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Run not found")
    with open(path, "r") as f:
        return json.load(f)
