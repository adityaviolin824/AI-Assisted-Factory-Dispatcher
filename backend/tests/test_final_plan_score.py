"""Offline checks of the score after the dispatcher's review (eval_run_report/final_plan_score.py) and of
the key-informed test dispatcher (eval_run_report/key_informed_choices.py), on small made-up tables. No
run folder, CSV file or model call is needed.

Run from backend/: uv run python -m unittest discover -s tests -v
"""
import unittest

from eval_run_report.final_plan_score import score_final_plan
from eval_run_report.key_informed_choices import key_informed_choices

# The allocator fields of every made-up case and task; each case adds its own order.
FIELDS = {"intent": "allocation", "due_date": "2026-04-20", "preference": "none", "requested_workshop": None,
          "excluded_workshops": [], "wants_split": False}
ORDERS = {f"ORD-{number}": {"pieces": 100} for number in range(1, 10)}


def case(number, outcome="recommendation", **expected):
    """Return a key case for order ORD-<number>, created from message L<number>."""
    return {"case_id": f"CASE-{number}", "order_row_id": f"ORD-{number}", "expected_outcome": outcome,
            "messages": [{"message_id": f"L{number}", "kind": "request"}],
            "expected": {**FIELDS, "order_id": f"ORD-{number}", **expected}}


def state(*numbers):
    """Return a processing state with one task, T:L<n>:J1, created from each message L<n>."""
    return {"items": {f"I{n}": {"message_id": f"L{n}", "excerpts": [f"ORD-{n}"]} for n in numbers},
            "tasks": {f"T:L{n}:J1": {"task_id": f"T:L{n}:J1", "item_ids": [f"I{n}"]} for n in numbers}}


def table(*rows, warnings=None):
    """Return a final table from (row ID, order, workshop, outcome, quantity) rows; "approved" rows are final."""
    return {"summary_rows": [{"id": row_id, "order_id": order, "workshop": workshop, "outcome": outcome,
                              "reason": "made up"} for row_id, order, workshop, outcome, _ in rows],
            "decisions": [{"task_id": row_id, "selected_metrics": {"tardiness_days": 0.0},
                           "task": {**FIELDS, "task_id": row_id, "order_id": order, "quantity": quantity}}
                          for row_id, order, _, _, quantity in rows],
            "final_ids": [row[0] for row in rows if row[3] == "approved"],
            "unresolved_ids": [row[0] for row in rows if row[3] != "approved"],
            "dispatcher_entries": {}, "review_warnings": warnings or {}}


def decisions_of(key, run_state, final):
    """Return {case ID: decision} and the extra rows of a scored table."""
    scores, extra = score_final_plan(key, run_state, final, ORDERS, {})
    return {score["case_id"]: score["decision"] for score in scores}, extra


class FinalPlanScore(unittest.TestCase):
    def test_an_approved_row_counts_for_the_case_of_its_order(self):
        key = {"cases": [case(1), case(2, "needs_clarification"), case(3)]}
        final = table(("T:L1:J1", "ORD-1", "W1", "approved", None),
                      ("T:L2:J1", "ORD-2", "W2", "approved", None),
                      ("T:L3:J1", "ORD-3", "W1", "review_required", None),
                      ("ADD-1", "ORD-3", "W5", "approved", None),
                      ("T:L9:J1", "ORD-9", "W1", "approved", None))
        decisions, extra = decisions_of(key, state(1, 2, 3, 9), final)
        # CASE-3's own task is unresolved, but the batch the dispatcher added carries its order.
        self.assertEqual(decisions, {"CASE-1": "correct allocation", "CASE-2": "unsafe allocation",
                                     "CASE-3": "correct allocation"})
        self.assertEqual(extra, ["T:L9:J1"])

    def test_an_excluded_workshop_or_too_many_pieces_is_wrong_and_no_approval_is_missed(self):
        key = {"cases": [case(1, excluded_workshops=["W1"]), case(3), case(4)]}
        final = table(("T:L1:J1", "ORD-1", "W1", "approved", None),
                      ("T:L3:J1", "ORD-3", "W1", "approved", None),
                      ("ADD-1", "ORD-3", "W2", "approved", 100),
                      ("T:L4:J1", "ORD-4", "W1", "provisional_recommendation", None))
        decisions, extra = decisions_of(key, state(1, 3, 4), final)
        self.assertEqual(decisions, {"CASE-1": "wrong allocation", "CASE-3": "wrong allocation",
                                     "CASE-4": "missed allocation"})
        self.assertEqual(extra, [])

    def test_a_cancelled_row_is_never_allocated(self):
        # As CASE-097 after the dispatcher cancels it (24 October 2026): never final, so never approved.
        key = {"cases": [case(7, "needs_clarification")]}
        final = table(("T:L7:J1", "ORD-7", None, "cancelled", None))
        scores, extra = score_final_plan(key, state(7), final, ORDERS, {})
        self.assertEqual([(score["decision"], score["outcome"]) for score in scores],
                         [("correct non-allocation", "cancelled")])
        self.assertEqual(extra, [])


class KeyInformedChoices(unittest.TestCase):
    def test_each_wrong_case_gets_the_decision_that_fixes_it(self):
        key = {"cases": [case(1, "needs_clarification"), case(4), case(5), case(6, excluded_workshops=["W2"])]}
        final = table(("T:L1:J1", "ORD-1", "W1", "approved", None),
                      ("T:L4:J1", "ORD-4", "W1", "provisional_recommendation", None),
                      ("T:L5:J1", "ORD-5", None, "review_required", None),
                      warnings={"T:L4:J1": ["L0099"]})
        run_state = state(1, 4, 5)
        verified = {task_id: {**FIELDS, "task_id": task_id, "order_id": f"ORD-{task_id[3]}"}
                    for task_id in run_state["tasks"]}
        reference = {"CASE-4": "W1", "CASE-5": "W1", "CASE-6": "W6"}
        scores = score_final_plan(key, run_state, final, ORDERS, reference)
        self.assertEqual(key_informed_choices(key, final, verified, scores, reference, level=0), [
            # An approved exception is taken out: a question is never planned.
            {"decision": "correct", "task_id": "T:L1:J1", "facts": {"intent": "question"}, "resolves": []},
            # A provisional row with the key's fields only needs its warnings checked.
            {"decision": "warnings_checked", "task_id": "T:L4:J1", "row_ids": ["L0099"]},
            # A blocked request is completed with the key's facts.
            {"decision": "complete", "task_id": "T:L5:J1",
             "facts": {"order_id": "ORD-5", "preference": "none", "due_date": "2026-04-20"}},
            # A case with no task is added, at the key's workshop because the key excludes one.
            {"decision": "add_batch", "facts": {"order_id": "ORD-6", "preference": "none", "due_date": "2026-04-20"},
             "workshop_id": "W6"}])


if __name__ == "__main__":
    unittest.main()
