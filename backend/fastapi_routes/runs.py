# runs.py: HTTP endpoints for saved runs (output/runs/<start time>/).
#
# GET /runs, GET /runs/{run_id} and GET /runs/{run_id}/usage only read files: no processing, no planning
# again and no model call. Review again (22 October 2026) changes a run's approved dispatcher plan: preview calculates the new
# choices on top of the saved ones and saves nothing; finalize saves the result as a new version,
# and plan-history/ keeps the earlier one. Both calculate in Python: no model call.
import json

from fastapi import APIRouter, HTTPException

from dispatcher_review.dispatcher_decisions import review_saved_plan, save_dispatcher_files
from dispatcher_review.dispatcher_plan import finalize_review
from eval_run_report.run_summary import PRICES, PRICES_CHECKED, stage_costs
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


def saved_run_dir(run_id):
    """Return a saved run's folder, or refuse with 404.

    Only the name of a saved run folder is accepted, so no other file on the computer can be used.
    """
    if run_id not in saved_run_ids():
        raise HTTPException(status_code=404, detail=f"No saved run {run_id}.")
    return RUNS_DIR / run_id


def approved_run_dir(run_id):
    """Return a saved run's folder once the dispatcher approved its plan, or refuse with 404."""
    run_dir = saved_run_dir(run_id)
    if not (run_dir / "dispatcher-plan.json").exists():
        raise HTTPException(status_code=404, detail=f"Run {run_id} has no approved dispatcher plan yet.")
    return run_dir


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
    """
    run_dir = saved_run_dir(run_id)
    return {"run_id": run_id, "plan": read_json(run_dir / "plan.json"),
            "dispatcher_plan": read_json(run_dir / "dispatcher-plan.json")}


@router.get("/runs/{run_id}/usage")
def read_run_usage(run_id: str):
    """Return one saved run's model calls, tokens, estimated model cost and model time, per stage.

    Calculated by stage_costs from the run's calls/*.json records. Only counts, tokens, dollars and
    seconds are returned: no prompt, chat text or model answer. "this_run" figures cover the calls
    this run paid for; "fresh" figures price every answered call, as a run with no saved answers would
    pay. A cost is None when a model has no listed price.
    """
    run_dir = saved_run_dir(run_id)
    calls = [read_json(path) for path in sorted((run_dir / "calls").glob("*.json"))]
    return {"run_id": run_id, "prices_checked": PRICES_CHECKED, "prices": PRICES, "stages": stage_costs(calls)}


@router.post("/runs/{run_id}/preview")
def preview_saved_plan(run_id: str, body: dict):
    """Show what Review again would save for new choices, {"decisions": [...]}, without saving.

    Returns {"review": the draft with its "changes" compared with the approved plan, "refused": None},
    or the approved plan unchanged with the reason the whole set would be refused. No file is written.
    """
    _, review, refusal = review_saved_plan(approved_run_dir(run_id), body.get("decisions"))
    return {"review": review, "refused": refusal}


@router.post("/runs/{run_id}/finalize")
def finalize_saved_plan(run_id: str, body: dict):
    """Review again: apply new choices, {"decisions": [...]}, on top of the saved ones and approve the result.

    The new dispatcher-plan.json and dispatcher-decisions.json replace the old ones, which stay in
    plan-history/. Returns {"review": the saved plan, whose "changes" lists the rows that differ from
    the previous approved plan, "refused": None}, or the approved plan unchanged with the reason the
    whole set was refused; then nothing is saved.
    """
    run_dir = approved_run_dir(run_id)
    decisions, review, refusal = review_saved_plan(run_dir, body.get("decisions"))
    if refusal is not None:
        return {"review": review, "refused": refusal}
    final = finalize_review(review)
    save_dispatcher_files(run_dir, decisions, final)
    return {"review": final, "refused": None}
