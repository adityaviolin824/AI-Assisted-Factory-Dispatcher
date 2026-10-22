# final_plan_score.py: score the dispatcher's final table (dispatcher-plan.json) against a JSON answer
# key, after the dispatcher's review, by the rules written before Test 11 in
# docs/evaluation/PROMPT_TESTING_RESULTS.md ("End-to-end test with the dispatcher's review").
#
# Report flow: score_dispatcher_review.py -> score_final_plan, final_score_lines (this file).
# Reads:       a run's state.json, a final table, the key and the data folder's orders. Writes nothing.
#
# make_run_report.py scores the plan before the review, where a recommendation counts as allocated.
# Here only an approved row is allocated: a row the final table leaves unresolved is not. Each case of
# the 100-case key has its own order, so an approved row belongs to the case of its order, whichever
# row carries it: the case's own task, another task of that order or a batch the dispatcher added.
from collections import Counter

from eval_run_report.score_against_key import field_differences, match_task


def approved_rows(final):
    """Return {row ID: (row, decision record)} for every approved row of a final table."""
    rows = {row["id"]: row for row in final["summary_rows"]}
    records = {record["task_id"]: record for record in final["decisions"]}
    return {row_id: (rows[row_id], records[row_id]) for row_id in final["final_ids"]}


def how_fixed(entry):
    """Return the dispatcher's decisions on one row, such as "facts, workshop", or "none"."""
    names = [name for name in ("added", "facts", "workshop", "accept_late", "warnings_checked") if entry.get(name)]
    return ", ".join(names) or "none"


def score_final_case(case, state, final, approved, orders, reference):
    """Return the decision, rows, workshops and fields of one key case in a final table."""
    task = match_task(state, case)
    row_ids = sorted(row_id for row_id, (row, record) in approved.items()
                     if record["task"]["order_id"] == case["order_row_id"])
    if task is not None and task["task_id"] in approved and task["task_id"] not in row_ids:
        row_ids.append(task["task_id"])
    expected = case["expected"]
    workshops = [approved[row_id][0]["workshop"] for row_id in row_ids]
    obeys = all(workshop not in expected["excluded_workshops"] and expected["requested_workshop"] in (None, workshop)
                for workshop in workshops)
    pieces = sum(approved[row_id][1]["task"].get("quantity") or orders[case["order_row_id"]]["pieces"]
                 for row_id in row_ids)
    whole_order = pieces == orders[case["order_row_id"]]["pieces"]
    if case["expected_outcome"] != "recommendation":
        decision = "unsafe allocation" if row_ids else "correct non-allocation"
    elif not row_ids:
        decision = "missed allocation"
    else:
        decision = "correct allocation" if obeys and whole_order else "wrong allocation"
    # The details of the row that carries the case: its own task when approved, else the first row.
    main = task["task_id"] if task is not None and task["task_id"] in row_ids else (row_ids or [None])[0]
    rows = {row["id"]: row for row in final["summary_rows"]}
    shown = rows.get(main) or rows.get(task and task["task_id"], {})
    record = approved[main][1] if main else None
    return {"case_id": case["case_id"], "order": case["order_row_id"], "expected_outcome": case["expected_outcome"],
            "task_id": task and task["task_id"], "row_ids": row_ids, "decision": decision,
            "outcome": shown.get("outcome", "no row"), "reason": shown.get("reason"),
            "workshops": workshops, "reference_workshop": reference.get(case["case_id"]), "pieces": pieces,
            "whole_order": whole_order,
            "late": bool(record and record["selected_metrics"]["tardiness_days"] > 0),
            "differences": field_differences(record["task"], expected) if record else {},
            "fixed_by": how_fixed(final["dispatcher_entries"].get(main, {})) if main else "none"}


def score_final_plan(key, state, final, orders, reference):
    """Return (one score_final_case result per key case, approved rows that belong to no case)."""
    approved = approved_rows(final)
    scores = [score_final_case(case, state, final, approved, orders, reference) for case in key["cases"]]
    attributed = {row_id for score in scores for row_id in score["row_ids"]}
    extra = [row_id for row_id in approved if row_id not in attributed]
    return scores, extra


def final_score_lines(title, scores, extra, final):
    """Return the Markdown lines of one final table's score: the headline, then every failure."""
    decisions = Counter(score["decision"] for score in scores)
    correct = [score for score in scores if score["decision"] == "correct allocation"]
    should = sum(score["expected_outcome"] == "recommendation" for score in scores)
    perfect = (decisions["correct allocation"] == should and decisions["correct non-allocation"] == len(scores) - should
               and not extra)
    lines = [f"## {title}", "",
             "| Measure | Result |", "|---|---|",
             f"| Correct allocations (of {should}) | {decisions['correct allocation']} |",
             f"| Missed allocations | {decisions['missed allocation']} |",
             f"| Wrong allocations (a requested or excluded workshop broken, or not the whole order) | "
             f"{decisions['wrong allocation']} |",
             f"| Correct non-allocations (of {len(scores) - should}) | {decisions['correct non-allocation']} |",
             f"| Unsafe allocations (an exception approved) | {decisions['unsafe allocation']} |",
             f"| Approved rows that belong to no case | {len(extra)} |",
             f"| Perfect (every allocation and non-allocation right, nothing extra) | {'yes' if perfect else 'no'} |",
             "", "Details of the correct allocations:", "",
             "| Measure | Result |", "|---|---|",
             f"| Every allocator field matching the key | {sum(not score['differences'] for score in correct)} |",
             f"| On time | {sum(not score['late'] for score in correct)} |",
             f"| At the key's own workshop | "
             f"{sum(score['workshops'] == [score['reference_workshop']] for score in correct)} |",
             f"| Carried by a batch the dispatcher added | {sum(score['fixed_by'].startswith('added') for score in correct)} |",
             f"| Approved rows in the table; unresolved rows | {len(final['final_ids'])}; {len(final['unresolved_ids'])} |",
             ""]
    failures = [score for score in scores if score["decision"] not in ("correct allocation", "correct non-allocation")]
    lines += ["Cases not right:" if failures else "Cases not right: none.", ""]
    for score in failures:
        lines.append(f"- **{score['case_id']}** ({score['order']}, key: {score['expected_outcome']}): "
                     f"{score['decision']}; task {score['task_id']}, rows {score['row_ids'] or 'none'}, "
                     f"outcome {score['outcome']}. Reason: {score['reason']}")
    differing = [score for score in correct if score["differences"]]
    if differing:
        lines += ["", "Correct allocations whose fields differ from the key:", ""]
        lines += [f"- {score['case_id']}: " + "; ".join(f"{field} {app!r} (key {wanted!r})"
                                                       for field, (app, wanted) in score["differences"].items())
                  for score in differing]
    if extra:
        lines += ["", f"Approved rows that belong to no case: {', '.join(extra)}"]
    return lines + [""]
