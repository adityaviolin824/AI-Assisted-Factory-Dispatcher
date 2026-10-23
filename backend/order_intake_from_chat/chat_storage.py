# chat_storage.py: the shared operations chat. Save each sent message in SQLite, and export the whole
# conversation as a fixed snapshot: the chat TXT that processing reads, with a manifest.
#
# Flow:      fastapi_routes/chat.py -> [save_message, read_messages, export_conversation] ->
#            read_chat_messages.read_messages reads a snapshot's dispatch_requests.txt for processing.
# Came from: the mock chat, experimentation_notebooks/mock_frontend/app.py (23 October 2026).
#            DISPLAY_TIMEZONE and the five storage functions are copied unchanged; the mock's comments
#            became docstrings. The mock's Streamlit screen stays there. CHAT_DIR, DATABASE and
#            SNAPSHOTS_DIR are new: the app keeps its chat in the output folder, apart from the mock's.
# Reads:     DATABASE.
# Writes:    DATABASE (save_message, initialize_storage) and one new folder per snapshot,
#            SNAPSHOTS_DIR/<snapshot ID>/ with dispatch_requests.txt and manifest.json (export_conversation).
#            No model is called.
import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from order_processing_into_tasks.settings_and_data import OUTPUT_DIR

# The app's chat, in the output folder (gitignored).
CHAT_DIR = OUTPUT_DIR / "chat"
DATABASE = CHAT_DIR / "messages.sqlite3"
SNAPSHOTS_DIR = CHAT_DIR / "snapshots"
# The time zone of the exported "[HH:MM]" times.
DISPLAY_TIMEZONE = "Asia/Singapore"


def initialize_storage(database):
    """Create the shared message store once; existing history is always retained."""
    database.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(database, timeout=10)) as connection, connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id TEXT NOT NULL UNIQUE,
                sender TEXT NOT NULL,
                raw_text TEXT NOT NULL,
                received_at_utc TEXT NOT NULL
            )
        """)


def save_message(database, submission_id, sender, raw_text):
    """Save one send event. Retrying that event returns its original record.

    Identical wording with a new submission ID is still a new message.
    """
    if not sender.strip():
        raise ValueError("Enter your name before sending a message.")
    if sender.splitlines() != [sender] or ":" in sender:
        raise ValueError("Use a single-line name without a colon.")
    if not raw_text.strip():
        raise ValueError("Write a message before pressing Send.")
    sender = sender.strip()
    received_at = datetime.now(timezone.utc).isoformat()
    with closing(sqlite3.connect(database, timeout=10)) as connection, connection:
        connection.row_factory = sqlite3.Row
        connection.execute(
            """INSERT INTO messages (submission_id, sender, raw_text, received_at_utc)
               VALUES (?, ?, ?, ?) ON CONFLICT(submission_id) DO NOTHING""",
            (submission_id, sender, raw_text, received_at),
        )
        row = dict(connection.execute(
            "SELECT * FROM messages WHERE submission_id = ?", (submission_id,)
        ).fetchone())
        if (row["sender"], row["raw_text"]) != (sender, raw_text):
            raise ValueError("This submission ID already belongs to a different message.")
    return row


def read_messages(database):
    """Return every message in saved order. One SELECT gives a consistent view for the timeline or an export."""
    with closing(sqlite3.connect(database, timeout=10)) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(
            "SELECT * FROM messages ORDER BY message_id"
        ).fetchall()]


def build_export(messages, snapshot_id, exported_at_utc):
    """Build the TXT and its metadata from the same captured messages, never from two reads.

    Each message becomes one line, such as "R01 [10:15] Chen: Please allocate ORD-061.", which
    processing numbers L0001; the manifest maps each database message to its R label and L ID.
    """
    if not messages:
        raise ValueError("There are no messages to export yet.")
    lines, mapped_messages = [], []
    for position, message in enumerate(messages, 1):
        label = f"R{position:02d}"
        local_time = datetime.fromisoformat(message["received_at_utc"]).astimezone(
            ZoneInfo(DISPLAY_TIMEZONE)
        )
        # The notebook uses splitlines(): even Unicode line separators must flatten.
        body = " ".join(message["raw_text"].splitlines())
        line = f"{label} [{local_time:%H:%M}] {message['sender']}: {body}"
        lines.append(line)
        mapped_messages.append({
            "message_id": message["message_id"],
            "request_label": label,
            "processing_message_id": f"L{position:04d}",
            "sender": message["sender"],
            "received_at_utc": message["received_at_utc"],
            "raw_text": message["raw_text"],
            "exported_line": line,
        })
    # Bytes avoid platform newline translation and match the supplied TXT exactly.
    txt_bytes = ("\r\n".join(lines) + "\r\n").encode("utf-8")
    manifest = {
        "schema_version": 1,
        "snapshot_id": snapshot_id,
        "exported_at_utc": exported_at_utc,
        "display_timezone": DISPLAY_TIMEZONE,
        "message_count": len(messages),
        "txt_sha256": hashlib.sha256(txt_bytes).hexdigest(),
        "messages": mapped_messages,
    }
    return txt_bytes, manifest


def export_conversation(database, exports_dir):
    """Write one new snapshot folder and return it.

    It is published only after both files have been written successfully: a failed write leaves a
    hidden ".pending-" folder, never a completed export.
    """
    messages = read_messages(database)
    now = datetime.now(timezone.utc)
    snapshot_id = f"{now:%Y%m%dT%H%M%S%fZ}-{uuid4().hex[:8]}"
    txt_bytes, manifest = build_export(messages, snapshot_id, now.isoformat())
    pending = exports_dir / f".pending-{snapshot_id}"
    pending.mkdir(parents=True)
    (pending / "dispatch_requests.txt").write_bytes(txt_bytes)
    (pending / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    destination = exports_dir / snapshot_id
    pending.rename(destination)
    return destination
