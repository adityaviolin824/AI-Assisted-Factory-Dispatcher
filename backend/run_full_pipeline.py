# run_full_pipeline.py: run the whole pipeline, chat file -> checked tasks -> plan -> dispatcher review,
# as one LangGraph run that pauses for the dispatcher.
#
# Run from backend/:  uv run python run_full_pipeline.py
#
# Steps: read_chat_messages (order_intake_from_chat/) turns the chat file named in config.toml into
# messages; run_graph (app_full_pipeline/pipeline_graph.py) processes them and plans the verified
# tasks, saving everything in output/runs/<start time>/. The folder holds the same files as
# run_intake_and_processing.py followed by run_allocation.py on that folder. The run then pauses
# with the dispatcher's first review and prints it with its thread ID; the paused run is kept in
# output/dispatcher-review-checkpoints.sqlite. Answer it with resume_dispatcher_review.py.
#
# Cost: a request already answered before (same prompt, model, payload and response format) is read
# from output/response-cache/ for free. Any other request is sent to the OpenAI API and paid for,
# using OPENAI_API_KEY from backend/.env. The output says how many requests were paid. The review
# makes no model call.
# LangSmith: with LANGSMITH_TRACING=true in backend/.env, every run, even a free one, sends the whole
# graph state (chat text, tasks, plan and the dispatcher's review) to LangSmith, as the run "full-pipeline".
import json
from pathlib import Path

from dotenv import load_dotenv
from langgraph.checkpoint.sqlite import SqliteSaver

from app_full_pipeline.pipeline_graph import CHECKPOINT_FILE, run_graph
from order_intake_from_chat.read_chat_messages import read_messages
from order_processing_into_tasks.settings_and_data import (
    BACKEND_DIR, CHAT_FILE, CONTEXT_SIZE, DATA_DIR, ORDER_INDEX, OUTPUT_DIR, REASONING_EFFORTS,
    STAGE_MODELS, TARGET_SIZE, TEMPERATURE, VERIFY_BATCH_SIZE, WORKSHOP_INDEX)
from resume_dispatcher_review import print_pause
from task_allocation_to_workshops.allocation_settings_and_data import DISPATCH_DATE, PLAN_OBJECTIVE


def main():
    """Read the configured chat file, run the graph to the dispatcher's first pause and print the review."""
    # Load OPENAI_API_KEY and the LangSmith settings from backend/.env. A variable that is already set
    # wins (override=False). The key is needed only for a request with no saved answer; it is never printed.
    load_dotenv(BACKEND_DIR / ".env", override=False)

    # Show the inputs and settings once, so every run starts with them visible.
    print(f"Loaded {len(ORDER_INDEX)} orders and {len(WORKSHOP_INDEX)} workshops from {DATA_DIR}.")
    print(f"Models: {STAGE_MODELS}; reasoning effort: {REASONING_EFFORTS}; "
          f"temperature (stages without an effort): {TEMPERATURE}")
    print(f"Batches: {TARGET_SIZE} new messages, {CONTEXT_SIZE} context messages, "
          f"{VERIFY_BATCH_SIZE} tasks per verification.")
    objective = PLAN_OBJECTIVE or "each request's own preference"
    print(f"Dispatch date: {DISPATCH_DATE}; objective: {objective}")
    print(f"Output folder: {OUTPUT_DIR}\n")

    messages = read_messages(CHAT_FILE)
    # The checkpoint file is in the output folder, which a first run may not have created yet.
    OUTPUT_DIR.mkdir(exist_ok=True)
    with SqliteSaver.from_conn_string(str(CHECKPOINT_FILE)) as checkpointer:
        graph_state, steps, thread_id, paused = run_graph(messages, CHAT_FILE.name, checkpointer)
    if graph_state is None:
        return

    # A call record without "reused_response" was sent to the API, so it was paid for.
    run_dir = Path(graph_state["run_dir"])
    call_files = sorted((run_dir / "calls").glob("*.json"))
    records = [json.loads(path.read_text(encoding="utf-8")) for path in call_files]
    paid = sum(not record.get("reused_response") for record in records)
    print(f"\nRun folder: {run_dir}")
    print(f"Plan complete: {graph_state['plan']['processing_complete']}; steps: {len(steps)}")
    print(f"Model calls: {len(records)}; sent to the API (paid): {paid}")
    print_pause(paused, run_dir, thread_id)


if __name__ == "__main__":
    main()
