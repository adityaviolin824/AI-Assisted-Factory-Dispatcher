# key_informed_choices.py: the choices of a simulated dispatcher who knows the answer key, for the
# end-to-end test with the dispatcher's review (Test 11). It is a test tool, not part of the app: no
# real dispatcher has the key. It only writes decisions in the form the dispatcher page sends; the
# app's own endpoints check, apply and plan them.
#
# Run from backend/:
#   uv run python -m eval_run_report.key_informed_choices <run folder> --key <key.json> --data <data folder>
#       --table <review or final table .json> --level 0|1|2 --out <choices.json>
# Level 0 is Approve all on the first review; level 1 is the first Review again; level 2 is a second
# Review again, used only if level 1 leaves a case wrong. The rules are in the docstring of
# key_informed_choices and in docs/evaluation/PROMPT_TESTING_RESULTS.md ("End-to-end test with the
# dispatcher's review", written before Test 11).
import argparse
import json
from collections import Counter
from pathlib import Path

from dispatcher_review.dispatcher_decisions import verified_tasks_by_id
from dispatcher_review.dispatcher_plan import RESERVING, finalize_review
from eval_run_report.final_plan_score import score_final_plan
from eval_run_report.key_reference_plan import read_data_folder, reference_workshops
from eval_run_report.score_against_key import field_differences

# Row outcomes that place a batch, before or after approval.
ALLOCATING = RESERVING + ("provisional_recommendation", "approved")
# The facts the dispatcher can correct that the key gives for a case.
CORRECTABLE_FIELDS = ("order_id", "due_date", "preference")
# The workshop rules the dispatcher cannot correct as facts; choose_workshop obeys them instead.
WORKSHOP_FIELDS = ("requested_workshop", "excluded_workshops")


def key_facts(expected):
    """Return the key's correctable facts for a case as text: order, preference and, when the key has
    one, the due date (otherwise orders.csv gives it)."""
    facts = {"order_id": expected["order_id"], "preference": expected["preference"]}
    if expected["due_date"]:
        facts["due_date"] = expected["due_date"]
    return facts


def relabel_or_remove(row_id, verified):
    """Return the decision that takes one approved row out of the table: correct its intent to
    "question" for a task (the only decision that stops a plannable request), clear for an added batch."""
    if row_id in verified:
        return {"decision": "correct", "task_id": row_id, "facts": {"intent": "question"}, "resolves": []}
    return {"decision": "clear", "task_id": row_id}


def key_informed_choices(key, table, verified, scores, reference, level):
    """Return the decisions that fix every case the table has wrong.

    For a case the key allocates:
    - nothing to do when it is a correct allocation whose fields match the key;
    - with no task the dispatcher can name (none, or one that failed verification), and no approved
      row carrying it: add_batch with the key's facts, and the key's own workshop when the key has a
      requested or excluded workshop or from level 1;
    - otherwise, on its own task: complete with the key's facts when its row places no batch, else
      correct the facts that differ from the key; choose_workshop with the key's own workshop when its
      workshop rules differ from the key, or from level 1 when the case is still wrong, or at level 2
      always; warnings_checked for the rows its warnings name;
    - a second approved row of its order is taken out (relabel_or_remove).
    For an exception, and for an approved row that belongs to no case: every approved row is taken out.
    """
    rows = {row["id"]: row for row in table["summary_rows"]}
    entries = table.get("dispatcher_entries", {})
    approved_ids = set(table["final_ids"])
    scored = {score["case_id"]: score for score in scores[0]}
    decisions = []
    for case in key["cases"]:
        score, expected = scored[case["case_id"]], case["expected"]
        task_id = score["task_id"]
        if case["expected_outcome"] != "recommendation":
            decisions += [relabel_or_remove(row_id, verified) for row_id in score["row_ids"]]
            continue
        # Keep one row per order: the case's own task when it is approved, else the first row.
        kept = task_id if task_id in score["row_ids"] else (score["row_ids"] or [None])[0]
        decisions += [relabel_or_remove(row_id, verified) for row_id in score["row_ids"] if row_id != kept]
        if task_id not in verified:
            if not score["row_ids"]:
                added = {"decision": "add_batch", "facts": key_facts(expected)}
                if level >= 1 or expected["requested_workshop"] or expected["excluded_workshops"]:
                    added["workshop_id"] = reference[case["case_id"]]
                decisions.append(added)
            continue
        effective = {**verified[task_id], **entries.get(task_id, {}).get("facts", {})}
        differences = field_differences(effective, expected)
        wrong = score["decision"] != "correct allocation"
        if wrong and rows.get(task_id, {}).get("outcome") not in ALLOCATING:
            decisions.append({"decision": "complete", "task_id": task_id, "facts": key_facts(expected)})
        else:
            facts = {field: expected[field] for field in CORRECTABLE_FIELDS
                     if field in differences and expected[field] is not None}
            if facts:
                decisions.append({"decision": "correct", "task_id": task_id, "facts": facts, "resolves": []})
        if (any(field in differences for field in WORKSHOP_FIELDS) or (level >= 1 and wrong) or level == 2) \
                and entries.get(task_id, {}).get("workshop") != reference[case["case_id"]]:
            decisions.append({"decision": "choose_workshop", "task_id": task_id,
                              "workshop_id": reference[case["case_id"]]})
        warnings = table["review_warnings"].get(task_id)
        if warnings and task_id not in approved_ids:
            decisions.append({"decision": "warnings_checked", "task_id": task_id, "row_ids": warnings})
    decisions += [relabel_or_remove(row_id, verified) for row_id in scores[1]]
    return decisions


def main():
    """Write the key-informed choices for one table, and print how many of each decision."""
    parser = argparse.ArgumentParser(description="Write a key-informed dispatcher's choices for one table.")
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--key", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--table", type=Path, required=True, help="the first review, or a saved final table")
    parser.add_argument("--level", type=int, choices=(0, 1, 2), required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    key = json.loads(args.key.read_text(encoding="utf-8"))
    orders, workshops = read_data_folder(args.data)
    state = json.loads((args.run_dir / "state.json").read_text(encoding="utf-8"))
    table = json.loads(args.table.read_text(encoding="utf-8"))
    # A first review is scored as Approve all with no choices would approve it.
    if table["status"] != "final":
        table = finalize_review(table)
    reference = reference_workshops(key, orders, workshops)
    scores = score_final_plan(key, state, table, orders, reference)
    decisions = key_informed_choices(key, table, verified_tasks_by_id(args.run_dir), scores, reference, args.level)
    args.out.write_text(json.dumps({"decisions": decisions}, indent=1), encoding="utf-8")
    print(f"{len(decisions)} decisions: {dict(Counter(decision['decision'] for decision in decisions))}")
    print(f"Saved: {args.out}")


if __name__ == "__main__":
    main()
