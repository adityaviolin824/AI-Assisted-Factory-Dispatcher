"""Tests for the dispatcher review modules (dispatcher_review/), with notebook 06 Part 8 as the
reference. Fully offline.

Run from backend/:  uv run python -m unittest discover -s tests -v

What they prove:
- the moved code has the notebook's logic (same syntax tree; docstrings and comments ignored), every
  other definition is declared changed or new, and the per-row approval code is gone (the dispatcher
  approves the whole shown review once; decision of 20 October 2026);
- with no decision, the review of every saved run (copied and planned again with today's rules) equals
  notebook 06's review and the run's plan.json: decisions, routes, planning order, queues and rows;
- the same decisions give the notebook's review, and the same decision entries when a workshop is
  chosen (the modules plan a chosen workshop first);
- notebook 06's controlled decision checks that do not use per-row approval hold for the modules,
  except that the dispatcher's workshop choice is always used, even when late, past the deadline or
  against a hard rule;
- finalize_review approves the shown allocations without planning again;
- apply_answer applies a valid answer and refuses an invalid one with nothing changed, including when
  the order or workshop data or the dispatch date changed;
- a dispatcher's quantity is the batch size in every estimate, batch cap and reservation, and must be
  a whole number of pieces above 0;
- complete resolves every blocker of a request, so Python plans it with the order and deadline the
  dispatcher gave, and refuses a request without an order;
- a request the dispatcher placed or completed skips the duplicate-order check and is planned, while
  the other requests for that order stay in review;
- a batch the dispatcher added is a row of its own, planned like any other batch and reserved once,
  even beside other batches of its order, and is refused without a valid order; a later answer can
  change or remove it, and a removed batch is listed in what changed;
- "finalize" applies a whole batch with one calculation, lists what changed and goes on to approval,
  and refuses the batch when a decision is not applied or an accepted lateness grew;
- every name the modules use is defined or imported.
No model is called, and every network connection is refused.
"""
import contextlib
import copy
import importlib
import io
import json
import shutil
import socket
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from notebook_reference import load_notebook_06_part_8, notebook_06_cell, top_level_definitions
from test_allocation_modules import NOTEBOOK_SETTINGS, pinned_settings
from test_processing_modules import logic, module_definitions, undefined_names

from dispatcher_review import dispatcher_decisions, dispatcher_plan
from dispatcher_review.dispatcher_decisions import (
    CHANGED_INPUTS, accept_late, add_batch, apply_answer, choose_workshop, clear, complete, correct,
    save_dispatcher_files, verified_tasks_by_id, warnings_checked)
from dispatcher_review.dispatcher_plan import blockers, build_dispatcher_plan, finalize_review
from order_processing_into_tasks.settings_and_data import RUNS_DIR
from task_allocation_to_workshops.allocation_plan import plan_saved_run

# The definitions each module copies unchanged from notebook 06 (Parts 1, 4a, 8a and 8b).
MOVED = {
    "dispatcher_review.dispatcher_plan": [
        "blockers", "option_text"],
    "dispatcher_review.dispatcher_decisions": ["PRINT_WIDTH", "show", "save_dispatcher_files"],
}
# Moved from notebook 06, then changed on purpose (20 October 2026). One final approval replaces
# per-row approval: RESERVING has no "approved" status, build_dispatcher_plan has no approved-first
# stage and no finalize mode, records the input signature, and choose_workshop removes no approval.
# The dispatcher decides: build_dispatcher_plan plans the tasks with a chosen workshop first, then the
# other ready tasks around them (each group earliest deadline first); named_option estimates a chosen
# workshop even when a hard rule forbids it and returns that rule; flexible_decision always uses the
# chosen workshop, accepting its lateness (also for a past deadline), and writes a broken rule in the reason. The helpers take the decisions and the run's
# tasks as arguments instead of notebook globals; correct takes its facts as a dict and refuses a
# blocker number outside the list (the notebook's -1 silently took the last blocker); entry_for and
# accept_late refuse with ValueError, not KeyError; warnings_checked takes a list; print_review takes
# the tasks and has no "after approved work" queue column. The dispatcher may give a quantity (22 October
# 2026): CORRECTABLE takes it, derive_task checks it and keeps it as a number, and batch_of and reserve
# use it through batch_pieces.
CHANGED = {
    "dispatcher_review.dispatcher_plan": [
        "CORRECTABLE", "RESERVING", "derive_task", "batch_of", "named_option", "reserve", "flexible_decision",
        "build_dispatcher_plan"],
    "dispatcher_review.dispatcher_decisions": [
        "entry_for", "correct", "choose_workshop", "accept_late", "warnings_checked", "clear",
        "open_blockers", "print_review"],
}
# Definitions that are new in the modules.
NEW = {
    "dispatcher_review.dispatcher_plan": ["added_task", "input_signature", "finalize_review"],
    "dispatcher_review.dispatcher_decisions": [
        "DECISION_FIELDS", "REQUIRED_FIELDS", "FIELD_FORMS", "CHANGED_INPUTS", "CHANGE_MARKERS", "verified_tasks_by_id",
        "complete", "add_batch",
        "valid_field", "answer_problem", "apply_decision", "apply_answer", "changed_rows", "review_saved_plan"],
}
# Notebook 06's per-row approval code, which the modules leave out.
DROPPED = ["approved_decision", "approve", "release"]

DECISIONS_RUN = "2026-10-14_14-40-08"  # the 30-request run of check_notebook_06.py
T4, T5, T7, T8, T9, T10, T11, T12, T14, T20, T21, T25 = (
    "T:L0004:J1", "T:L0005:J1", "T:L0007:J1", "T:L0008:J1", "T:L0009:J1", "T:L0010:J1", "T:L0011:J1", "T:L0012:J1",
    "T:L0014:J1", "T:L0020:J1", "T:L0021:J1", "T:L0025:J1")


def refuse_network(*args, **kwargs):
    """Stand-in for opening a network connection: these tests are offline."""
    raise AssertionError("These tests are offline; a network connection was attempted.")


def block_network():
    """Refuse every network connection until the calling test module's tests end."""
    for target, name in ((socket.socket, "connect"), (socket, "create_connection")):
        patcher = mock.patch.object(target, name, refuse_network)
        patcher.start()
        unittest.addModuleCleanup(patcher.stop)


def setUpModule():
    block_network()


@contextlib.contextmanager
def pinned_review_settings():
    """pinned_settings, with the same dispatch date in dispatcher_plan."""
    with (pinned_settings(),
          mock.patch.object(dispatcher_plan, "DISPATCH_DATE", NOTEBOOK_SETTINGS["DISPATCH_DATE"])):
        yield


def copy_and_plan(run_name, runs_dir):
    """Copy a saved run's manifest and state into runs_dir and plan the copy with today's rules.
    Returns the copy's folder and its plan.
    """
    run_dir = runs_dir / run_name
    run_dir.mkdir()
    for name in ("manifest.json", "state.json"):
        shutil.copy2(RUNS_DIR / run_name / name, run_dir / name)
    with contextlib.redirect_stdout(io.StringIO()):
        return run_dir, plan_saved_run(run_dir)


def no_decisions(run_dir):
    """Return an empty set of decisions for a run, as a new review starts."""
    return {"source_run": run_dir.name, "revision": 0, "decisions": {}}


def without(result, *keys):
    """Return a dict without the given keys."""
    return {key: value for key, value in result.items() if key not in keys}


def record(result, task_id):
    """Return the decision record of one task in a review."""
    return next(decision for decision in result["decisions"] if decision["task_id"] == task_id)


def row(result, row_id):
    """Return the summary row of one task or message in a review."""
    return next(row for row in result["summary_rows"] if row["id"] == row_id)


def answer(*decisions, then="review_again"):
    """Return a dispatcher's answer with these decisions."""
    return {"decisions": list(decisions), "then": then}


class SameCodeAsNotebook(unittest.TestCase):
    """The modules against notebook 06's cells, read as saved."""

    @classmethod
    def setUpClass(cls):
        cls.reference = {}
        for prefix in ("# Part 1", "# Part 4a", "# Part 8a", "# Part 8b"):
            cls.reference.update(top_level_definitions(notebook_06_cell(prefix)))

    def test_moved_code_has_the_notebook_logic(self):
        for module_name, names in MOVED.items():
            moved = module_definitions(importlib.import_module(module_name))
            for name in names:
                with self.subTest(module=module_name, name=name):
                    self.assertEqual(logic(moved[name]), logic(self.reference[name]))

    def test_changed_code_differs_from_the_notebook(self):
        for module_name, names in CHANGED.items():
            changed = module_definitions(importlib.import_module(module_name))
            for name in names:
                with self.subTest(module=module_name, name=name):
                    self.assertNotEqual(logic(changed[name]), logic(self.reference[name]))

    def test_every_definition_is_moved_changed_or_new(self):
        for module_name in MOVED | CHANGED | NEW:
            definitions = set(module_definitions(importlib.import_module(module_name)))
            declared = (set(MOVED.get(module_name, [])) | set(CHANGED.get(module_name, []))
                        | set(NEW.get(module_name, [])))
            with self.subTest(module=module_name):
                self.assertEqual(definitions, declared)

    def test_per_row_approval_is_gone(self):
        self.assertTrue(set(DROPPED) <= set(self.reference))
        for module_name in MOVED | CHANGED | NEW:
            definitions = module_definitions(importlib.import_module(module_name))
            with self.subTest(module=module_name):
                self.assertEqual(set(DROPPED) & set(definitions), set())


class SameResultsAsNotebook(unittest.TestCase):
    """The module review and notebook 06's review on copies of the saved runs, planned again with today's rules."""

    @classmethod
    def setUpClass(cls):
        runs_dir = Path(cls.enterClassContext(tempfile.TemporaryDirectory()))
        cls.runs = {}
        with pinned_review_settings():
            for folder in sorted(RUNS_DIR.iterdir()):
                if (folder / "plan.json").exists():
                    cls.runs[folder.name] = copy_and_plan(folder.name, runs_dir)

    def test_review_without_decisions_equals_the_notebook_and_the_plan(self):
        self.assertIn(DECISIONS_RUN, self.runs)
        for run_name, (run_dir, plan) in self.runs.items():
            with self.subTest(run=run_name), pinned_review_settings():
                notebook = load_notebook_06_part_8(run_dir)
                expected = notebook["build_dispatcher_plan"](run_dir, no_decisions(run_dir))
                review = build_dispatcher_plan(run_dir, no_decisions(run_dir))
                self.assertEqual(expected.pop("queues_after_approved"), expected["queues_before_plan"])
                self.assertEqual(without(review, "created_at", "input_signature"), without(expected, "created_at"))
                for key in ("processing_complete", "planning_order", "decisions", "duplicate_order_reviews",
                            "needs_clarification", "reference_tasks", "intake_review", "task_review",
                            "link_review", "non_task_messages", "not_processed", "review_warnings",
                            "queues_before_plan", "queues_after_plan"):
                    self.assertEqual(review[key], plan[key], key)
                self.assertEqual([without(row, "final") for row in review["summary_rows"]], plan["summary_rows"])
                self.assertEqual((review["final_ids"], review["status"]), ([], "draft"))

    def test_same_decisions_give_the_notebook_review(self):
        run_dir, _ = self.runs[DECISIONS_RUN]
        with pinned_review_settings():
            notebook = load_notebook_06_part_8(run_dir)
            tasks = verified_tasks_by_id(run_dir)
            decisions = no_decisions(run_dir)
            notebook_review = notebook["build_dispatcher_plan"](run_dir, notebook["decisions"])
            module_review = build_dispatcher_plan(run_dir, decisions)
            steps = [
                (lambda: notebook["correct"](T5, resolves=[0, 1], due_date="2026-04-20"),
                 lambda: correct(decisions, tasks, T5, {"due_date": "2026-04-20"}, [0, 1])),
                (lambda: notebook["accept_late"](notebook_review, T12),
                 lambda: accept_late(decisions, tasks, module_review, T12)),
                (lambda: notebook["warnings_checked"](T9, "L0019"),
                 lambda: warnings_checked(decisions, tasks, T9, ["L0019"])),
                (lambda: notebook["choose_workshop"](T8, "W1"),
                 lambda: choose_workshop(decisions, tasks, T8, "W1")),
                (lambda: notebook["clear"](T8), lambda: clear(decisions, T8)),
            ]
            for number, (notebook_step, module_step) in enumerate(steps, start=1):
                notebook_step()
                module_step()
                notebook_review = notebook["build_dispatcher_plan"](run_dir, notebook["decisions"])
                module_review = build_dispatcher_plan(run_dir, decisions)
                with self.subTest(step=number):
                    self.assertEqual(decisions, notebook["decisions"])
                    if T8 in decisions["decisions"]:
                        # The notebook plans T8 in deadline order; the modules plan the chosen workshop first.
                        self.assertEqual(module_review["planning_order"][0], T8)
                        self.assertNotEqual(notebook_review["planning_order"][0], T8)
                    else:
                        self.assertEqual(without(module_review, "created_at", "input_signature"),
                                         without(notebook_review, "created_at", "queues_after_approved"))
            self.assertEqual(record(module_review, T12)["status"], "accepted_late")


class ControlledDecisions(unittest.TestCase):
    """Notebook 06's controlled decision checks (check_notebook_06.py) without per-row approval, on a
    copy of the 30-request run. The decisions are examples that nobody made.
    """

    def setUp(self):
        self.enterContext(pinned_review_settings())
        self.run_dir, _ = copy_and_plan(DECISIONS_RUN, Path(self.enterContext(tempfile.TemporaryDirectory())))
        self.tasks = verified_tasks_by_id(self.run_dir)
        self.decisions = no_decisions(self.run_dir)

    def build(self):
        return build_dispatcher_plan(self.run_dir, self.decisions)

    def test_a_correction_resolves_only_the_named_blockers(self):
        self.assertEqual(row(self.build(), T5)["outcome"], "needs_clarification")
        correct(self.decisions, self.tasks, T5, {"due_date": "2026-04-20"}, [0])
        self.assertEqual(row(self.build(), T5)["outcome"], "needs_clarification")  # blocker [1] is still open
        correct(self.decisions, self.tasks, T5, {}, [1])
        entry = copy.deepcopy(self.decisions["decisions"][T5])
        correct(self.decisions, self.tasks, T5, {"due_date": "2026-04-20"}, [1])  # the same again changes nothing
        self.assertEqual((self.decisions["decisions"][T5], entry["decision_version"]), (entry, 1))
        first, second = self.build(), self.build()
        self.assertEqual(without(first, "created_at"), without(second, "created_at"))
        corrected = record(first, T5)
        self.assertEqual((corrected["status"], corrected["version"]), ("recommendation", self.tasks[T5]["version"] + 1))
        self.assertEqual(corrected["order_snapshot"]["due_date"], "2026-04-20")
        self.assertEqual(corrected["task"]["dispatcher"], {
            "facts": {"due_date": "2026-04-20"}, "resolved": blockers(self.tasks[T5]),
            "recorded": {"due_date": self.tasks[T5]["due_date"]}, "recorded_deadline": "2026-04-26"})

    def test_a_completed_request_is_planned_with_the_dispatchers_facts(self):
        # A corrected order ID alone leaves T10's questions open (what the frontend sent before 22 October 2026).
        correct(self.decisions, self.tasks, T10, {"order_id": "ORD-041"}, [])
        self.assertEqual(row(self.build(), T10)["outcome"], "needs_clarification")
        # Completed, every blocker is resolved: ORD-041 is planned with its due date in orders.csv.
        complete(self.decisions, self.tasks, T10, {"order_id": "ORD-041"})
        planned = record(self.build(), T10)
        self.assertEqual((planned["status"], planned["order_snapshot"]["due_date"]), ("recommendation", "2026-04-21"))
        self.assertEqual(planned["task"]["dispatcher"]["resolved"], blockers(self.tasks[T10]))
        # T7 names its order but its intent is unclear: completing it with a deadline makes it an allocation.
        complete(self.decisions, self.tasks, T7, {"due_date": "2026-04-20"})
        planned = record(self.build(), T7)
        self.assertEqual((planned["status"], planned["task"]["intent"]), ("recommendation", "allocation"))

    def test_completing_a_request_needs_its_order(self):
        with self.assertRaisesRegex(ValueError, f"complete {T10}: give the order ID."):
            complete(self.decisions, self.tasks, T10, {"due_date": "2026-04-20"})

    def test_completing_a_request_uses_its_saved_corrections(self):
        # Review again: an earlier, saved correction gave T10 its order, so completing it needs no order again.
        correct(self.decisions, self.tasks, T10, {"order_id": "ORD-041"}, [])
        complete(self.decisions, self.tasks, T10, {})
        self.assertEqual(record(self.build(), T10)["status"], "recommendation")
        # T8 was corrected to a question; completing it makes it an allocation again, back in its first outcome.
        first_outcome = row(build_dispatcher_plan(self.run_dir, no_decisions(self.run_dir)), T8)["outcome"]
        correct(self.decisions, self.tasks, T8, {"intent": "question"}, [])
        self.assertEqual(row(self.build(), T8)["outcome"], "reference")
        complete(self.decisions, self.tasks, T8, {})
        completed = self.build()
        self.assertEqual((row(completed, T8)["outcome"], record(completed, T8)["task"]["intent"]),
                         (first_outcome, "allocation"))

    def test_a_dispatchers_quantity_is_the_batch_size(self):
        # T9's order has 150 pieces in orders.csv, within W8's 300-piece cap.
        self.assertIn("W8", record(self.build(), T9)["candidate_metrics"])
        correct(self.decisions, self.tasks, T9, {"quantity": "301"}, [])
        review = self.build()
        planned = record(review, T9)
        self.assertEqual((planned["status"], planned["order_snapshot"]["pieces"]), ("recommendation", 301))
        self.assertIn("exceeds_batch_cap=301>300",
                      [rejected["reason"] for rejected in planned["rejected_candidates"] if rejected["workshop_id"] == "W8"])
        self.assertEqual(planned["task"]["dispatcher"]["recorded"], {"quantity": None})  # orders.csv applied before
        # Each workshop's reserved pieces are the batch sizes reserved there, T9's 301 among them.
        workshop = planned["selected_workshop"]
        reserved_here = [record(review, task_id) for task_id in review["reservation_order"]
                         if record(review, task_id)["selected_workshop"] == workshop]
        self.assertIn(planned, reserved_here)
        self.assertEqual(review["pieces_after_plan"][workshop],
                         sum(decision["order_snapshot"]["pieces"] for decision in reserved_here))

    def test_a_quantity_must_be_a_whole_number_above_0(self):
        for quantity in ("0", "-5", "2.5", "300 pieces", ""):
            with self.subTest(quantity=quantity):
                decisions = no_decisions(self.run_dir)
                correct(decisions, self.tasks, T9, {"quantity": quantity}, [])
                result = build_dispatcher_plan(self.run_dir, decisions)
                self.assertIn(f"{quantity!r} is not a whole number of pieces above 0", row(result, T9)["reason"])
                self.assertEqual(record(result, T9)["order_snapshot"]["pieces"], 150)

    def test_a_placed_or_completed_request_skips_the_duplicate_order_check(self):
        # T14 and T20 both name ORD-103, so both are duplicate-order reviews.
        self.assertEqual([review["task_id"] for review in self.build()["duplicate_order_reviews"]], [T14, T20])
        # Before 22 October 2026 a workshop chosen for T14 was saved but never used.
        choose_workshop(self.decisions, self.tasks, T14, "W1")
        review = self.build()
        placed = record(review, T14)
        self.assertEqual((placed["status"] in ("dispatcher_choice", "accepted_late"), placed["selected_workshop"]),
                         (True, "W1"))
        self.assertIn(T14, review["reservation_order"])
        self.assertEqual([review["task_id"] for review in review["duplicate_order_reviews"]], [T20])
        # Completing T20 too makes it a second batch of ORD-103: both are planned, none is in review.
        complete(self.decisions, self.tasks, T20, {})
        review = self.build()
        self.assertEqual(review["duplicate_order_reviews"], [])
        self.assertEqual([task_id for task_id in review["planning_order"] if task_id in (T14, T20)], [T14, T20])

    def test_an_added_batch_is_planned_and_reserved_once(self):
        # T10 is completed as 300 pieces of ORD-041; the dispatcher adds the other 300 as a batch of its own.
        complete(self.decisions, self.tasks, T10, {"order_id": "ORD-041", "quantity": "300"})
        self.assertEqual(add_batch(self.decisions, {"order_id": "ORD-041", "quantity": "300"}), "ADD-1")
        review = self.build()
        added = record(review, "ADD-1")
        self.assertEqual((added["status"], added["order_snapshot"]["pieces"], added["order_snapshot"]["due_date"]),
                         ("recommendation", 300, "2026-04-21"))  # no deadline given: orders.csv's
        self.assertEqual((added["task"]["added"], added["task"]["source_message_ids"]), (True, []))
        self.assertEqual(review["reservation_order"].count("ADD-1"), 1)
        workshop = added["selected_workshop"]
        reserved_here = [record(review, task_id) for task_id in review["reservation_order"]
                         if record(review, task_id)["selected_workshop"] == workshop]
        self.assertEqual(review["pieces_after_plan"][workshop],
                         sum(decision["order_snapshot"]["pieces"] for decision in reserved_here))
        # The other batch of ORD-041 is named, and neither is sent to the duplicate-order review.
        self.assertTrue(row(review, "ADD-1")["reason"].startswith(
            f"Added by the dispatcher. Other planned batches of ORD-041: {T10}. "))
        self.assertEqual(record(review, T10)["status"], "recommendation")
        self.assertNotIn("ORD-041", [review["order_id"] for review in review["duplicate_order_reviews"]])

    def test_two_added_batches_of_one_order_are_both_planned(self):
        # A split: ORD-041 sent as two batches, the second to a workshop the dispatcher chose.
        add_batch(self.decisions, {"order_id": "ORD-041", "quantity": "300", "preference": "quality"})
        self.assertEqual(add_batch(self.decisions, {"order_id": "ORD-041", "quantity": "300"}, "W2"), "ADD-2")
        review = self.build()
        first, second = record(review, "ADD-1"), record(review, "ADD-2")
        self.assertEqual((first["status"], first["objective"]), ("recommendation", "minimize_defects"))
        self.assertEqual((second["status"] in ("dispatcher_choice", "accepted_late"), second["selected_workshop"]),
                         (True, "W2"))
        self.assertEqual([task_id for task_id in review["reservation_order"] if task_id.startswith("ADD-")],
                         ["ADD-2", "ADD-1"])  # the chosen workshop is planned first
        self.assertIn("Other planned batches of ORD-041: ADD-2.", row(review, "ADD-1")["reason"])

    def test_an_added_batch_needs_a_valid_order(self):
        with self.assertRaisesRegex(ValueError, "add_batch: give the order ID."):
            add_batch(self.decisions, {"quantity": "100"})
        self.assertEqual(self.decisions, no_decisions(self.run_dir))
        add_batch(self.decisions, {"order_id": "ORD-999"})
        review = self.build()
        self.assertEqual(review["decision_problems"], {"ADD-1": ["ORD-999 is not in orders.csv"]})
        self.assertNotIn("ADD-1", review["reservation_order"])

    def test_a_wrong_blocker_number_is_refused(self):
        for number in (-1, len(blockers(self.tasks[T5]))):
            with self.subTest(number=number):
                with self.assertRaisesRegex(ValueError, rf"has no blocker \[{number}\]"):
                    correct(self.decisions, self.tasks, T5, {}, [number])

    def test_an_unknown_order_id_is_not_applied_and_shown(self):
        correct(self.decisions, self.tasks, T10, {"order_id": "ORD-999"}, [])
        result = self.build()
        self.assertEqual(row(result, T10)["outcome"], "needs_clarification")
        self.assertIn("Dispatcher decision not applied: ORD-999 is not in orders.csv.", row(result, T10)["reason"])

    def test_a_past_deadline_returns_with_a_revised_date(self):
        correct(self.decisions, self.tasks, T4, {"due_date": "2026-04-01"}, [])
        self.assertEqual(record(self.build(), T4)["status"], "deadline_passed")
        correct(self.decisions, self.tasks, T4, {"due_date": "2026-04-24"}, [])
        revised = record(self.build(), T4)
        self.assertEqual(revised["status"], "recommendation")
        self.assertEqual(revised["task"]["dispatcher"]["recorded_deadline"], "2026-04-01")

    def test_a_past_deadline_takes_the_dispatchers_choice_late(self):
        correct(self.decisions, self.tasks, T4, {"due_date": "2026-04-01"}, [])
        choose_workshop(self.decisions, self.tasks, T4, "W1")
        review = self.build()
        chosen = record(review, T4)
        self.assertEqual((chosen["status"], chosen["selected_workshop"]), ("accepted_late", "W1"))
        self.assertGreater(chosen["selected_metrics"]["tardiness_days"], 0)
        self.assertIn("The deadline 2026-04-01 stays on record.", chosen["reason"])
        self.assertEqual(review["reservation_order"][0], T4)

    def test_a_manual_choice_is_always_used_and_a_broken_rule_is_written(self):
        self.assertEqual(record(self.build(), T8)["option_without_request"]["workshop_id"], "W6")
        choose_workshop(self.decisions, self.tasks, T8, "W1")
        choose_workshop(self.decisions, self.tasks, T11, "W7")
        choose_workshop(self.decisions, self.tasks, "T:L0024:J1", "W4")
        result = self.build()
        chosen = record(result, T8)
        self.assertEqual((chosen["status"], chosen["selected_workshop"], chosen["task"]["requested_workshop"]),
                         ("dispatcher_choice", "W1", "W8"))
        self.assertIn("It overrides the requested W8.", chosen["reason"])
        for task_id, workshop_id, rule in ((T11, "W7", "status=SUSPENDED"),
                                           ("T:L0024:J1", "W4", "cannot_make_category=TOPS")):
            with self.subTest(task=task_id):
                self.assertEqual(record(result, task_id)["selected_workshop"], workshop_id)
                self.assertIn(task_id, result["reservation_order"])
                self.assertIn(f"It overrides the hard rule {rule}.", record(result, task_id)["reason"])
        choose_workshop(self.decisions, self.tasks, T8, "W8")  # the latest choice replaces W1
        over_cap = record(self.build(), T8)
        self.assertEqual(over_cap["selected_workshop"], "W8")
        self.assertIn("It overrides the hard rule exceeds_batch_cap=400>300.", over_cap["reason"])

    def test_chosen_workshops_are_planned_first(self):
        choose_workshop(self.decisions, self.tasks, T25, "W6")
        review = self.build()
        self.assertEqual(review["planning_order"][0], T25)
        self.assertEqual(review["reservation_order"][0], T25)
        # Nothing is ahead of the chosen task but the workshop's own starting queue.
        self.assertEqual(record(review, T25)["selected_metrics"]["queue_days"], review["queues_before_plan"]["W6"])
        self.assertEqual(review["planning_order"][1:], [task_id for task_id in self.build_without(T25)["planning_order"]
                                                         if task_id != T25])

    def build_without(self, task_id):
        """Return the review with the decision entry of one task left out."""
        decisions = copy.deepcopy(self.decisions)
        decisions["decisions"].pop(task_id)
        return build_dispatcher_plan(self.run_dir, decisions)

    def test_lateness_is_used_only_as_accepted(self):
        review = self.build()
        late = record(review, T12)
        self.assertEqual((late["status"], late["closest_option"]["workshop_id"]), ("review_required", "W5"))
        accept_late(self.decisions, self.tasks, review, T12)
        accepted = record(self.build(), T12)
        self.assertEqual((accepted["status"], accepted["selected_workshop"]), ("accepted_late", "W5"))
        self.assertEqual(accepted["selected_metrics"]["tardiness_days"], late["closest_option"]["tardiness_days"])
        self.assertGreater(accepted["selected_metrics"]["tardiness_days"], 0)
        self.assertEqual(accepted["order_snapshot"]["due_date"], "2026-04-10")
        self.assertIn("stays on record", accepted["reason"])
        accept_late(self.decisions, self.tasks, review, T12, max_days=0.01)
        self.assertIn("does not cover it", record(self.build(), T12)["reason"])

    def test_a_late_choice_is_used_at_once_and_worse_accepted_lateness_returns_to_review(self):
        # T12's late W5 option is accepted. Then the dispatcher chooses W5, late too, for T11: the choice
        # is used at once and planned first, so W5 is busier and T12's accepted lateness no longer covers it.
        accept_late(self.decisions, self.tasks, self.build(), T12)
        self.assertEqual(record(self.build(), T12)["status"], "accepted_late")
        choose_workshop(self.decisions, self.tasks, T11, "W5")
        worse = self.build()
        chosen = record(worse, T11)
        self.assertEqual((chosen["status"], chosen["selected_workshop"]), ("accepted_late", "W5"))
        self.assertGreater(chosen["selected_metrics"]["tardiness_days"], 0)
        self.assertIn("Lateness accepted by the dispatcher", chosen["reason"])
        self.assertEqual(record(worse, T12)["status"], "review_required")
        self.assertIn("does not cover it", record(worse, T12)["reason"])
        self.assertNotIn(T12, worse["reservation_order"])

    def test_finalize_changes_only_the_labels(self):
        choose_workshop(self.decisions, self.tasks, T8, "W1")
        accept_late(self.decisions, self.tasks, self.build(), T12)
        with mock.patch.object(dispatcher_plan, "possibly_affected_tasks", lambda state: {T9: ["L0019"]}):
            draft = self.build()
            shown = copy.deepcopy(draft)
            final = finalize_review(draft)
            self.assertEqual(draft, shown)  # the review passed in is not changed
            numbers = ("planning_order", "queues_before_plan", "queues_after_plan", "pieces_after_plan",
                       "reservation_order", "review_warnings", "created_at", "input_signature")
            self.assertTrue(all(final[key] == draft[key] for key in numbers))
            self.assertEqual(final["status"], "final")
            self.assertEqual(sorted(final["final_ids"]), sorted([T8, T12, T21, T25]))
            for task_id in (T8, T12, T21, T25):
                before, after = record(draft, task_id), record(final, task_id)
                self.assertEqual(after["status"], "approved")
                self.assertEqual(without(after, "status"), without(before, "status"))
                self.assertEqual(without(row(final, task_id), "outcome", "final"),
                                 without(row(draft, task_id), "outcome", "final"))
            # T9's recommendation has an unchecked warning, so it stays provisional and unresolved.
            self.assertEqual((row(final, T9)["outcome"], row(final, T9)["final"]), ("provisional_recommendation", False))
            self.assertIn(T9, final["unresolved_ids"])
            self.assertTrue(all(row(final, row_id)["outcome"] == row(draft, row_id)["outcome"]
                                for row_id in final["unresolved_ids"]))
            warnings_checked(self.decisions, self.tasks, T9, ["L0019"])
            self.assertIn(T9, finalize_review(self.build())["final_ids"])

    def test_saving_writes_the_two_files_and_their_history_copies(self):
        source = {name: (self.run_dir / name).read_bytes() for name in ("manifest.json", "state.json", "plan.json")}
        choose_workshop(self.decisions, self.tasks, T8, "W1")
        final = finalize_review(self.build())
        with contextlib.redirect_stdout(io.StringIO()):
            save_dispatcher_files(self.run_dir, self.decisions, final)
        saved = json.loads((self.run_dir / "dispatcher-plan.json").read_text(encoding="utf-8"))
        self.assertEqual((saved["decisions_revision"], saved["final_ids"]), (1, final["final_ids"]))
        self.assertEqual(json.loads((self.run_dir / "dispatcher-decisions.json").read_text(encoding="utf-8")),
                         self.decisions)
        self.assertEqual(len(list((self.run_dir / "plan-history").glob("*_dispatcher-*.json"))), 2)
        self.assertTrue(all((self.run_dir / name).read_bytes() == data for name, data in source.items()))


class ApplyAnswer(unittest.TestCase):
    """The dispatcher's answers on a copy of the 30-request run."""

    @classmethod
    def setUpClass(cls):
        cls.enterClassContext(pinned_review_settings())
        cls.run_dir, _ = copy_and_plan(DECISIONS_RUN, Path(cls.enterClassContext(tempfile.TemporaryDirectory())))
        cls.tasks = verified_tasks_by_id(cls.run_dir)
        cls.review = build_dispatcher_plan(cls.run_dir, no_decisions(cls.run_dir))

    def assert_refused(self, reply, message, decisions):
        """An answer is refused: the same decisions and review come back, "review_again" and the reason."""
        decisions_before = copy.deepcopy(decisions)
        result = apply_answer(self.run_dir, decisions, self.review, reply)
        self.assertIs(result[0], decisions)
        self.assertIs(result[1], self.review)
        self.assertEqual(result[2], "review_again")
        self.assertIn(message, result[3])
        self.assertEqual(decisions, decisions_before)

    def test_each_decision_calls_its_helper(self):
        cases = [
            ({"decision": "correct", "task_id": T5, "facts": {"due_date": "2026-04-20"}, "resolves": [0, 1]},
             lambda decisions: correct(decisions, self.tasks, T5, {"due_date": "2026-04-20"}, [0, 1])),
            ({"decision": "complete", "task_id": T10, "facts": {"order_id": "ORD-041"}},
             lambda decisions: complete(decisions, self.tasks, T10, {"order_id": "ORD-041"})),
            ({"decision": "add_batch", "facts": {"order_id": "ORD-041"}, "workshop_id": "W8"},
             lambda decisions: add_batch(decisions, {"order_id": "ORD-041"}, "W8")),
            ({"decision": "choose_workshop", "task_id": T8, "workshop_id": "W1"},
             lambda decisions: choose_workshop(decisions, self.tasks, T8, "W1")),
            ({"decision": "accept_late", "task_id": T12},
             lambda decisions: accept_late(decisions, self.tasks, self.review, T12)),
            ({"decision": "accept_late", "task_id": T12, "max_days": 2},
             lambda decisions: accept_late(decisions, self.tasks, self.review, T12, 2)),
            ({"decision": "warnings_checked", "task_id": T9, "row_ids": ["L0019"]},
             lambda decisions: warnings_checked(decisions, self.tasks, T9, ["L0019"])),
        ]
        for entry, helper in cases:
            with self.subTest(decision=entry["decision"]):
                decisions = no_decisions(self.run_dir)
                applied, review, then, refusal = apply_answer(self.run_dir, decisions, self.review, answer(entry))
                expected = no_decisions(self.run_dir)
                helper(expected)
                self.assertEqual((applied, then, refusal), (expected, "review_again", None))
                self.assertEqual(decisions, no_decisions(self.run_dir))  # applied to a copy
                self.assertEqual(without(review, "created_at"),
                                 without(build_dispatcher_plan(self.run_dir, expected), "created_at"))
        decisions = no_decisions(self.run_dir)
        choose_workshop(decisions, self.tasks, T8, "W1")
        applied, _, _, _ = apply_answer(self.run_dir, decisions, self.review,
                                        answer({"decision": "clear", "task_id": T8}))
        self.assertEqual(applied, no_decisions(self.run_dir))

    def test_approve_all_keeps_the_shown_review(self):
        decisions = no_decisions(self.run_dir)
        with mock.patch.object(dispatcher_decisions, "build_dispatcher_plan") as build:
            result = apply_answer(self.run_dir, decisions, self.review, answer(then="approve_all"))
        build.assert_not_called()
        self.assertIs(result[0], decisions)
        self.assertIs(result[1], self.review)
        self.assertEqual(result[2:], ("approve_all", None))

    def test_finalize_applies_every_decision_at_once_and_approves(self):
        # One batch, calculated once: a workshop choice, a checked warning and accepted lateness together.
        entries = [{"decision": "choose_workshop", "task_id": T8, "workshop_id": "W1"},
                   {"decision": "warnings_checked", "task_id": T9, "row_ids": ["L0019"]},
                   {"decision": "accept_late", "task_id": T12}]
        decisions = no_decisions(self.run_dir)
        with mock.patch.object(dispatcher_decisions, "build_dispatcher_plan", wraps=build_dispatcher_plan) as build:
            applied, review, then, refusal = apply_answer(self.run_dir, decisions, self.review,
                                                          answer(*entries, then="finalize"))
        self.assertEqual(build.call_count, 1)
        expected = no_decisions(self.run_dir)
        choose_workshop(expected, self.tasks, T8, "W1")
        warnings_checked(expected, self.tasks, T9, ["L0019"])
        accept_late(expected, self.tasks, self.review, T12)
        self.assertEqual((applied, then, refusal), (expected, "approve_all", None))
        self.assertEqual(decisions, no_decisions(self.run_dir))  # applied to a copy
        self.assertEqual(without(review, "created_at", "changes"),
                         without(build_dispatcher_plan(self.run_dir, expected), "created_at"))
        # changes lists every row whose outcome, workshop or delivery estimate differs from the shown review.
        def summary(row):
            return row["outcome"], row["workshop"], row["delivery_days"]
        shown = {row["id"]: row for row in self.review["summary_rows"]}
        self.assertEqual([change["id"] for change in review["changes"]],
                         [row["id"] for row in review["summary_rows"] if summary(row) != summary(shown[row["id"]])])
        changes = {change["id"]: change for change in review["changes"]}
        self.assertEqual(changes[T8]["after"]["workshop"], "W1")
        self.assertEqual((changes[T12]["before"]["outcome"], changes[T12]["after"]["outcome"]),
                         ("review_required", "accepted_late"))
        self.assertEqual(changes[T12]["after"]["reason"], next(row for row in review["summary_rows"] if row["id"] == T12)["reason"])

    def test_finalize_lists_an_added_batch_as_a_new_row(self):
        entry = {"decision": "add_batch", "facts": {"order_id": "ORD-041", "quantity": "250"}}
        _, review, then, refusal = apply_answer(self.run_dir, no_decisions(self.run_dir), self.review,
                                                answer(entry, then="finalize"))
        self.assertEqual((then, refusal), ("approve_all", None))
        added = next(change for change in review["changes"] if change["id"] == "ADD-1")
        self.assertEqual((added["before"], added["after"]["outcome"]), (None, "recommendation"))
        self.assertEqual(finalize_review(review)["final_ids"].count("ADD-1"), 1)

    def test_an_added_batch_can_be_changed_or_removed_later(self):
        # The decisions already hold ADD-1, as after an approval, so a later answer can name it.
        decisions = no_decisions(self.run_dir)
        add_batch(decisions, {"order_id": "ORD-041", "quantity": "250"})
        review = build_dispatcher_plan(self.run_dir, decisions)
        _, moved, _, refusal = apply_answer(self.run_dir, decisions, review, answer(
            {"decision": "choose_workshop", "task_id": "ADD-1", "workshop_id": "W2"}))
        self.assertEqual((refusal, row(moved, "ADD-1")["workshop"]), (None, "W2"))
        removed, after, then, refusal = apply_answer(self.run_dir, decisions, review, answer(
            {"decision": "clear", "task_id": "ADD-1"}, then="finalize"))
        self.assertEqual((then, refusal), ("approve_all", None))
        self.assertEqual(removed, no_decisions(self.run_dir))
        self.assertNotIn("ADD-1", [summary_row["id"] for summary_row in after["summary_rows"]])
        # The removed batch comes last in what changed, with its earlier row and no later one.
        earlier = row(review, "ADD-1")
        self.assertEqual(after["changes"][-1], {
            "id": "ADD-1", "order_id": "ORD-041", "after": None,
            "before": {field: earlier[field] for field in ("outcome", "workshop", "delivery_days", "reason")}})

    def test_finalize_refuses_lateness_that_grew(self):
        # T12's late W5 option is accepted, but choosing W5 for T11 in the same batch makes T12 later.
        entries = [{"decision": "accept_late", "task_id": T12},
                   {"decision": "choose_workshop", "task_id": T11, "workshop_id": "W5"}]
        self.assert_refused(answer(*entries, then="finalize"), f"Not applied: {T12}: Late: ", no_decisions(self.run_dir))

    def test_invalid_answers_are_refused_with_nothing_changed(self):
        choose = {"decision": "choose_workshop", "task_id": T8, "workshop_id": "W1"}
        cases = [
            ("not a dict", 'An answer must be {"decisions"'),
            ({"decisions": []}, 'An answer must be {"decisions"'),
            ({"decisions": [], "then": "review_again", "note": "x"}, 'An answer must be {"decisions"'),
            (answer(then="save_draft"),
             "\"then\" must be \"review_again\", \"approve_all\" or \"finalize\", not 'save_draft'"),
            ({"decisions": "clear", "then": "review_again"}, '"decisions" must be a list'),
            (answer(choose, then="approve_all"), "Approve all takes no decisions"),
            (answer({"decision": "accept_late", "task_id": T12}, choose), "Send accept_late alone"),
            (answer({"decision": "approve", "task_id": T9}), "Unknown decision 'approve'"),
            (answer({"decision": "release", "task_id": T9}), "Unknown decision 'release'"),
            (answer({"decision": ["clear"], "task_id": T9}), "Unknown decision ['clear']"),
            (answer({"decision": "clear", "task_id": "T:L0999:J1"}), "'T:L0999:J1' is not a verified task"),
            # No batch was added, so ADD-1 names nothing.
            (answer({"decision": "clear", "task_id": "ADD-1"}), "'ADD-1' is not a verified task or added batch"),
            (answer({"decision": "clear", "task_id": ["T:L0009:J1"]}), "is not a verified task"),
            (answer({"decision": "choose_workshop", "task_id": T8, "workshop": "W1"}), "unknown field workshop"),
            (answer({"decision": "choose_workshop", "task_id": T8}), "workshop_id is missing"),
            (answer({"decision": "warnings_checked", "task_id": T9}), "row_ids is missing"),
            (answer({"decision": "choose_workshop", "task_id": T8, "workshop_id": 1}), "workshop_id must be"),
            (answer({"decision": "correct", "task_id": T5, "facts": {"due_date": 20}}), "facts must be"),
            (answer({"decision": "correct", "task_id": T5, "facts": ["due_date"]}), "facts must be"),
            (answer({"decision": "correct", "task_id": T5, "resolves": [True]}), "resolves must be"),
            (answer({"decision": "correct", "task_id": T5, "resolves": "0"}), "resolves must be"),
            (answer({"decision": "accept_late", "task_id": T12, "max_days": -1}), "max_days must be"),
            (answer({"decision": "accept_late", "task_id": T12, "max_days": float("inf")}), "max_days must be"),
            (answer({"decision": "accept_late", "task_id": T12, "max_days": "2"}), "max_days must be"),
            (answer({"decision": "warnings_checked", "task_id": T9, "row_ids": "L0019"}), "row_ids must be"),
            (answer({"decision": "correct", "task_id": T5, "resolves": [-1]}), f"{T5} has no blocker [-1]"),
            (answer({"decision": "correct", "task_id": T5, "resolves": [2]}), f"{T5} has no blocker [2]"),
            (answer({"decision": "accept_late", "task_id": T5}), f"{T5} has no allocation record in this review"),
            (answer({"decision": "accept_late", "task_id": T21}), f"{T21} has no late option in this review"),
            (answer({"decision": "choose_workshop", "task_id": T8, "workshop_id": "W99"}),
             f"Not applied: {T8}: W99 is not a workshop."),
            (answer({"decision": "choose_workshop", "task_id": T8, "workshop_id": "W99"}, then="finalize"),
             f"Not applied: {T8}: W99 is not a workshop."),
            (answer({"decision": "correct", "task_id": T10, "facts": {"order_id": "ORD-999"}}),
             f"Not applied: {T10}: ORD-999 is not in orders.csv."),
            (answer({"decision": "correct", "task_id": T5, "facts": {"due_date": "20 April"}}),
             "'20 April' is not a date written YYYY-MM-DD"),
            (answer({"decision": "correct", "task_id": T5, "facts": {"pieces": "100"}}),
             "pieces cannot be corrected here"),
            (answer({"decision": "correct", "task_id": T5, "facts": {"preference": "soon"}}),
             "'soon' is not a valid preference"),
            (answer({"decision": "add_batch", "task_id": T8, "facts": {"order_id": "ORD-041"}}),
             "add_batch: Python names the added batch, so give no task_id."),
            (answer({"decision": "add_batch", "facts": {"quantity": "100"}}), "add_batch: give the order ID."),
            (answer({"decision": "add_batch", "facts": {"order_id": "ORD-041"}, "workshop": "W1"}),
             "add_batch: unknown field workshop"),
            (answer({"decision": "add_batch", "facts": {"order_id": "ORD-041"}, "workshop_id": 1}),
             "add_batch: workshop_id must be"),
            (answer({"decision": "add_batch", "facts": {"order_id": "ORD-999"}}),
             "Not applied: ADD-1: ORD-999 is not in orders.csv."),
            (answer({"decision": "add_batch", "facts": {"order_id": "ORD-041", "quantity": "0"}}),
             "Not applied: ADD-1: '0' is not a whole number of pieces above 0."),
            # A valid decision followed by an invalid one: the whole answer is refused.
            (answer(choose, {"decision": "correct", "task_id": T5, "resolves": [5]}), f"{T5} has no blocker [5]"),
        ]
        for reply, message in cases:
            with self.subTest(reply=reply):
                self.assert_refused(reply, message, no_decisions(self.run_dir))

    def test_an_answer_is_refused_when_the_inputs_changed(self):
        with mock.patch.object(dispatcher_plan, "DISPATCH_DATE", date(2026, 4, 2)):
            self.assert_refused(answer(then="approve_all"), CHANGED_INPUTS, no_decisions(self.run_dir))
        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            for name in ("orders.csv", "workshops.csv"):
                shutil.copy2(dispatcher_plan.DATA_DIR / name, data_dir / name)
            with mock.patch.object(dispatcher_plan, "DATA_DIR", data_dir):
                self.assertEqual(dispatcher_plan.input_signature(), self.review["input_signature"])
                with (data_dir / "workshops.csv").open("a", encoding="utf-8") as file:
                    file.write("\n")
                self.assert_refused(answer({"decision": "clear", "task_id": T8}), CHANGED_INPUTS,
                                    no_decisions(self.run_dir))


class EveryNameIsDefined(unittest.TestCase):

    def test_no_module_uses_an_undefined_name(self):
        for module_name in MOVED | CHANGED | NEW:
            with self.subTest(module=module_name):
                self.assertEqual(undefined_names(importlib.import_module(module_name)), set())


if __name__ == "__main__":
    unittest.main()
