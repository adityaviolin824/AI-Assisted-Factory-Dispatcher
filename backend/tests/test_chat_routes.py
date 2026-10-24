"""Tests for the operations chat (order_intake_from_chat/chat_storage.py and fastapi_routes/chat.py),
called through FastAPI's TestClient. Fully offline.

Run from backend/:  uv run python -m unittest discover -s tests -v

What they prove, with the chat, the runs and the checkpoint file in a temporary folder:
- the chat storage functions have the mock chat's logic (same syntax tree; docstrings and comments
  ignored), and every other definition is declared new;
- reading messages or snapshots before the first message gives [] and creates no file;
- GET /chat/dates gives the message date and dispatch date that processing and allocation use;
- POST /chat/messages saves a message, saves nothing new for a repeated submission ID, and refuses an
  invalid name, empty text or a missing field with 422 and the mock's own message;
- POST /chat/snapshots refuses an empty chat with 400, and captures the whole conversation: the TXT
  exactly as saved, each message's R label and L message ID, and "not_started"; later messages go
  into the next snapshot only; snapshots are listed newest first, and an unknown ID gets 404;
- the supplied 30-message chat, stored as chat messages, gives a snapshot byte-identical to
  data/dispatch_requests.txt, and processing it runs the real pipeline from saved answers to the
  dispatcher's first pause: the snapshot reads "finished" with the run and thread IDs, the run is
  listed, its paused review can be read, and its plan equals that of the supplied file;
- processing is refused with 403 unless ALLOW_PAID_PROCESSING=1, and with 409 for a snapshot already
  sent or while another one runs; nothing starts then;
- a failed run reads "failed" with only the error's type, and the error is raised again; a run left
  "running" by an earlier server process reads "failed" and blocks nothing;
- every name the modules use is defined or imported.
No API client is ever created, every network connection is refused, backend/.env is never loaded and
nothing is sent to LangSmith.
"""
import contextlib
import importlib
import io
import json
import os
import re
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from langgraph.checkpoint.sqlite import SqliteSaver

from notebook_reference import CHAT_FILE, top_level_definitions
from test_dispatcher_review import block_network, pinned_review_settings
from test_pipeline_graph import paused_run
from test_processing_modules import logic, module_definitions, offline_modules, undefined_names

import main
from fastapi_routes import chat, dispatcher, runs
from order_intake_from_chat import chat_storage
from order_processing_into_tasks.settings_and_data import MESSAGE_DATE
from task_allocation_to_workshops.allocation_settings_and_data import DISPATCH_DATE

MOCK_APP = Path(__file__).resolve().parents[1] / "experimentation_notebooks/mock_frontend/app.py"
# The definitions chat_storage copies unchanged from the mock chat's app.py.
MOVED = ["DISPLAY_TIMEZONE", "initialize_storage", "save_message", "read_messages", "build_export",
         "export_conversation"]
# Definitions that are new in chat_storage: where the app keeps its chat.
NEW = ["CHAT_DIR", "DATABASE", "SNAPSHOTS_DIR"]
# One line of the supplied chat file: "R01 [07:53] Chen: Need scarves ...".
CHAT_LINE = re.compile(r"^R\d+ \[(\d\d):(\d\d)\] ([^:]+): (.*)$")


def setUpModule():
    block_network()


def message(sender="Chen", raw_text="Please allocate ORD-061.", submission_id=None):
    """Return the body of one Send, with a new submission ID unless one is given."""
    return {"submission_id": submission_id or uuid4().hex, "sender": sender, "raw_text": raw_text}


def store_supplied_chat(database):
    """Store the supplied chat file's messages as chat messages with the same senders and Singapore
    times, as if they had been sent through the chat on 1 April 2026.
    """
    chat_storage.initialize_storage(database)
    with contextlib.closing(sqlite3.connect(database)) as connection, connection:
        for line in CHAT_FILE.read_text(encoding="utf-8").splitlines():
            hour, minute, sender, raw_text = CHAT_LINE.match(line).groups()
            sent = datetime(2026, 4, 1, int(hour), int(minute), tzinfo=ZoneInfo(chat_storage.DISPLAY_TIMEZONE))
            connection.execute(
                "INSERT INTO messages (submission_id, sender, raw_text, received_at_utc) VALUES (?, ?, ?, ?)",
                (uuid4().hex, sender, raw_text, sent.astimezone(timezone.utc).isoformat()))


class SameCodeAsMock(unittest.TestCase):

    def test_moved_code_has_the_mock_logic(self):
        mock_definitions = top_level_definitions(MOCK_APP.read_text(encoding="utf-8"))
        moved = module_definitions(chat_storage)
        for name in MOVED:
            with self.subTest(name=name):
                self.assertEqual(logic(moved[name]), logic(mock_definitions[name]))

    def test_every_definition_is_moved_or_new(self):
        self.assertEqual(set(module_definitions(chat_storage)), set(MOVED) | set(NEW))


class Endpoints(unittest.TestCase):
    """The chat endpoints, with the chat, the runs and the checkpoint file in a temporary folder."""

    def setUp(self):
        self.work_dir = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.chat_dir = self.work_dir / "chat"
        self.checkpoint_file = self.work_dir / "dispatcher-review-checkpoints.sqlite"
        for target, name, value in ((chat_storage, "DATABASE", self.chat_dir / "messages.sqlite3"),
                                    (chat_storage, "SNAPSHOTS_DIR", self.chat_dir / "snapshots"),
                                    (chat, "CHECKPOINT_FILE", self.checkpoint_file),
                                    (dispatcher, "CHECKPOINT_FILE", self.checkpoint_file),
                                    (runs, "RUNS_DIR", self.work_dir / "runs"),
                                    (chat, "load_dotenv", lambda *args, **kwargs: None)):
            self.enterContext(mock.patch.object(target, name, value))
        self.enterContext(mock.patch.dict(os.environ))
        os.environ.pop("ALLOW_PAID_PROCESSING", None)
        self.client = TestClient(main.app)

    def send(self, body):
        return self.client.post("/chat/messages", json=body)

    def capture(self):
        """Capture a snapshot; return its JSON."""
        response = self.client.post("/chat/snapshots")
        self.assertEqual(response.status_code, 200)
        return response.json()

    def process(self, snapshot_id):
        return self.client.post(f"/chat/snapshots/{snapshot_id}/process")

    def snapshot(self, snapshot_id):
        return self.client.get(f"/chat/snapshots/{snapshot_id}").json()

    def test_reading_before_the_first_message_creates_nothing(self):
        self.assertEqual(self.client.get("/chat/messages").json(), [])
        self.assertEqual(self.client.get("/chat/snapshots").json(), [])
        self.assertFalse(self.chat_dir.exists())

    def test_the_dates_are_those_processing_and_allocation_use(self):
        self.assertEqual(self.client.get("/chat/dates").json(),
                         {"message_date": MESSAGE_DATE.isoformat(), "dispatch_date": DISPATCH_DATE.isoformat()})
        self.assertFalse(self.chat_dir.exists())

    def test_a_message_is_saved_once_per_submission(self):
        body = message()
        first = self.send(body)
        self.assertEqual(first.status_code, 200)
        self.assertEqual({key: first.json()[key] for key in ("message_id", "sender", "raw_text")},
                         {"message_id": 1, "sender": "Chen", "raw_text": "Please allocate ORD-061."})
        self.assertEqual(self.send(body).json(), first.json())  # a retried Send saves nothing new
        self.send(message())  # the same words with a new submission ID are a new message
        # Two messages in saved order. SQLite may skip an ID after a retried Send; R labels and L IDs
        # count positions, not database IDs.
        saved = self.client.get("/chat/messages").json()
        self.assertEqual((len(saved), saved[0]["message_id"] < saved[1]["message_id"]), (2, True))

    def test_an_invalid_message_is_refused_with_the_mocks_words(self):
        cases = [(message(sender=" "), "Enter your name before sending a message."),
                 (message(sender="Chen: ops"), "Use a single-line name without a colon."),
                 (message(sender="Chen\nRavi"), "Use a single-line name without a colon."),
                 (message(raw_text="  "), "Write a message before pressing Send.")]
        for body, detail in cases:
            with self.subTest(body=body):
                response = self.send(body)
                self.assertEqual((response.status_code, response.json()["detail"]), (422, detail))
        missing = self.send({"sender": "Chen", "raw_text": "hello"})
        self.assertEqual(missing.status_code, 422)  # FastAPI's own check: no submission_id
        self.assertEqual(self.client.get("/chat/messages").json(), [])

    def test_a_snapshot_captures_the_whole_conversation_once(self):
        empty = self.client.post("/chat/snapshots")
        self.assertEqual((empty.status_code, empty.json()["detail"]), (400, "There are no messages to export yet."))
        self.send(message(raw_text="Please allocate ORD-061.\nIt is urgent."))
        self.send(message(sender="Ravi", raw_text="For ORD-061, avoid QuickStitch."))
        first = self.capture()
        saved = (chat_storage.SNAPSHOTS_DIR / first["snapshot_id"] / "dispatch_requests.txt").read_bytes()
        self.assertEqual(first["text"].encode("utf-8"), saved)  # CRLF line endings kept
        self.assertEqual(first["message_count"], 2)
        self.assertRegex(first["text"], r"^R01 \[\d\d:\d\d\] Chen: Please allocate ORD-061\. It is urgent\.\r\n"
                                        r"R02 \[\d\d:\d\d\] Ravi: For ORD-061, avoid QuickStitch\.\r\n$")
        self.assertEqual(first["lines"], [
            {"message_id": 1, "request_label": "R01", "processing_message_id": "L0001"},
            {"message_id": 2, "request_label": "R02", "processing_message_id": "L0002"}])
        self.assertEqual({key: first[key] for key in ("processing", "run_id", "thread_id", "error")},
                         chat.NOT_STARTED)
        # A later message goes into the next snapshot; the first one stays as captured.
        self.send(message(raw_text="Also ORD-062, please."))
        second = self.capture()
        self.assertEqual(second["message_count"], 3)
        self.assertEqual([listed["snapshot_id"] for listed in self.client.get("/chat/snapshots").json()],
                         [second["snapshot_id"], first["snapshot_id"]])
        self.assertEqual(self.snapshot(first["snapshot_id"]), first)
        for unknown in ("20990101T000000000000Z-00000000", "..", ".pending-x"):
            with self.subTest(snapshot_id=unknown):
                self.assertEqual(self.client.get(f"/chat/snapshots/{unknown}").status_code, 404)

    def test_processing_a_snapshot_of_the_supplied_chat_pauses_for_the_dispatcher(self):
        store_supplied_chat(chat_storage.DATABASE)
        snapshot = self.capture()
        self.assertEqual(snapshot["text"].encode("utf-8"), CHAT_FILE.read_bytes())
        os.environ["ALLOW_PAID_PROCESSING"] = "1"
        with offline_modules(self.work_dir), pinned_review_settings(), contextlib.redirect_stdout(io.StringIO()):
            started = self.process(snapshot["snapshot_id"])
            # The answer comes before processing; TestClient then runs the background task to its end.
            self.assertEqual((started.status_code, started.json()["processing"]), (200, "running"))
            finished = self.snapshot(snapshot["snapshot_id"])
            self.assertEqual((finished["processing"], finished["error"]), ("finished", None))
            self.assertIn(finished["run_id"], [run["run_id"] for run in self.client.get("/runs").json()])
            run = self.client.get(f"/runs/{finished['run_id']}").json()
            review = self.client.get(f"/reviews/{finished['thread_id']}").json()
        self.assertEqual(review["status"], "waiting")
        self.assertEqual(review["review"]["source_run"], finished["run_id"])
        manifest = json.loads((self.work_dir / "runs" / finished["run_id"] / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["label"], snapshot["snapshot_id"])
        # The same plan as the supplied file's own run, apart from the run's name and time.
        with SqliteSaver.from_conn_string(str(self.work_dir / "reference.sqlite")) as checkpointer:
            reference_state, _, _, _ = paused_run(self.work_dir / "reference", checkpointer)
        for key in ("summary_rows", "decisions", "queues_after_plan", "processing_complete"):
            self.assertEqual(run["plan"][key], json.loads(json.dumps(reference_state["plan"][key])), key)

    def test_processing_needs_permission_and_runs_once(self):
        self.send(message())
        snapshot = self.capture()
        with mock.patch.object(chat, "run_graph") as run_graph:
            refused = self.process(snapshot["snapshot_id"])
            self.assertEqual((refused.status_code, refused.json()["detail"]), (403, chat.PAID_PROCESSING_OFF))
            self.assertEqual(self.snapshot(snapshot["snapshot_id"])["processing"], "not_started")
            os.environ["ALLOW_PAID_PROCESSING"] = "1"
            self.assertEqual(self.process("20990101T000000000000Z-00000000").status_code, 404)
            run_graph.return_value = ({"run_dir": str(self.work_dir / "runs/2026-10-23_10-00-00")}, [], "thread-1", {})
            self.assertEqual(self.process(snapshot["snapshot_id"]).status_code, 200)
            self.assertEqual(run_graph.call_count, 1)
            messages, label, _ = run_graph.call_args.args
            self.assertEqual((messages[0]["message_id"], label), ("L0001", snapshot["snapshot_id"]))
            self.assertEqual({key: self.snapshot(snapshot["snapshot_id"])[key] for key in ("processing", "run_id", "thread_id")},
                             {"processing": "finished", "run_id": "2026-10-23_10-00-00", "thread_id": "thread-1"})
            again = self.process(snapshot["snapshot_id"])
            self.assertEqual((again.status_code, again.json()["detail"]),
                             (409, f"Snapshot {snapshot['snapshot_id']} was already sent for processing."))
            # While one snapshot runs, no other starts.
            running = self.capture()
            chat.write_status(chat_storage.SNAPSHOTS_DIR / running["snapshot_id"], processing="running",
                              server_process=os.getpid())
            later = self.capture()
            blocked = self.process(later["snapshot_id"])
            self.assertEqual((blocked.status_code, blocked.json()["detail"]),
                             (409, f"Snapshot {running['snapshot_id']} is still being processed; wait until it finishes."))
            self.assertEqual(run_graph.call_count, 1)

    def test_a_failed_run_is_recorded_and_raised(self):
        self.send(message())
        snapshot = self.capture()
        os.environ["ALLOW_PAID_PROCESSING"] = "1"
        with mock.patch.object(chat, "run_graph", side_effect=RuntimeError("the model API refused the request")):
            with self.assertRaisesRegex(RuntimeError, "the model API refused"):
                self.process(snapshot["snapshot_id"])
        failed = self.snapshot(snapshot["snapshot_id"])
        self.assertEqual((failed["processing"], failed["error"]),
                         ("failed", "RuntimeError. The API server's terminal shows the details."))

    def test_a_run_of_an_earlier_server_process_reads_failed(self):
        self.send(message())
        stale = self.capture()
        chat.write_status(chat_storage.SNAPSHOTS_DIR / stale["snapshot_id"], processing="running",
                          server_process=os.getpid() + 1)
        self.assertEqual({key: self.snapshot(stale["snapshot_id"])[key] for key in ("processing", "error")},
                         {"processing": "failed", "error": "The API server stopped while this snapshot was being processed."})
        os.environ["ALLOW_PAID_PROCESSING"] = "1"
        with mock.patch.object(chat, "run_graph", return_value=({"run_dir": "runs/x"}, [], "thread-2", {})):
            self.assertEqual(self.process(self.capture()["snapshot_id"]).status_code, 200)


class EveryNameIsDefined(unittest.TestCase):

    def test_no_module_uses_an_undefined_name(self):
        for module_name in ("order_intake_from_chat.chat_storage", "fastapi_routes.chat", "main"):
            with self.subTest(module=module_name):
                self.assertEqual(undefined_names(importlib.import_module(module_name)), set())


if __name__ == "__main__":
    unittest.main()
