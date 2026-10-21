# dispatcher.py: HTTP endpoints for the dispatcher's review of a run that run_full_pipeline.py paused.
#
# They do what resume_dispatcher_review.py does: paused_review and resume_graph
# (app_full_pipeline/pipeline_graph.py) on the same SQLite checkpoint file. The thread ID is the one
# run_full_pipeline.py printed; it is not a run ID. Resuming calculates in Python: no model call.
from fastapi import APIRouter, HTTPException
from langgraph.checkpoint.sqlite import SqliteSaver

from app_full_pipeline.pipeline_graph import CHECKPOINT_FILE, paused_review, resume_graph

router = APIRouter(tags=["dispatcher review"])


@router.get("/reviews/{thread_id}")
def read_review(thread_id: str):
    """Return the paused review of a thread.

    The answer is {"status": "waiting", "review": ..., "refused": ...}, where refused is why the
    dispatcher's last answer was refused, or None.
    """
    with SqliteSaver.from_conn_string(str(CHECKPOINT_FILE)) as checkpointer:
        _, paused = paused_review(thread_id, checkpointer)
    if paused is None:
        raise HTTPException(status_code=404, detail=f"Thread {thread_id} has no paused dispatcher review.")
    return {"status": "waiting", "review": paused["review"], "refused": paused["refused"]}


@router.post("/reviews/{thread_id}/answer")
def answer_review(thread_id: str, answer: dict):
    """Send one dispatcher answer to a paused review and return what follows.

    - After an edit, or a refused answer, the review waits again:
      {"status": "waiting", "review": ..., "refused": the reason (nothing changed) or None}.
    - After approve_all: {"status": "finished", "review": the final review saved in the run folder,
      "refused": None}.
    The answer is checked by apply_answer, so its refusal messages reach the dispatcher unchanged.
    """
    with SqliteSaver.from_conn_string(str(CHECKPOINT_FILE)) as checkpointer:
        _, paused = paused_review(thread_id, checkpointer)
        if paused is None:
            raise HTTPException(status_code=404, detail=f"Thread {thread_id} has no paused dispatcher review.")
        graph_state, _, _, paused_again = resume_graph(thread_id, answer, checkpointer)
    if paused_again is None:
        return {"status": "finished", "review": graph_state["review"], "refused": None}
    return {"status": "waiting", "review": paused_again["review"], "refused": paused_again["refused"]}
