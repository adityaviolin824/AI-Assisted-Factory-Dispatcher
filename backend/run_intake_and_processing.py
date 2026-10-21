# run_intake_and_processing.py: run intake and processing on the chat file named in config.toml.
#
# Run from backend/:  uv run python run_intake_and_processing.py
#
# Steps: read_chat_messages (order_intake_from_chat/) turns the chat file into messages, then
# process_messages (order_processing_into_tasks/) extracts items, creates and links tasks, verifies
# them and saves the run in output/runs/<start time>/.
#
# Cost: a request already answered before (same prompt, model, payload and response format) is read
# from output/response-cache/ for free. Any other request is sent to the OpenAI API and paid for,
# using OPENAI_API_KEY from backend/.env. The last line says how many requests were paid.
import json

from dotenv import load_dotenv

from order_intake_from_chat.read_chat_messages import read_messages
from order_processing_into_tasks.processing_run import process_messages
from order_processing_into_tasks.settings_and_data import (
    BACKEND_DIR, CHAT_FILE, CONTEXT_SIZE, DATA_DIR, ORDER_INDEX, OUTPUT_DIR, REASONING_EFFORTS,
    STAGE_MODELS, TARGET_SIZE, TEMPERATURE, VERIFY_BATCH_SIZE, WORKSHOP_INDEX)


def main():
    """Read the configured chat file, process it in one new run and print where the results are."""
    # Load OPENAI_API_KEY and the LangSmith settings from backend/.env. A variable that is already set
    # wins (override=False). The key is needed only for a request with no saved answer; it is never
    # printed. With LANGSMITH_TRACING=true, paid requests (with the chat text) are sent to LangSmith.
    load_dotenv(BACKEND_DIR / ".env", override=False)

    # Show the inputs and settings once, so every run starts with them visible.
    print(f"Loaded {len(ORDER_INDEX)} orders and {len(WORKSHOP_INDEX)} workshops from {DATA_DIR}.")
    print(f"Models: {STAGE_MODELS}; reasoning effort: {REASONING_EFFORTS}; "
          f"temperature (stages without an effort): {TEMPERATURE}")
    print(f"Batches: {TARGET_SIZE} new messages, {CONTEXT_SIZE} context messages, "
          f"{VERIFY_BATCH_SIZE} tasks per verification.")
    print(f"Output folder: {OUTPUT_DIR}\n")

    messages = read_messages(CHAT_FILE)
    run_dir, state, summary = process_messages(messages, CHAT_FILE.name)
    if run_dir is None:
        return

    # A call record without "reused_response" was sent to the API, so it was paid for.
    call_files = sorted((run_dir / "calls").glob("*.json"))
    records = [json.loads(path.read_text(encoding="utf-8")) for path in call_files]
    paid = sum(not record.get("reused_response") for record in records)
    print(f"\nRun folder: {run_dir}")
    print(f"Model calls: {len(records)}; sent to the API (paid): {paid}")


if __name__ == "__main__":
    main()
