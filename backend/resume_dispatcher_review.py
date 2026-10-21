# resume_dispatcher_review.py: show or answer a dispatcher review that run_full_pipeline.py paused.
#
# Run from backend/:
#   uv run python resume_dispatcher_review.py <thread ID>                 show the paused review again
#   uv run python resume_dispatcher_review.py <thread ID> <answer.json>   send the dispatcher's answer
# With no thread ID, it prints how to use it and stops.
#
# Paused runs are kept in output/dispatcher-review-checkpoints.sqlite, so a review can be answered after
# the program that paused it has ended. An answer file holds one answer, for example:
#   {"decisions": [{"decision": "choose_workshop", "task_id": "T:L0009:J1", "workshop_id": "W1"}],
#    "then": "review_again"}
# Decisions: correct (facts, resolves), choose_workshop (workshop_id), accept_late (optional max_days;
# sent alone), warnings_checked (row_ids) and clear. Each answer with "review_again" is checked, applied
# and shown as a new review. {"decisions": [], "then": "approve_all"} approves the review last shown and
# saves dispatcher-plan.json and dispatcher-decisions.json in the run folder. Use the task IDs of this
# run's review. A refused answer changes nothing and says why.
#
# Cost: none. Resuming calculates in Python and makes no model call.
# LangSmith: with LANGSMITH_TRACING=true in backend/.env, each resumed run sends the review and the
# dispatcher's decisions to LangSmith, as the run "full-pipeline".
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from langgraph.checkpoint.sqlite import SqliteSaver

from app_full_pipeline.pipeline_graph import CHECKPOINT_FILE, paused_review, resume_graph
from dispatcher_review.dispatcher_decisions import print_review, verified_tasks_by_id
from order_processing_into_tasks.settings_and_data import BACKEND_DIR


def print_pause(paused, run_dir, thread_id, before=None):
    """Print a paused review: why the last answer was refused (if it was), the review, and how to answer.

    With before (the review the dispatcher answered), changed rows are marked.
    """
    if paused["refused"]:
        print(f"\nAnswer refused; nothing changed: {paused['refused']}")
    print()
    print_review(paused["review"], verified_tasks_by_id(run_dir), before)
    print(f"\nWaiting for the dispatcher. Thread ID: {thread_id}")
    print(f"Answer with:  uv run python resume_dispatcher_review.py {thread_id} <answer.json>")


def main():
    """Show the paused review of the thread named on the command line, or send it an answer file."""
    if len(sys.argv) not in (2, 3):
        print("Usage: uv run python resume_dispatcher_review.py <thread ID> [<answer.json>]")
        return
    # LangSmith settings from backend/.env; a variable that is already set wins.
    load_dotenv(BACKEND_DIR / ".env", override=False)
    thread_id = sys.argv[1]
    with SqliteSaver.from_conn_string(str(CHECKPOINT_FILE)) as checkpointer:
        graph_state, paused = paused_review(thread_id, checkpointer)
        if paused is None:
            print(f"Thread {thread_id} has no paused dispatcher review in {CHECKPOINT_FILE}.")
            return
        run_dir = Path(graph_state["run_dir"])
        if len(sys.argv) == 2:
            print_pause(paused, run_dir, thread_id)
            return
        answer = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        graph_state, _, _, paused_again = resume_graph(thread_id, answer, checkpointer)
    if paused_again is not None:
        print_pause(paused_again, run_dir, thread_id, before=paused["review"])
        return
    print()
    print_review(graph_state["review"], verified_tasks_by_id(run_dir))
    print(f"\nApproved and saved in {run_dir}: dispatcher-plan.json and dispatcher-decisions.json.")


if __name__ == "__main__":
    main()
