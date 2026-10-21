# runs.py: HTTP endpoints that read saved runs (output/runs/<start time>/).
#
# They only read files: no processing, no planning again and no model call.
import json

from fastapi import APIRouter, HTTPException

from order_processing_into_tasks.settings_and_data import RUNS_DIR

router = APIRouter(tags=["runs"])


def read_json(path):
    """Return a JSON file's content, or None when the file is not there."""
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def saved_run_ids():
    """Return the names of the saved run folders (each one holds a manifest.json), oldest first."""
    return [path.parent.name for path in sorted(RUNS_DIR.glob("*/manifest.json"))]


@router.get("/runs")
def list_runs():
    """List the saved runs, as run_allocation.py does: each run's ID, label and message count."""
    runs = []
    for run_id in saved_run_ids():
        manifest = read_json(RUNS_DIR / run_id / "manifest.json")
        runs.append({"run_id": run_id, "label": manifest["label"], "messages": len(manifest["messages"])})
    return runs


@router.get("/runs/{run_id}")
def read_run(run_id: str):
    """Return one saved run's plan.json, and its dispatcher-plan.json once the dispatcher approved
    (None before).

    Only the name of a saved run folder is accepted, so no other file on the computer can be read.
    """
    if run_id not in saved_run_ids():
        raise HTTPException(status_code=404, detail=f"No saved run {run_id}.")
    run_dir = RUNS_DIR / run_id
    return {"run_id": run_id, "plan": read_json(run_dir / "plan.json"),
            "dispatcher_plan": read_json(run_dir / "dispatcher-plan.json")}
