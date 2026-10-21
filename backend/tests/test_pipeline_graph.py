"""Tests for the LangGraph pipeline module, with notebook 05's graph as the reference. Fully offline.

Run from backend/:  uv run python -m unittest discover -s tests -v

What they prove:
- the moved graph code has the notebook's logic (same syntax tree; docstrings and comments ignored),
  and every other function is declared changed or new;
- the graph has the notebook's nodes and edges, except that save_outputs always goes on to
  plan_allocation (the notebook's after_save router is removed) and plan_allocation goes on to the
  dispatcher's review loop (dispatcher_review, then save_review once the dispatcher approves);
- on the supplied chat file, the graph takes notebook 05's 25 steps before it pauses for the
  dispatcher, and saves the notebook graph's manifest (plus its reasoning_effort and message_date
  records), state, call records and plan, with 0 API requests;
- one graph run saves the same files as the two steps, process_messages then plan_saved_run;
- the first pause shows the review of the plan just made; an edit pauses again with a new review;
  approve all saves the review last shown as final, with no new calculation; a refused answer pauses
  again with nothing changed; clearing every edit keeps an empty draft; changed order or workshop
  data is refused; a paused run continues after its SQLite connection is closed, through
  run_full_pipeline.py and resume_dispatcher_review.py;
- the step limits hold with the smallest margin that works;
- an empty chat file makes no run folder; an error stops the graph with no plan; an incomplete run
  still gets a plan, marked partial, and a review;
- every name the modules use is defined or imported.
No API client is ever created, every network connection is refused, and nothing is sent to LangSmith
(notebook_reference turns tracing off).
"""
import ast
import contextlib
import importlib
import io
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.errors import GraphRecursionError

from notebook_reference import CHAT_FILE, definitions_source, load_notebook_05, top_level_definitions
from test_allocation_modules import api_failure, assert_same_plan, failing_model_calls, pinned_settings
from test_dispatcher_review import block_network, no_decisions, pinned_review_settings, record, row, without
from test_processing_modules import (logic, module_definitions, offline_modules, paid_requests, read_run,
                                     undefined_names)

import resume_dispatcher_review
import run_full_pipeline
from app_full_pipeline import pipeline_graph
from dispatcher_review import dispatcher_plan
from dispatcher_review.dispatcher_decisions import CHANGED_INPUTS
from dispatcher_review.dispatcher_plan import build_dispatcher_plan, finalize_review
from order_intake_from_chat.read_chat_messages import read_messages
from order_processing_into_tasks import processing_run
from task_allocation_to_workshops import allocation_plan

# The definitions copied unchanged from notebook 05 (Sections 14 and 15).
MOVED = {
    "app_full_pipeline.pipeline_graph": [
        "start_run", "link_items", "extract_batch", "verify_tasks", "save_outputs", "after_link",
        "recursion_limit"],
}
# Moved from notebook 05, then changed on purpose (see docs/legacy/LANGGRAPH_MODULARIZATION_PLAN.md):
# plan_allocation calls the allocation module's plan_allocation; build_graph always goes on from
# save_outputs to plan_allocation (after_save removed); run_graph names its LangSmith run "full-pipeline".
# Since 20 October 2026 (DISPATCHER_REVIEW_GRAPH_PLAN.md) the graph pauses for the dispatcher:
# PipelineState has the review keys, plan_allocation also calculates the first review, build_graph
# compiles with a checkpointer and adds the review loop, and run_graph runs on a new thread to the
# first pause.
CHANGED = {
    "app_full_pipeline.pipeline_graph": ["PipelineState", "plan_allocation", "build_graph", "run_graph"],
}
# Functions that are new in the modules.
NEW = {
    "app_full_pipeline.pipeline_graph": [
        "dispatcher_review", "save_review", "after_review", "stream_to_pause", "paused_review", "resume_graph"],
    "run_full_pipeline": ["main"],
    "resume_dispatcher_review": ["print_pause", "main"],
}
T8, T9, T21 = "T:L0008:J1", "T:L0009:J1", "T:L0021:J1"
# The files a run folder holds before the dispatcher approves.
RUN_FILES = {"manifest.json", "state.json", "calls", "plan.json", "plan-history"}
DISPATCHER_FILES = {"dispatcher-decisions.json", "dispatcher-plan.json"}


def setUpModule():
    block_network()


def graph_edges(compiled_graph):
    """Return the drawn graph's edges as a set of (source, target, conditional)."""
    return {(edge.source, edge.target, edge.conditional) for edge in compiled_graph.get_graph().edges}


def paused_run(work_dir, checkpointer):
    """Run the graph on the supplied chat file from saved answers, to the dispatcher's first pause.
    Returns run_graph's (graph_state, steps, thread_id, paused).
    """
    with offline_modules(work_dir), pinned_review_settings(), contextlib.redirect_stdout(io.StringIO()):
        return pipeline_graph.run_graph(read_messages(CHAT_FILE), CHAT_FILE.name, checkpointer)


def resume(thread_id, checkpointer, *decisions, then="review_again"):
    """Answer a paused run; returns resume_graph's (graph_state, steps, thread_id, paused)."""
    with pinned_review_settings(), contextlib.redirect_stdout(io.StringIO()):
        return pipeline_graph.resume_graph(thread_id, {"decisions": list(decisions), "then": then}, checkpointer)


def choose(task_id, workshop_id):
    """Return a choose_workshop decision of an answer."""
    return {"decision": "choose_workshop", "task_id": task_id, "workshop_id": workshop_id}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def as_json(value):
    """Return value as the checkpoint and the JSON files hold it: the ranking_keys tuples become lists."""
    return json.loads(json.dumps(value))


class SameAsNotebook(unittest.TestCase):
    """The graph module against notebook 05's code, loaded in memory as saved."""

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

    def test_every_function_and_class_is_moved_or_declared(self):
        for module_name in MOVED | NEW | CHANGED:
            definitions = module_definitions(importlib.import_module(module_name))
            functions = {name for name, node in definitions.items() if not isinstance(node, ast.Assign)}
            declared = (set(MOVED.get(module_name, [])) | set(NEW.get(module_name, []))
                        | set(CHANGED.get(module_name, [])))
            with self.subTest(module=module_name):
                self.assertEqual(functions - declared, set())

    def test_same_graph_except_planning_always_and_the_review_loop(self):
        notebook_edges = graph_edges(self.notebook["build_graph"]())
        # The notebook's after_save router chose between plan_allocation and END, and the notebook
        # ended after plan_allocation.
        removed = {("save_outputs", "plan_allocation", True), ("save_outputs", "__end__", True),
                   ("plan_allocation", "__end__", False)}
        self.assertTrue(removed <= notebook_edges)
        added = {("save_outputs", "plan_allocation", False), ("plan_allocation", "dispatcher_review", False),
                 ("dispatcher_review", "dispatcher_review", True), ("dispatcher_review", "save_review", True),
                 ("save_review", "__end__", False)}
        graph = pipeline_graph.build_graph(InMemorySaver())
        self.assertEqual(graph_edges(graph), (notebook_edges - removed) | added)
        self.assertEqual(set(graph.get_graph().nodes),
                         set(self.notebook["build_graph"]().get_graph().nodes) | {"dispatcher_review", "save_review"})


class EndToEnd(unittest.TestCase):
    """Notebook 05's graph, the module graph (to the dispatcher's first pause) and the two steps
    (process_messages then plan_saved_run) on the supplied chat file, all from saved answers.
    """

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work_dir = Path(cls.temp.name)
        with contextlib.redirect_stdout(io.StringIO()):
            notebook = load_notebook_05(work_dir / "notebook")
            messages = notebook["read_messages"](CHAT_FILE)
            cls.notebook_state, cls.notebook_steps = notebook["run_graph"](messages, CHAT_FILE.name)
            cls.graph_state, cls.steps, _, cls.paused = paused_run(work_dir / "graph", InMemorySaver())
            with offline_modules(work_dir / "two-steps"), pinned_settings():
                two_step_dir, _, _ = processing_run.process_messages(messages, CHAT_FILE.name)
                cls.two_step_plan = allocation_plan.plan_saved_run(two_step_dir)
        cls.run_dir = Path(cls.graph_state["run_dir"])
        cls.graph_run = read_run(cls.run_dir)
        cls.notebook_run = read_run(Path(cls.notebook_state["run_dir"]))
        cls.two_step_run = read_run(two_step_dir)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_same_steps_as_the_notebook_graph(self):
        # 10 intake batches: 2N + 5 = 25 finished steps, then the pause.
        self.assertEqual(len(self.steps), 25)
        self.assertEqual(self.steps, self.notebook_steps)
        self.assertIsNotNone(self.paused)

    def test_complete_and_free(self):
        self.assertEqual(paid_requests(self.graph_run["calls"]), 0)
        self.assertTrue(self.graph_state["summary"]["complete"])
        self.assertTrue(self.graph_state["plan"]["processing_complete"])

    def test_graph_saves_what_the_notebook_graph_saves(self):
        # The declared differences: the modules' manifest also records the reasoning efforts (none
        # here) and the message date.
        manifest = dict(self.graph_run["manifest"])
        self.assertEqual(manifest.pop("reasoning_effort"), {})
        self.assertEqual(manifest.pop("message_date"), "2026-04-01")
        self.assertEqual(manifest, self.notebook_run["manifest"])
        self.assertEqual(self.graph_run["state"], self.notebook_run["state"])
        self.assertEqual(self.graph_run["calls"], self.notebook_run["calls"])
        self.assertEqual(self.graph_state["summary"], self.notebook_state["summary"])

    def test_same_plan_as_the_notebook_graph(self):
        # The graph state comes from the checkpoint, so the notebook's plan is compared as JSON too.
        assert_same_plan(self, self.graph_state["plan"], as_json(self.notebook_state["plan"]))

    def test_graph_run_equals_the_two_steps(self):
        self.assertEqual(self.graph_run, self.two_step_run)
        # created_at (when the plan was made) is the only difference.
        self.assertEqual(self.graph_state["plan"] | {"created_at": None},
                         as_json(self.two_step_plan | {"created_at": None}))

    def test_run_folder_holds_processing_and_plan_files(self):
        self.assertEqual({path.name for path in self.run_dir.iterdir()}, RUN_FILES)
        self.assertEqual(len(list((self.run_dir / "plan-history").iterdir())), 1)
        saved_plan = read_json(self.run_dir / "plan.json")
        self.assertEqual(saved_plan, json.loads(json.dumps(self.graph_state["plan"])))
        saved_state = read_json(self.run_dir / "state.json")
        self.assertEqual(saved_state, self.graph_state["processing"])

    def test_first_pause_shows_the_review_of_the_plan(self):
        review, plan = self.paused["review"], self.graph_state["plan"]
        self.assertIsNone(self.paused["refused"])
        self.assertEqual(self.graph_state["review"], review)
        self.assertEqual(self.graph_state["decisions"], no_decisions(self.run_dir))
        with pinned_review_settings():
            expected = build_dispatcher_plan(self.run_dir, no_decisions(self.run_dir))
        self.assertEqual(without(review, "created_at"), as_json(without(expected, "created_at")))
        self.assertEqual([without(row, "final") for row in review["summary_rows"]], plan["summary_rows"])
        for key in ("planning_order", "decisions", "queues_after_plan"):
            self.assertEqual(review[key], plan[key])
        self.assertEqual((review["status"], review["final_ids"]), ("draft", []))


class DispatcherReview(unittest.TestCase):
    """The dispatcher's answers to a paused run of the supplied chat file, kept by an InMemorySaver."""

    def setUp(self):
        self.work_dir = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.checkpointer = InMemorySaver()
        graph_state, _, self.thread_id, self.paused = paused_run(self.work_dir, self.checkpointer)
        self.run_dir = Path(graph_state["run_dir"])
        self.source = {name: (self.run_dir / name).read_bytes() for name in ("manifest.json", "state.json", "plan.json")}

    def assert_files(self, names):
        """The run folder holds the processing and plan files, unchanged, and the named dispatcher files."""
        self.assertEqual({path.name for path in self.run_dir.iterdir()}, RUN_FILES | names)
        self.assertTrue(all((self.run_dir / name).read_bytes() == data for name, data in self.source.items()))

    def test_an_edit_pauses_again_and_approve_all_saves_the_review_shown(self):
        first = self.paused["review"]
        _, steps, _, paused = resume(self.thread_id, self.checkpointer, choose(T8, "W1"))
        self.assertEqual((steps, paused["refused"]), (["dispatcher_review"], None))
        self.assertEqual(record(paused["review"], T8)["selected_workshop"], "W1")
        # The latest choice wins: W6 replaces W1.
        _, steps, _, paused = resume(self.thread_id, self.checkpointer, choose(T8, "W6"))
        shown = paused["review"]
        self.assertEqual((record(shown, T8)["status"], record(shown, T8)["selected_workshop"]), ("dispatcher_choice", "W6"))
        # The chosen W6 is fixed first; T9, which the allocator gave W6, is planned around it.
        self.assertEqual(shown["planning_order"][0], T8)
        self.assertEqual((record(first, T9)["selected_workshop"], record(shown, T9)["selected_workshop"]), ("W6", "W8"))
        self.assert_files(set())
        graph_state, steps, _, paused = resume(self.thread_id, self.checkpointer, then="approve_all")
        self.assertEqual((steps, paused), (["dispatcher_review", "save_review"], None))
        final = graph_state["review"]
        self.assertEqual(without(final, "decisions_revision"), finalize_review(shown))
        self.assertEqual(sorted(final["final_ids"]), sorted([T8, T9, T21]))
        self.assertEqual((row(final, T8)["workshop"], row(final, T8)["delivery_days"]),
                         (row(shown, T8)["workshop"], row(shown, T8)["delivery_days"]))
        self.assert_files(DISPATCHER_FILES)
        saved_plan = read_json(self.run_dir / "dispatcher-plan.json")
        saved_decisions = read_json(self.run_dir / "dispatcher-decisions.json")
        self.assertEqual(saved_plan, final)
        self.assertEqual(saved_decisions, graph_state["decisions"])
        self.assertEqual((saved_decisions["source_run"], saved_plan["source_run"], saved_plan["decisions_revision"]),
                         (self.run_dir.name, self.run_dir.name, 1))
        self.assertEqual(list(saved_decisions["decisions"]), [T8])
        self.assertEqual(saved_decisions["decisions"][T8]["workshop"], "W6")
        self.assertEqual(len(list((self.run_dir / "plan-history").iterdir())), 3)
        with self.assertRaisesRegex(ValueError, "has no paused dispatcher review"):
            resume(self.thread_id, self.checkpointer, then="approve_all")

    def test_approve_all_without_edits_saves_the_plan_as_shown(self):
        graph_state, _, _, paused = resume(self.thread_id, self.checkpointer, then="approve_all")
        self.assertIsNone(paused)
        final = graph_state["review"]
        self.assertEqual(without(final, "decisions_revision"), finalize_review(self.paused["review"]))
        self.assertEqual(sorted(final["final_ids"]), sorted([T9, T21]))
        self.assertEqual(read_json(self.run_dir / "dispatcher-decisions.json"),
                         {"source_run": self.run_dir.name, "revision": 1, "decisions": {}})
        self.assert_files(DISPATCHER_FILES)

    def test_a_refused_answer_pauses_again_with_nothing_changed(self):
        _, _, _, edited = resume(self.thread_id, self.checkpointer, choose(T8, "W1"))
        replies = [
            ([{"decision": "clear", "task_id": "T:L0999:J1"}], "review_again", "is not a verified task"),
            ([], "save_draft", "\"then\" must be"),
            ([choose(T8, "W6")], "approve_all", "Approve all takes no decisions"),
            ([{"decision": "approve", "task_id": T9}], "review_again", "Unknown decision 'approve'"),
        ]
        for decisions, then, message in replies:
            with self.subTest(then=then, decisions=decisions):
                graph_state, steps, _, paused = resume(self.thread_id, self.checkpointer, *decisions, then=then)
                self.assertEqual(steps, ["dispatcher_review"])
                self.assertIn(message, paused["refused"])
                self.assertEqual(paused["review"], edited["review"])
                self.assertEqual(list(graph_state["decisions"]["decisions"]), [T8])
                self.assertEqual(graph_state["decisions"]["decisions"][T8]["workshop"], "W1")
        self.assert_files(set())
        _, _, _, paused = resume(self.thread_id, self.checkpointer)  # an empty edit clears the refusal
        self.assertIsNone(paused["refused"])

    def test_clearing_every_edit_keeps_an_empty_draft(self):
        resume(self.thread_id, self.checkpointer, choose(T8, "W1"))
        graph_state, _, _, paused = resume(self.thread_id, self.checkpointer, {"decision": "clear", "task_id": T8})
        self.assertEqual(graph_state["decisions"], no_decisions(self.run_dir))
        self.assertEqual(without(paused["review"], "created_at"), without(self.paused["review"], "created_at"))
        graph_state, _, _, _ = resume(self.thread_id, self.checkpointer, then="approve_all")
        self.assertEqual(read_json(self.run_dir / "dispatcher-decisions.json")["decisions"], {})
        self.assertEqual(row(graph_state["review"], T8)["outcome"], "review_required")

    def test_reviewing_again_reserves_nothing_twice(self):
        resume(self.thread_id, self.checkpointer, choose(T8, "W6"))
        queues = []
        for _ in range(3):
            _, _, _, paused = resume(self.thread_id, self.checkpointer, choose(T8, "W6"))
            queues.append(paused["review"]["queues_after_plan"])
        decisions = no_decisions(self.run_dir)
        decisions["decisions"][T8] = {"source_version": record(self.paused["review"], T8)["version"], "workshop": "W6"}
        with pinned_review_settings():
            expected = build_dispatcher_plan(self.run_dir, decisions)["queues_after_plan"]
        self.assertEqual(queues, [expected] * 3)

    def test_changed_inputs_are_refused_while_paused(self):
        with mock.patch.object(dispatcher_plan, "DISPATCH_DATE", date(2026, 4, 2)), \
                contextlib.redirect_stdout(io.StringIO()):
            graph_state, _, _, paused = pipeline_graph.resume_graph(
                self.thread_id, {"decisions": [], "then": "approve_all"}, self.checkpointer)
        self.assertEqual(paused["refused"], CHANGED_INPUTS)
        self.assertEqual(paused["review"], self.paused["review"])
        self.assertEqual(graph_state["decisions"], no_decisions(self.run_dir))
        self.assert_files(set())


class StepLimits(unittest.TestCase):
    """recursion_limit and RESUME_RECURSION_LIMIT hold, and the smallest limits are as stated."""

    def test_the_first_pause_needs_2n_plus_6_steps(self):
        batches = len(list(pipeline_graph.owned_windows(read_messages(CHAT_FILE), set())))
        self.assertEqual(pipeline_graph.recursion_limit(read_messages(CHAT_FILE)), 2 * batches + 10)
        with tempfile.TemporaryDirectory() as temp:
            with mock.patch.object(pipeline_graph, "recursion_limit", lambda messages: 2 * batches + 5):
                with self.assertRaises(GraphRecursionError):
                    paused_run(Path(temp) / "too-small", InMemorySaver())
            with mock.patch.object(pipeline_graph, "recursion_limit", lambda messages: 2 * batches + 6):
                self.assertIsNotNone(paused_run(Path(temp) / "smallest", InMemorySaver())[3])

    def test_a_resume_needs_one_step(self):
        with (tempfile.TemporaryDirectory() as temp, mock.patch.object(pipeline_graph, "RESUME_RECURSION_LIMIT", 1)):
            checkpointer = InMemorySaver()
            _, _, thread_id, _ = paused_run(Path(temp), checkpointer)
            self.assertIsNotNone(resume(thread_id, checkpointer, choose(T8, "W6"))[3])
            self.assertIsNone(resume(thread_id, checkpointer, then="approve_all")[3])
        self.assertEqual(pipeline_graph.RESUME_RECURSION_LIMIT, 10)


class SqliteRunnerScripts(unittest.TestCase):
    """run_full_pipeline.py pauses a run in a SQLite file and ends; resume_dispatcher_review.py later
    shows and answers it with a new connection and a newly built graph.
    """

    def run_script(self, module, *arguments):
        """Run a script's main with these command-line arguments; return what it printed."""
        printed = io.StringIO()
        with (mock.patch.object(sys, "argv", [module.__name__, *arguments]), pinned_review_settings(),
              contextlib.redirect_stdout(printed)):
            module.main()
        return printed.getvalue()

    def test_a_paused_review_continues_after_the_program_ends(self):
        work_dir = Path(self.enterContext(tempfile.TemporaryDirectory()))
        checkpoint_file = work_dir / "output" / "dispatcher-review-checkpoints.sqlite"
        for module in (run_full_pipeline, resume_dispatcher_review):
            self.enterContext(mock.patch.object(module, "CHECKPOINT_FILE", checkpoint_file))
            # The scripts load backend/.env; the tests never do.
            self.enterContext(mock.patch.object(module, "load_dotenv"))
        self.enterContext(mock.patch.object(run_full_pipeline, "OUTPUT_DIR", work_dir / "output"))
        self.enterContext(mock.patch.object(run_full_pipeline, "CHAT_FILE", CHAT_FILE))
        with offline_modules(work_dir):
            printed = self.run_script(run_full_pipeline)
        thread_id = printed.split("Thread ID: ")[1].split()[0]
        self.assertIn("DRAFT plan of run", printed)
        self.assertIn("sent to the API (paid): 0", printed)
        self.assertIn(f"resume_dispatcher_review.py {thread_id} <answer.json>", printed)
        with SqliteSaver.from_conn_string(str(checkpoint_file)) as checkpointer:
            graph_state, paused = pipeline_graph.paused_review(thread_id, checkpointer)
        run_dir = Path(graph_state["run_dir"])

        self.assertIn("Usage:", self.run_script(resume_dispatcher_review))
        self.assertIn("has no paused dispatcher review", self.run_script(resume_dispatcher_review, "no-such-thread"))
        self.assertIn("DRAFT plan of run", self.run_script(resume_dispatcher_review, thread_id))
        answer_file = work_dir / "answer.json"
        answer_file.write_text(json.dumps({"decisions": [choose(T8, "W6")], "then": "review_again"}), encoding="utf-8")
        printed = self.run_script(resume_dispatcher_review, thread_id, str(answer_file))
        self.assertIn("changed, was review_required", printed)
        self.assertNotIn("Answer refused", printed)
        answer_file.write_text(json.dumps({"decisions": [], "then": "save_draft"}), encoding="utf-8")
        self.assertIn("Answer refused; nothing changed", self.run_script(resume_dispatcher_review, thread_id, str(answer_file)))
        with SqliteSaver.from_conn_string(str(checkpoint_file)) as checkpointer:
            graph_state, paused = pipeline_graph.paused_review(thread_id, checkpointer)
        self.assertEqual(record(paused["review"], T8)["selected_workshop"], "W6")
        self.assertEqual(graph_state["decisions"]["decisions"][T8]["workshop"], "W6")

        answer_file.write_text(json.dumps({"decisions": [], "then": "approve_all"}), encoding="utf-8")
        printed = self.run_script(resume_dispatcher_review, thread_id, str(answer_file))
        self.assertIn("FINAL plan of run", printed)
        self.assertIn(f"Approved and saved in {run_dir}", printed)
        saved = read_json(run_dir / "dispatcher-plan.json")
        self.assertEqual((saved["status"], row(saved, T8)["outcome"], row(saved, T8)["workshop"]), ("final", "approved", "W6"))
        self.assertIn("has no paused dispatcher review", self.run_script(resume_dispatcher_review, thread_id))


class EmptyAndStoppedRuns(unittest.TestCase):
    """Runs that end early, and a run that finishes incomplete."""

    def test_empty_and_blank_files_make_no_run(self):
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            with offline_modules(work_dir), contextlib.redirect_stdout(io.StringIO()):
                for name, text in [("empty.txt", ""), ("blank.txt", "  \n\t\n")]:
                    path = work_dir / name
                    path.write_text(text, encoding="utf-8")
                    self.assertEqual(pipeline_graph.run_graph(read_messages(path), name, InMemorySaver()),
                                     (None, [], None, None))
            self.assertFalse((work_dir / "runs").exists())

    def test_error_stops_the_graph_without_a_plan(self):
        # A failed API request during verification stops the graph, as it stops process_messages.
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            with (offline_modules(work_dir), pinned_review_settings(), contextlib.redirect_stdout(io.StringIO()),
                  failing_model_calls("verify", {2: api_failure()})):
                with self.assertRaisesRegex(RuntimeError, "injected"):
                    pipeline_graph.run_graph(read_messages(CHAT_FILE), CHAT_FILE.name, InMemorySaver())
            (run_dir,) = (work_dir / "runs").iterdir()
            self.assertTrue((run_dir / "state.json").is_file())
            self.assertFalse((run_dir / "plan.json").exists())

    def test_incomplete_run_still_gets_a_partial_plan_and_a_review(self):
        # A finished but incomplete run is hard to make from saved answers, so the completeness
        # checks are patched to say "incomplete". PartialRuns (test_allocation_modules) tests real
        # incomplete states; this test only checks that the graph still plans and pauses.
        with tempfile.TemporaryDirectory() as temp:
            with (mock.patch.object(processing_run, "pipeline_complete", return_value=False),
                  mock.patch.object(allocation_plan, "pipeline_complete", return_value=False),
                  mock.patch.object(dispatcher_plan, "pipeline_complete", return_value=False)):
                graph_state, steps, _, paused = paused_run(Path(temp), InMemorySaver())
            self.assertFalse(graph_state["summary"]["complete"])
            self.assertEqual((len(steps), steps[-1]), (25, "plan_allocation"))
            self.assertFalse(graph_state["plan"]["processing_complete"])
            self.assertFalse(paused["review"]["processing_complete"])
            self.assertTrue((Path(graph_state["run_dir"]) / "plan.json").is_file())


class EveryNameIsDefined(unittest.TestCase):

    def test_no_module_uses_an_undefined_name(self):
        for module_name in MOVED | NEW | CHANGED:
            with self.subTest(module=module_name):
                self.assertEqual(undefined_names(importlib.import_module(module_name)), set())


if __name__ == "__main__":
    unittest.main()
