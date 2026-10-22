# dispatcher_plan.py: the dispatcher's review of one run. Apply the dispatcher's decisions to copies of
# the verified tasks, route and plan them as allocation does, and list every input with its outcome.
#
# Review flow: pipeline_graph.plan_allocation and dispatcher_decisions.apply_answer ->
#              [build_dispatcher_plan] -> derive_task, route_tasks, flexible_decision (recommend) ->
#              summarize_plan. pipeline_graph.save_review -> [finalize_review].
# Came from:   notebook 06, Part 8a. Changed on purpose (20 October 2026): the dispatcher approves the
#              whole shown review once, so there is no per-row approval and no approved-first planning.
#              finalize_review labels the shown review instead of planning again. input_signature is
#              new. The dispatcher decides (later on 20 October): a workshop the dispatcher chose is
#              fixed first and always used, even when it is late, the deadline has passed or it breaks
#              a hard rule, and the other ready tasks are planned around it, earliest deadline first as
#              in plan.json. added_task is new (22 October 2026): a batch the dispatcher added is
#              planned like any other batch, with a row of its own.
# Reads:       the run folder's manifest.json and state.json, orders.csv and workshops.csv.
# Writes:      nothing. A review is a preview: it commits no assignment and changes no queue outside
#              its own copy. No model is called.
import contextlib
import copy
import hashlib
import io
import json
from datetime import date, datetime

from order_processing_into_tasks.processing_run import pipeline_complete, verified_tasks
from order_processing_into_tasks.settings_and_data import DATA_DIR
from order_processing_into_tasks.verify_tasks import possibly_affected_tasks
from task_allocation_to_workshops.allocation_plan import inputs_without_outcome, summarize_plan
from task_allocation_to_workshops.allocation_settings_and_data import (
    DISPATCH_DATE, INITIAL_QUEUES, ORDERS, WORKSHOPS)
from task_allocation_to_workshops.recommend_one_task import batch_pieces, recommend, task_deadline
from task_allocation_to_workshops.workshop_rules_and_estimates import candidate_metrics, rejection_reason
from task_routing.route_verified_tasks import route_task, route_tasks

# The facts a dispatcher may correct, with their allowed values (None: checked on their own). A
# quantity is a whole number of pieces; without one, orders.csv gives the order's quantity. Only the
# dispatcher may replace that quantity, never processing (decision of 22 October 2026).
CORRECTABLE = {"order_id": None, "due_date": None, "quantity": None,
               "preference": {"none", "fastest", "cheapest", "quality"}, "intent": {"allocation", "question"}}
# The outcomes that reserve queue time.
RESERVING = ("recommendation", "dispatcher_choice", "accepted_late")


def blockers(task):
    """Return a task's blockers in one list: missing facts, open questions and unsupported conditions.

    The review numbers them, and correct resolves them by number.
    """
    return task["missing_details"] + task["doubts_to_clarify"] + task["unhandled_constraints"]


def derive_task(task, entry):
    """Apply one decision entry to a verified task, on a copy; return (task, problems).

    Corrected facts make a new version, the source version plus the entry's decision_version, so
    replaying the same decisions always gives the same version. Only the blockers the dispatcher named
    are removed, and readiness then follows verification's own rule. An entry with any problem is not
    applied, and the row says why.
    """
    facts = entry.get("facts", {})
    resolved = entry.get("resolves", [])
    problems = [f"{name} cannot be corrected here" for name in facts if name not in CORRECTABLE]
    problems += [f"{facts[name]!r} is not a valid {name}" for name in ("preference", "intent")
                 if name in facts and facts[name] not in CORRECTABLE[name]]
    if "order_id" in facts and facts["order_id"] not in ORDERS:
        problems.append(f"{facts['order_id']} is not in orders.csv")
    if "due_date" in facts:
        try:
            date.fromisoformat(facts["due_date"])
        except ValueError:
            problems.append(f"{facts['due_date']!r} is not a date written YYYY-MM-DD")
    if "quantity" in facts and not (facts["quantity"].isdecimal() and int(facts["quantity"]) > 0):
        problems.append(f"{facts['quantity']!r} is not a whole number of pieces above 0")
    problems += [f"not a blocker of this task: {text}" for text in resolved if text not in blockers(task)]
    if entry.get("workshop") is not None and entry["workshop"] not in WORKSHOPS:
        problems.append(f"{entry['workshop']} is not a workshop")
    if entry and entry["source_version"] != task["version"]:
        problems.append(f"the decision is for version {entry['source_version']}, the task is version {task['version']}")
    task = copy.deepcopy(task)
    if problems or not (facts or resolved):
        return task, problems
    # What processing recorded stays on record next to what the dispatcher supplied.
    deadline = task_deadline(task)
    # Processing records no quantity, so its recorded value is None: orders.csv applied.
    task["dispatcher"] = {"facts": facts, "resolved": resolved, "recorded": {name: task.get(name) for name in facts},
                          "recorded_deadline": deadline.isoformat() if deadline else None}
    task.update(facts)
    if "quantity" in facts:
        task["quantity"] = int(facts["quantity"])
    if facts:
        task["version"] += entry["decision_version"]
    for field in ("missing_details", "doubts_to_clarify", "unhandled_constraints"):
        task[field] = [text for text in task[field] if text not in resolved]
    task["information_sufficient"] = (task["intent"] == "allocation" and task["order_id"] in ORDERS
                                      and not task["missing_details"] and not task["doubts_to_clarify"])
    return task, problems


def added_task(task_id):
    """Return the starting record of a batch the dispatcher added: an allocation with no order, no
    chat message and version 0, marked "added". derive_task then applies the dispatcher's facts, so
    they are checked exactly as a correction is.
    """
    return {"task_id": task_id, "version": 0, "added": True, "description": "Added by the dispatcher",
            "source_message_ids": [], "intent": "allocation", "order_id": None, "due_date": None, "urgency_phrase": None,
            "deadline_phrase": None, "preference": "none", "requested_workshop": None, "excluded_workshops": [],
            "workshop_rules": [], "wants_split": False, "missing_details": [], "doubts_to_clarify": [],
            "unhandled_constraints": [], "information_sufficient": False}


def batch_of(task):
    """Return the batch of a ready task, built exactly as recommend builds it."""
    order = ORDERS[task["order_id"]]
    return {"order_id": task["order_id"], "category": order["category"], "pieces": batch_pieces(task),
            "sent_date": DISPATCH_DATE, "due_date": task_deadline(task)}


def named_option(task, workshop_id, queues, pieces):
    """Estimate one workshop that the dispatcher named, under the working queues.

    Returns (metrics, broken_rule): the dispatcher decides, so the choice is always estimated, and
    broken_rule is the hard rule or request exclusion it overrides, or None. A requested workshop does
    not restrict the choice either: naming another one is a recorded dispatcher override.
    """
    batch = batch_of(task)
    workshop = WORKSHOPS[workshop_id]
    broken_rule = rejection_reason(workshop, batch, task["excluded_workshops"])
    total = sum(pieces.values()) + batch["pieces"]
    return candidate_metrics(workshop, batch, queues[workshop_id], pieces.get(workshop_id, 0), total), broken_rule


def option_text(option):
    """Return one line describing a workshop option, in the words of the allocator's reasons."""
    text = (f"{option['workshop_id']} ({option['name']}), delivery in {option['eta_days']:.2f} of "
            f"{option['days_until_due']} available days, cost {option['cost']}")
    if option["tardiness_days"] > 0:
        text += f", {option['tardiness_days']:.2f} days late"
    return text


def reserve(decision, queues, pieces, reserved):
    """Reserve one allocation in the working queues and piece counts: its production and expected
    rework, once, as plan_tasks does. A review outcome reserves nothing.
    """
    if decision["status"] not in RESERVING:
        return
    workshop_id, chosen = decision["selected_workshop"], decision["selected_metrics"]
    queues[workshop_id] += chosen["processing_days"] + chosen["expected_rework_days"]
    pieces[workshop_id] = pieces.get(workshop_id, 0) + batch_pieces(decision["task"])
    reserved.append(decision["task_id"])


def flexible_decision(task, entry, queues, pieces):
    """Decide one ready task.

    With no dispatcher choice this is the allocator's own recommend. A workshop the dispatcher chose is
    always used: choosing a late workshop accepts its lateness, also for a past deadline, and a broken
    hard rule is written in the reason. The allocator's late option is used only when the dispatcher
    accepted lateness for that workshop and task version, up to the accepted days; otherwise the task
    stays in review and shows the late option.
    """
    decision = recommend(task, queues, pieces)
    # recommend stops before any estimate for an unsupported request or a past deadline; only the past
    # deadline can take the dispatcher's choice.
    can_choose = "order_snapshot" in decision or decision["status"] == "deadline_passed"
    if entry.get("workshop") and can_choose:
        option, broken_rule = named_option(task, entry["workshop"], queues, pieces)
        status = "dispatcher_choice"
    elif entry.get("accept_late") and decision["closest_option"]:
        option, status, broken_rule = decision["closest_option"], "accepted_late", None
    else:
        return decision
    accepted = entry.get("accept_late")
    covered = (accepted is not None and accepted["workshop"] == option["workshop_id"]
               and accepted["version"] == task["version"] and option["tardiness_days"] <= accepted["days"])
    if option["tardiness_days"] > 0 and not covered and status != "dispatcher_choice":
        reason = f"Late: {option_text(option)}. Accept this lateness explicitly to use it"
        if accepted is not None:
            reason += (f"; the accepted lateness ({accepted['workshop']}, version {accepted['version']}, "
                       f"up to {accepted['days']:.2f} days) does not cover it")
        decision.update(status="review_required", selected_workshop=None, selected_metrics=None,
                        alternatives=[], late_option=option, reason=reason + ".")
        return decision
    if option["tardiness_days"] > 0:
        status = "accepted_late"
        reason = (f"Lateness accepted by the dispatcher: {option_text(option)}. The deadline "
                  f"{task_deadline(task)} stays on record.")
    else:
        reason = f"Dispatcher's choice: {option_text(option)}."
    if task["requested_workshop"] not in (None, option["workshop_id"]):
        reason += f" It overrides the requested {task['requested_workshop']}."
    if broken_rule:
        reason += f" It overrides the hard rule {broken_rule}."
    decision.update(status=status, selected_workshop=option["workshop_id"], selected_metrics=option,
                    alternatives=[], reason=reason)
    return decision


def input_signature():
    """Return a SHA-256 of orders.csv, workshops.csv and the dispatch date.

    Every review of one run must use the same inputs: a review records this signature, and
    dispatcher_decisions.apply_answer refuses an answer when it no longer matches.
    """
    digest = hashlib.sha256(DISPATCH_DATE.isoformat().encode())
    for name in ("orders.csv", "workshops.csv"):
        digest.update((DATA_DIR / name).read_bytes())
    return digest.hexdigest()


def build_dispatcher_plan(run_folder, decisions):
    """Calculate the dispatcher's draft review of one saved run, from its source files and the
    current decisions, and return it; nothing is saved here.

    From the original queues, the tasks with a workshop the dispatcher chose are planned first, then
    every other ready task around them, each group earliest deadline first, so reviewing again never
    reserves the same work twice. Every input keeps exactly one row, as in plan.json, and every batch
    the dispatcher added has one more. Nothing is final in a draft: finalize_review approves the review
    the dispatcher saw.
    """
    manifest = json.loads((run_folder / "manifest.json").read_text(encoding="utf-8"))
    state = json.loads((run_folder / "state.json").read_text(encoding="utf-8"))
    messages, entries = manifest["messages"], decisions["decisions"]
    # 1. Apply the decisions to the verified tasks, then route them as allocation does.
    tasks, problems = [], {}
    for task in verified_tasks(state):
        task, issues = derive_task(task, entries.get(task["task_id"], {}))
        tasks.append(task)
        if issues:
            problems[task["task_id"]] = issues
    routes = route_tasks(tasks)
    # A batch the dispatcher added is routed on its own: it skips the duplicate-order check and never
    # sends another request for its order to review (22 October 2026).
    for task_id, entry in entries.items():
        if entry.get("added"):
            task, issues = derive_task(added_task(task_id), entry)
            routes[route_task(task)].append(task)
            if issues:
                problems[task_id] = issues
    usable ={task_id: entry for task_id, entry in entries.items() if task_id not in problems}
    chosen = {task_id for task_id, entry in usable.items() if entry.get("workshop")}
    # A request the dispatcher placed (a chosen workshop) or completed is a batch of its own, so it skips
    # the duplicate-order check; the other requests for that order stay in review (22 October 2026).
    decided = chosen | {task_id for task_id, entry in usable.items() if entry.get("complete")}
    routes["allocate"] += [review["task"] for review in routes["duplicate_order"] if review["task_id"] in decided]
    routes["duplicate_order"] = [review for review in routes["duplicate_order"] if review["task_id"] not in decided]
    planning_order = sorted(routes["allocate"],
                            key=lambda task: (task["task_id"] not in chosen, task_deadline(task) or date.max))

    # 2. From the original queues, the dispatcher's chosen workshops first, then the other ready tasks
    #    around them, each group earliest deadline first. Each allocation adds its production and
    #    rework once.
    queues, pieces, made, reserved = dict(INITIAL_QUEUES), {}, [], []
    for task in planning_order:
        made.append(flexible_decision(task, usable.get(task["task_id"], {}), queues, pieces))
        reserve(made[-1], queues, pieces, reserved)

    # 3. The same records and summary rows as plan.json. A checked warning no longer makes a row provisional.
    warnings = {}
    for task_id, row_ids in possibly_affected_tasks(state).items():
        unchecked = [row_id for row_id in row_ids if row_id not in usable.get(task_id, {}).get("warnings_checked", [])]
        if unchecked:
            warnings[task_id] = unchecked
    texts = {message["message_id"]: message["raw_text"] for message in messages}
    result = {"source_run": run_folder.name, "dispatch_date": DISPATCH_DATE.isoformat(),
              "input_signature": input_signature(), "created_at": datetime.now().isoformat(), "status": "draft",
              "processing_complete": pipeline_complete(state, messages),
              "dispatcher_entries": copy.deepcopy(entries), "decision_problems": problems,
              "planning_order": [task["task_id"] for task in planning_order], "decisions": made,
              "duplicate_order_reviews": routes["duplicate_order"],
              "needs_clarification": routes["needs_clarification"], "reference_tasks": routes["reference"],
              "intake_review": state["intake_review"], "task_review": list(state["task_review"].values()),
              "link_review": list(state["unresolved_links"].values()),
              "non_task_messages": [{"message_id": message_id, "raw_text": texts[message_id]}
                                    for message_id in state["non_task_message_ids"]],
              "not_processed": inputs_without_outcome(state, messages), "review_warnings": warnings,
              "queues_before_plan": dict(INITIAL_QUEUES), "queues_after_plan": queues,
              "pieces_after_plan": pieces, "reservation_order": reserved}
    with contextlib.redirect_stdout(io.StringIO()):  # summarize_plan also prints its own table
        result["summary_rows"] = summarize_plan(result)

    # 4. Label each batch the dispatcher added, naming the other planned batches of its order, and show
    #    each decision that was not applied. Every row is unresolved until finalize_review.
    planned = {}
    for decision in made:
        if decision["status"] in RESERVING:
            planned.setdefault(decision["order_id"], []).append(decision["task_id"])
    for row in result["summary_rows"]:
        if entries.get(row["id"], {}).get("added"):
            others = [task_id for task_id in planned.get(row["order_id"], []) if task_id != row["id"]]
            also = f" Other planned batches of {row['order_id']}: {', '.join(others)}." if others else ""
            row["reason"] = f"Added by the dispatcher.{also} {row['reason']}"
        if row["id"] in problems:
            row["reason"] += f" Dispatcher decision not applied: {'; '.join(problems[row['id']])}."
        row["final"] = False
    result["final_ids"] = []
    result["unresolved_ids"] = [row["id"] for row in result["summary_rows"] if row["outcome"] != "non_task"]
    return result


def finalize_review(review):
    """Return a copy of a draft review with the dispatcher's one final approval applied.

    Every allocation row (a recommendation, a dispatcher's choice or accepted lateness) without an
    unchecked warning becomes "approved" and final, in its row and its decision record. Every other row
    stays unresolved. Nothing is planned again, so every workshop, number and queue stays as shown;
    the review passed in is not changed.
    """
    final = copy.deepcopy(review)
    final["status"] = "final"
    approved = {row["id"] for row in final["summary_rows"]
                if row["outcome"] in RESERVING and row["id"] not in final["review_warnings"]}
    for decision in final["decisions"]:
        if decision["task_id"] in approved:
            decision["status"] = "approved"
    for row in final["summary_rows"]:
        row["final"] = row["id"] in approved
        if row["final"]:
            row["outcome"] = "approved"
    final["final_ids"] = [row["id"] for row in final["summary_rows"] if row["final"]]
    final["unresolved_ids"] = [row["id"] for row in final["summary_rows"]
                               if not row["final"] and row["outcome"] != "non_task"]
    return final
