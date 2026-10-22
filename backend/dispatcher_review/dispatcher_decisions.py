# dispatcher_decisions.py: the dispatcher's answer to a paused review. Check the answer, apply it to a
# copy of the decisions and calculate the review again; print a review; save the approved result.
#
# Review flow: pipeline_graph.dispatcher_review -> [apply_answer] -> correct, complete, add_batch,
#              choose_workshop, accept_late, warnings_checked or clear -> dispatcher_plan.build_dispatcher_plan.
#              pipeline_graph.save_review -> dispatcher_plan.finalize_review -> [save_dispatcher_files].
# Review again: fastapi_routes/runs.py -> [review_saved_plan] -> [apply_answer] on the saved plan.
# Came from:   notebook 06, Part 8b (show: Part 4a; PRINT_WIDTH: Part 1). The helpers take the
#              decisions and the run's tasks as arguments instead of the notebook's globals, and every
#              refusal is a ValueError. approve and release are gone: the dispatcher approves the whole
#              shown review once. verified_tasks_by_id, complete, add_batch, answer_problem, valid_field,
#              apply_decision, apply_answer, changed_rows and review_saved_plan are new.
# Reads:       the run folder's state.json (verified_tasks_by_id); review_saved_plan also reads the
#              saved dispatcher-decisions.json and dispatcher-plan.json.
# Writes:      only save_dispatcher_files: dispatcher-decisions.json and dispatcher-plan.json in the run
#              folder, each with a copy in plan-history/.
#
# An answer, the decisions and a review are plain JSON data. A refused answer changes nothing. No model
# is called.
import copy
import json
import math
import textwrap
from collections import Counter
from datetime import datetime

from dispatcher_review.dispatcher_plan import (
    added_task, blockers, build_dispatcher_plan, finalize_review, input_signature)
from order_processing_into_tasks.processing_run import verified_tasks
from order_processing_into_tasks.settings_and_data import write_json

# The width of a printed detail line.
PRINT_WIDTH = 120
# The fields each decision of an answer takes besides "decision" and "task_id". Each decision is named
# after the helper it calls. add_batch takes no task_id: Python names the added batch.
DECISION_FIELDS = {"correct": ["facts", "resolves"], "complete": ["facts"], "add_batch": ["facts", "workshop_id"],
                   "choose_workshop": ["workshop_id"], "accept_late": ["max_days"], "warnings_checked": ["row_ids"],
                   "clear": []}
# The fields each decision must give; the others are optional.
REQUIRED_FIELDS = {"choose_workshop": ["workshop_id"], "warnings_checked": ["row_ids"]}
# What each field must be, as a refusal states it.
FIELD_FORMS = {"facts": 'an object of text values, such as {"due_date": "2026-04-20"}',
               "resolves": "a list of blocker numbers, such as [0, 1]",
               "workshop_id": 'a workshop ID, such as "W1"',
               "max_days": "a number of days, 0 or more",
               "row_ids": 'a list of row IDs, such as ["L0019"]'}
# The refusal when the order or workshop data, or the dispatch date, changed while the review was paused.
CHANGED_INPUTS = ("orders.csv, workshops.csv or the dispatch date changed after this review was calculated, "
                  "so its numbers no longer hold. Restore them, or process the chat again as a new run.")
# The fields that mark a summary row as changed between two reviews (print_review's rule).
CHANGE_MARKERS = ("outcome", "workshop", "delivery_days")


def verified_tasks_by_id(run_dir):
    """Return this run's verified tasks by task ID: their versions, which decisions refer to, and their
    blockers, numbered for correct.
    """
    state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    return {task["task_id"]: task for task in verified_tasks(state)}


def entry_for(decisions, tasks, task_id):
    """Return the decision entry of one task, created on first use with the task's version in this run."""
    if task_id not in tasks:
        raise ValueError(f"{task_id} is not a verified task of run {decisions['source_run']}.")
    entry = decisions["decisions"].setdefault(task_id, {"source_version": tasks[task_id]["version"]})
    return entry, tasks[task_id]


def correct(decisions, tasks, task_id, facts, resolves):
    """Correct facts, and resolve blockers by their numbers in the review.

    New facts count as a new decision version; the same facts again change nothing. The blocker numbers
    are checked first, so a wrong number raises before anything is recorded.
    """
    entry, task = entry_for(decisions, tasks, task_id)
    numbered = blockers(task)
    for number in resolves:
        if not 0 <= number < len(numbered):
            raise ValueError(f"{task_id} has no blocker [{number}]; it has {len(numbered)} blockers, numbered from 0.")
    chosen = [numbered[number] for number in resolves]
    merged = {**entry.get("facts", {}), **facts}
    if merged != entry.get("facts", {}):
        entry["facts"] = merged
        entry["decision_version"] = entry.get("decision_version", 0) + 1
    entry["resolves"] = list(dict.fromkeys(entry.get("resolves", []) + chosen))


def complete(decisions, tasks, task_id, facts):
    """Complete a request: correct its facts and plan it as an allocation, with every blocker resolved.

    The dispatcher supplies what Python needs to place the batch without the model: the order, here or
    already on the task, and optionally a deadline (otherwise the order's due date in orders.csv) and a
    preference. The order is required, so a request without one is refused. A completed request is a
    batch of its own, so it skips the duplicate-order check.
    """
    entry, task = entry_for(decisions, tasks, task_id)
    # The request as the dispatcher's earlier, saved corrections left it (Review again).
    corrected = {**task, **entry.get("facts", {})}
    if not (facts.get("order_id") or corrected["order_id"]):
        raise ValueError(f"complete {task_id}: give the order ID.")
    # A completed request is always an allocation, whatever intent the form also sent.
    facts = {name: value for name, value in facts.items() if name != "intent"}
    if corrected["intent"] != "allocation":
        facts["intent"] = "allocation"
    correct(decisions, tasks, task_id, facts, list(range(len(blockers(task)))))
    entry["complete"] = True


def add_batch(decisions, facts, workshop_id=None):
    """Add a batch that no row covers: one part of a split, a request processing missed, or a message
    that never became a task. Returns its ID, ADD-1, ADD-2 and so on, after the batches already added.

    The dispatcher gives the order (required) and optionally a quantity, a deadline, a preference and
    a workshop; a fact left out is the order's own in orders.csv. build_dispatcher_plan checks the facts
    as it checks a correction and plans the batch like any other. Another batch of the same order
    blocks nothing, because the dispatcher decides.
    """
    if not facts.get("order_id"):
        raise ValueError("add_batch: give the order ID.")
    entries = decisions["decisions"]
    numbers = [int(task_id.removeprefix("ADD-")) for task_id, entry in entries.items() if entry.get("added")]
    task_id = f"ADD-{max(numbers, default=0) + 1}"
    entries[task_id] = {"source_version": 0, "added": True, "facts": facts, "decision_version": 1}
    if workshop_id:
        entries[task_id]["workshop"] = workshop_id
    return task_id


def choose_workshop(decisions, tasks, task_id, workshop_id):
    """Send a task to a workshop the dispatcher chose (an override, checked by the hard rules).

    A later choice for the same task replaces the earlier one.
    """
    entry, _ = entry_for(decisions, tasks, task_id)
    entry["workshop"] = workshop_id


def accept_late(decisions, tasks, review, task_id, max_days=None):
    """Accept the lateness of the late option shown for a task in one review: that workshop, that task
    version, and at most that lateness (or max_days, if given).
    """
    records = {decision["task_id"]: decision for decision in review["decisions"]}
    if task_id not in records:
        raise ValueError(f"{task_id} has no allocation record in this review.")
    record = records[task_id]
    option = record.get("late_option") or record["closest_option"]
    if option is None:
        raise ValueError(f"{task_id} has no late option in this review.")
    entry, _ = entry_for(decisions, tasks, task_id)
    entry["accept_late"] = {"workshop": option["workshop_id"], "version": record["version"],
                            "days": option["tardiness_days"] if max_days is None else max_days}


def warnings_checked(decisions, tasks, task_id, row_ids):
    """Confirm that unresolved rows (such as "L0019") do not change this task, so it is no longer provisional."""
    entry, _ = entry_for(decisions, tasks, task_id)
    entry["warnings_checked"] = sorted(set(entry.get("warnings_checked", [])) | set(row_ids))


def clear(decisions, task_id):
    """Undo: remove a task's whole decision entry."""
    decisions["decisions"].pop(task_id, None)


def valid_field(field, value):
    """Return True when a field of an answer's decision has the form its helper expects (FIELD_FORMS)."""
    if field == "facts":
        return isinstance(value, dict) and all(isinstance(text, str) for text in value.values())
    if field in ("resolves", "row_ids"):
        item_type = int if field == "resolves" else str
        return isinstance(value, list) and all(type(item) is item_type for item in value)
    if field == "max_days":
        return type(value) in (int, float) and math.isfinite(value) and value >= 0
    return isinstance(value, str)


def answer_problem(answer, tasks):
    """Return why an answer is refused before anything is applied, or None when its form is valid.

    An answer is {"decisions": [...], "then": "review_again", "approve_all" or "finalize"}. Approve all
    takes no decisions. With review_again, accepted lateness comes alone, because any other decision can
    change the estimate it accepts; finalize checks that estimate after the whole batch instead. The
    values themselves (facts, workshop IDs) are checked when the review is calculated.
    """
    if not isinstance(answer, dict) or set(answer) != {"decisions", "then"}:
        return 'An answer must be {"decisions": [...], "then": "review_again", "approve_all" or "finalize"}.'
    if answer["then"] not in ("review_again", "approve_all", "finalize"):
        return f'"then" must be "review_again", "approve_all" or "finalize", not {answer["then"]!r}.'
    entries = answer["decisions"]
    if not isinstance(entries, list) or not all(isinstance(entry, dict) for entry in entries):
        return '"decisions" must be a list of decisions, each written as {"decision": ..., "task_id": ...}.'
    if answer["then"] == "approve_all" and entries:
        return "Approve all takes no decisions: send them with review_again, check the new review, then approve."
    if (answer["then"] == "review_again" and len(entries) > 1
            and any(entry.get("decision") == "accept_late" for entry in entries)):
        return "Send accept_late alone: other decisions can change the lateness it accepts."
    for entry in entries:
        name, task_id = entry.get("decision"), entry.get("task_id")
        if not isinstance(name, str) or name not in DECISION_FIELDS:
            return f"Unknown decision {name!r}: use {', '.join(DECISION_FIELDS)}."
        if name == "add_batch":
            if "task_id" in entry:
                return "add_batch: Python names the added batch, so give no task_id."
        elif not isinstance(task_id, str) or task_id not in tasks:
            return f"{name}: {task_id!r} is not a verified task or added batch of this run."
        label = name if name == "add_batch" else f"{name} {task_id}"
        fields = DECISION_FIELDS[name]
        unknown = sorted(set(entry) - {"decision", "task_id"} - set(fields))
        if unknown:
            return f"{label}: unknown field {', '.join(unknown)}; it takes {', '.join(fields) or 'no other field'}."
        for field in fields:
            if field in REQUIRED_FIELDS.get(name, []) and field not in entry:
                return f"{label}: {field} is missing."
            if field in entry and not valid_field(field, entry[field]):
                return f"{label}: {field} must be {FIELD_FORMS[field]}."
    return None


def apply_decision(decisions, tasks, review, entry):
    """Apply one decision of an answer with the helper it names."""
    name, task_id = entry["decision"], entry.get("task_id")
    if name == "correct":
        correct(decisions, tasks, task_id, entry.get("facts", {}), entry.get("resolves", []))
    elif name == "complete":
        complete(decisions, tasks, task_id, entry.get("facts", {}))
    elif name == "add_batch":
        add_batch(decisions, entry.get("facts", {}), entry.get("workshop_id"))
    elif name == "choose_workshop":
        choose_workshop(decisions, tasks, task_id, entry["workshop_id"])
    elif name == "accept_late":
        accept_late(decisions, tasks, review, task_id, entry.get("max_days"))
    elif name == "warnings_checked":
        warnings_checked(decisions, tasks, task_id, entry["row_ids"])
    else:
        clear(decisions, task_id)


def apply_answer(run_dir, decisions, review, answer):
    """Apply the dispatcher's answer to the review they were shown. Returns (decisions, review, then, refusal).

    1. Refuse the answer if the order or workshop data or the dispatch date changed since the review.
    2. Check the answer's form (answer_problem).
    3. "approve_all" approves the shown review as it is: nothing is calculated again.
    4. Otherwise apply every decision to a copy of the decisions and calculate the review again. A
       decision the review cannot apply (decision_problems) refuses the whole answer.
    5. "finalize" then goes on to approval with the new review, whose "changes" lists the rows that
       differ from the shown one (changed_rows). Accepted lateness that the rest of the batch made
       longer than accepted refuses the whole answer, so no accepted task silently stays in review.
    A refused answer returns the decisions and review unchanged, "review_again" and the reason; an
    accepted one returns the new decisions and review, its next step ("approve_all" after finalize)
    and None.
    """
    if review["input_signature"] != input_signature():
        return decisions, review, "review_again", CHANGED_INPUTS
    tasks = verified_tasks_by_id(run_dir)
    # A batch the dispatcher added earlier can be named too, to change or remove it (Review again).
    tasks.update({task_id: added_task(task_id) for task_id, entry in decisions["decisions"].items()
                  if entry.get("added")})
    refusal = answer_problem(answer, tasks)
    if refusal is not None:
        return decisions, review, "review_again", refusal
    if answer["then"] == "approve_all":
        return decisions, review, "approve_all", None
    proposed = copy.deepcopy(decisions)
    try:
        for entry in answer["decisions"]:
            apply_decision(proposed, tasks, review, entry)
    except ValueError as error:
        return decisions, review, "review_again", str(error)
    new_review = build_dispatcher_plan(run_dir, proposed)
    if new_review["decision_problems"]:
        problems = "; ".join(f"{task_id}: {', '.join(issues)}"
                             for task_id, issues in new_review["decision_problems"].items())
        return decisions, review, "review_again", f"Not applied: {problems}."
    if answer["then"] == "review_again":
        return proposed, new_review, "review_again", None
    late_ids = {entry["task_id"] for entry in answer["decisions"] if entry["decision"] == "accept_late"}
    uncovered = [record for record in new_review["decisions"]
                 if record["task_id"] in late_ids and record["status"] == "review_required"]
    if uncovered:
        reasons = "; ".join(f"{record['task_id']}: {record['reason']}" for record in uncovered)
        return decisions, review, "review_again", f"Not applied: {reasons}"
    new_review["changes"] = changed_rows(review, new_review)
    return proposed, new_review, "approve_all", None


def changed_rows(before, after):
    """Return the rows of review after whose outcome, workshop or delivery estimate differ from review
    before, in after's order, each with both versions and their reasons. A batch the dispatcher added
    has no earlier row, so its "before" is None; an added batch the dispatcher removed (Review again)
    has no later row, so its "after" is None, and it comes last.
    """
    fields = (*CHANGE_MARKERS, "reason")
    earlier = {row["id"]: row for row in before["summary_rows"]}
    later = {row["id"] for row in after["summary_rows"]}
    changes = []
    for row in after["summary_rows"]:
        old = earlier.get(row["id"])
        if old is None or any(old[field] != row[field] for field in CHANGE_MARKERS):
            changes.append({"id": row["id"], "order_id": row["order_id"],
                            "before": None if old is None else {field: old[field] for field in fields},
                            "after": {field: row[field] for field in fields}})
    changes += [{"id": row["id"], "order_id": row["order_id"], "before": {field: row[field] for field in fields},
                 "after": None} for row in before["summary_rows"] if row["id"] not in later]
    return changes


def review_saved_plan(run_dir, new_decisions):
    """Apply new choices to a run's approved plan (Review again). Returns (decisions, draft, refusal).

    It starts from the saved dispatcher-decisions.json, so every earlier choice stays, and it plans
    once from the original queues, as finalize does, so nothing is reserved twice. Python may move any
    row the dispatcher did not choose a workshop for (decision of 22 October 2026). The draft's
    "changes" lists the rows that approval would change compared with the saved dispatcher-plan.json:
    the saved rows are approved, so the draft is compared as finalize_review would label it. A refused
    set returns the saved decisions and plan unchanged, with the reason.
    """
    saved_decisions = json.loads((run_dir / "dispatcher-decisions.json").read_text(encoding="utf-8"))
    saved_plan = json.loads((run_dir / "dispatcher-plan.json").read_text(encoding="utf-8"))
    decisions, draft, _, refusal = apply_answer(run_dir, saved_decisions, saved_plan,
                                                {"decisions": new_decisions, "then": "finalize"})
    if refusal is None:
        draft["changes"] = changed_rows(saved_plan, finalize_review(draft))
    return decisions, draft, refusal


def open_blockers(tasks, result, row_id):
    """Return the open blockers of one row of a review, each with its number in the source task (the
    number correct takes). Only a task that needs clarification lists them.
    """
    for task in result["needs_clarification"]:
        if task["task_id"] == row_id:
            return [(number, text) for number, text in enumerate(blockers(tasks[row_id]))
                    if text in blockers(task)]
    return []


def show(label, text):
    """Print one labelled detail line, wrapped to PRINT_WIDTH, with later lines indented under the text.

    A multi-line text keeps its own line breaks.
    """
    prefix = f"    {label:<14}"
    lines = [line for line in str(text).splitlines() if line.strip()]
    for number, line in enumerate(lines):
        first = prefix if number == 0 else " " * len(prefix)
        print(textwrap.fill(line, PRINT_WIDTH, initial_indent=first, subsequent_indent=" " * len(prefix)))


def print_review(result, tasks, before=None):
    """Print a review: the counts, the queues, then one line per row.

    Rows that still need the dispatcher show their reason, and open blockers are numbered for correct.
    With before (an earlier review), a row whose outcome, workshop or delivery estimate changed is marked.
    """
    earlier = {row["id"]: row for row in before["summary_rows"]} if before else {}
    counts = Counter(row["outcome"] for row in result["summary_rows"])
    print(f"{result['status'].upper()} plan of run {result['source_run']}, dispatch date {result['dispatch_date']}: "
          + ", ".join(f"{count} {outcome}" for outcome, count in sorted(counts.items())))
    print("Queue days per workshop: start -> after the plan")
    for workshop_id, start in result["queues_before_plan"].items():
        print(f"  {workshop_id}: {start:.2f} -> {result['queues_after_plan'][workshop_id]:.2f}")
    print(f"\n{'ID':<12}{'Order':<9}{'Outcome':<27}{'Workshop':<9}{'Delivery':>8}")
    for row in result["summary_rows"]:
        if row["outcome"] == "non_task":
            continue
        delivery = "-" if row["delivery_days"] is None else f"{row['delivery_days']:.2f}"
        mark = "  FINAL" if row["final"] else ""
        old = earlier.get(row["id"])
        if old and (old["outcome"], old["workshop"], old["delivery_days"]) != (
                row["outcome"], row["workshop"], row["delivery_days"]):
            mark += f"  changed, was {old['outcome']} {old['workshop'] or ''}".rstrip()
        print(f"{row['id']:<12}{row['order_id'] or '-':<9}{row['outcome']:<27}{row['workshop'] or '-':<9}"
              f"{delivery:>8}{mark}")
        if row["outcome"] not in ("recommendation", "approved") or row["id"] in result["review_warnings"]:
            show("Reason", row["reason"])
        for number, text in open_blockers(tasks, result, row["id"]):
            show(f"[{number}]", text)
    print(f"\nFinal: {len(result['final_ids'])}; unresolved: {len(result['unresolved_ids'])}")


def save_dispatcher_files(run_folder, decisions, result):
    """Save the decisions and the plan in the run folder, each also as a timestamped copy in
    plan-history/ (the convention of plan.json). The revision counts the saves.
    """
    decisions["revision"] += 1
    result["decisions_revision"] = decisions["revision"]
    stamp = f"{datetime.now():%Y-%m-%d_%H-%M-%S_%f}"
    (run_folder / "plan-history").mkdir(exist_ok=True)
    for name, value in (("dispatcher-decisions.json", decisions), ("dispatcher-plan.json", result)):
        write_json(run_folder / "plan-history" / f"{stamp}_{name}", value)
        write_json(run_folder / name, value)
        print(f"Saved {run_folder / name}")
