"""Offline checks of make_run_report.py and eval_run_report/: costs from call records, the key's own
plan, and the score of a made-up run built from the 100-case key, first perfect, then with one known
fault per check. The run's model answers are never needed, so no model call is made.

Run from backend/: uv run python -m unittest discover -s tests -v
"""
import copy
import json
import unittest
from dataclasses import asdict

from eval_run_report.key_reference_plan import read_data_folder, reference_workshops
from eval_run_report.report_markdown import report_text, score_section
from eval_run_report.run_summary import call_cost, cost_row
from eval_run_report.score_against_key import check_key_matches_run, message_labels, score_cases
from order_processing_into_tasks.settings_and_data import BACKEND_DIR
from task_allocation_to_workshops import recommend_one_task

KEY_FILE = BACKEND_DIR / "docs/evaluation/extended_dispatch_100_human_team_golden.json"
DATA_FOLDER = BACKEND_DIR / "data/extended_dispatch_100"


def call(model="gpt-5.6-luna", stage="verify", reused=False, tokens=(2208, 1483, 2060, 1536), seconds=18.2):
    """Return a saved call record with tokens (input, cached input, output, reasoning)."""
    record = {"request": {"stage": stage, "model": model}, "elapsed_seconds": seconds,
              "usage": {"input_tokens": tokens[0], "input_token_details": {"cache_read": tokens[1]},
                        "output_tokens": tokens[2], "output_token_details": {"reasoning": tokens[3]}}}
    return {**record, "reused_response": True} if reused else record


class CallCosts(unittest.TestCase):
    def test_one_call_is_priced_from_its_tokens(self):
        # gpt-5.6-luna: 725 uncached input at $0.20, 1483 cached at $0.02, 2060 output at $1.20 per million.
        self.assertAlmostEqual(call_cost(call()), (725 * 0.20 + 1483 * 0.02 + 2060 * 1.20) / 1_000_000)

    def test_reused_failed_and_unpriced_calls(self):
        failed = {"request": {"stage": "verify", "model": "gpt-5.6-luna"}, "error_type": "APITimeoutError"}
        row = cost_row("verify", [call(), call(reused=True), failed])
        self.assertEqual((row["calls"], row["paid"], row["failed"]), (3, 1, 1))
        self.assertAlmostEqual(row["cost_this_run"], call_cost(call()))
        self.assertAlmostEqual(row["cost_fresh"], 2 * call_cost(call()))
        self.assertEqual((row["input_tokens"], row["reasoning_tokens"], row["seconds_fresh"]), (2208, 1536, 36.4))
        self.assertIsNone(cost_row("verify", [call(model="another-model")])["cost_this_run"])


def perfect_run(key, orders, workshops, reference):
    """Return a made-up run in which every case was read and planned exactly as the key expects.

    Each case's first message makes its task and its follow-ups join it; a two-job message gets one
    item per job, whose excerpt names only that job's order, as intake writes it.
    """
    state = {"items": {}, "tasks": {}, "intake_review": [], "task_review": {}, "unresolved_links": {},
             "non_task_message_ids": [m["message_id"] for m in key["messages"] if m["expected_kind"] == "non_task"]}
    texts = {m["message_id"]: m for m in key["messages"]}
    rows = []
    for case in key["cases"]:
        item_ids = []
        for message in case["messages"]:
            source = texts[message["message_id"]]
            job = source["case_ids"].index(case["case_id"]) + 1
            item_id = f"{message['message_id']}:J{job}"
            excerpt = case["order_row_id"] if len(source["case_ids"]) > 1 else source["raw_text"]
            state["items"][item_id] = {"item_id": item_id, "message_id": message["message_id"],
                                       "kind": message["kind"], "excerpts": [excerpt]}
            item_ids.append(item_id)
        task_id = "T:" + item_ids[0]
        message_ids = [m["message_id"] for m in case["messages"]]
        state["tasks"][task_id] = {"task_id": task_id, "item_ids": item_ids, "version": len(item_ids),
                                   "verified_version": len(item_ids),
                                   "verified": {**case["expected"], "task_id": task_id, "source_message_ids": message_ids}}
        recommended = case["case_id"] in reference
        rows.append({"id": task_id, "order_id": case["expected"]["order_id"],
                     "outcome": "recommendation" if recommended else case["expected_outcome"],
                     "workshop": reference.get(case["case_id"]), "delivery_days": None, "days_available": None,
                     "reason": "made up", "messages": message_ids})
    profiles = {wid: {**asdict(w), "makes": sorted(w.makes)} for wid, w in workshops.items()}
    manifest = {"messages": [{"message_id": m["message_id"], "raw_text": m["raw_text"]} for m in key["messages"]]}
    return {"manifest": manifest, "state": state, "calls": [],
            "plan": {"summary_rows": rows, "workshop_profiles": profiles}}


def row_of(run, task_id):
    """Return the plan row of one task in a made-up run."""
    return next(row for row in run["plan"]["summary_rows"] if row["id"] == task_id)


class KeyScore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = json.loads(KEY_FILE.read_text(encoding="utf-8"))
        cls.orders, cls.workshops = read_data_folder(DATA_FOLDER)
        cls.reference = reference_workshops(cls.key, cls.orders, cls.workshops)
        cls.perfect = perfect_run(cls.key, cls.orders, cls.workshops, cls.reference)

    def scores(self, run):
        return {score["case_id"]: score for score in score_cases(self.key, run, self.orders, self.workshops)}

    def test_the_key_plan_recommends_the_85_expected_cases(self):
        expected = {c["case_id"] for c in self.key["cases"] if c["expected_outcome"] == "recommendation"}
        self.assertEqual(set(self.reference), expected)
        # The allocation modules use config.toml's data again afterwards.
        self.assertEqual(sorted(recommend_one_task.ORDERS)[0], "ORD-001")

    def test_a_perfect_run_scores_full_marks(self):
        scores = self.scores(self.perfect)
        decisions = [s["decision"] for s in scores.values()]
        self.assertEqual(decisions.count("correct allocation"), 85)
        self.assertEqual(decisions.count("correct non-allocation"), 15)
        self.assertTrue(all(not s["differences"] and not s["problem"] and all(s["joined"].values())
                            for s in scores.values()))
        self.assertEqual(sum(len(s["joined"]) for s in scores.values()), 45)
        labels = message_labels(self.key, self.perfect["state"])
        self.assertEqual((len(labels), sum(wanted == app for _, wanted, app in labels)), (149, 149))
        # A message with two jobs is matched by the order its excerpt names, never by J number.
        self.assertEqual((scores["CASE-081"]["task_id"], scores["CASE-082"]["task_id"]), ("T:L0130:J1", "T:L0130:J2"))

    def test_a_follow_up_made_its_own_task_is_an_intake_miss(self):
        run = copy.deepcopy(self.perfect)
        case = next(c for c in self.key["cases"] if c["expected_outcome"] == "recommendation" and len(c["messages"]) > 1)
        task_id = "T:" + case["messages"][0]["message_id"] + ":J1"
        follow_up = case["messages"][1]["message_id"] + ":J1"
        state = run["state"]
        state["tasks"][task_id]["item_ids"].remove(follow_up)
        state["tasks"]["T:" + follow_up] = {"task_id": "T:" + follow_up, "item_ids": [follow_up]}
        state["items"][follow_up]["kind"] = "request"
        row_of(run, task_id).update(outcome="review_required", workshop=None)
        score = self.scores(run)[case["case_id"]]
        self.assertEqual((score["decision"], score["problem"]), ("missed allocation", "intake"))
        self.assertEqual(score["unjoined"], {case["messages"][1]["message_id"]: "task T:" + follow_up})

    def test_a_follow_up_in_link_review_is_a_link_miss(self):
        run = copy.deepcopy(self.perfect)
        case = next(c for c in self.key["cases"] if c["expected_outcome"] == "recommendation" and len(c["messages"]) > 1)
        task_id = "T:" + case["messages"][0]["message_id"] + ":J1"
        follow_up = case["messages"][1]["message_id"] + ":J1"
        run["state"]["tasks"][task_id]["item_ids"].remove(follow_up)
        run["state"]["unresolved_links"][follow_up] = {"item_id": follow_up}
        row_of(run, task_id).update(outcome="needs_clarification", workshop=None)
        score = self.scores(run)[case["case_id"]]
        self.assertEqual((score["decision"], score["problem"]), ("missed allocation", "link"))

    def test_a_misread_field_is_a_verification_miss_and_a_queue_miss_is_allocation(self):
        run = copy.deepcopy(self.perfect)
        run["state"]["tasks"]["T:L0002:J1"]["verified"]["preference"] = "quality"
        row_of(run, "T:L0002:J1").update(outcome="needs_clarification", workshop=None)
        row_of(run, "T:L0003:J1").update(outcome="review_required", workshop=None)
        scores = self.scores(run)
        self.assertEqual(scores["CASE-001"]["differences"], {"preference": ("quality", "none")})
        self.assertEqual((scores["CASE-001"]["problem"], scores["CASE-002"]["problem"]), ("verification", "allocation"))

    def test_an_exception_or_an_excluded_workshop_allocated_is_unsafe(self):
        run = copy.deepcopy(self.perfect)
        exception = next(c for c in self.key["cases"] if c["expected_outcome"] == "needs_clarification")
        row_of(run, "T:" + exception["messages"][0]["message_id"] + ":J1").update(outcome="recommendation", workshop="W3")
        excluded = next(c for c in self.key["cases"] if c["expected_outcome"] == "recommendation" and c["expected"]["excluded_workshops"])
        row_of(run, "T:" + excluded["messages"][0]["message_id"] + ":J1")["workshop"] = excluded["expected"]["excluded_workshops"][0]
        scores = self.scores(run)
        self.assertEqual((scores[exception["case_id"]]["decision"], scores[excluded["case_id"]]["decision"]),
                         ("unsafe allocation", "unsafe allocation"))

    def test_another_chat_or_data_folder_is_refused(self):
        run = copy.deepcopy(self.perfect)
        run["manifest"]["messages"][0]["raw_text"] += " (edited)"
        with self.assertRaisesRegex(ValueError, "messages differ"):
            check_key_matches_run(self.key, run, self.orders, self.workshops)
        supplied_orders, _ = read_data_folder(BACKEND_DIR / "data")
        with self.assertRaisesRegex(ValueError, "lacks the key's orders"):
            check_key_matches_run(self.key, self.perfect, supplied_orders, self.workshops)

    def reportable(self):
        """Return a copy of the perfect run with the manifest and plan fields the report prints."""
        run = copy.deepcopy(self.perfect)
        run["manifest"].update(label="test chat", models={"verify": "gpt-5.6-luna"}, temperature=0.0,
                               target_size=3, context_size=2, verify_batch_size=3, max_payload_chars=24000)
        run["plan"].update(created_at="2026-10-19T00:00:00", dispatch_date="2026-04-01", objective_setting=None,
                           processing_complete=True, not_processed=[], review_warnings={})
        return run

    def test_a_plan_made_before_review_warnings_is_reported(self):
        # 12 saved plans from 13-15 October 2026 have no review_warnings; their count is unknown, not 0.
        run = self.reportable()
        del run["plan"]["review_warnings"]
        self.assertIn("review warnings: not recorded (this plan was made before review warnings",
                      report_text("output/runs/old", run))

    def test_the_report_shows_the_score(self):
        run = self.reportable()
        scores = score_cases(self.key, run, self.orders, self.workshops)
        text = report_text("output/runs/test", run, score_section(
            "docs/evaluation/key.json", "0" * 64, self.key, "data/extended_dispatch_100", scores,
            message_labels(self.key, run["state"])))
        self.assertIn("| - allocated, obeying the key's requested and excluded workshops | 85 |", text)
        self.assertIn("Workshop choice: 85 of 85 correct allocations", text)
        self.assertIn("149 of 149 messages have the key's label.", text)
        self.assertIn("45 of 45 follow-ups joined their case's task.", text)
        self.assertIn("Reviewers: 3 human team members.", text)
        self.assertIn("Comprehensive manual, line-by-line review by human team members, not AI.", text)
        self.assertNotIn(str(BACKEND_DIR), text)
        # An older key with no review provenance must not acquire a human-review claim.
        draft_key = copy.deepcopy(self.key)
        del draft_key["provenance"]
        draft_text = score_section("draft.json", "0" * 64, draft_key, "data/extended_dispatch_100",
                                   scores, message_labels(self.key, run["state"]))
        self.assertNotIn("Reviewers:", draft_text)


if __name__ == "__main__":
    unittest.main()
