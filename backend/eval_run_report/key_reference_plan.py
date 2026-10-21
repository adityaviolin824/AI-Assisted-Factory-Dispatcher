# key_reference_plan.py: the plan the answer key implies, calculated by the app's own routing and
# allocation rules from the test set's CSV files, so a run's workshop choices can be compared with it.
#
# Report flow: make_run_report.py --key --data -> score_against_key -> reference_workshops (this file).
# Came from:   experimentation_notebooks/testing/check_extended_dispatch_100.py (expected_tasks and
#              calculate), which proves this plan feasible for the 100-case set.
# Reads:       orders.csv and workshops.csv in the data folder given. Writes nothing; no model call.
import contextlib
import csv
import io
from datetime import date
from unittest.mock import patch

from task_allocation_to_workshops import allocation_plan, recommend_one_task, workshop_rules_and_estimates
from task_allocation_to_workshops.allocation_settings_and_data import Workshop
from task_routing.route_verified_tasks import route_tasks


def read_data_folder(folder):
    """Return (orders, workshops) from a data folder, converted as allocation_settings_and_data does."""
    with (folder / "orders.csv").open(newline="", encoding="utf-8") as file:
        orders = {row["order_id"]: {**row, "pieces": int(row["pieces"]), "due_date": date.fromisoformat(row["due_date"])}
                  for row in csv.DictReader(file)}
    with (folder / "workshops.csv").open(newline="", encoding="utf-8") as file:
        workshops = {row["workshop_id"]: Workshop(
            workshop_id=row["workshop_id"], name=row["name"], capacity=int(row["capacity_pieces_per_day"]),
            lead_days=int(row["pickup_lead_days"]), defect_rate=float(row["defect_rate"]),
            cost=float(row["cost_per_piece"]), makes=set(row["makes"].split("+")), status=row["status"],
            max_batch=int(row["max_batch_pieces"]) if row["max_batch_pieces"] else None,
            queue0=float(row["current_queue_days"]), notes=row["notes"])
            for row in csv.DictReader(file)}
    return orders, workshops


def key_task(case, texts):
    """Return the verified task record the key expects for one case, built from the key, never a model.

    texts maps message IDs to their chat text. The task ID only needs to be unique within the key.
    """
    expected = case["expected"]
    message_ids = [message["message_id"] for message in case["messages"]]
    workshop_rules = [{"workshop_id": expected["requested_workshop"], "role": "requested"}] if expected["requested_workshop"] else []
    workshop_rules += [{"workshop_id": wid, "role": "excluded"} for wid in expected["excluded_workshops"]]
    evidence = [{"evidence_id": f"{case['case_id']}:E{n}", "message_id": message_id, "text": texts[message_id]}
                for n, message_id in enumerate(message_ids, 1)]
    return {**expected, "task_id": case["case_id"], "version": len(message_ids),
            "description": "\n".join(texts[message_id] for message_id in message_ids),
            "source_message_ids": message_ids, "workshop_rules": workshop_rules, "source_evidence": evidence}


def reference_workshops(key, orders, workshops):
    """Return {case_id: workshop} for every case the key's own plan recommends.

    The allocation modules read ORDERS, WORKSHOPS, DISPATCH_DATE and INITIAL_QUEUES from config.toml's
    data folder when imported, so they are replaced here only while this plan is made; the modules'
    code and the configured data are unchanged afterwards.
    """
    texts = {message["message_id"]: message["raw_text"] for message in key["messages"]}
    tasks = [key_task(case, texts) for case in key["cases"]]
    initial = {wid: workshop.queue0 for wid, workshop in workshops.items()}
    replacements = {"ORDERS": orders, "WORKSHOPS": workshops, "INITIAL_QUEUES": initial,
                    "DISPATCH_DATE": date.fromisoformat(key["dispatch_date"])}
    with contextlib.ExitStack() as stack:
        for module in (allocation_plan, recommend_one_task, workshop_rules_and_estimates):
            for name, value in replacements.items():
                if hasattr(module, name):
                    stack.enter_context(patch.object(module, name, value))
        # plan_tasks prints its planning steps; the report needs only the result.
        with contextlib.redirect_stdout(io.StringIO()):
            plan = allocation_plan.plan_tasks(route_tasks(tasks)["allocate"], initial)
    return {decision["task_id"]: decision["selected_workshop"]
            for decision in plan["decisions"] if decision["status"] == "recommendation"}
