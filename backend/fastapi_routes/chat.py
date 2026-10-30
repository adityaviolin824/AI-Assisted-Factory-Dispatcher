# chat.py: HTTP endpoints for the operations chat: send and read messages, capture snapshots, and
# process one snapshot (agreed 21 October 2026 in frontend/BACKEND_PROPOSAL.md, section 1; built
# 23 October 2026).
#
# Send, history and snapshots call the mock chat's functions, copied into
# order_intake_from_chat/chat_storage.py, and make no model call. GET /chat/dates (24 October 2026)
# returns the configured dates that relative words in the chat count from. Processing runs the whole pipeline
# on one snapshot's dispatch_requests.txt up to the dispatcher's first pause, as run_full_pipeline.py
# does on the configured chat file. It can make paid model calls, so it is refused unless the server
# was started with ALLOW_PAID_PROCESSING=1. It answers at once and runs in the background; the
# snapshot's processing.json records how far it got, and the page reads the snapshot again until
# processing finished or failed.
# POST /chat/transcriptions (29 October 2026) turns one short recording from the Record button into
# text for the message box. It calls a paid model, so it needs ALLOW_PAID_PROCESSING=1 as well; it
# saves nothing, and the worker checks and edits the text before Send.
# Send translates a message with Chinese characters into English on this computer first, when
# config.toml [translation] is on (30 October 2026); that is free and needs no switch.
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile
from langgraph.checkpoint.sqlite import SqliteSaver
from openai import OpenAIError
from pydantic import BaseModel

from app_full_pipeline.pipeline_graph import CHECKPOINT_FILE, run_graph
from order_intake_from_chat import chat_storage
from order_intake_from_chat.read_chat_messages import read_messages
from order_intake_from_chat.transcribe_speech import transcribe
from order_intake_from_chat.translate_message import needs_translation, translate_to_english
from order_processing_into_tasks.settings_and_data import BACKEND_DIR, MESSAGE_DATE
from task_allocation_to_workshops.allocation_settings_and_data import DISPATCH_DATE

router = APIRouter(tags=["chat"])

# The refusal when the server was started without permission for paid processing.
PAID_PROCESSING_OFF = ("Processing is switched off because it calls paid AI models. Start the API with "
                       "ALLOW_PAID_PROCESSING=1 to allow it.")
# The status of a snapshot that nobody has asked to process.
NOT_STARTED = {"processing": "not_started", "run_id": None, "thread_id": None, "error": None}
# The refusal of voice input under the same switch.
VOICE_OFF = ("Voice input is switched off because it calls a paid AI model. Start the API with "
             "ALLOW_PAID_PROCESSING=1 to allow it, or type the message.")
# The largest recording accepted. The page stops recording after one minute, about 0.5 MB of compressed
# browser audio; this keeps an unexpectedly long upload from becoming a large paid call.
MAX_AUDIO_BYTES = 5_000_000


class NewMessage(BaseModel):
    """One send event from the chat page. Sending the same submission_id again saves nothing new."""
    submission_id: str
    sender: str
    raw_text: str


def snapshot_ids():
    """Return the IDs of the saved snapshots, newest first (an ID starts with its UTC time).

    A hidden ".pending-" folder is an export whose writing failed, so it is not a snapshot.
    """
    return sorted((path.parent.name for path in chat_storage.SNAPSHOTS_DIR.glob("*/manifest.json")
                   if not path.parent.name.startswith(".")), reverse=True)


def snapshot_dir(snapshot_id):
    """Return a snapshot's folder, or refuse with 404.

    Only the ID of a saved snapshot is accepted, so no other file on the computer can be read.
    """
    if snapshot_id not in snapshot_ids():
        raise HTTPException(status_code=404, detail=f"No snapshot {snapshot_id}.")
    return chat_storage.SNAPSHOTS_DIR / snapshot_id


def processing_status(folder):
    """Return a snapshot's processing status: {"processing", "run_id", "thread_id", "error"}.

    Before anyone asked to process it, the status is "not_started". A run started by an earlier server
    process stopped with that process (for example when the dev server reloaded), so it reads "failed".
    """
    path = folder / "processing.json"
    if not path.exists():
        return dict(NOT_STARTED)
    status = json.loads(path.read_text(encoding="utf-8"))
    if status["processing"] == "running" and status.pop("server_process") != os.getpid():
        status.update(processing="failed", error="The API server stopped while this snapshot was being processed.")
    return status


def write_status(folder, **status):
    """Save a snapshot's processing status in processing.json, beside its TXT and manifest."""
    text = json.dumps({**NOT_STARTED, **status}, indent=2) + "\n"
    (folder / "processing.json").write_text(text, encoding="utf-8")


def snapshot(folder):
    """Return one snapshot as the chat page reads it: its ID, time and message count, the exported
    TXT exactly as saved, each message's R label and L message ID, and its processing status.
    """
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    lines = [{name: message[name] for name in ("message_id", "request_label", "processing_message_id")}
             for message in manifest["messages"]]
    return {"snapshot_id": manifest["snapshot_id"], "exported_at_utc": manifest["exported_at_utc"],
            "message_count": manifest["message_count"],
            "text": (folder / "dispatch_requests.txt").read_bytes().decode("utf-8"), "lines": lines,
            **processing_status(folder)}


def process_in_background(folder):
    """Run the pipeline on a snapshot's dispatch_requests.txt up to the dispatcher's first pause, as
    run_full_pipeline.py does, and record the result in processing.json.

    The result is "finished", with the new run and thread IDs, or "failed". A failure keeps only the
    error's type for the page, since a model API error can quote part of the API key; the error is
    raised again, so the server's terminal shows all of it.
    """
    # OPENAI_API_KEY and the LangSmith settings come from backend/.env, as in run_full_pipeline.py.
    load_dotenv(BACKEND_DIR / ".env", override=False)
    try:
        messages = read_messages(folder / "dispatch_requests.txt")
        with SqliteSaver.from_conn_string(str(CHECKPOINT_FILE)) as checkpointer:
            graph_state, _, thread_id, _ = run_graph(messages, folder.name, checkpointer)
    except Exception as error:
        write_status(folder, processing="failed",
                     error=f"{type(error).__name__}. The API server's terminal shows the details.")
        raise
    write_status(folder, processing="finished", run_id=Path(graph_state["run_dir"]).name, thread_id=thread_id)


@router.get("/chat/dates")
def chat_dates():
    """Return the dates from config.toml that processing uses: {message_date, dispatch_date}.

    Relative delivery words in the chat, such as "by Friday", count from message_date, and every plan
    starts from dispatch_date. The chat page shows them, because they are not today's date.
    """
    return {"message_date": MESSAGE_DATE.isoformat(), "dispatch_date": DISPATCH_DATE.isoformat()}


@router.get("/chat/messages")
def list_messages():
    """Return every chat message in saved order: {message_id, submission_id, sender, raw_text,
    received_at_utc}. Before the first message there is none, and reading creates no file.
    """
    if not chat_storage.DATABASE.exists():
        return []
    return chat_storage.read_messages(chat_storage.DATABASE)


@router.post("/chat/messages")
def send_message(message: NewMessage):
    """Save one message and return it, as the mock chat's Send does. It makes no paid model call.

    A message with Chinese characters is saved as its English translation when translation is on.
    An empty name or text, or a name with a colon or a line break, is refused with 422 and the mock's
    own message; so is a translation that did not keep the order and workshop IDs.
    """
    chat_storage.initialize_storage(chat_storage.DATABASE)
    text = message.raw_text
    try:
        if needs_translation(text):
            text = translate_to_english(text)
        return chat_storage.save_message(chat_storage.DATABASE, message.submission_id, message.sender, text)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.get("/chat/snapshots")
def list_snapshots():
    """Return every snapshot, newest first."""
    return [snapshot(chat_storage.SNAPSHOTS_DIR / snapshot_id) for snapshot_id in snapshot_ids()]


@router.post("/chat/snapshots")
def create_snapshot():
    """Capture the whole conversation as a new, fixed snapshot and return it. It makes no model call.

    An empty chat is refused with 400 "There are no messages to export yet."
    """
    chat_storage.initialize_storage(chat_storage.DATABASE)
    try:
        folder = chat_storage.export_conversation(chat_storage.DATABASE, chat_storage.SNAPSHOTS_DIR)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    return snapshot(folder)


@router.get("/chat/snapshots/{snapshot_id}")
def read_snapshot(snapshot_id: str):
    """Return one snapshot; the page reads it again while it is being processed."""
    return snapshot(snapshot_dir(snapshot_id))


@router.post("/chat/snapshots/{snapshot_id}/process")
def process_snapshot(snapshot_id: str, background_tasks: BackgroundTasks):
    """Start the pipeline on one snapshot and return the snapshot at once, with processing "running".

    Paid model calls: refused with 403 unless the server was started with ALLOW_PAID_PROCESSING=1. A
    snapshot is processed at most once, and one at a time; otherwise 409. The page then reads the
    snapshot until processing is "finished", with the run and thread IDs, or "failed".
    """
    folder = snapshot_dir(snapshot_id)
    if os.environ.get("ALLOW_PAID_PROCESSING") != "1":
        raise HTTPException(status_code=403, detail=PAID_PROCESSING_OFF)
    if processing_status(folder)["processing"] != "not_started":
        raise HTTPException(status_code=409, detail=f"Snapshot {snapshot_id} was already sent for processing.")
    running = [other for other in snapshot_ids()
               if processing_status(chat_storage.SNAPSHOTS_DIR / other)["processing"] == "running"]
    if running:
        raise HTTPException(status_code=409, detail=f"Snapshot {running[0]} is still being processed; "
                                                    "wait until it finishes.")
    write_status(folder, processing="running", server_process=os.getpid())
    background_tasks.add_task(process_in_background, folder)
    return snapshot(folder)


@router.post("/chat/transcriptions")
def transcribe_recording(audio: UploadFile):
    """Return {"text"}: one recording from the Record button, as text in the language spoken.

    Paid model call: refused with 403 unless the server was started with ALLOW_PAID_PROCESSING=1, and
    with 413 for a recording over MAX_AUDIO_BYTES. Nothing is saved. A failed model call answers 502
    with only the error's type, because a model API error can quote part of the API key.
    """
    if os.environ.get("ALLOW_PAID_PROCESSING") != "1":
        raise HTTPException(status_code=403, detail=VOICE_OFF)
    recording = audio.file.read()
    if len(recording) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="The recording is too long. Record up to one minute.")
    # OPENAI_API_KEY comes from backend/.env, as for processing.
    load_dotenv(BACKEND_DIR / ".env", override=False)
    try:
        text = transcribe(recording, audio.filename)
    except OpenAIError as error:
        raise HTTPException(status_code=502, detail=f"Transcription failed ({type(error).__name__}). "
                                                    "Type the message instead.") from error
    return {"text": text}
