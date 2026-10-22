"""Tests for the routing and allocation modules, with notebook 05 as the reference. Fully offline.

Run from backend/:  uv run python -m unittest discover -s tests -v

What they prove:
- the moved code has the notebook's logic (same syntax tree; docstrings and comments ignored), and
  every other function is declared new or declared changed;
- the workshop and order data equal the notebook's. The tests pin the notebook's dispatch date and
  objective, whatever config.toml says;
- the modules make notebook 05's decisions (the acceptance test, assert_same_decisions) on the
  controlled checks C1-C14, on routing cases, on every unique saved run in output/runs/, on the
  notebook's saved plan and end to end on the supplied chat file;
- an incomplete processing run gets a plan marked partial, with every input accounted for;
- a planned task that an unresolved input may modify is marked provisional, with its decision unchanged;
- a request whose deadline is on or before the dispatch date is review only, with nothing calculated
  (declared change of 18 October 2026, applied to the notebook's records by expected_decision);
- every name the modules use is defined or imported.
Allocation never calls a model, so nothing here can cost money.
"""
import ast
import contextlib
import copy
import importlib
import io
import json
import tempfile
import unittest
from collections import Counter
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from unittest import mock

from notebook_reference import BACKEND_DIR, CHAT_FILE, definitions_source, load_notebook_05, top_level_definitions
from test_processing_modules import logic, module_definitions, offline_modules, undefined_names

from order_intake_from_chat.read_chat_messages import read_messages
from order_processing_into_tasks import create_and_link_tasks, model_calls_with_cache, processing_run, settings_and_data
from task_allocation_to_workshops import allocation_plan, allocation_settings_and_data
from task_allocation_to_workshops.rank_workshops import DEFAULT_HYBRID_WEIGHTS, rank_candidates
from task_routing import route_verified_tasks

# The definitions each module copies unchanged from notebook 05.
MOVED = {
    "task_allocation_to_workshops.allocation_settings_and_data": ["Workshop", "INITIAL_QUEUES"],
    "task_allocation_to_workshops.workshop_rules_and_estimates": [
        "rejection_reason", "split_rejected", "hard_rule_reason", "candidate_metrics"],
    "task_allocation_to_workshops.rank_workshops": [
        "DEFAULT_OBJECTIVE", "OBJECTIVE_FIELDS", "OBJECTIVE_ALIASES", "PREFERENCE_OBJECTIVES",
        "DEFAULT_HYBRID_WEIGHTS", "hybrid_score", "rank_candidates"],
    "task_allocation_to_workshops.recommend_one_task": [
        "task_deadline", "review_decision", "option_without_request"],
}
# Functions that are new in the modules (everything else is moved or changed).
NEW = {
    "task_routing.route_verified_tasks": ["route_task", "route_tasks"],
    "task_allocation_to_workshops.allocation_plan": ["summary_row", "inputs_without_outcome", "plan_saved_run"],
    "task_allocation_to_workshops.recommend_one_task": ["batch_pieces"],
    "run_allocation": ["main"],
}
# Moved from notebook 05, then changed on purpose (see docs/legacy/ALLOCATION_MODULARIZATION_PLAN.md): routing
# and the duplicate-order check moved out of plan_tasks into route_tasks; summarize_plan also lists
# the duplicate-order reviews and the inputs without an outcome; plan_allocation takes (run_dir,
# state, messages), calls route_tasks, records created_at, keeps a copy of every plan in
# plan-history/ (checked by PlanFiles) and plans an incomplete run as a partial plan (checked by
# PartialRuns). Since 15 October 2026 (debugging/held-tasks-never-verified.md) plan_allocation
# saves review_warnings, and summarize_plan marks the planned tasks an unresolved input may modify
# as provisional (checked by PartialRuns and ProvisionalRows). Since 18 October 2026 recommend gives
# a request whose deadline is on or before the dispatch date the status "deadline_passed" and
# calculates nothing for it (checked through expected_decision and by ControlledChecks). Since 22 October
# 2026 recommend sizes the batch with batch_pieces: a quantity only the dispatcher's review can give,
# otherwise the order's pieces as before (checked in test_dispatcher_review.py).
CHANGED = {
    "task_allocation_to_workshops.allocation_plan": ["plan_tasks", "summarize_plan", "plan_allocation"],
    "task_allocation_to_workshops.recommend_one_task": ["recommend"],
}
# The notebook's allocation settings. pinned_settings sets them in every module that uses them, so
# the comparisons hold whatever config.toml says.
NOTEBOOK_SETTINGS = {"DISPATCH_DATE": date(2026, 4, 1), "PLAN_OBJECTIVE": None}
# Notebook 05's saved plan of 13 October and the module run with the same processing state.
NOTEBOOK_RUN = BACKEND_DIR / "experimentation_notebooks/output/order-pipeline-mvp/runs/2026-10-13_12-13-34"
MODULE_RUN = settings_and_data.RUNS_DIR / "2026-10-13_19-32-08"
# Test 6 on the blocker cases file (docs/evaluation/PROMPT_TESTING_RESULTS.md). The graph run of 21:19:26 saved the same state.
TEST_6_RUN = settings_and_data.RUNS_DIR / "2026-10-15_15-28-46"


@contextlib.contextmanager
def pinned_settings():
    """Use the notebook's dispatch date and objective in every allocation module."""
    with contextlib.ExitStack() as stack:
        for module_name in MOVED | NEW | CHANGED:
            module = importlib.import_module(module_name)
            for name, value in NOTEBOOK_SETTINGS.items():
                if hasattr(module, name):
                    stack.enter_context(mock.patch.object(module, name, value))
        yield


def check_task(task_id, order_id, **changes):
    """Return a ready allocation task for a controlled check (notebook 05's test helper).

    Each check states only the fields it is about; everything else is a plain ready task.
    """
    task = {"task_id": task_id, "version": 1, "order_id": order_id, "intent": "allocation",
            "information_sufficient": True, "description": f"Controlled check {task_id}",
            "source_message_ids": [task_id], "preference": "none", "requested_workshop": None,
            "excluded_workshops": [], "due_date": None, "wants_split": False,
            "unhandled_constraints": [], "doubts_to_clarify": [], "missing_details": [],
            "workshop_rules": []}
    return {**task, **changes}


def plan_from_tasks(tasks, initial_queues, objective=None):
    """Route and plan made-up tasks as plan_allocation does, with no run folder or processing state."""
    routes = route_verified_tasks.route_tasks(tasks)
    plan = allocation_plan.plan_tasks(routes["allocate"], initial_queues, objective)
    plan.update(duplicate_order_reviews=routes["duplicate_order"],
                needs_clarification=routes["needs_clarification"], reference_tasks=routes["reference"],
                intake_review=[], task_review=[], link_review=[], non_task_messages=[], not_processed=[],
                review_warnings={})
    return plan


def task_ids(tasks):
    """Return the task IDs of a list of tasks, in order."""
    return [task["task_id"] for task in tasks]


# The declared change of 18 October 2026, as the modules must now word it.
PAST_DEADLINE_REASON = ("The delivery deadline {due} is on or before the dispatch date 2026-04-01, so no "
                        "workshop can meet it. Nothing is estimated or reserved; only a revised deadline "
                        "confirmed by the dispatcher can return this request to allocation, and the "
                        "original date stays on record.")


def past_deadline(record):
    """Return the due date of a notebook 05 decision whose deadline is on or before the dispatch date,
    otherwise None. Such a decision has an order snapshot: the notebook estimated it."""
    snapshot = record.get("order_snapshot")
    if snapshot and snapshot["due_date"] <= NOTEBOOK_SETTINGS["DISPATCH_DATE"].isoformat():
        return snapshot["due_date"]
    return None


def expected_decision(record):
    """Return notebook 05's decision record as the modules now make it.

    A past deadline becomes status "deadline_passed" with nothing calculated: no estimates,
    least-late option, ranking or snapshots. Its identity, task and warnings stay the notebook's.
    Every other record is unchanged.
    """
    due = past_deadline(record)
    if due is None:
        return record
    kept = {key: record[key] for key in ("task_id", "version", "order_id", "task", "warnings")}
    return {**kept, "status": "deadline_passed", "selected_workshop": None, "selected_metrics": None,
            "closest_option": None, "option_without_request": None,
            "reason": PAST_DEADLINE_REASON.format(due=due), "candidate_metrics": {}, "ranking": [],
            "ranking_keys": {}, "rejected_candidates": [], "alternatives": []}


def expected_summary_rows(notebook):
    """Return notebook 05's summary rows, with each past-deadline row as the modules now make it:
    the new outcome and reason, and no workshop columns."""
    changed = {record["task_id"]: expected_decision(record) for record in notebook["decisions"]
               if past_deadline(record)}
    return [{**row, "outcome": "deadline_passed", "workshop": None, "delivery_days": None,
             "days_available": None, "reason": changed[row["id"]]["reason"]} if row["id"] in changed else row
            for row in notebook["summary_rows"]]


def without_provisional_marks(plan):
    """Return the plan's summary rows without the provisional marks of 15 October 2026, as notebook 05
    made them: a provisional recommendation is a recommendation, and the warning sentence is removed."""
    rows = []
    for row in plan["summary_rows"]:
        if row["id"] in plan["review_warnings"]:
            outcome = "recommendation" if row["outcome"] == "provisional_recommendation" else row["outcome"]
            row = {**row, "outcome": outcome, "reason": row["reason"].split(" Provisional: ")[0]}
        rows.append(row)
    return rows


def assert_same_decisions(test, module, notebook):
    """The acceptance test: the module plan makes notebook 05's decisions for the same tasks.

    The same tasks in each route; every decision record and duplicate-order review equal to the
    notebook's; the same queues; and the notebook's planning order, without the routed-out tasks,
    equal to the module's. Each decision records the queues it saw, so this also proves that every
    decision came in the same order, after the same reservations. The notebook's past-deadline
    decisions are compared as expected_decision makes them.
    """
    decisions = {record["task_id"]: record for record in module["decisions"]}
    duplicates = {record["task_id"]: record for record in module["duplicate_order_reviews"]}
    reference = {record["task_id"]: expected_decision(record) for record in notebook["decisions"]}
    test.assertEqual(sorted(task_ids(module["needs_clarification"])),
                     sorted(task_ids(notebook["needs_clarification"])))
    test.assertEqual(sorted(task_ids(module["reference_tasks"])), sorted(task_ids(notebook["reference_tasks"])))
    test.assertEqual(decisions.keys() | duplicates.keys(), reference.keys())
    test.assertFalse(decisions.keys() & duplicates.keys())
    for task_id, record in {**decisions, **duplicates}.items():
        with test.subTest(task=task_id):
            test.assertEqual(record, reference[task_id])
    test.assertEqual(module["queues_before_plan"], notebook["queues_before_plan"])
    test.assertEqual(module["queues_after_plan"], notebook["queues_after_plan"])
    test.assertEqual(module["planning_order"],
                     [task_id for task_id in notebook["planning_order"] if task_id in decisions])


def assert_same_plan(test, module, notebook):
    """assert_same_decisions, plus the same summary rows and the same other plan fields.

    The declared new fields: duplicate_order_reviews (the notebook kept them in decisions),
    created_at (when the plan was made), processing_complete and not_processed (always true and
    empty here: the notebook planned complete runs only) and review_warnings (compared through the
    summary rows: a provisional row would differ from the notebook's).
    """
    assert_same_decisions(test, module, notebook)
    test.assertEqual(set(module), set(notebook) | {"duplicate_order_reviews", "created_at",
                                                   "processing_complete", "not_processed", "review_warnings"})
    test.assertTrue(module["processing_complete"])
    test.assertEqual(module["not_processed"], [])
    test.assertEqual(module["summary_rows"], expected_summary_rows(notebook))
    for key in set(notebook) - {"decisions", "planning_order", "needs_clarification", "reference_tasks",
                                "summary_rows"}:
        with test.subTest(key=key):
            test.assertEqual(module[key], notebook[key])


def read_saved_run(run_dir):
    """Return (messages, state) of a saved processing run folder."""
    messages = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))["messages"]
    state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    return messages, state


def unique_saved_runs():
    """Return the run folders in output/runs/ whose messages or state differ, oldest first.

    Each state is compared with its own folder path removed, because review records name it.
    """
    runs, seen = [], set()
    for state_file in sorted(settings_and_data.RUNS_DIR.glob("*/state.json")):
        run_dir = state_file.parent
        messages, _ = read_saved_run(run_dir)
        key = (json.dumps(messages), state_file.read_text(encoding="utf-8").replace(str(run_dir), "<run_dir>"))
        if key not in seen:
            seen.add(key)
            runs.append(run_dir)
    return runs


def notebook_plan(notebook, state, messages, run_dir):
    """Return notebook 05's plan for a processing state: its plan_allocation node, without the graph."""
    graph_state = {"processing": copy.deepcopy(state), "messages": messages, "run_dir": str(run_dir)}
    with contextlib.redirect_stdout(io.StringIO()):
        return notebook["plan_allocation"](graph_state)["plan"]


def module_plan(state, messages, run_dir):
    """Return the modules' plan for a processing state (plan_allocation with the notebook's settings)."""
    with pinned_settings(), contextlib.redirect_stdout(io.StringIO()):
        return allocation_plan.plan_allocation(run_dir, copy.deepcopy(state), messages)


class SameAsNotebook(unittest.TestCase):
    """The modules against notebook 05's code, loaded in memory as saved."""

    @classmethod
    def setUpClass(cls):
        cls.work_dir = tempfile.TemporaryDirectory()
        cls.notebook = load_notebook_05(Path(cls.work_dir.name))

    @classmethod
    def tearDownClass(cls):
        cls.work_dir.cleanup()

    def test_moved_code_has_the_notebook_logic(self):
        reference = top_level_definitions(definitions_source())
        for module_name, names in MOVED.items():
            moved = module_definitions(importlib.import_module(module_name))
            for name in names:
                with self.subTest(module=module_name, name=name):
                    self.assertEqual(logic(moved[name]), logic(reference[name]))

    def test_every_function_and_class_is_moved_or_declared_new(self):
        for module_name in MOVED | NEW | CHANGED:
            definitions = module_definitions(importlib.import_module(module_name))
            functions = {name for name, node in definitions.items() if not isinstance(node, ast.Assign)}
            declared = (set(MOVED.get(module_name, [])) | set(NEW.get(module_name, []))
                        | set(CHANGED.get(module_name, [])))
            with self.subTest(module=module_name):
                self.assertEqual(functions - declared, set())

    def test_data_equals_the_notebook(self):
        module = allocation_settings_and_data
        self.assertEqual({wid: asdict(w) for wid, w in module.WORKSHOPS.items()},
                         {wid: asdict(w) for wid, w in self.notebook["WORKSHOPS"].items()})
        self.assertEqual(module.ORDERS, self.notebook["ORDERS"])
        self.assertEqual(module.INITIAL_QUEUES, self.notebook["INITIAL_QUEUES"])

    def test_settings_come_from_config(self):
        # The pinned values are the notebook's, and config.toml gives a real date (not quoted text).
        self.assertEqual(NOTEBOOK_SETTINGS, {name: self.notebook[name] for name in NOTEBOOK_SETTINGS})
        self.assertIsInstance(allocation_settings_and_data.DISPATCH_DATE, date)


class ControlledChecks(unittest.TestCase):
    """Notebook 05's controlled checks C1-C14 on the modules: made-up tasks with hand-worked
    answers, using the real CSV values. Each plan is also compared with the notebook's plan_tasks.
    """

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        notebook = load_notebook_05(Path(cls.temp.name))
        check_tasks = [
            check_task("C2", "ORD-073", requested_workshop="W8"),  # 400 pieces, FreshStart's cap is 300
            check_task("C3", "ORD-083"),                           # due 23 March, before the dispatch date
            check_task("C4", "ORD-061", wants_split=True),         # splitting is not supported
            check_task("C5", "ORD-103", requested_workshop="W2"),  # W2 allowed but late; nobody is on time
            check_task("C6", "ORD-099"), check_task("C7", "ORD-099"),  # two requests for one order
            check_task("C8", "ORD-020", intent="question", information_sufficient=False),  # nothing to ask
            check_task("C9", None, intent="unclear", information_sufficient=False),        # nothing recorded
            check_task("C10", "ORD-053", workshop_rules=[{"workshop_id": "W1", "evidence_id": "C10:E1",
                                                          "role": "reference", "superseded_by": None}]),
        ]
        # EDD: confirmed chat dates set these deadlines, so the expected order needs no CSV values.
        edd_tasks = [
            check_task("C11", "ORD-053", due_date="2026-04-07"),  # first in the chat, but due later
            check_task("C12", "ORD-073", due_date="2026-04-05"),  # earliest deadline
            check_task("C13", "ORD-045", due_date="2026-04-05"),  # same deadline as C12; CSV date is 9 April
            check_task("C14", None, intent="unclear", information_sufficient=False),  # no deadline
        ]
        queues = allocation_settings_and_data.INITIAL_QUEUES
        with pinned_settings(), contextlib.redirect_stdout(io.StringIO()):
            # C1 is planned first, on its own; C2 to C10 start from the queues after C1, as in the
            # notebook. None of them reserves time, so their own order cannot change any answer.
            cls.first = plan_from_tasks([check_task("C1", "ORD-045")], queues)  # 150 TOPS, 8 days
            cls.checks = plan_from_tasks(check_tasks, cls.first["queues_after_plan"])
            cls.rows = {row["id"]: row for row in allocation_plan.summarize_plan(cls.checks)}
            cls.edd = plan_from_tasks(edd_tasks, queues)
            # The same tasks through notebook 05's plan_tasks, which routed inside the plan.
            cls.notebook_first = notebook["plan_tasks"]([check_task("C1", "ORD-045")], notebook["INITIAL_QUEUES"])
            cls.notebook_checks = notebook["plan_tasks"](check_tasks, cls.notebook_first["queues_after_plan"])
            cls.notebook_edd = notebook["plan_tasks"](edd_tasks, notebook["INITIAL_QUEUES"])
        cls.decision = {record["task_id"]: record for record in
                        cls.first["decisions"] + cls.checks["decisions"] + cls.checks["duplicate_order_reviews"]}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_same_decisions_as_the_notebook(self):
        for name, module, notebook in [("C1", self.first, self.notebook_first),
                                       ("C2-C10", self.checks, self.notebook_checks),
                                       ("C11-C14", self.edd, self.notebook_edd)]:
            with self.subTest(checks=name):
                assert_same_decisions(self, module, notebook)

    def test_c1_reserves_only_production_and_rework(self):
        initial = allocation_settings_and_data.INITIAL_QUEUES
        queues = self.first["queues_after_plan"]
        self.assertEqual(self.decision["C1"]["selected_workshop"], "W6")
        w6 = self.decision["C1"]["selected_metrics"]
        self.assertEqual(queues["W6"], initial["W6"] + (w6["processing_days"] + w6["expected_rework_days"]))
        self.assertTrue(all(queues[wid] == initial[wid] for wid in initial if wid != "W6"))
        # C2 to C10 are reviews, clarifications or reference questions: they reserve nothing.
        # The starting queues themselves never change.
        self.assertEqual(self.checks["queues_after_plan"], queues)
        self.assertEqual(initial, {wid: w.queue0 for wid, w in allocation_settings_and_data.WORKSHOPS.items()})

    def test_c2_to_c5_reviews(self):
        # C2 and C5: a requested workshop is never replaced; the option without it is information only.
        self.assertEqual(self.decision["C2"]["status"], "review_required")
        self.assertIn("exceeds_batch_cap=400>300", self.decision["C2"]["reason"])
        self.assertTrue(self.decision["C2"]["option_without_request"]["on_time"])
        self.assertEqual(self.decision["C5"]["closest_option"]["workshop_id"], "W2")
        self.assertIsNone(self.decision["C5"]["option_without_request"])
        # C3: a past deadline is review only, with nothing calculated and no least-late option
        # (declared change of 18 October 2026; the notebook named W1 as the least-late option).
        self.assertEqual(self.decision["C3"]["status"], "deadline_passed")
        self.assertIsNone(self.decision["C3"]["closest_option"])
        self.assertEqual(self.decision["C3"]["candidate_metrics"], {})
        self.assertEqual(self.decision["C3"]["reason"], PAST_DEADLINE_REASON.format(due="2026-03-23"))
        self.assertEqual(self.rows["C3"]["outcome"], "deadline_passed")
        # C4: an unsupported request goes to review before any calculation.
        self.assertIn("split requested", self.decision["C4"]["reason"])
        self.assertEqual(self.decision["C4"]["candidate_metrics"], {})

    def test_c6_to_c10_routing_and_reference_gate(self):
        # C6 and C7: two requests for one order are routed to review before any calculation.
        self.assertEqual(task_ids(self.checks["duplicate_order_reviews"]), ["C6", "C7"])
        self.assertTrue(all("C6, C7" in self.decision[task_id]["reason"] for task_id in ("C6", "C7")))
        # C8 and C9: a question with nothing to ask is reference; an unclear request still gets a reason.
        self.assertEqual(task_ids(self.checks["reference_tasks"]), ["C8"])
        self.assertEqual(self.rows["C9"]["outcome"], "needs_clarification")
        self.assertEqual(self.rows["C9"]["reason"], "Intent unclear; no question was recorded, so ask the requester.")
        # C10: a top workshop mentioned only as a reference is not recommended (and W1 is not reserved).
        self.assertEqual(self.decision["C10"]["status"], "review_required")
        self.assertIn("recorded as a reference", self.decision["C10"]["reason"])

    def test_c11_to_c14_earliest_deadline_first(self):
        # The earliest deadline is planned first, and equal deadlines keep chat order (C12 before C13).
        # C13 before C11 shows that the confirmed chat date (5 April) is used, not the CSV due date
        # (9 April). Declared change: C14 (unclear, no deadline) is routed out before planning, so it
        # is not in the allocator's planning order (the notebook put it last).
        self.assertEqual(self.edd["planning_order"], ["C12", "C13", "C11"])
        self.assertEqual(task_ids(self.edd["needs_clarification"]), ["C14"])

    def test_objectives_and_ties(self):
        queues = allocation_settings_and_data.INITIAL_QUEUES
        with pinned_settings(), contextlib.redirect_stdout(io.StringIO()):
            # An alternate spelling is resolved; an unknown name stops before planning.
            self.assertEqual(allocation_plan.plan_tasks([], queues, "minimise_cost")["objective_setting"],
                             "minimize_cost")
            with self.assertRaisesRegex(ValueError, "Unknown PLAN_OBJECTIVE: fastest"):
                allocation_plan.plan_tasks([], queues, "fastest")
        # Equal ranking keys keep workshop file order.
        tied = {"W2": {"tardiness_days": 0.0, "eta_days": 3.0, "cost": 100.0},
                "W1": {"tardiness_days": 0.0, "eta_days": 3.0, "cost": 100.0}}
        self.assertEqual(rank_candidates(tied, "minimize_tardiness", DEFAULT_HYBRID_WEIGHTS)[0], ["W2", "W1"])


class RoutingCases(unittest.TestCase):
    """Each route, including a ready task that shares its order with a request that is not ready."""

    def test_routes_and_notebook_decisions(self):
        tasks = [
            check_task("R1", "ORD-020", intent="question", information_sufficient=False),  # nothing to ask
            check_task("R2", "ORD-020", intent="question", information_sufficient=False,
                       doubts_to_clarify=["Which batch is meant?"]),                    # open doubt
            check_task("R3", None, intent="unclear", information_sufficient=False),     # unclear
            check_task("R4", "ORD-045"),                                                 # ready, but see R5
            check_task("R5", "ORD-045", information_sufficient=False,
                       missing_details=["deadline"]),                                    # same order, not ready
            check_task("R6", "ORD-061"),                                                 # ready, unique order
            check_task("R7", "ORD-061", intent="question", information_sufficient=False),  # a question is not
        ]                                                                                # an allocation
        routes = route_verified_tasks.route_tasks(tasks)
        self.assertEqual({route: [record["task_id"] for record in records] for route, records in routes.items()},
                         {"allocate": ["R6"], "duplicate_order": ["R4"],
                          "needs_clarification": ["R2", "R3", "R5"], "reference": ["R1", "R7"]})
        self.assertEqual(routes["duplicate_order"][0]["reason"],
                         "Allocation requests R4, R5 all name ORD-045; clarify the intended batches.")
        with tempfile.TemporaryDirectory() as temp:
            notebook = load_notebook_05(Path(temp))
            with pinned_settings(), contextlib.redirect_stdout(io.StringIO()):
                module = plan_from_tasks(tasks, allocation_settings_and_data.INITIAL_QUEUES)
                reference = notebook["plan_tasks"](tasks, notebook["INITIAL_QUEUES"])
        assert_same_decisions(self, module, reference)


class SavedRuns(unittest.TestCase):
    """Every unique saved run in output/runs/: the module plan against notebook 05's plan_allocation
    node on the same processing state. output/ is gitignored, so a fresh copy may have no runs.
    """

    def test_every_unique_saved_run(self):
        runs = unique_saved_runs()
        if not runs:
            self.skipTest("no saved runs in output/runs/")
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            notebook = load_notebook_05(work_dir / "notebook")
            for run_dir in runs:
                if run_dir == TEST_6_RUN:
                    continue  # one row differs on purpose; ProvisionalRows checks it
                with self.subTest(run=run_dir.name):
                    messages, state = read_saved_run(run_dir)
                    for side in ("notebook-plan", "module-plan"):
                        (work_dir / run_dir.name / side).mkdir(parents=True)
                    reference = notebook_plan(notebook, state, messages, work_dir / run_dir.name / "notebook-plan")
                    module = module_plan(state, messages, work_dir / run_dir.name / "module-plan")
                    # A run with unresolved inputs has provisional rows by design (ProvisionalRows
                    # checks them on Test 6); Test 8's run has 39. Compare the rest with the notebook.
                    module["summary_rows"] = without_provisional_marks(module)
                    assert_same_plan(self, module, reference)


class ProvisionalRows(unittest.TestCase):
    """Test 6's saved state (blocker cases): intake made R15 "Fastest workshop excluding QuickStitch"
    a task of its own, with no order, so it may modify R14's request. R14 keeps its recommendation,
    marked provisional; every decision and every other row stays the notebook's.
    """

    def test_r15_makes_r14_provisional(self):
        if not (TEST_6_RUN / "state.json").is_file():
            self.skipTest("Test 6's saved run is not here")
        messages, state = read_saved_run(TEST_6_RUN)
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            for side in ("notebook-plan", "module-plan"):
                (work_dir / side).mkdir()
            notebook = load_notebook_05(work_dir / "notebook")
            reference = notebook_plan(notebook, state, messages, work_dir / "notebook-plan")
            module = module_plan(state, messages, work_dir / "module-plan")
        assert_same_decisions(self, module, reference)
        expected_rows = expected_summary_rows(reference)
        self.assertEqual(len(module["summary_rows"]), len(expected_rows))
        changed = [(row, old) for row, old in zip(module["summary_rows"], expected_rows) if row != old]
        self.assertEqual([row["id"] for row, _ in changed], ["T:L0014:J1"])
        row, old = changed[0]
        self.assertEqual((old["outcome"], row["outcome"]), ("recommendation", "provisional_recommendation"))
        self.assertEqual(row["reason"], old["reason"] + " Provisional: T:L0015:J1 may modify this request. "
                         "Please confirm whether it applies; the result may need recalculation.")


class NotebookSavedPlan(unittest.TestCase):
    """The plan notebook 05 saved on 13 October against the module plan of the same processing state."""

    def test_module_plan_equals_the_saved_notebook_plan(self):
        if not (NOTEBOOK_RUN / "plan.json").is_file() or not (MODULE_RUN / "state.json").is_file():
            self.skipTest("the saved runs of 13 October are not here")
        messages, state = read_saved_run(MODULE_RUN)
        self.assertEqual((messages, state), read_saved_run(NOTEBOOK_RUN))
        saved = json.loads((NOTEBOOK_RUN / "plan.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temp:
            plan = module_plan(state, messages, Path(temp))
        # Compared as saved: JSON turns the ranking-key tuples into lists.
        assert_same_plan(self, json.loads(json.dumps(plan)), saved)


class EndToEndPlan(unittest.TestCase):
    """Notebook 05's whole graph against process_messages then plan_saved_run, on the supplied chat
    file, both from saved answers.
    """

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work_dir = Path(cls.temp.name)
        with contextlib.redirect_stdout(io.StringIO()):
            notebook = load_notebook_05(work_dir / "notebook")
            messages = notebook["read_messages"](CHAT_FILE)
            graph_state, _ = notebook["run_graph"](messages, CHAT_FILE.name)
            with offline_modules(work_dir / "modules"), pinned_settings():
                cls.run_dir, _, _ = processing_run.process_messages(messages, CHAT_FILE.name)
                cls.plan = allocation_plan.plan_saved_run(cls.run_dir)
        cls.notebook_plan = graph_state["plan"]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_same_plan_as_the_notebook_graph(self):
        assert_same_plan(self, self.plan, self.notebook_plan)

    def test_saved_plan_file_equals_the_returned_plan(self):
        saved = json.loads((self.run_dir / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual(saved, json.loads(json.dumps(self.plan)))

    def test_baseline_outcome(self):
        # The recorded baseline (docs/project-plan.md): 2 recommendations, 16 reviews (2 of them for
        # the two ORD-103 requests), 10 clarification tasks, 1 reference question, 30 of 30 messages.
        recommendations = {record["task_id"]: record["selected_workshop"] for record in self.plan["decisions"]
                           if record["status"] == "recommendation"}
        self.assertEqual(recommendations, {"T:L0009:J1": "W6", "T:L0021:J1": "W5"})
        self.assertEqual(len(self.plan["decisions"]), 16)
        self.assertEqual(task_ids(self.plan["duplicate_order_reviews"]), ["T:L0014:J1", "T:L0020:J1"])
        self.assertEqual(len(self.plan["needs_clarification"]), 10)
        self.assertEqual(task_ids(self.plan["reference_tasks"]), ["T:L0013:J1"])
        covered = {message_id for row in self.plan["summary_rows"] for message_id in row["messages"]}
        self.assertEqual(len(covered), 30)


class PlanFiles(unittest.TestCase):
    """plan.json is the latest plan, the one the pipeline reads; every plan is also kept in plan-history/."""

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        with offline_modules(Path(cls.temp.name)), contextlib.redirect_stdout(io.StringIO()):
            cls.source_run, _, _ = processing_run.process_messages(read_messages(CHAT_FILE), CHAT_FILE.name)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def fresh_run(self):
        """Return a new run folder holding a copy of the processing run's manifest and state."""
        run_dir = Path(tempfile.mkdtemp(dir=self.temp.name))
        for name in ("manifest.json", "state.json"):
            (run_dir / name).write_bytes((self.source_run / name).read_bytes())
        return run_dir

    def plan(self, run_dir, objective=None):
        """Plan run_dir with the notebook's settings, or with objective as PLAN_OBJECTIVE."""
        with (pinned_settings(), mock.patch.object(allocation_plan, "PLAN_OBJECTIVE", objective),
              contextlib.redirect_stdout(io.StringIO())):
            return allocation_plan.plan_saved_run(run_dir)

    def test_plan_file_and_history_copy_are_equal(self):
        run_dir = self.fresh_run()
        plan = self.plan(run_dir)
        (copy_file,) = (run_dir / "plan-history").iterdir()
        self.assertEqual(copy_file.read_bytes(), (run_dir / "plan.json").read_bytes())
        created_at = datetime.fromisoformat(plan["created_at"])
        self.assertEqual(copy_file.name, f"{created_at:%Y-%m-%d_%H-%M-%S_%f}_plan.json")
        # The processing files are only read.
        for name in ("manifest.json", "state.json"):
            self.assertEqual((run_dir / name).read_bytes(), (self.source_run / name).read_bytes())

    def test_a_later_plan_keeps_the_earlier_copy(self):
        # Two plans in the same second: both copies are kept, and plan.json is the later plan.
        run_dir = self.fresh_run()
        with mock.patch.object(allocation_plan, "datetime") as clock:
            clock.now.side_effect = [datetime(2026, 10, 16, 10, 5, 12, 1), datetime(2026, 10, 16, 10, 5, 12, 2)]
            first, second = self.plan(run_dir), self.plan(run_dir)
        copies = sorted((run_dir / "plan-history").iterdir())
        self.assertEqual([path.name for path in copies],
                         ["2026-10-16_10-05-12_000001_plan.json", "2026-10-16_10-05-12_000002_plan.json"])
        self.assertEqual(json.loads(copies[0].read_text(encoding="utf-8")), json.loads(json.dumps(first)))
        self.assertEqual((run_dir / "plan.json").read_bytes(), copies[1].read_bytes())
        # The creation time is the only difference: it changes no decision.
        self.assertEqual(first | {"created_at": None}, second | {"created_at": None})

    def test_objective_plan_leaves_the_default_plan(self):
        run_dir = self.fresh_run()
        self.plan(run_dir)
        default = (run_dir / "plan.json").read_bytes()
        hybrid = self.plan(run_dir, objective="hybrid")
        self.assertEqual(hybrid["objective_setting"], "hybrid")
        self.assertTrue((run_dir / "plan-hybrid.json").is_file())
        self.assertEqual((run_dir / "plan.json").read_bytes(), default)
        # Each copy's name ends with its plan file name, so the objective plan's copy names it.
        names = sorted(path.name.split("_", 3)[-1] for path in (run_dir / "plan-history").iterdir())
        self.assertEqual(names, ["plan-hybrid.json", "plan.json"])


def failing_calls(owner, name, errors, is_counted=lambda *args: True):
    """Patch owner.name so that the counted calls listed in errors raise the given exceptions.

    errors maps a call number (1 = the first counted call) to the exception that call raises; every
    other call runs as usual. is_counted picks the calls to count, such as one stage's model calls.
    """
    original = getattr(owner, name)
    counted_calls = []

    def patched(*args):
        if is_counted(*args):
            counted_calls.append(args)
            if len(counted_calls) in errors:
                raise errors[len(counted_calls)]
        return original(*args)

    return mock.patch.object(owner, name, patched)


def failing_model_calls(stage, errors):
    """Patch the recorded model so that the listed calls of one stage ("intake" or "verify") fail."""
    return failing_calls(model_calls_with_cache.RecordedModel, "__call__", errors,
                         lambda model, call_stage, *request: call_stage == stage)


def api_failure():
    """Return the error RecordedModel raises when an API request fails; it stops processing."""
    return RuntimeError("API request failed (injected); inspect its saved trace.")


class PartialRuns(unittest.TestCase):
    """An incomplete processing run still gets a plan, marked partial, with every input accounted for.

    Processing of the supplied chat (from saved answers) is stopped by an injected failure, the way a
    failed API request stops it; the run's state.json then holds the last checkpoint.
    """

    def stopped_run(self, work_dir, failure):
        """Process the supplied chat file with failure patched in; return the run folder."""
        with offline_modules(work_dir), contextlib.redirect_stdout(io.StringIO()), failure:
            with self.assertRaisesRegex(RuntimeError, "injected"):
                processing_run.process_messages(read_messages(CHAT_FILE), CHAT_FILE.name)
        (run_dir,) = (work_dir / "runs").iterdir()
        return run_dir

    def partial_plan(self, run_dir):
        """Plan run_dir with the notebook's settings and check what every partial plan must show.

        The plan is marked partial with a warning, every message and task has a row, and the run's
        manifest.json and state.json are unchanged, byte for byte. Returns the plan and the state.
        """
        saved_files = {name: (run_dir / name).read_bytes() for name in ("manifest.json", "state.json")}
        with pinned_settings(), contextlib.redirect_stdout(io.StringIO()) as printed:
            plan = allocation_plan.plan_saved_run(run_dir)
        self.assertEqual({name: (run_dir / name).read_bytes() for name in saved_files}, saved_files)
        messages, state = read_saved_run(run_dir)
        self.assertFalse(plan["processing_complete"])
        self.assertIn("WARNING: processing is incomplete", printed.getvalue())
        covered = {message_id for row in plan["summary_rows"] for message_id in row["messages"]}
        self.assertEqual(covered, {message["message_id"] for message in messages})
        self.assertLessEqual(set(state["tasks"]), {row["id"] for row in plan["summary_rows"]})
        return plan, state

    def test_stop_during_extraction(self):
        failure = failing_model_calls("intake", {2: api_failure()})
        with tempfile.TemporaryDirectory() as temp:
            plan, _ = self.partial_plan(self.stopped_run(Path(temp), failure))
        # Only the first batch (L0001-L0003) was read. Its 2 tasks were never verified, so nothing is
        # planned; they are listed with the 27 unread messages.
        self.assertEqual(plan["decisions"], [])
        kinds = Counter(record["kind"] for record in plan["not_processed"])
        self.assertEqual(kinds, Counter(message=27, task=2))

    def test_stop_during_linking(self):
        # The supplied chat has no follow-up, so it makes no link call that could fail. The failure is
        # injected when linking reaches the first batch's second item instead: a failed link call for
        # that item stops at the same checkpoint, with the item saved but not yet in a task.
        failure = failing_calls(create_and_link_tasks, "link_or_create_task", {2: api_failure()})
        with tempfile.TemporaryDirectory() as temp:
            plan, _ = self.partial_plan(self.stopped_run(Path(temp), failure))
        kinds = Counter(record["kind"] for record in plan["not_processed"])
        self.assertEqual(kinds, Counter(message=27, item=1, task=1))

    def test_stop_during_verification(self):
        failure = failing_model_calls("verify", {2: api_failure()})
        with tempfile.TemporaryDirectory() as temp:
            plan, state = self.partial_plan(self.stopped_run(Path(temp), failure))
        # The first batch's 3 tasks were verified: they are routed and planned. The 26 others are listed.
        verified = task_ids(processing_run.verified_tasks(state))
        routed = (task_ids(plan["decisions"]) + task_ids(plan["duplicate_order_reviews"])
                  + task_ids(plan["needs_clarification"]) + task_ids(plan["reference_tasks"]))
        self.assertEqual(verified, ["T:L0001:J1", "T:L0003:J1", "T:L0004:J1"])
        self.assertEqual(sorted(routed), sorted(verified))
        self.assertEqual({record["id"] for record in plan["not_processed"]}, set(state["tasks"]) - set(verified))

    def test_review_found_before_the_stop_marks_its_order_provisional(self):
        # Verification call 7 (T:L0020:J1, T:L0021:J1, T:L0022:J1) returns an unreadable answer, so
        # that batch goes to review; call 8 fails, so processing stops. T:L0014:J1, the other ORD-103
        # request besides T:L0020:J1, was verified in call 5. It is planned, and its row says that
        # T:L0020:J1 may modify it (decision of 15 October 2026; before, it was held).
        failure = failing_model_calls("verify", {7: model_calls_with_cache.ReviewRequired("Unreadable answer (injected)."),
                                                 8: api_failure()})
        with tempfile.TemporaryDirectory() as temp:
            run_dir = self.stopped_run(Path(temp), failure)
            plan, _ = self.partial_plan(run_dir)
            # plan_allocation leaves the state it is given unchanged.
            messages, state = read_saved_run(run_dir)
            with pinned_settings(), contextlib.redirect_stdout(io.StringIO()):
                allocation_plan.plan_allocation(run_dir, state, messages)
            self.assertEqual(state, read_saved_run(run_dir)[1])
        rows = {row["id"]: row for row in plan["summary_rows"]}
        self.assertIn("T:L0014:J1", plan["planning_order"])
        self.assertEqual(plan["review_warnings"]["T:L0014:J1"], ["T:L0020:J1"])
        self.assertTrue(rows["T:L0014:J1"]["reason"].endswith(
            " Provisional: T:L0020:J1 may modify this request. Please confirm whether it applies; "
            "the result may need recalculation."))
        self.assertEqual(rows["T:L0020:J1"]["reason"], "Unreadable answer (injected).")


class EveryNameIsDefined(unittest.TestCase):

    def test_no_module_uses_an_undefined_name(self):
        for module_name in MOVED | NEW | CHANGED:
            with self.subTest(module=module_name):
                self.assertEqual(undefined_names(importlib.import_module(module_name)), set())


if __name__ == "__main__":
    unittest.main()
