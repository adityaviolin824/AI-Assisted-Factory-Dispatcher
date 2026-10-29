"""Tests for the HTTP API (main.py and fastapi_routes/), called through FastAPI's TestClient. Fully offline.

Run from backend/:  uv run python -m unittest discover -s tests -v

What they prove, on a run of the supplied chat file paused for the dispatcher in a temporary SQLite file:
- GET /runs lists the saved runs and GET /runs/{run_id} returns a run's plan.json, then its
  dispatcher-plan.json once approved; an unknown run ID, or a path such as "..", is refused with 404;
- GET /runs/{run_id}/usage returns stage_costs of the run's call records with the price table and its
  date, and nothing else: a run answered from saved answers paid nothing, but has a fresh-run cost;
- GET /reviews/{thread_id} returns the paused review; POST /reviews/{thread_id}/answer applies an edit,
  returns apply_answer's own refusal message with nothing changed, and after approve_all returns the
  final review that was saved; a finished or unknown thread gets 404;
- POST /reviews/{thread_id}/finalize refuses a batch with nothing changed, or applies every choice with
  one calculation, saves the final review with what changed, and leaves no paused review;
- POST /reviews/{thread_id}/preview returns what finalize would approve, or its refusal, and changes no
  file, checkpoint or paused review;
- Review again, POST /runs/{run_id}/preview and /finalize, needs an approved plan; it refuses a set with
  nothing saved, previews without saving, and saves exactly the preview as a new version that keeps
  the earlier workshop choice, can remove an added batch, lists what changed against the previous
  plan, keeps the earlier version in plan-history/ and equals one calculation with all the choices;
- before any run has paused, the review endpoints answer 404 and create no checkpoint file;
- an answer that is not a JSON object is refused by FastAPI (422) and changes nothing;
- every name the API modules use is defined or imported.
No API client is ever created, every network connection is refused, and nothing is sent to LangSmith.
"""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import HTTPException
from fastapi.testclient import TestClient
from langgraph.checkpoint.sqlite import SqliteSaver

from test_dispatcher_review import block_network, no_decisions, pinned_review_settings, record, row, without
from test_pipeline_graph import T8, as_json, choose, paused_run, read_json
from test_processing_modules import undefined_names

import main
from dispatcher_review.dispatcher_decisions import apply_answer
from dispatcher_review.dispatcher_plan import finalize_review
from eval_run_report.run_summary import PRICES, PRICES_CHECKED, stage_costs
from fastapi_routes import dispatcher, runs

# ORD-008: in review in the first review, with a late option at W1.
T11 = "T:L0011:J1"
# A batch the dispatcher adds in the first approval; it becomes ADD-1.
ADDED = {"decision": "add_batch", "facts": {"order_id": "ORD-041", "quantity": "300"}}


def folder_contents(folder):
    """Return every file under a folder, by its relative path, with its bytes."""
    return {path.relative_to(folder): path.read_bytes() for path in folder.rglob("*") if path.is_file()}


def setUpModule():
    block_network()


class Endpoints(unittest.TestCase):
    """The endpoints, with the runs folder and the checkpoint file in a temporary folder."""

    def setUp(self):
        work_dir = Path(self.enterContext(tempfile.TemporaryDirectory()))
        checkpoint_file = work_dir / "dispatcher-review-checkpoints.sqlite"
        with SqliteSaver.from_conn_string(str(checkpoint_file)) as checkpointer:
            graph_state, _, self.thread_id, paused = paused_run(work_dir, checkpointer)
        self.run_dir = Path(graph_state["run_dir"])
        # The first review, as the API returns it (JSON turns the checkpoint's tuples into lists).
        self.first_review = as_json({"status": "waiting", "review": paused["review"], "refused": paused["refused"]})
        self.enterContext(mock.patch.object(runs, "RUNS_DIR", work_dir / "runs"))
        self.enterContext(mock.patch.object(dispatcher, "CHECKPOINT_FILE", checkpoint_file))
        self.enterContext(pinned_review_settings())
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))  # the graph prints its steps
        self.client = TestClient(main.app)

    def answer(self, decisions, then):
        """Post one answer to the paused review; return the response."""
        return self.client.post(f"/reviews/{self.thread_id}/answer", json={"decisions": decisions, "then": then})

    def assert_no_paused_review(self, response, thread_id):
        """The response is the 404 for a thread with no paused review."""
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": f"Thread {thread_id} has no paused dispatcher review."})

    def test_saved_runs_are_listed_and_read(self):
        manifest = read_json(self.run_dir / "manifest.json")
        self.assertEqual(self.client.get("/runs").json(), [
            {"run_id": self.run_dir.name, "label": manifest["label"], "messages": len(manifest["messages"])}])
        self.assertEqual(self.client.get(f"/runs/{self.run_dir.name}").json(), {
            "run_id": self.run_dir.name, "plan": read_json(self.run_dir / "plan.json"), "dispatcher_plan": None})
        missing = self.client.get("/runs/no-such-run")
        self.assertEqual((missing.status_code, missing.json()), (404, {"detail": "No saved run no-such-run."}))
        with self.assertRaises(HTTPException):
            runs.read_run("..")  # only a saved run folder's name is read

    def test_run_usage_is_counted_from_the_call_records(self):
        calls = [read_json(path) for path in sorted((self.run_dir / "calls").glob("*.json"))]
        usage = self.client.get(f"/runs/{self.run_dir.name}/usage").json()
        # Only the price table and stage_costs' counts, tokens, dollars and seconds: no prompt or answer.
        self.assertEqual(usage, {"run_id": self.run_dir.name, "prices_checked": PRICES_CHECKED, "prices": PRICES,
                                 "stages": stage_costs(calls)})
        # The test run was answered entirely from saved answers: it paid nothing, but a fresh run would pay.
        total = usage["stages"][-1]
        self.assertEqual((total["stage"], total["calls"], total["paid"], total["cost_this_run"]),
                         ("total", len(calls), 0, 0))
        self.assertGreater(total["cost_fresh"], 0)
        missing = self.client.get("/runs/no-such-run/usage")
        self.assertEqual((missing.status_code, missing.json()), (404, {"detail": "No saved run no-such-run."}))
        with self.assertRaises(HTTPException):
            runs.read_run_usage("..")  # only a saved run folder's name is read

    def test_a_paused_review_is_shown_answered_and_approved(self):
        self.assertEqual(self.client.get(f"/reviews/{self.thread_id}").json(), self.first_review)
        edited = self.answer([choose(T8, "W6")], "review_again").json()
        self.assertEqual((edited["status"], edited["refused"]), ("waiting", None))
        self.assertEqual(record(edited["review"], T8)["selected_workshop"], "W6")
        # A refused answer returns apply_answer's own message, and the review is unchanged.
        refused = self.answer([], "save_draft").json()
        self.assertEqual(refused, {"status": "waiting", "review": edited["review"],
                                   "refused": "\"then\" must be \"review_again\", \"approve_all\" or \"finalize\", not 'save_draft'."})
        # Approve all saves the review last shown; then the run has a dispatcher plan and no paused review.
        finished = self.answer([], "approve_all").json()
        self.assertEqual((finished["status"], finished["review"]["status"], finished["refused"]), ("finished", "final", None))
        self.assertEqual(record(finished["review"], T8)["selected_workshop"], "W6")
        self.assertEqual(finished["review"], read_json(self.run_dir / "dispatcher-plan.json"))
        self.assertEqual(self.client.get(f"/runs/{self.run_dir.name}").json()["dispatcher_plan"], finished["review"])
        # A finished thread, and a thread that never existed, have no paused review.
        self.assert_no_paused_review(self.client.get(f"/reviews/{self.thread_id}"), self.thread_id)
        self.assert_no_paused_review(self.answer([], "approve_all"), self.thread_id)
        self.assert_no_paused_review(self.client.get("/reviews/no-such-thread"), "no-such-thread")

    def test_finalize_applies_every_choice_once_and_saves(self):
        finalize = f"/reviews/{self.thread_id}/finalize"
        # A refused batch keeps the review waiting, unchanged, with apply_answer's reason.
        refused = self.client.post(finalize, json={"decisions": [choose(T8, "W99")]}).json()
        self.assertEqual(refused, {**self.first_review, "refused": f"Not applied: {T8}: W99 is not a workshop."})
        # An accepted batch is calculated, approved and saved at once, with what changed in the review.
        finished = self.client.post(finalize, json={"decisions": [choose(T8, "W6")]}).json()
        self.assertEqual((finished["status"], finished["review"]["status"], finished["refused"]), ("finished", "final", None))
        self.assertEqual(record(finished["review"], T8)["selected_workshop"], "W6")
        self.assertEqual(finished["review"], read_json(self.run_dir / "dispatcher-plan.json"))
        change = next(change for change in finished["review"]["changes"] if change["id"] == T8)
        self.assertEqual((change["before"]["outcome"], change["after"]["outcome"], change["after"]["workshop"]),
                         ("review_required", "dispatcher_choice", "W6"))
        self.assert_no_paused_review(self.client.post(finalize, json={"decisions": []}), self.thread_id)

    def test_preview_saves_nothing_and_equals_what_finalize_saves(self):
        preview = f"/reviews/{self.thread_id}/preview"
        # The temporary folder holds the run folder and the checkpoint file.
        before = folder_contents(dispatcher.CHECKPOINT_FILE.parent)
        # A refused set returns the shown review with apply_answer's reason.
        refused = self.client.post(preview, json={"decisions": [choose(T8, "W99")]}).json()
        self.assertEqual(refused, {"review": self.first_review["review"],
                                   "refused": f"Not applied: {T8}: W99 is not a workshop."})
        # An accepted set returns the draft that finalize would approve, with what would change.
        previewed = self.client.post(preview, json={"decisions": [choose(T8, "W6")]}).json()
        self.assertEqual((previewed["refused"], previewed["review"]["status"]), (None, "draft"))
        self.assertEqual(record(previewed["review"], T8)["selected_workshop"], "W6")
        self.assertIn(T8, [change["id"] for change in previewed["review"]["changes"]])
        # Nothing was saved or resumed: every file is unchanged and the same review still waits.
        self.assertEqual(folder_contents(dispatcher.CHECKPOINT_FILE.parent), before)
        self.assertEqual(self.client.get(f"/reviews/{self.thread_id}").json(), self.first_review)
        # Finalize with the same choices saves exactly the preview, approved.
        self.client.post(f"/reviews/{self.thread_id}/finalize", json={"decisions": [choose(T8, "W6")]})
        self.assertEqual(without(read_json(self.run_dir / "dispatcher-plan.json"), "created_at", "decisions_revision"),
                         without(finalize_review(previewed["review"]), "created_at"))
        self.assert_no_paused_review(self.client.post(preview, json={"decisions": []}), self.thread_id)
        self.assert_no_paused_review(self.client.post("/reviews/no-such-thread/preview", json={"decisions": []}),
                                     "no-such-thread")

    def approve_first(self):
        """Approve the paused review with T8 sent to W6 and one added batch; return the saved plan."""
        self.client.post(f"/reviews/{self.thread_id}/finalize", json={"decisions": [choose(T8, "W6"), ADDED]})
        return read_json(self.run_dir / "dispatcher-plan.json")

    def review_again(self, endpoint, decisions):
        """Post new choices to Review again's preview or finalize endpoint; return the response."""
        return self.client.post(f"/runs/{self.run_dir.name}/{endpoint}", json={"decisions": decisions})

    def test_review_again_needs_an_approved_plan(self):
        for endpoint in ("preview", "finalize"):
            with self.subTest(endpoint=endpoint):
                response = self.review_again(endpoint, [])
                self.assertEqual((response.status_code, response.json()),
                                 (404, {"detail": f"Run {self.run_dir.name} has no approved dispatcher plan yet."}))
                missing = self.client.post(f"/runs/no-such-run/{endpoint}", json={"decisions": []})
                self.assertEqual((missing.status_code, missing.json()), (404, {"detail": "No saved run no-such-run."}))
        with self.assertRaises(HTTPException):
            runs.finalize_saved_plan("..", {"decisions": []})  # only a saved run folder's name is used

    def test_review_again_previews_then_saves_a_new_version(self):
        first = self.approve_first()
        new = [{"decision": "clear", "task_id": "ADD-1"}, choose(T11, "W1")]
        before = folder_contents(self.run_dir)
        # A refused set returns the approved plan with apply_answer's reason, and saves nothing.
        refused = self.review_again("finalize", [choose(T8, "W99")]).json()
        self.assertEqual(refused, {"review": first, "refused": f"Not applied: {T8}: W99 is not a workshop."})
        # A preview saves nothing either.
        previewed = self.review_again("preview", new).json()
        self.assertEqual((previewed["refused"], previewed["review"]["status"]), (None, "draft"))
        self.assertEqual(folder_contents(self.run_dir), before)
        # Finalize saves exactly the preview, approved, as the next version.
        saved = self.review_again("finalize", new).json()
        self.assertEqual(saved, {"review": read_json(self.run_dir / "dispatcher-plan.json"), "refused": None})
        self.assertEqual(without(saved["review"], "created_at", "decisions_revision"),
                         without(finalize_review(previewed["review"]), "created_at"))
        self.assertEqual(read_json(self.run_dir / "dispatcher-decisions.json")["revision"], 2)
        # T8's workshop, chosen in the first approval, stays fixed; ADD-1 is removed; T11 goes to W1.
        self.assertEqual((row(saved["review"], T8)["workshop"], row(saved["review"], T8)["outcome"]), ("W6", "approved"))
        self.assertNotIn("ADD-1", [summary_row["id"] for summary_row in saved["review"]["summary_rows"]])
        # What changed is compared with the first approved plan, so the unchanged T8 is not listed.
        changes = {change["id"]: change for change in saved["review"]["changes"]}
        self.assertNotIn(T8, changes)
        self.assertEqual((changes["ADD-1"]["before"]["outcome"], changes["ADD-1"]["after"]), ("approved", None))
        self.assertEqual((changes[T11]["before"]["outcome"], changes[T11]["after"]["outcome"],
                          changes[T11]["after"]["workshop"]), ("review_required", "approved", "W1"))
        # plan-history/ keeps the first version beside the new one.
        history = sorted((self.run_dir / "plan-history").glob("*_dispatcher-plan.json"))
        self.assertEqual([read_json(path) for path in history], [first, saved["review"]])

    def test_review_again_equals_one_calculation_with_all_choices(self):
        self.approve_first()
        saved = self.review_again("finalize", [{"decision": "clear", "task_id": "ADD-1"}, choose(T11, "W1")]).json()
        # The choices that remain, applied at once to the first review, give the same rows and queues:
        # nothing was reserved twice.
        _, once, _, _ = apply_answer(self.run_dir, no_decisions(self.run_dir), self.first_review["review"],
                                     {"decisions": [choose(T8, "W6"), choose(T11, "W1")], "then": "finalize"})
        self.assertEqual(saved["review"]["queues_after_plan"], once["queues_after_plan"])
        self.assertEqual(saved["review"]["summary_rows"], as_json(finalize_review(once))["summary_rows"])

    def test_an_answer_must_be_a_json_object(self):
        response = self.client.post(f"/reviews/{self.thread_id}/answer", json=[])
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.get(f"/reviews/{self.thread_id}").json(), self.first_review)


class NoCheckpointFile(unittest.TestCase):
    """Before any run has paused, reading or answering a review creates no checkpoint file."""

    def test_reviews_get_404_and_no_file_is_created(self):
        checkpoint_file = Path(self.enterContext(tempfile.TemporaryDirectory())) / "dispatcher-review-checkpoints.sqlite"
        self.enterContext(mock.patch.object(dispatcher, "CHECKPOINT_FILE", checkpoint_file))
        client = TestClient(main.app)
        expected = (404, {"detail": "No paused dispatcher reviews exist yet."})
        read = client.get("/reviews/some-thread")
        answered = client.post("/reviews/some-thread/answer", json={"decisions": [], "then": "approve_all"})
        finalized = client.post("/reviews/some-thread/finalize", json={"decisions": []})
        previewed = client.post("/reviews/some-thread/preview", json={"decisions": []})
        for response in (read, answered, finalized, previewed):
            self.assertEqual((response.status_code, response.json()), expected)
        self.assertFalse(checkpoint_file.exists())


class EveryNameIsDefined(unittest.TestCase):

    def test_no_module_uses_an_undefined_name(self):
        for module in (main, runs, dispatcher):
            with self.subTest(module=module.__name__):
                self.assertEqual(undefined_names(module), set())


if __name__ == "__main__":
    unittest.main()
