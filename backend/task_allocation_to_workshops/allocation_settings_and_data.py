# allocation_settings_and_data.py: the allocation settings and the two CSV files, converted for allocation.
#
# Allocation flow: route_verified_tasks (task_routing/) -> allocation_plan -> recommend_one_task,
#                  which uses workshop_rules_and_estimates and rank_workshops.
#                  Every allocation file imports its settings and data from here.
#
# Came from: notebook 05, Sections 1 and 2 (the allocation parts).
# Reads:     [allocation] in backend/config.toml, then workshops.csv and orders.csv from the data folder.
# Writes:    nothing.
import csv
from dataclasses import dataclass
from datetime import date

from order_processing_into_tasks.settings_and_data import CONFIG, DATA_DIR

# Every request is planned from this snapshot date (a TOML date, read as datetime.date).
DISPATCH_DATE = CONFIG["allocation"]["dispatch_date"]
# None keeps each request's own preference. An objective name from rank_workshops.py (for example
# "hybrid") ranks every request with it instead, and the plan is saved to its own file.
PLAN_OBJECTIVE = CONFIG["allocation"].get("plan_objective")


@dataclass
class Workshop:
    """One workshop, with only the CSV fields that the rules, formulas and saved records use."""
    workshop_id: str
    name: str
    capacity: int
    lead_days: int
    defect_rate: float
    cost: float
    makes: set[str]
    status: str
    max_batch: int | None
    queue0: float
    notes: str


# The workshop CSV rows converted once: numbers, a set of categories, None for a blank batch cap.
# The CSV files are only read, never changed.
with (DATA_DIR / "workshops.csv").open(newline="", encoding="utf-8") as file:
    WORKSHOPS = {
        row["workshop_id"]: Workshop(
            workshop_id=row["workshop_id"], name=row["name"],
            capacity=int(row["capacity_pieces_per_day"]), lead_days=int(row["pickup_lead_days"]),
            defect_rate=float(row["defect_rate"]), cost=float(row["cost_per_piece"]),
            makes=set(row["makes"].split("+")), status=row["status"],
            max_batch=int(row["max_batch_pieces"]) if row["max_batch_pieces"] else None,
            queue0=float(row["current_queue_days"]), notes=row["notes"])
        for row in csv.DictReader(file)
    }
# Each order keeps every CSV column (the hard rules use status and current_stage);
# pieces becomes a number and due_date a date.
with (DATA_DIR / "orders.csv").open(newline="", encoding="utf-8") as file:
    ORDERS = {row["order_id"]: {**row, "pieces": int(row["pieces"]),
                               "due_date": date.fromisoformat(row["due_date"])}
              for row in csv.DictReader(file)}
# Each workshop's starting queue, in days. Plans work on a copy; nothing changes this one.
INITIAL_QUEUES = {wid: workshop.queue0 for wid, workshop in WORKSHOPS.items()}
