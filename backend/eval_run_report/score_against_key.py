# score_against_key.py: score one run against a JSON answer key, such as
# docs/evaluation/extended_dispatch_100_human_team_golden.json, by the rules fixed before any paid run in
# docs/evaluation/NEW_TEST_SETS_PLAN.md ("How the score works").
#
# Report flow: make_run_report.py --key --data -> check_key_matches_run -> score_cases, message_labels
#              (this file) -> report_markdown.
# Reads:       the run (run_summary.read_run), the key and the data folder's CSVs. Writes nothing.
#
# Not allocating a case the key marks as an exception is correct, whatever the review route.
from eval_run_report.key_reference_plan import reference_workshops

# The fields allocation uses, after the order itself; compared on every verified matched task.
FIELDS = ("order_id", "due_date", "preference", "requested_workshop", "excluded_workshops", "wants_split")
RECOMMENDED = ("recommendation", "provisional_recommendation")
# Why an expected allocation was missed or went to another workshop; the first that applies is used.
PROBLEM_CLASSES = {
    "intake": "intake made a follow-up its own task, read a case message as no task or could not read it",
    "link": "a follow-up stayed in link review or joined another task",
    "verification": "verification blocked the task or read a field differently from the key",
    "allocation": "every field matches the key, but the plan differs: earlier tasks took the queue time, "
                  "or another task names the same order",
}


def check_key_matches_run(key, run, orders, workshops):
    """Raise ValueError when the key or the data folder does not belong to this run.

    A key scored against another chat, or a reference plan made from other CSV files, would give
    a wrong score with no visible error, so both are checked first.
    """
    pairs = [(message["message_id"], message["raw_text"]) for message in key["messages"]]
    if pairs != [(message["message_id"], message["raw_text"]) for message in run["manifest"]["messages"]]:
        raise ValueError("The key's messages differ from this run's chat messages; use the key of this chat.")
    missing = sorted({case["order_row_id"] for case in key["cases"]} - set(orders))
    if missing:
        raise ValueError(f"The data folder's orders.csv lacks the key's orders {missing[:5]}; use the test set's folder.")
    profiles = {wid: {**vars(workshop), "makes": sorted(workshop.makes)} for wid, workshop in workshops.items()}
    if profiles != run["plan"]["workshop_profiles"]:
        raise ValueError("The data folder's workshops.csv differs from the workshops this run was planned with.")


def first_message(state, task):
    """Return the chat message of a task's first item: the message the task was created from."""
    return state["items"][task["item_ids"][0]]["message_id"]


def match_task(state, case):
    """Return the app task created from the case's first message, or None when there is none.

    One message can hold two jobs, so when several tasks start at that message, the one whose
    excerpts name the case's order is used. The J number is never used: it can differ.
    """
    root = case["messages"][0]["message_id"]
    tasks = [task for task in state["tasks"].values() if first_message(state, task) == root]
    if len(tasks) > 1:
        order = case["expected"]["order_id"] or case["order_row_id"]
        tasks = [task for task in tasks if any(order in excerpt for item_id in task["item_ids"]
                                               for excerpt in state["items"][item_id]["excerpts"])]
    return tasks[0] if tasks else None


def where_message_went(state, message_id):
    """Return what processing did with one message, such as "task T:L0005:J1" or "link review"."""
    if message_id in {review["message_id"] for review in state["intake_review"]}:
        return ["intake review"]
    if message_id in state["non_task_message_ids"]:
        return ["no task"]
    places = []
    for item_id, item in state["items"].items():
        if item["message_id"] != message_id:
            continue
        task = next((task for task in state["tasks"].values() if item_id in task["item_ids"]), None)
        if item_id in state["unresolved_links"]:
            places.append("link review")
        elif task is None:
            places.append("not processed")
        else:
            places.append(f"{'task' if task['item_ids'][0] == item_id else 'joined'} {task['task_id']}")
    return places or ["not processed"]


def field_differences(record, expected):
    """Return {field: (app value, key value)} for each allocator field that differs."""
    differences = {}
    for field in FIELDS:
        app, wanted = record[field], expected[field]
        if field == "excluded_workshops":
            app, wanted = sorted(app), sorted(wanted)
        if app != wanted:
            differences[field] = (app, wanted)
    return differences


def problem_class(state, case, task, outcome, differences, joined):
    """Return the PROBLEM_CLASSES name for a missed or changed allocation."""
    messages = [message["message_id"] for message in case["messages"]]
    task_starts = {first_message(state, other) for other in state["tasks"].values()}
    follow_ups = [message["message_id"] for message in case["messages"] if message["kind"] == "follow_up"]
    if (task is None or any(message_id in task_starts for message_id in follow_ups)
            or any(where_message_went(state, message_id)[0] in ("intake review", "no task") for message_id in messages)):
        return "intake"
    if not all(joined.values()):
        return "link"
    if outcome not in RECOMMENDED + ("review_required", "deadline_passed") or differences:
        return "verification"
    return "allocation"


def score_case(case, state, rows, reference):
    """Return the decision, outcome, workshop, fields and links of one key case in this run."""
    task = match_task(state, case)
    verified = task is not None and task["verified"] is not None and task["verified_version"] == task["version"]
    record = task["verified"] if verified else None
    if task is None:
        outcome = "no own task: " + ", ".join(where_message_went(state, case["messages"][0]["message_id"]))
        row = {}
    else:
        row = rows.get(task["task_id"], {})
        outcome = row.get("outcome", "no plan row")
    message_ids = set() if task is None else {state["items"][item_id]["message_id"] for item_id in task["item_ids"]}
    joined = {message["message_id"]: message["message_id"] in message_ids
              for message in case["messages"] if message["kind"] == "follow_up"}
    expected = case["expected"]
    workshop = row.get("workshop") if outcome in RECOMMENDED else None
    obeys = workshop not in expected["excluded_workshops"] and expected["requested_workshop"] in (None, workshop)
    should_allocate = case["expected_outcome"] == "recommendation"
    if outcome in RECOMMENDED:
        decision = "correct allocation" if should_allocate and obeys else "unsafe allocation"
    else:
        decision = "missed allocation" if should_allocate else "correct non-allocation"
    differences = field_differences(record, expected) if record else {}
    changed = decision == "correct allocation" and workshop != reference.get(case["case_id"])
    problem = (problem_class(state, case, task, outcome, differences, joined)
               if decision == "missed allocation" or changed else None)
    return {"case_id": case["case_id"], "order": case["order_row_id"], "scenario": case["scenario"],
            "expected_outcome": case["expected_outcome"], "task_id": task and task["task_id"],
            "verified": verified, "outcome": outcome, "reason": row.get("reason"), "workshop": workshop,
            "reference_workshop": reference.get(case["case_id"]), "decision": decision,
            "differences": differences, "joined": joined, "problem": problem,
            "unjoined": {message_id: ", ".join(where_message_went(state, message_id))
                         for message_id, done in joined.items() if not done}}


def score_cases(key, run, orders, workshops):
    """Check the key against the run, then return one score_case result per key case."""
    check_key_matches_run(key, run, orders, workshops)
    rows = {row["id"]: row for row in run["plan"]["summary_rows"]}
    reference = reference_workshops(key, orders, workshops)
    return [score_case(case, run["state"], rows, reference) for case in key["cases"]]


def app_label(state, message_id):
    """Return the app's label for one message: request, follow_up, non_task, intake_review or not_processed."""
    if message_id in {review["message_id"] for review in state["intake_review"]}:
        return "intake_review"
    if message_id in state["non_task_message_ids"]:
        return "non_task"
    kinds = {item["kind"] for item in state["items"].values() if item["message_id"] == message_id}
    if "request" in kinds:
        return "request"
    return "follow_up" if kinds else "not_processed"


def message_labels(key, state):
    """Return (message_id, key label, app label) for every message of the key."""
    return [(message["message_id"], message["expected_kind"], app_label(state, message["message_id"]))
            for message in key["messages"]]
