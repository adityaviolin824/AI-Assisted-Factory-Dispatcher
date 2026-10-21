"""Tests for the HTTP API (main.py and fastapi_routes/), called through FastAPI's TestClient. Fully offline.

Run from backend/:  uv run python -m unittest discover -s tests -v

What they prove, on a run of the supplied chat file paused for the dispatcher in a temporary SQLite file:
- GET /runs lists the saved runs and GET /runs/{run_id} returns a run's plan.json, then its
  dispatcher-plan.json once approved; an unknown run ID, or a path such as "..", is refused with 404;
- GET /reviews/{thread_id} returns the paused review; POST /reviews/{thread_id}/answer applies an edit,
  returns apply_answer's own refusal message with nothing changed, and after approve_all returns the
  final review that was saved; a finished or unknown thread gets 404;
- POST /reviews/{thread_id}/finalize refuses a batch with nothing changed, or applies every choice with
  one calculation, saves the final review with what changed, and leaves no paused review;
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

from test_dispatcher_review import block_network, pinned_review_settings, record
from test_pipeline_graph import T8, as_json, choose, paused_run, read_json
from test_processing_modules import undefined_names

import main
from fastapi_routes import dispatcher, runs


def setUpModule():
    block_network()


class Endpoints(unittest.TestCase):
    """The four endpoints, with the runs folder and the checkpoint file in a temporary folder."""

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
        for response in (read, answered, finalized):
            self.assertEqual((response.status_code, response.json()), expected)
        self.assertFalse(checkpoint_file.exists())


class EveryNameIsDefined(unittest.TestCase):

    def test_no_module_uses_an_undefined_name(self):
        for module in (main, runs, dispatcher):
            with self.subTest(module=module.__name__):
                self.assertEqual(undefined_names(module), set())


if __name__ == "__main__":
    unittest.main()
