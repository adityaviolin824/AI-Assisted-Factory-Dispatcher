# settings_and_data.py: the settings, the two CSV files and the small helpers every processing step uses.
#
# Processing flow (each file imports its settings and helpers from here):
#   read_chat_messages -> extract_items -> create_and_link_tasks -> verify_tasks -> processing_run
#
# Came from: notebook 05, Sections 1 and 2.
# Reads:     backend/config.toml, then orders.csv and workshops.csv from the configured data folder.
# Writes:    nothing on import. write_json and save_checkpoint write the file they are given.
import csv
import hashlib
import json
import re
import tomllib
from pathlib import Path

# backend/, the folder that holds config.toml. Paths in config.toml are relative to it.
BACKEND_DIR = Path(__file__).resolve().parents[1]

with (BACKEND_DIR / "config.toml").open("rb") as file:
    CONFIG = tomllib.load(file)

# Input and output locations.
CHAT_FILE = BACKEND_DIR / CONFIG["input"]["chat_file"]
DATA_DIR = BACKEND_DIR / CONFIG["input"]["data_folder"]
MESSAGE_DATE = CONFIG["input"]["message_date"]  # a datetime.date; relative delivery words count from it
OUTPUT_DIR = BACKEND_DIR / CONFIG["output"]["folder"]
RUNS_DIR = OUTPUT_DIR / "runs"  # one folder per run, named by its start time
CACHE_DIR = OUTPUT_DIR / "response-cache"  # saved model answers, reused by every run

# Model settings. The stage model, its temperature or reasoning effort, the prompt, the payload and
# the response format together form each request's fingerprint, the key of its saved answer. Change
# one and the saved answer is no longer found, so that request is sent to the API again (and paid for).
STAGE_MODELS = {stage: CONFIG["models"][stage] for stage in ("intake", "link", "verify")}
# float(): "temperature = 0" in the config must give the same fingerprint as "0.0".
TEMPERATURE = float(CONFIG["models"]["temperature"])
# The reasoning effort of each stage that uses a reasoning model, such as {"intake": "high"}. Such a
# stage sends its effort instead of the temperature; a stage not listed keeps the temperature.
REASONING_EFFORTS = CONFIG.get("reasoning_effort", {})

# Batch settings, also part of the fingerprints (they decide what each request contains).
TARGET_SIZE = CONFIG["batches"]["target_size"]  # new messages per extraction call
CONTEXT_SIZE = CONFIG["batches"]["context_size"]  # earlier messages shown as context only
VERIFY_BATCH_SIZE = CONFIG["batches"]["verify_batch_size"]  # tasks per verification call
MAX_PAYLOAD_CHARS = CONFIG["batches"]["max_payload_chars"]  # largest request, in characters

# Fixed rules, kept in code rather than in config.toml.
DATA_YEAR = 2026  # year given to dates written without one, such as "Apr 02" (the dataset's year)
MAX_CANDIDATES = 6  # a follow-up with more possible task matches than this goes to review
HOLD_WINDOW = 2  # a review naming no order or message may modify the tasks of this many messages before it

# The CSV rows as raw text. ORDER_INDEX rows are copied into verification requests exactly as
# written, so converting them (for example pieces to numbers) would change every fingerprint.
# The CSV files are only read, never changed.
with (DATA_DIR / "orders.csv").open(newline="", encoding="utf-8") as file:
    ORDER_INDEX = {row["order_id"]: row for row in csv.DictReader(file)}
with (DATA_DIR / "workshops.csv").open(newline="", encoding="utf-8") as file:
    WORKSHOP_INDEX = {row["workshop_id"]: row for row in csv.DictReader(file)}
WORKSHOP_NAMES = [row["name"] for row in WORKSHOP_INDEX.values()]


def write_json(path, value):
    """Save value as a readable JSON file at path.

    It writes a temporary file and then renames it, so a crash never leaves a half-written file.
    Used for the run folder, the checkpoints, the call records and the saved answers.
    """
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    temporary.replace(path)


def save_checkpoint(run_dir, state):
    """Save the processing state to run_dir/state.json.

    Called after every accepted step, so after an error state.json shows how far the run got.
    """
    write_json(run_dir / "state.json", state)


def digest(value):
    """Return the SHA-256 fingerprint of a JSON value (64 hex characters).

    Keys are sorted first, so key order never changes the fingerprint. It is the saved-answer key.
    """
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def order_references(text):
    """Return the order IDs written in text, such as "ORD-061", each once, in the order first seen.

    Used to check that extraction kept every written order ID, to find link candidates and to
    look up orders. A shared order ID is only a hint: it never merges two tasks on its own.
    """
    return list(dict.fromkeys(
        re.findall(r"(?<![\w-])ORD-\d+(?![\w-])", text)
    ))
