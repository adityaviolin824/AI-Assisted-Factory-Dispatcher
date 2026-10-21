"""Tests for the intake and processing modules, with notebook 05 as the reference. Fully offline.

Run from backend/:  uv run python -m unittest discover -s tests -v

What they prove:
- the moved code has the notebook's logic (same syntax tree; docstrings and comments ignored), and
  every other function is declared new or declared changed;
- the prompts, response formats, data and settings equal the notebook's, except the declared
  VERIFY_PROMPT changes. The tests pin the notebook's models with no reasoning effort, whatever
  config.toml names, and the notebook's VERIFY_PROMPT, so saved answers still match;
- every name the modules use is defined or imported, also on paths a test run never takes;
- on the supplied chat file, the modules save the same manifest (plus its reasoning_effort and
  message_date records),
  state, call records and summary as notebook 05's graph, with 0 API requests;
- repairs I03 (empty input) and I04 (deadline year) hold, and each stage's model can be swapped alone;
- Python counts the agreed relative delivery words from the message date, and asks about any other;
  with no deadline selected, dispatch timing keeps the CSV date and an omitted delivery date asks;
- a piece count written for the task's order that differs from orders.csv blocks readiness;
- a stage with a reasoning effort sends and records the effort instead of the temperature;
- a review naming no order or message targets only the tasks of the two messages before it;
- an unresolved input never stops a task's verification; possibly_affected_tasks finds the tasks
  it may modify, from the reviews and from two kinds of verified task.
No API client is ever created: a request without a saved answer raises CacheMiss.
"""
import ast
import builtins
import contextlib
import copy
import importlib
import io
import json
import shutil
import symtable
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from notebook_reference import (CHAT_FILE, SAVED_ANSWERS, CacheMiss, definitions_source, load_notebook_05,
                                notebook_prompt, refuse_api_call, top_level_definitions)
from order_intake_from_chat.read_chat_messages import read_messages
from order_processing_into_tasks import (
    create_and_link_tasks, extract_items, model_calls_with_cache, model_prompts, processing_run, settings_and_data,
    verify_tasks)

# The definitions each module copies unchanged from notebook 05.
MOVED = {
    "order_intake_from_chat.read_chat_messages": ["read_messages"],
    "order_processing_into_tasks.settings_and_data": [
        "write_json", "save_checkpoint", "digest", "order_references"],
    "order_processing_into_tasks.model_prompts": ["INTAKE_PROMPT", "LINK_PROMPT"],
    "order_processing_into_tasks.model_calls_with_cache": ["ReviewRequired", "StrictModel"],
    "order_processing_into_tasks.extract_items": [
        "ExtractedItem", "IntakeBatch", "owned_windows", "validate_intake", "accept_intake"],
    "order_processing_into_tasks.create_and_link_tasks": [
        "task_evidence", "evidence_text", "index_task", "create_task", "LinkDecision",
        "candidate_task_ids", "apply_link", "link_or_create_task", "link_pending_items"],
    "order_processing_into_tasks.verify_tasks": [
        "WorkshopId", "WorkshopRule", "SchedulingDetails", "EvidenceAssessment", "TaskAssessment",
        "VerificationBatch", "verification_payload", "workshop_references", "MONTH_NAMES",
        "OPTIONAL_YEAR", "DATE_PATTERN", "read_date",
        "verification_batches", "finish_verification_batch"],
    "order_processing_into_tasks.processing_run": [
        "new_state", "prepare_run", "verified_tasks"],
}
# Functions and classes that are new in the modules (everything else is moved or changed).
NEW = {
    "order_processing_into_tasks.processing_run": ["process_messages"],
    "order_processing_into_tasks.verify_tasks": ["possibly_affected_tasks", "last_day_of_month", "read_relative_date",
                                                 "possible_deadline_words", "stated_piece_counts"],
    "run_intake_and_processing": ["main"],
}
# Moved from notebook 05, then changed on purpose:
# - 14 October 2026: a stage can use a reasoning model, which gets a reasoning effort instead of the
#   temperature, and the manifest records the efforts. A stage with no effort sends the notebook's
#   requests unchanged (checked by EndToEnd).
# - 15 October 2026: a review naming no order or message holds only the tasks of the HOLD_WINDOW
#   messages before it, not every earlier task (Test 5 in docs/evaluation/PROMPT_TESTING_RESULTS.md; checked by
#   ReviewHolds). A review naming an order or a message holds the same tasks as before.
# - 15 October 2026, later (debugging/held-tasks-never-verified.md): an unresolved input no longer
#   holds tasks. hold_reviewed_requests became possibly_affected_tasks (new), which only finds the
#   tasks the plan marks provisional; run_verification verifies every task; intake and link reviews
#   no longer store held_task_ids; record_task_review writes only "verify" reviews; pipeline_complete
#   and save_run_outputs no longer check or apply holds (checked by PossiblyAffectedTasks).
# - 18 October 2026: relative delivery words are counted in Python. resolve_scheduling passes an
#   exactly copied relative deadline to read_relative_date (new) before asking for a calendar date,
#   and the manifest records MESSAGE_DATE (checked by Deadlines). VERIFY_PROMPT has the declared
#   changes in VERIFY_PROMPT_CHANGES.
# - 19 October 2026: with no deadline selected, resolve_scheduling asks about the dates and time words
#   of possible_deadline_words (new) instead of every written date: dispatch timing is skipped, and an
#   omitted "deliver tomorrow" no longer falls back to the CSV date (checked by Deadlines).
#   Later that day, after Test 7: resolve_scheduling reads the one written date inside a copied
#   phrase such as "due Apr 13", still checked against the evidence (checked by Deadlines).
# - 19 October 2026, after Test 8: finish_verification blocks an allocation whose evidence writes a
#   piece count for its order that differs from orders.csv, found by stated_piece_counts (new). In
#   Test 8, R191 ("ORD-105, 1300 vests"; the CSV has 200) was recommended (checked by PieceCounts).
CHANGED = {
    "order_processing_into_tasks.model_calls_with_cache": ["make_chat_model", "RecordedModel"],
    "order_processing_into_tasks.processing_run": ["run_configuration", "pipeline_complete", "save_run_outputs"],
    "order_processing_into_tasks.extract_items": ["review_targets", "intake_window"],
    "order_processing_into_tasks.create_and_link_tasks": ["record_link_review"],
    "order_processing_into_tasks.verify_tasks": ["record_task_review", "run_verification", "resolve_scheduling",
                                                 "finish_verification"],
}
# The models notebook 05's saved answers were made with. offline_modules pins them, with no reasoning
# effort, so the tests check the code whatever models config.toml names.
NOTEBOOK_MODELS = {"intake": "gpt-4.1-mini", "link": "gpt-4.1-mini", "verify": "gpt-4.1-mini"}
# Values that are part of every request fingerprint or decision. They must equal the notebook's.
# STAGE_MODELS is a model choice in config.toml, so it is pinned (NOTEBOOK_MODELS) instead.
SAME_VALUES = {
    "order_processing_into_tasks.settings_and_data": [
        "TEMPERATURE", "DATA_YEAR", "TARGET_SIZE", "CONTEXT_SIZE", "MAX_CANDIDATES",
        "VERIFY_BATCH_SIZE", "MAX_PAYLOAD_CHARS", "ORDER_INDEX", "WORKSHOP_INDEX", "WORKSHOP_NAMES"],
    "order_processing_into_tasks.model_prompts": ["INTAKE_PROMPT", "LINK_PROMPT"],
}
# The declared changes to notebook 05's VERIFY_PROMPT (decision of 18 October 2026), as (notebook
# text, module text): delivery deadlines only, the CSV date when the chat has none, relative words
# copied for Python, and no estimated quantities. Saved answers were made with the notebook's prompt,
# so offline_modules pins it (NOTEBOOK_VERIFY_PROMPT).
VERIFY_PROMPT_CHANGES = [
    ("COMPLETE is allowed in this experiment.\n",
     "COMPLETE is allowed in this experiment.\n"
     'A vague amount such as "usual quantities" is not a quantity. Never estimate one: the identified order\'s\n'
     "CSV quantity applies; without an order, ask for the order ID.\n"),
    ("deadline_evidence_id: source stating the current explicit deadline, or null.\n",
     "deadline_evidence_id: source stating the current explicit deadline, or null.\n"
     "A deadline is a delivery date: due, deliver by, back by, must be back by, or the customer's ship date.\n"
     'Dispatch timing such as "send out today", "go out this week" or "place it today" is never a deadline.\n'
     "With no deadline in the evidence, deadline_evidence_id=null: the CSV due date applies.\n"),
    ("  Unconfirmed dates, unresolved contradictions and relative dates without a known reference need "
     "clarification.\n",
     "  Unconfirmed dates and unresolved contradictions need clarification. Copy relative delivery words exactly,\n"
     '  such as "by end of next week": Python turns them into a date or asks for one.\n'),
]
NOTEBOOK_VERIFY_PROMPT = notebook_prompt("VERIFY_PROMPT")
# Response formats. Their JSON schema is part of every request's key, so it must equal the notebook's.
SCHEMAS = {
    "order_processing_into_tasks.extract_items": ["ExtractedItem", "IntakeBatch"],
    "order_processing_into_tasks.create_and_link_tasks": ["LinkDecision"],
    "order_processing_into_tasks.verify_tasks": [
        "WorkshopRule", "SchedulingDetails", "EvidenceAssessment", "TaskAssessment",
        "VerificationBatch"],
}

# Repair I04 (a deadline keeps its written year) and relative delivery words (18 October 2026), with
# the message date pinned to Wednesday 1 April 2026. Each case: (evidence text, the model's proposed
# due_date_text, the selected deadline evidence, expected (due_date, blockers) or REVIEW).
EVIDENCE_ID = "T:L0001:J1:E1"
REVIEW = "review"
DEADLINE_CASES = [
    # A rewritten date with another year goes to review, and so does a copied part that drops its year.
    ("Please deliver ORD-045 by April 2, 2027.", "April 2, 2026", EVIDENCE_ID, REVIEW),
    ("Please deliver ORD-045 by April 2, 2027.", "April 2", EVIDENCE_ID, REVIEW),
    ("Please deliver ORD-045 by April 2, 2027.", "April 2, 2027", EVIDENCE_ID, ("2027-04-02", [])),
    # A date written without a year gets DATA_YEAR (2026).
    ("Please deliver ORD-045 by Apr 2.", "Apr 2", EVIDENCE_ID, ("2026-04-02", [])),
    ("Please deliver ORD-045 by 2026-04-05.", "2026-04-05", EVIDENCE_ID, ("2026-04-05", [])),
    # Day-first dates are found too, also when the model rewrites them month-first.
    ("Please deliver ORD-045 by 2 April 2027.", "2 April 2027", EVIDENCE_ID, ("2027-04-02", [])),
    ("Please deliver ORD-045 by 2 April 2027.", "April 2, 2027", EVIDENCE_ID, ("2027-04-02", [])),
    # A quantity after the date is not a year.
    ("Allocate ORD-045, Apr 13 1500 pcs", "Apr 13", EVIDENCE_ID, ("2026-04-13", [])),
    # A copy that keeps its delivery word (Test 7, 19 October 2026) is read by its one written date,
    # which must still match the evidence, year included. Two dates still ask which one applies.
    ("ORD-109 — 500 vests for Harbor Knits, due Apr 13.", "due Apr 13", EVIDENCE_ID, ("2026-04-13", [])),
    ("ORD-029 needs a home today. 1500 beanies, back by Apr 01.", "back by Apr 01", EVIDENCE_ID, ("2026-04-01", [])),
    ("Please deliver ORD-045 by April 2, 2027.", "by April 2", EVIDENCE_ID, REVIEW),
    ("Deliver ORD-045 between Apr 2 and Apr 5.", "between Apr 2 and Apr 5", EVIDENCE_ID,
     (None, ["Confirm the deadline as an explicit calendar date."])),
    # Agreed relative words, copied exactly: Python counts them (a week ends on Friday, a month on
    # its last day). A deadline of today is kept; the allocator sends it to review as past.
    ("Please deliver ORD-045 by end of next week.", "by end of next week", EVIDENCE_ID, ("2026-04-10", [])),
    ("ORD-045 must be back by the end of this week.", "by the end of this week", EVIDENCE_ID, ("2026-04-03", [])),
    ("ORD-045 must be back by the end of this month.", "end of this month", EVIDENCE_ID, ("2026-04-30", [])),
    ("Deliver ORD-045 by tomorrow.", "tomorrow", EVIDENCE_ID, ("2026-04-02", [])),
    ("Deliver ORD-045 today.", "today", EVIDENCE_ID, ("2026-04-01", [])),
    # Other unreadable dates: an exact copy becomes a question; anything else goes to review.
    ("Please deliver ORD-045 by next Friday.", "next Friday", EVIDENCE_ID,
     (None, ["Confirm the deadline as an explicit calendar date."])),
    ("Please deliver ORD-045 by Friday.", "by Friday", EVIDENCE_ID,
     (None, ["Confirm the deadline as an explicit calendar date."])),
    ("Please deliver ORD-045 by next Friday.", "Friday next week", EVIDENCE_ID, REVIEW),
    ("Please deliver ORD-045 by end of next week.", "next week's end", EVIDENCE_ID, REVIEW),
    # No deadline selected, but a date is written (here day-first): ask which date applies.
    ("Allocate ORD-045. The customer said 2 April 2027 works.", None, None,
     (None, ["Confirm which written date is the current deadline."])),
    # "2 decisions" is not a date.
    ("Allocate ORD-045, 2 decisions pending.", None, None, (None, [])),
    # 19 October 2026, no deadline selected. Dispatch timing keeps the CSV date without a question;
    # a delivery date or time word that the model left out asks instead of falling back to the CSV.
    ("Send out ORD-045 on April 2.", None, None, (None, [])),
    ("ORD-045 needs to go out this week.", None, None, (None, [])),
    ("That big reorder from last week - send ORD-045 to whoever is quickest.", None, None, (None, [])),
    ("Deliver ORD-045 tomorrow.", None, None, (None, ["Confirm which written date is the current deadline."])),
    ("Please deliver ORD-045 by Friday.", None, None, (None, ["Confirm which written date is the current deadline."])),
    ("Send out ORD-045 on April 2 so it arrives by April 5.", None, None,
     (None, ["Confirm which written date is the current deadline."])),
    ("ORD-045 needs to ship Mar 23, so it has to go out today.", None, None,
     (None, ["Confirm which written date is the current deadline."])),
]

# Piece counts written in one quote for one order (19 October 2026, after Test 8). Each case:
# (quote, order ID, expected counts).
PIECE_COUNT_CASES = [
    # Test 8, R191, and CASE-094 of data/extended_dispatch_100, with and without a thousands comma.
    ("ORD-105, 1300 vests, Bright Basics, Apr 10. Cheapest feasible.", "ORD-105", [1300]),
    ("Allocate ORD-294: 1250 cardigan pieces for Cotton Club. Delivery due May 2.", "ORD-294", [1250]),
    ("Allocate ORD-294: 1,250 pieces.", "ORD-294", [1250]),
    # Up to two words between the number and the product or "pieces".
    ("Please allocate ORD-201, 120 crewneck sweater pieces for Maple & Co.", "ORD-201", [120]),
    ("Farm out the complete ORD-205 batch: 360 pieces, Vest, TrendCart.", "ORD-205", [360]),
    ("Send ORD-073 (400 hoodies) to FreshStart, their quote was good.", "ORD-073", [400]),
    ("ORD-045 — 150 vests for Cotton Club, due Apr 09.", "ORD-045", [150]),
    ("Allocate ORD-045, Apr 13 1500 pcs", "ORD-045", [1500]),
    # Text after another order ID belongs to that order; text before any order ID to every order.
    ("Allocate ORD-281, 120 crewneck sweater pieces, due Apr 29. Also allocate ORD-282, 180 hoodie pieces.",
     "ORD-281", [120]),
    ("Allocate ORD-281, 120 crewneck sweater pieces, due Apr 29. Also allocate ORD-282, 180 hoodie pieces.",
     "ORD-282", [180]),
    ("Make it 300 pieces.", "ORD-073", [300]),
    # Order IDs, workshop IDs, dates and other numbers are not piece counts.
    ("Place the whole ORD-291 batch of 500 vests with FreshStart (W8). Deliver by May 2.", "ORD-291", [500]),
    ("Split ORD-045 across 2 workshops; total cost must not exceed 100.", "ORD-045", []),
    ("Allocate ORD-045, 2 decisions pending.", "ORD-045", []),
]


def module_definitions(module):
    """Return {name: AST node} for every top-level function, class and NAME = value in a module file."""
    return top_level_definitions(Path(module.__file__).read_text(encoding="utf-8"))


def logic(node):
    """Return a definition's syntax tree as text, without docstrings. Comments are never in the tree."""
    node = copy.deepcopy(node)
    for inner in ast.walk(node):
        if isinstance(inner, (ast.FunctionDef, ast.ClassDef)) and ast.get_docstring(inner) is not None:
            inner.body = inner.body[1:] or [ast.Pass()]
    return ast.dump(node)


def undefined_names(module):
    """Return the names a module's functions and classes use that the module never defines or imports."""
    source = Path(module.__file__).read_text(encoding="utf-8")
    scopes = list(symtable.symtable(source, module.__file__, "exec").get_children())
    missing = set()
    while scopes:
        scope = scopes.pop()
        scopes.extend(scope.get_children())
        for symbol in scope.get_symbols():
            name = symbol.get_name()
            if (symbol.is_global() and symbol.is_referenced()
                    and not hasattr(module, name) and not hasattr(builtins, name)):
                missing.add(name)
    return missing


@contextlib.contextmanager
def offline_modules(work_dir):
    """Point the modules' run folders and a copy of the saved answers at work_dir; block API calls.

    Also pins NOTEBOOK_MODELS with no reasoning effort, and the notebook's VERIFY_PROMPT, so the
    saved answers match whatever config.toml names and despite the declared prompt changes.
    """
    shutil.copytree(SAVED_ANSWERS, work_dir / "response-cache")
    with (mock.patch.object(processing_run, "RUNS_DIR", work_dir / "runs"),
          mock.patch.object(model_calls_with_cache, "CACHE_DIR", work_dir / "response-cache"),
          mock.patch.object(model_calls_with_cache, "make_chat_model", refuse_api_call),
          mock.patch.dict(settings_and_data.STAGE_MODELS, NOTEBOOK_MODELS),
          mock.patch.dict(settings_and_data.REASONING_EFFORTS, clear=True),
          mock.patch.object(verify_tasks, "VERIFY_PROMPT", NOTEBOOK_VERIFY_PROMPT),
          mock.patch.object(processing_run, "VERIFY_PROMPT", NOTEBOOK_VERIFY_PROMPT),
          mock.patch.object(model_calls_with_cache, "VERIFY_PROMPT", NOTEBOOK_VERIFY_PROMPT)):
        yield


class RefusingClient:
    """Stand-in API client: it accepts the structured-output setup, then refuses to send the request."""

    def with_structured_output(self, *args, **kwargs):
        return self

    def invoke(self, messages):
        raise CacheMiss("cache miss: no API call was made")


def read_run(run_dir):
    """Return a run folder's manifest, state and call records, with the run folder path replaced."""
    def read(path):
        return json.loads(path.read_text(encoding="utf-8").replace(str(run_dir), "<run_dir>"))
    return {"manifest": read(run_dir / "manifest.json"),
            "state": read(run_dir / "state.json"),
            "calls": {path.name: read(path) for path in sorted((run_dir / "calls").glob("*.json"))}}


def paid_requests(calls):
    """Count the call records that were not answered from the saved answers."""
    return sum(not record.get("reused_response") for record in calls.values())


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

    def test_settings_prompts_and_data_equal_the_notebook(self):
        # Compared as JSON text, so 0 and 0.0 count as different, as they do in a fingerprint.
        for module_name, names in SAME_VALUES.items():
            module = importlib.import_module(module_name)
            for name in names:
                with self.subTest(module=module_name, name=name):
                    self.assertEqual(json.dumps(getattr(module, name)), json.dumps(self.notebook[name]))
        self.assertEqual(NOTEBOOK_MODELS, self.notebook["STAGE_MODELS"])

    def test_verify_prompt_has_only_the_declared_changes(self):
        self.assertEqual(NOTEBOOK_VERIFY_PROMPT, self.notebook["VERIFY_PROMPT"])
        prompt = self.notebook["VERIFY_PROMPT"]
        for old, new in VERIFY_PROMPT_CHANGES:
            self.assertEqual(prompt.count(old), 1)
            prompt = prompt.replace(old, new)
        self.assertEqual(model_prompts.VERIFY_PROMPT, prompt)

    def test_response_formats_have_the_notebook_json_schema(self):
        for module_name, names in SCHEMAS.items():
            module = importlib.import_module(module_name)
            for name in names:
                with self.subTest(module=module_name, name=name):
                    self.assertEqual(getattr(module, name).model_json_schema(),
                                     self.notebook[name].model_json_schema())

    def test_read_messages_gives_the_notebook_messages(self):
        with contextlib.redirect_stdout(io.StringIO()):
            messages = read_messages(CHAT_FILE)
            self.assertEqual(messages, self.notebook["read_messages"](CHAT_FILE))
        self.assertEqual(len(messages), 30)


class EndToEnd(unittest.TestCase):
    """Notebook 05's graph and process_messages on the supplied chat file, both from saved answers."""

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        work_dir = Path(cls.temp.name)
        with contextlib.redirect_stdout(io.StringIO()):
            # The reference: notebook 05's whole graph (processing, then allocation).
            notebook = load_notebook_05(work_dir / "notebook")
            messages = notebook["read_messages"](CHAT_FILE)
            graph_state, _ = notebook["run_graph"](messages, CHAT_FILE.name)
            # The modules, on the same messages and label.
            with offline_modules(work_dir / "modules"):
                run_dir, cls.module_state, cls.module_summary = processing_run.process_messages(
                    messages, CHAT_FILE.name)
        cls.notebook_run = read_run(Path(graph_state["run_dir"]))
        cls.notebook_summary = graph_state["summary"]
        cls.module_run = read_run(run_dir)
        cls.module_files = {path.name for path in run_dir.iterdir()}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_both_runs_are_complete_and_free(self):
        for name, run, summary in [("notebook", self.notebook_run, self.notebook_summary),
                                   ("modules", self.module_run, self.module_summary)]:
            with self.subTest(run=name):
                self.assertEqual(paid_requests(run["calls"]), 0)
                self.assertTrue(summary["complete"])
                self.assertEqual((summary["input_messages"], summary["tasks"]), (30, 29))

    def test_modules_save_what_the_notebook_saves(self):
        self.assertEqual(self.module_files, {"manifest.json", "state.json", "calls"})
        # The declared differences: the modules' manifest also records the reasoning efforts (none
        # here) and the message date.
        manifest = dict(self.module_run["manifest"])
        self.assertEqual(manifest.pop("reasoning_effort"), {})
        self.assertEqual(manifest.pop("message_date"), settings_and_data.MESSAGE_DATE.isoformat())
        saved = {"manifest": manifest, "state": self.module_run["state"], "calls": self.module_run["calls"]}
        for part in ("manifest", "state", "calls"):
            with self.subTest(part=part):
                self.assertEqual(saved[part], self.notebook_run[part])
        self.assertEqual(self.module_summary, self.notebook_summary)

    def test_returned_state_equals_saved_state(self):
        self.assertEqual(self.module_state, self.module_run["state"])


class EmptyInput(unittest.TestCase):
    """Repair I03 on the modules: an empty or blank chat file makes no run folder."""

    def test_empty_and_blank_files_make_no_run(self):
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            with offline_modules(work_dir), contextlib.redirect_stdout(io.StringIO()):
                for name, text in [("empty.txt", ""), ("blank.txt", "  \n\t\n")]:
                    path = work_dir / name
                    path.write_text(text, encoding="utf-8")
                    result = processing_run.process_messages(read_messages(path), name)
                    self.assertEqual(result, (None, None, None))
            self.assertFalse((work_dir / "runs").exists())


class StageModelSwap(unittest.TestCase):
    """Changing one stage's model in config.toml makes only that stage's requests new."""

    def test_verify_model_swap_reuses_every_intake_answer(self):
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            with (offline_modules(work_dir), contextlib.redirect_stdout(io.StringIO()),
                  mock.patch.dict(settings_and_data.STAGE_MODELS, {"verify": "gpt-4.1"})):
                messages = read_messages(CHAT_FILE)
                with self.assertRaisesRegex(CacheMiss, r"\(model gpt-4\.1\)$"):
                    processing_run.process_messages(messages, CHAT_FILE.name)
            (run_dir,) = (work_dir / "runs").iterdir()
            run = read_run(run_dir)
        self.assertEqual(run["manifest"]["models"],
                         {"intake": "gpt-4.1-mini", "link": "gpt-4.1-mini", "verify": "gpt-4.1"})
        # The run stopped at the first verify request, after reusing all 10 saved intake answers.
        stages = {record["request"]["stage"] for record in run["calls"].values()}
        self.assertEqual(stages, {"intake"})
        self.assertEqual((len(run["calls"]), paid_requests(run["calls"])), (10, 0))


class ReasoningEffort(unittest.TestCase):
    """A stage with a reasoning effort sends and records the effort instead of the temperature."""

    def test_reasoning_stage_sends_its_effort_instead_of_the_temperature(self):
        clients = []

        def record_client(model_name, sampling):
            """Stand-in for make_chat_model: note the client settings, then return a refusing client."""
            clients.append((model_name, sampling))
            return RefusingClient()

        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            with (offline_modules(work_dir), contextlib.redirect_stdout(io.StringIO()),
                  mock.patch.dict(settings_and_data.STAGE_MODELS, {"intake": "gpt-5.6-luna"}),
                  mock.patch.dict(settings_and_data.REASONING_EFFORTS, {"intake": "high"}),
                  mock.patch.object(model_calls_with_cache, "make_chat_model", record_client)):
                with self.assertRaisesRegex(RuntimeError, r"API request failed \(CacheMiss\)"):
                    processing_run.process_messages(read_messages(CHAT_FILE), CHAT_FILE.name)
            (run_dir,) = (work_dir / "runs").iterdir()
            run = read_run(run_dir)
        # The run stopped at its first intake request (no saved answer), after saving that request.
        self.assertEqual(clients, [("gpt-5.6-luna", {"reasoning_effort": "high"})])
        (record,) = run["calls"].values()
        self.assertEqual(record["request"]["reasoning_effort"], "high")
        self.assertNotIn("temperature", record["request"])
        self.assertEqual(run["manifest"]["reasoning_effort"], {"intake": "high"})


class Deadlines(unittest.TestCase):
    """Repair I04 on the module: a proposed date must equal a whole date written in its evidence.
    Relative delivery words (18 October 2026) are counted in Python from the message date."""

    def deadline_result(self, evidence, due_date_text, deadline_evidence_id):
        """Run resolve_scheduling on one made-up task; return (due_date, blockers), or REVIEW."""
        catalog = [{"evidence_id": EVIDENCE_ID, "message_id": "L0001", "text": evidence}]
        payload = {"evidence": [{"message_id": "L0001", "excerpts": [evidence]}], "evidence_catalog": catalog}
        scheduling = verify_tasks.SchedulingDetails(
            due_date_text=due_date_text, preference="none", preference_evidence_id=None,
            workshop_rules=[], split_evidence_id=None, unhandled_constraints=[])
        assessment = verify_tasks.EvidenceAssessment(
            intent="allocation", order_id="ORD-045", urgency_evidence_id=None,
            deadline_evidence_id=deadline_evidence_id, quality_evidence_id=None,
            constraint_evidence_ids=[], missing_details=[], doubts_to_clarify=[], scheduling=scheduling)
        try:
            with mock.patch.object(verify_tasks, "MESSAGE_DATE", date(2026, 4, 1)):
                fields, blockers = verify_tasks.resolve_scheduling(payload, assessment)
        except verify_tasks.ReviewRequired:
            return REVIEW
        return fields["due_date"], blockers

    def test_deadline_cases(self):
        for evidence, due_date_text, evidence_id, expected in DEADLINE_CASES:
            with self.subTest(evidence=evidence, due_date_text=due_date_text):
                self.assertEqual(self.deadline_result(evidence, due_date_text, evidence_id), expected)

    def test_relative_words_from_other_message_dates(self):
        # On a Saturday, which Friday "this week" means is unclear, so week words ask for a date.
        # "next month" from December crosses the year.
        cases = [(date(2026, 4, 4), "this week", None), (date(2026, 4, 4), "next week", None),
                 (date(2026, 4, 4), "this month", "2026-04-30"), (date(2026, 12, 15), "next week", "2026-12-25"),
                 (date(2026, 12, 15), "next month", "2027-01-31"), (date(2026, 4, 1), "end of the week", None)]
        for message_date, words, expected in cases:
            with self.subTest(message_date=message_date, words=words):
                with mock.patch.object(verify_tasks, "MESSAGE_DATE", message_date):
                    self.assertEqual(verify_tasks.read_relative_date(words), expected)

    def test_every_order_has_a_csv_due_date(self):
        # A ready allocation task needs an order in orders.csv, so with no deadline in the chat the
        # allocator always has the CSV date; without an order, the task asks for one.
        self.assertTrue(all(row["due_date"] for row in settings_and_data.ORDER_INDEX.values()))


class PieceCounts(unittest.TestCase):
    """A piece count written for the task's order must equal orders.csv (19 October 2026, after Test 8).
    A different count is a conflict or an unconfirmed change, so the task asks instead of being ready."""

    def test_piece_count_cases(self):
        for quote, order_id, expected in PIECE_COUNT_CASES:
            with self.subTest(quote=quote, order_id=order_id):
                self.assertEqual(verify_tasks.stated_piece_counts(quote, order_id), expected)

    def verified(self, quote, order_id):
        """Run finish_verification on a made-up answer that raises no question; return the record."""
        catalog = [{"evidence_id": EVIDENCE_ID, "message_id": "L0001", "text": quote}]
        payload = {"evidence": [{"message_id": "L0001", "excerpts": [quote]}], "evidence_catalog": catalog,
                   "anchor_order_ids": [order_id], "workshop_mentions": [],
                   "order_lookups": [{"order_id": order_id, "found": True,
                                      "order": settings_and_data.ORDER_INDEX[order_id]}]}
        scheduling = verify_tasks.SchedulingDetails(
            due_date_text=None, preference="none", preference_evidence_id=None,
            workshop_rules=[], split_evidence_id=None, unhandled_constraints=[])
        assessment = verify_tasks.EvidenceAssessment(
            intent="allocation", order_id=order_id, urgency_evidence_id=None,
            deadline_evidence_id=None, quality_evidence_id=None,
            constraint_evidence_ids=[], missing_details=[], doubts_to_clarify=[], scheduling=scheduling)
        return verify_tasks.finish_verification({"task_id": "T:L0001:J1", "version": 1}, payload, assessment)

    def test_a_different_count_blocks_readiness(self):
        # orders.csv records ORD-105 as 200 hoodies; Test 8's model marked this request ready.
        record = self.verified("ORD-105, 1300 vests, Bright Basics. Cheapest feasible.", "ORD-105")
        self.assertFalse(record["information_sufficient"])
        self.assertEqual(record["missing_details"], [
            "The chat states 1300 pieces for ORD-105, but orders.csv records 200; confirm the quantity."])

    def test_the_recorded_count_or_no_count_stays_ready(self):
        for quote in ("ORD-045 — 150 vests for Cotton Club.", "Please place ORD-045."):
            with self.subTest(quote=quote):
                record = self.verified(quote, "ORD-045")
                self.assertTrue(record["information_sufficient"])
                self.assertEqual(record["missing_details"], [])


class ReviewHolds(unittest.TestCase):
    """The tasks a review targets: those it names, otherwise those of the two messages before it.

    (Named when reviews held these tasks; since 15 October 2026 they are only marked provisional.)
    """

    def test_review_targets(self):
        state = {"source_index": {"L0001": ["T:L0001:J1"], "L0002": ["T:L0002:J1"],
                                  "L0003": ["T:L0003:J1"], "L0005": ["T:L0005:J1"]},
                 "order_index": {"ORD-017": ["T:L0001:J1"]}}
        cases = [
            # Names nothing: the tasks of the two messages before it, never those of a later message.
            ("Yes.", "L0004", ["T:L0002:J1", "T:L0003:J1"]),
            # At the start of the chat there are fewer messages before it, or none.
            ("Yes.", "L0002", ["T:L0001:J1"]),
            ("Yes.", "L0001", []),
            # Names an order or a message: only the tasks linked to it.
            ("Cancel ORD-017.", "L0004", ["T:L0001:J1"]),
            ("Same as L0003.", "L0004", ["T:L0003:J1"]),
            # A failed task's evidence that names nothing targets no other task.
            ("Yes.", None, []),
        ]
        for text, message_id, expected in cases:
            with self.subTest(text=text, message_id=message_id):
                self.assertEqual(extract_items.review_targets(state, text, message_id), expected)


def made_up_state():
    """Return a small processing state for the review-warning checks.

    Ten tasks, one per message, all verified except T:L0011:J1, whose verification failed. L0005
    "Yes." is a link review and L0006, a cancellation, is an intake review.
    """
    lines = [
        # (message ID, text, intent, order ID, excluded workshops); intent None: verification failed
        ("L0001", "ORD-017 — 800 cardigans, due Apr 10.", "allocation", "ORD-017", []),
        ("L0002", "Please place ORD-095: 800 hoodies.", "allocation", "ORD-095", []),
        ("L0003", "ORD-108, 2000 scarves. Move it now.", "allocation", "ORD-108", []),
        ("L0004", "Speed priority?", "question", None, []),
        ("L0007", "ORD-024, 300 vests, Apr 15.", "allocation", "ORD-024", []),
        ("L0008", "Fastest workshop excluding QuickStitch.", "allocation", None, ["W1"]),
        ("L0009", "Don't allocate based on memory.", "unclear", None, []),
        ("L0010", "ORD-017 is paused.", "unclear", "ORD-017", []),
        ("L0011", "Same job as L0007, but 400 vests.", None, None, []),
        ("L0012", "Second batch of ORD-024, 200 vests.", "allocation", "ORD-024", []),
    ]
    state = processing_run.new_state()
    with contextlib.redirect_stdout(io.StringIO()):
        for message_id, text, intent, order_id, excluded in lines:
            item = {"message_id": message_id, "kind": "request", "excerpts": [text], "item_id": f"{message_id}:J1"}
            state["items"][item["item_id"]] = item
            task = create_and_link_tasks.create_task(state, item)
            if intent is None:
                verify_tasks.record_task_review(state, task, "Unreadable answer (test).")
            else:
                task.update(verified_version=1, verified={
                    "task_id": task["task_id"], "intent": intent, "order_id": order_id,
                    "excluded_workshops": excluded, "requested_workshop": None,
                    "description": text, "source_message_ids": [message_id]})
        follow_up = {"message_id": "L0005", "kind": "follow_up", "excerpts": ["Yes."], "item_id": "L0005:J1"}
        state["items"][follow_up["item_id"]] = follow_up
        create_and_link_tasks.record_link_review(state, follow_up, ["T:L0003:J1", "T:L0004:J1"], "Unclear reply (test).")
        state["intake_review"].append({"message_id": "L0006", "raw_text": "ORD-095 has been cancelled."})
    return state


class PossiblyAffectedTasks(unittest.TestCase):
    """The tasks an unresolved input may modify. Since 15 October 2026 they are verified and planned,
    and the plan marks them provisional (debugging/held-tasks-never-verified.md); before, they were
    held and never verified.
    """

    def test_reviews_warn_their_targets(self):
        state = made_up_state()
        # Leave out the two verified tasks that warn others; the next test checks them.
        for task_id in ("T:L0008:J1", "T:L0010:J1"):
            state["tasks"][task_id].update(verified=None, verified_version=None)
        # A run saved before 15 October may have a "related_review" record: a hold, not a failure,
        # so ORD-017's other request is not warned.
        with contextlib.redirect_stdout(io.StringIO()):
            verify_tasks.record_task_review(state, state["tasks"]["T:L0001:J1"], "Held (test).")
        state["task_review"]["T:L0001:J1"]["stage"] = "related_review"
        before = copy.deepcopy(state)
        self.assertEqual(verify_tasks.possibly_affected_tasks(state), {
            "T:L0003:J1": ["L0005:J1"], "T:L0004:J1": ["L0005:J1"],  # "Yes.": the two messages before it
            "T:L0002:J1": ["L0006"],                                   # the cancellation names ORD-095
            "T:L0007:J1": ["T:L0011:J1"],                              # the failed task names L0007,
            "T:L0012:J1": ["T:L0011:J1"]})                             # so the other ORD-024 request too
        self.assertEqual(state, before)

    def test_verified_tasks_that_may_modify_others(self):
        # "Speed priority?" (a question) and "Don't allocate based on memory." (unclear, no order)
        # warn nothing.
        self.assertEqual(verify_tasks.possibly_affected_tasks(made_up_state()), {
            "T:L0003:J1": ["L0005:J1"], "T:L0004:J1": ["L0005:J1"], "T:L0002:J1": ["L0006"],
            # The exclusion with no order warns the task of the message before it (L0006 has none).
            "T:L0007:J1": ["T:L0011:J1", "T:L0008:J1"], "T:L0012:J1": ["T:L0011:J1", "T:L0008:J1"],
            # The unclear task naming ORD-017 warns the other ORD-017 request, never itself.
            "T:L0001:J1": ["T:L0010:J1"]})

    def test_a_review_does_not_stop_verification(self):
        state = made_up_state()
        for task in state["tasks"].values():
            task.update(verified=None, verified_version=None)
        state["task_review"].clear()
        requested = []

        def ask(stage, prompt, payload, response_format):
            """Record the tasks sent for verification, then give an unreadable answer."""
            requested.extend(task["task_id"] for task in payload["tasks"])
            raise model_calls_with_cache.ReviewRequired("Unreadable answer (test).")

        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            verify_tasks.run_verification(Path(temp), state, ask)
        self.assertEqual(sorted(requested), sorted(state["tasks"]))


class EveryNameIsDefined(unittest.TestCase):

    def test_no_module_uses_an_undefined_name(self):
        for module_name in MOVED | NEW | CHANGED:
            with self.subTest(module=module_name):
                self.assertEqual(undefined_names(importlib.import_module(module_name)), set())


if __name__ == "__main__":
    unittest.main()
