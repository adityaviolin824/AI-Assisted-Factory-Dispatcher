# run_allocation.py: plan one saved processing run. Allocation makes no model call, so it is free
# and can be repeated as often as needed.
#
# Run from backend/:  uv run python run_allocation.py output/runs/<start time>
# With no run folder, it lists the saved runs and stops; it never picks a run by itself.
#
# Steps: plan_saved_run (task_allocation_to_workshops/allocation_plan.py) reads the run's messages and
# processing state, routes the verified tasks (task_routing/), plans the ready ones and saves the plan
# in the run folder: plan.json, or plan-<objective>.json when plan_objective is set in config.toml.
import json
import sys
from pathlib import Path

from order_processing_into_tasks.settings_and_data import DATA_DIR, RUNS_DIR
from task_allocation_to_workshops.allocation_plan import plan_saved_run
from task_allocation_to_workshops.allocation_settings_and_data import (
    DISPATCH_DATE, ORDERS, PLAN_OBJECTIVE, WORKSHOPS)


def main():
    """Plan the run folder named on the command line, or list the saved runs when none is named."""
    if len(sys.argv) != 2:
        print("Usage: uv run python run_allocation.py output/runs/<start time>\n")
        print(f"Saved runs in {RUNS_DIR}:")
        for manifest_file in sorted(RUNS_DIR.glob("*/manifest.json")):
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            print(f"  {manifest_file.parent.name}  {manifest['label']} ({len(manifest['messages'])} messages)")
        return

    run_dir = Path(sys.argv[1])
    # Show the inputs and settings once, so every plan starts with them visible.
    objective = PLAN_OBJECTIVE or "each request's own preference"
    print(f"Loaded {len(ORDERS)} orders and {len(WORKSHOPS)} workshops from {DATA_DIR}.")
    print(f"Dispatch date: {DISPATCH_DATE}; objective: {objective}")
    print(f"Run folder: {run_dir}\n")
    plan_saved_run(run_dir)


if __name__ == "__main__":
    main()
