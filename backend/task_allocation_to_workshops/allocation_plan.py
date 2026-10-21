# allocation_plan.py: the plan. Route the verified tasks, plan the ready ones earliest deadline
# first, reserve queue time for recommendations only, then list every input with its outcome.
#
# Allocation flow: plan_saved_run (a saved run folder) -> plan_allocation -> route_tasks
#                  (task_routing/) -> plan_tasks -> recommend (recommend_one_task), once per ready
#                  task -> summarize_plan -> plan.json.
# Came from:       notebook 05, Section 13 and the body of the graph node plan_allocation.
#                  plan_saved_run is new: it plans a saved run folder, so allocation runs by itself.
# Reads:           the processing state (verified tasks, reviews, non-task messages) and the messages.
# Writes:          run_dir/plan.json (plan-<objective>.json when PLAN_OBJECTIVE is set), and the
#                  same plan as a copy in run_dir/plan-history/, named by the time it was made.
#
# A plan is a preview: it commits no assignment and changes no queue outside its own copy.
# An incomplete processing run is still planned, but its plan is marked partial and lists every
# input without an outcome; use complete runs for evaluation. A task that an unresolved input may
# modify is planned as usual and marked provisional.
import json
from dataclasses import asdict
from datetime import date, datetime

from order_processing_into_tasks.processing_run import pipeline_complete, verified_tasks
from order_processing_into_tasks.settings_and_data import write_json
from order_processing_into_tasks.verify_tasks import possibly_affected_tasks
from task_allocation_to_workshops.allocation_settings_and_data import (
    DISPATCH_DATE, INITIAL_QUEUES, PLAN_OBJECTIVE, WORKSHOPS)
from task_allocation_to_workshops.rank_workshops import OBJECTIVE_ALIASES, OBJECTIVE_FIELDS
from task_allocation_to_workshops.recommend_one_task import recommend, task_deadline
from task_routing.route_verified_tasks import route_tasks


def plan_tasks(tasks, initial_queues, objective=None):
    """Build the tentative plan for the ready allocation tasks, earliest deadline first (EDD).

    tasks are the "allocate" tasks of route_tasks; objective None means each task's own preference.
    The plan is greedy: each recommendation reserves queue time that later tasks see. In chat order,
    a request that can wait could take the fast workshop an urgent request needs, so tasks are
    sorted by task_deadline. sorted() is stable, so equal deadlines keep chat order. Queues and
    pieces are working copies. Returns the planning order, the decisions, the workshop profiles and
    the queues before and after the plan.
    """
    # 1. Resolve an alternate objective spelling once, and stop at once on an unknown name
    #    instead of failing halfway through the plan.
    if objective is not None:
        objective = OBJECTIVE_ALIASES.get(objective, objective)
        if objective not in OBJECTIVE_FIELDS and objective != "hybrid":
            raise ValueError(f"Unknown PLAN_OBJECTIVE: {objective}")
    # 2. Work on a fresh copy of the queues, so repeated previews never change the starting queues
    #    and never reserve the same time twice.
    queues = dict(initial_queues)
    pieces_so_far = {}
    decisions = []
    planning_order = sorted(tasks, key=lambda task: task_deadline(task) or date.max)

    print(f"[Plan] {len(tasks)} ready allocation tasks; objective setting: {objective}")
    print("[Plan] Planning order, earliest deadline first: " + ", ".join(
        f"{task['task_id']} ({task_deadline(task) or 'no deadline'})" for task in planning_order))
    print("[Plan] Starting queues:", queues)
    # 3. Decide each task in planning order.
    for task in planning_order:
        decision = recommend(task, queues, pieces_so_far, objective)
        decisions.append(decision)

        # 4. Only a recommendation reserves time in this tentative plan. Transport uses no
        #    production capacity, so only production and rework are added.
        if decision["status"] == "recommendation":
            wid = decision["selected_workshop"]
            chosen = decision["selected_metrics"]
            added = chosen["processing_days"] + chosen["expected_rework_days"]
            print(f"  {task['task_id']}: recommendation {wid}; queue {queues[wid]:.2f} -> "
                  f"{queues[wid] + added:.2f} days")
            queues[wid] += added
            pieces_so_far[wid] = pieces_so_far.get(wid, 0) + decision["order_snapshot"]["pieces"]
        else:
            print(f"  {task['task_id']}: {decision['status']} (no queue time reserved)")
    print("[Plan] Final tentative queues:", queues)
    # Workshop profiles are saved once per plan, not inside every decision.
    return {"dispatch_date": DISPATCH_DATE.isoformat(), "objective_setting": objective,
            "planning_order": [task["task_id"] for task in planning_order],
            "workshop_profiles": {wid: {**asdict(w), "makes": sorted(w.makes)} for wid, w in WORKSHOPS.items()},
            "decisions": decisions, "queues_before_plan": dict(initial_queues), "queues_after_plan": queues}


def summary_row(row_id, order_id, outcome, reason, messages, option=None):
    """Return one row of the plan table. option is the metrics of the workshop the row names, if any."""
    option = option or {}
    return {"id": row_id, "order_id": order_id, "outcome": outcome,
            "workshop": option.get("workshop_id"), "delivery_days": option.get("eta_days"),
            "days_available": option.get("days_until_due"), "reason": reason, "messages": messages}


def summarize_plan(plan):
    """Return one row per task or message, sorted by chat line, and print them as a table.

    "id" is a task ID, an item ID (link review) or a message ID (intake review or non-task message);
    "messages" lists every chat message the row covers. The dispatcher sees every input once, with
    its outcome and reason. For a review, the workshop columns show the option named in its reason
    (the best option without the request, otherwise the closest late option). Empty fields are None
    in the file and "-" in the table.
    """
    rows = []
    for record in plan["decisions"] + plan["duplicate_order_reviews"]:
        option = record["selected_metrics"] or record["option_without_request"] or record["closest_option"]
        rows.append(summary_row(record["task_id"], record["order_id"], record["status"], record["reason"],
                                record["task"]["source_message_ids"], option))
    for task in plan["needs_clarification"]:
        # An unclear request can arrive with no recorded question; the row still says what to do.
        questions = "; ".join(task["doubts_to_clarify"] or task["missing_details"])
        fallback = f"Intent {task['intent']}; no question was recorded, so ask the requester."
        rows.append(summary_row(task["task_id"], task["order_id"], "needs_clarification",
                                questions or fallback, task["source_message_ids"]))
    for task in plan["reference_tasks"]:
        # The question is recorded for the dispatcher, not answered.
        reason = f"Information question; not an allocation, and not answered here: {task['description']}"
        rows.append(summary_row(task["task_id"], task["order_id"], "reference", reason, task["source_message_ids"]))
    for review in plan["intake_review"]:
        reason = f"Processing could not read this message reliably: {review['raw_text']}"
        rows.append(summary_row(review["message_id"], None, "intake_review", reason, [review["message_id"]]))
    # Processing task and link reviews never enter plan_tasks: their interpretations are not
    # trusted enough for allocation, so they have no selected workshop or queue reservation.
    for review in plan["task_review"]:
        rows.append(summary_row(review["task_id"], None, "processing_review", review["reason"],
                                review["source_message_ids"]))
    for review in plan["link_review"]:
        rows.append(summary_row(review["item_id"], None, "link_review", review["reason"], [review["message_id"]]))
    for message in plan["non_task_messages"]:
        # Messages in which processing found no request or question.
        reason = f"Processing found no request or question: {message['raw_text']}"
        rows.append(summary_row(message["message_id"], None, "non_task", reason, [message["message_id"]]))
    for record in plan["not_processed"]:
        # Only in a partial plan: inputs that processing never finished.
        rows.append(summary_row(record["id"], None, "not_processed", record["reason"], record["messages"]))
    # A planned task that an unresolved input may modify keeps its outcome, marked provisional; a
    # recommendation still reserves its queue time. Review and not_processed rows were never planned.
    for row in rows:
        warned_by = plan["review_warnings"].get(row["id"])
        if warned_by and row["outcome"] not in ("processing_review", "not_processed"):
            if row["outcome"] == "recommendation":
                row["outcome"] = "provisional_recommendation"
            row["reason"] += (f" Provisional: {', '.join(warned_by)} may modify this request. "
                              "Please confirm whether it applies; the result may need recalculation.")
    # Sort by chat line (L0001, L0002, ...) so the table reads in message order.
    rows.sort(key=lambda row: row["id"].removeprefix("T:"))

    print(f"\n{'ID':<11} {'Order':<8} {'Outcome':<26} {'Workshop':<8} {'Delivery':>8} {'Available':>9}  Messages")
    for row in rows:
        delivery = "-" if row["delivery_days"] is None else f"{row['delivery_days']:.2f}"
        available = "-" if row["days_available"] is None else row["days_available"]
        print(f"{row['id']:<11} {row['order_id'] or '-':<8} {row['outcome']:<26} "
              f"{row['workshop'] or '-':<8} {delivery:>8} {available:>9}  {', '.join(row['messages'])}")
        print(f"    {row['reason']}")
    return rows


def inputs_without_outcome(state, messages):
    """Return one record for each input that processing never finished, so a partial plan lists it.

    The three kinds follow pipeline_complete's checks: messages not yet read by extraction, items
    not yet in a task or a link review, and tasks with neither a current verification nor a current
    review. Each record keeps its own ID and the chat messages it covers, so message, item and task
    counts are never mixed. For a complete run the list is empty.
    """
    records = []
    processed = set(state["processed_message_ids"])
    for message in messages:
        if message["message_id"] not in processed:
            records.append({"id": message["message_id"], "kind": "message", "messages": [message["message_id"]],
                            "reason": f"Processing stopped before reading this message: {message['raw_text']}"})
    assigned = {item_id for task in state["tasks"].values() for item_id in task["item_ids"]}
    for item_id, item in state["items"].items():
        if item_id not in assigned and item_id not in state["unresolved_links"]:
            records.append({"id": item_id, "kind": "item", "messages": [item["message_id"]],
                            "reason": "Processing stopped before linking this item to a task."})
    for task in state["tasks"].values():
        review = state["task_review"].get(task["task_id"])
        verified = task["verified"] is not None and task["verified_version"] == task["version"]
        if not verified and not (review and review["version"] == task["version"]):
            message_ids = [state["items"][item_id]["message_id"] for item_id in task["item_ids"]]
            records.append({"id": task["task_id"], "kind": "task", "messages": list(dict.fromkeys(message_ids)),
                            "reason": "Processing stopped before verifying this task."})
    return records


def plan_allocation(run_dir, state, messages):
    """Route and plan the verified tasks of one processing run, then save the plan in run_dir.

    run_dir is the run's folder (a Path), state its processing state and messages its chat lines.
    Processing reviews and non-task messages are listed for the dispatcher as recorded; they never
    reach plan_tasks, so they reserve nothing. Returns the plan, saved as run_dir/plan.json, the file
    the pipeline reads (plan-<objective>.json when PLAN_OBJECTIVE is set, so an objective experiment
    never overwrites the default plan). The same plan is also saved in run_dir/plan-history/, so
    earlier plans stay available for comparison; the two files are written one after the other.

    An incomplete run is planned too, but the plan is partial: processing_complete is False and
    every input without an outcome gets a not_processed row. A missing task can change the
    duplicate-order check, the planning order and the queues, so a partial plan is a preview only.

    A task that an unresolved input may modify is planned as usual, and its row is marked
    provisional. plan["review_warnings"] keeps, for each such task, the rows that may modify it.
    """
    created_at = datetime.now()
    complete = pipeline_complete(state, messages)
    if not complete:
        print("[Plan] WARNING: processing is incomplete, so this plan is partial. Inputs without an "
              "outcome are listed as not_processed; use complete runs for evaluation.")
    tasks = verified_tasks(state)
    routes = route_tasks(tasks)
    print(f"[Route] {len(tasks)} verified tasks: " + ", ".join(
        f"{route} {len(records)}" for route, records in routes.items()))
    # created_at is when the plan was made; dispatch_date is the date it plans from.
    plan = {"created_at": created_at.isoformat(), "processing_complete": complete,
            **plan_tasks(routes["allocate"], INITIAL_QUEUES, PLAN_OBJECTIVE)}
    plan["duplicate_order_reviews"] = routes["duplicate_order"]
    plan["needs_clarification"] = routes["needs_clarification"]
    plan["reference_tasks"] = routes["reference"]
    texts = {message["message_id"]: message["raw_text"] for message in messages}
    plan["input_message_count"] = len(messages)
    plan["intake_review"] = state["intake_review"]
    plan["task_review"] = list(state["task_review"].values())
    plan["link_review"] = list(state["unresolved_links"].values())
    plan["non_task_messages"] = [{"message_id": message_id, "raw_text": texts[message_id]}
                                 for message_id in state["non_task_message_ids"]]
    plan["not_processed"] = inputs_without_outcome(state, messages)
    plan["review_warnings"] = possibly_affected_tasks(state)
    # One row per task or message, printed as a table and saved with the plan.
    plan["summary_rows"] = summarize_plan(plan)
    covered = {message_id for row in plan["summary_rows"] for message_id in row["messages"]}
    print(f"\n[Plan] Chat messages covered by the table: {len(covered)} of {len(messages)}")
    if not complete:
        print(f"[Plan] WARNING: partial plan; {len(plan['not_processed'])} inputs have no processing outcome.")
    if plan["objective_setting"] is None:
        file_name = "plan.json"
    else:
        file_name = f"plan-{plan['objective_setting']}.json"
    # The copy's name starts with the creation time, to the microsecond, so a later plan (even in the
    # same second) never overwrites it, and the copies sort in the order they were made.
    history_file = run_dir / "plan-history" / f"{created_at:%Y-%m-%d_%H-%M-%S_%f}_{file_name}"
    history_file.parent.mkdir(exist_ok=True)
    write_json(history_file, plan)
    plan_file = run_dir / file_name
    write_json(plan_file, plan)
    print(f"[Plan] Saved: {plan_file}; copy: {history_file.relative_to(run_dir)}")
    return plan


def plan_saved_run(run_dir):
    """Plan a saved processing run folder (output/runs/<start time>/) with plan_allocation.

    Reads the messages from run_dir/manifest.json and the processing state from run_dir/state.json,
    and never changes either file. Returns the plan; an incomplete run gives a partial plan.
    """
    messages = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))["messages"]
    state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    return plan_allocation(run_dir, state, messages)
