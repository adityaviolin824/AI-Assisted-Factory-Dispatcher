# pipeline_graph.py: the LangGraph pipeline. One graph run takes the chat messages through
# processing (order_processing_into_tasks/) and allocation (task_allocation_to_workshops/) to a plan,
# then pauses for the dispatcher's review (dispatcher_review/) until the dispatcher approves it.
#
# The graph:
#   START -> start_run -> link_items --after_link--> extract_batch -> back to link_items (one turn per batch)
#                                    \-------------> verify_tasks -> save_outputs -> plan_allocation
#   plan_allocation -> dispatcher_review --after_review--> dispatcher_review (pause again)
#                                        \---------------> save_review -> END
#
# Came from: notebook 05, Sections 14 and 15. The plan_allocation node now calls the allocation
#            module, so every run gets a plan (a partial one when processing is incomplete), and the
#            notebook's after_save router is gone. The review pause is new (20 October 2026).
# Writes:    RUNS_DIR/<start time>/: manifest.json, state.json, calls/, plan.json and plan-history/,
#            the same files as run_intake_and_processing.py followed by run_allocation.py; after the
#            dispatcher's approval also dispatcher-decisions.json and dispatcher-plan.json. While a run
#            waits for the dispatcher, the checkpointer (CHECKPOINT_FILE for the runner scripts) keeps it.
#
# Nodes hold no rules: each calls the module functions and returns only the graph-state keys it
# changed (LangGraph replaces those keys; there are no reducers). Nodes catch no errors: an API, file
# or programming error stops the graph and is shown as it is; state.json then holds the progress, and
# run_allocation.py can still plan that folder. "graph_state" is the LangGraph state; "processing" is
# the processing state, saved as state.json.
#
# The pause is LangGraph's interrupt(): dispatcher_review stops the run and the checkpointer saves its
# state under a thread ID. resume_graph continues it with the dispatcher's answer; LangGraph then runs
# dispatcher_review again from its start, so that node only reads the saved review before interrupt()
# and writes nothing. The state is saved only when the run stops (durability "exit"): at the pause, at
# the end or on an error, not after every processing step.
import uuid
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from dispatcher_review.dispatcher_decisions import apply_answer, save_dispatcher_files
from dispatcher_review.dispatcher_plan import build_dispatcher_plan, finalize_review
from order_processing_into_tasks.create_and_link_tasks import link_pending_items
from order_processing_into_tasks.extract_items import intake_window, owned_windows
from order_processing_into_tasks.model_calls_with_cache import RecordedModel
from order_processing_into_tasks.processing_run import prepare_run, save_run_outputs
from order_processing_into_tasks.settings_and_data import OUTPUT_DIR, save_checkpoint
from order_processing_into_tasks.verify_tasks import run_verification
from task_allocation_to_workshops import allocation_plan

# The SQLite file in which run_full_pipeline.py and resume_dispatcher_review.py keep paused reviews.
CHECKPOINT_FILE = OUTPUT_DIR / "dispatcher-review-checkpoints.sqlite"
# LangGraph's step limit for one resume. A resume runs dispatcher_review, then either pauses there again
# or runs save_review; it needs a limit of 1, so 10 stops a routing bug quickly.
RESUME_RECURSION_LIMIT = 10


class PipelineState(TypedDict, total=False):
    """The keys of the graph state. Every value is plain data, so LangSmith shows the whole state at
    every step. langgraph silently drops a returned key that is not listed here.
    """
    messages: list    # the chat lines: [{"message_id": "L0001", "raw_text": "..."}, ...]
    label: str        # the run label, saved in manifest.json
    run_dir: str      # this run's folder (start_run)
    processing: dict  # the processing state (start_run, then every processing node)
    summary: dict     # the counts from save_run_outputs
    plan: dict        # the tentative plan, also saved as plan.json (plan_allocation)
    decisions: dict   # the dispatcher's accepted decisions (plan_allocation, dispatcher_review)
    review: dict      # the review shown to the dispatcher; after save_review, the approved final plan
    then: str         # the dispatcher's next step: "review_again" or "approve_all" (dispatcher_review)
    review_error: str | None  # why the dispatcher's last answer was refused, or None


# ---------------------------------------------------------------------------------------------
# The eight nodes.
# ---------------------------------------------------------------------------------------------


def start_run(graph_state):
    """Node 1: open a new run folder with manifest.json and an empty processing state.

    Every run starts from scratch; saved model answers make a repeated run free, so there is no resume.
    """
    run_dir, processing = prepare_run(graph_state["messages"], graph_state["label"])
    print(f"[Graph] start_run: {len(graph_state['messages'])} messages; run folder {run_dir}")
    return {"run_dir": str(run_dir), "processing": processing}


def link_items(graph_state):
    """Node 2: give each new item a task, or attach a follow-up to its task.

    Runs after start_run and after every extract_batch, so a follow-up is compared with the tasks that
    exist when it arrives. Items already handled are skipped, so running it again is safe.
    """
    print("\n[Graph] link_items")
    run_dir, processing = Path(graph_state["run_dir"]), graph_state["processing"]
    # One model caller per node. It creates the API client only for a request with no saved answer.
    ask = RecordedModel(run_dir)
    link_pending_items(processing, ask, lambda: save_checkpoint(run_dir, processing))
    return {"processing": processing}


def extract_batch(graph_state):
    """Node 3: extract the next batch of unread messages into items, then save state.json.

    Every batch, accepted or rejected, marks its target messages processed, so the first remaining
    window of owned_windows is always the next batch.
    """
    run_dir, processing, messages = Path(graph_state["run_dir"]), graph_state["processing"], graph_state["messages"]
    # after_link sends the graph here only when a window remains, so next() always finds one.
    context, targets = next(owned_windows(messages, set(processing["processed_message_ids"])))
    print(f"\n[Graph] extract_batch: {', '.join(message['message_id'] for message in targets)}")
    ask = RecordedModel(run_dir)
    intake_window(processing, context, targets, ask)
    save_checkpoint(run_dir, processing)
    return {"processing": processing}


def verify_tasks(graph_state):
    """Node 4: verify the current version of every task that needs it.

    Runs once every message is read and linked, so each task is checked with its latest correction.
    One node, not one per batch: run_verification's batches drop stale reviews while they run.
    """
    print("\n[Graph] verify_tasks")
    run_dir, processing = Path(graph_state["run_dir"]), graph_state["processing"]
    ask = RecordedModel(run_dir)
    run_verification(run_dir, processing, ask)
    return {"processing": processing}


def save_outputs(graph_state):
    """Node 5: save state.json and count the outcomes."""
    print("\n[Graph] save_outputs")
    processing = graph_state["processing"]
    summary = save_run_outputs(Path(graph_state["run_dir"]), processing, graph_state["messages"])
    return {"processing": processing, "summary": summary}


def plan_allocation(graph_state):
    """Node 6: plan this run's verified tasks and save plan.json (and its plan-history/ copy), then
    calculate the dispatcher's first review, with no decision yet.

    The tasks come straight from this run's graph state, so the plan can only use the run that was
    just processed. An incomplete run gets a plan marked partial (see allocation_plan.plan_allocation).
    The review is returned here, so it is in the saved state before dispatcher_review shows it.
    """
    print("\n[Graph] plan_allocation")
    run_dir = Path(graph_state["run_dir"])
    plan = allocation_plan.plan_allocation(run_dir, graph_state["processing"], graph_state["messages"])
    decisions = {"source_run": run_dir.name, "revision": 0, "decisions": {}}
    review = build_dispatcher_plan(run_dir, decisions)
    return {"plan": plan, "decisions": decisions, "review": review, "review_error": None}


def dispatcher_review(graph_state):
    """Node 7: pause for the dispatcher with the saved review, then apply their answer.

    interrupt() stops the run and hands the review (and why the last answer was refused) to the
    caller. When resume_graph sends the answer, LangGraph runs this node again from its start and
    interrupt() returns that answer. An edit gives a new review and pauses again; "approve_all"
    goes on to save_review with the review the dispatcher saw.
    """
    answer = interrupt({"review": graph_state["review"], "refused": graph_state["review_error"]})
    print("\n[Graph] dispatcher_review")
    decisions, review, then, refusal = apply_answer(Path(graph_state["run_dir"]), graph_state["decisions"],
                                                    graph_state["review"], answer)
    return {"decisions": decisions, "review": review, "then": then, "review_error": refusal}


def save_review(graph_state):
    """Node 8: label the approved review final and save it with the decisions (dispatcher-plan.json and
    dispatcher-decisions.json, each with a plan-history/ copy).

    It plans nothing again and commits no workshop assignment: the saved numbers are the ones shown.
    """
    print("\n[Graph] save_review")
    run_dir, decisions = Path(graph_state["run_dir"]), graph_state["decisions"]
    final = finalize_review(graph_state["review"])
    save_dispatcher_files(run_dir, decisions, final)
    return {"decisions": decisions, "review": final}


# ---------------------------------------------------------------------------------------------
# The router, the graph and the run.
# ---------------------------------------------------------------------------------------------


def after_link(graph_state):
    """Router after link_items: "extract_batch" while a message is unread, then "verify_tasks".

    It asks owned_windows, the same function extract_batch uses, so the router and the node never
    disagree about which batch is left. Routers never print, write files or change the state.
    """
    processed = set(graph_state["processing"]["processed_message_ids"])
    if next(owned_windows(graph_state["messages"], processed), None) is not None:
        return "extract_batch"
    return "verify_tasks"


def after_review(graph_state):
    """Router after dispatcher_review: "save_review" once the dispatcher approved all, otherwise
    "dispatcher_review" again (after an edit or a refused answer). Routers never print, write files or
    change the state.
    """
    if graph_state["then"] == "approve_all":
        return "save_review"
    return "dispatcher_review"


def build_graph(checkpointer):
    """Build and compile the graph drawn at the top of this file, with the checkpointer that keeps a
    paused run (an InMemorySaver or a SqliteSaver).

    add_conditional_edges lists the router's possible targets, so the drawn graph shows only the real
    paths; compile() checks that every edge has a known node.
    """
    graph = StateGraph(PipelineState)
    graph.add_node("start_run", start_run)
    graph.add_node("link_items", link_items)
    graph.add_node("extract_batch", extract_batch)
    graph.add_node("verify_tasks", verify_tasks)
    graph.add_node("save_outputs", save_outputs)
    graph.add_node("plan_allocation", plan_allocation)
    graph.add_node("dispatcher_review", dispatcher_review)
    graph.add_node("save_review", save_review)
    graph.add_edge(START, "start_run")
    graph.add_edge("start_run", "link_items")
    graph.add_conditional_edges("link_items", after_link, ["extract_batch", "verify_tasks"])
    graph.add_edge("extract_batch", "link_items")
    graph.add_edge("verify_tasks", "save_outputs")
    graph.add_edge("save_outputs", "plan_allocation")
    graph.add_edge("plan_allocation", "dispatcher_review")
    graph.add_conditional_edges("dispatcher_review", after_review, ["dispatcher_review", "save_review"])
    graph.add_edge("save_review", END)
    return graph.compile(checkpointer=checkpointer)


def recursion_limit(messages):
    """Return LangGraph's step limit for these messages: 2N + 10 for N intake batches.

    A run to the dispatcher's first pause takes 2N + 6 steps: start_run, the first link_items, N times
    extract_batch + link_items, then verify_tasks, save_outputs, plan_allocation and dispatcher_review,
    which pauses. 2N + 6 is the smallest limit that works; the margin of 4 stops a routing bug quickly.
    """
    return 2 * len(list(owned_windows(messages, set()))) + 10


def stream_to_pause(pipeline, graph_input, config):
    """Run the graph until it pauses for the dispatcher or ends, and save its state when it stops.

    Returns (graph_state, steps, paused): the saved graph state, the nodes that finished in the order
    they ran, and the pause's {"review", "refused"} (None when the graph ended). A pause arrives as an
    "__interrupt__" update, not as a finished node, so it is not counted as a step.
    """
    steps = []
    # Each update is {node name: the keys that node returned}.
    for update in pipeline.stream(graph_input, config=config, stream_mode="updates", durability="exit"):
        steps += [node for node in update if node != "__interrupt__"]
    snapshot = pipeline.get_state(config)
    paused = snapshot.interrupts[0].value if snapshot.interrupts else None
    print(f"\n[Graph] {'Paused for the dispatcher' if paused else 'Done'} after {len(steps)} steps: "
          f"{' -> '.join(steps)}")
    return snapshot.values, steps, paused


def run_graph(messages, label, checkpointer):
    """Run the whole pipeline once over the messages from read_messages, up to the dispatcher's first
    pause; label is saved in manifest.json. The checkpointer keeps the paused run.

    Returns (graph_state, steps, thread_id, paused): the saved graph state, the nodes in the order they
    ran, the new thread ID that resume_graph needs, and the pause's {"review", "refused"}. An empty
    chat file makes no run folder or plan and returns (None, [], None, None). The run is named
    "full-pipeline" in LangSmith.
    """
    if not messages:
        print("No messages to process: no run folder or plan was created.")
        return None, [], None, None
    thread_id = str(uuid.uuid4())
    config = {"recursion_limit": recursion_limit(messages), "run_name": "full-pipeline",
              "configurable": {"thread_id": thread_id}}
    graph_state, steps, paused = stream_to_pause(build_graph(checkpointer), {"messages": messages, "label": label},
                                                 config)
    return graph_state, steps, thread_id, paused


def paused_review(thread_id, checkpointer):
    """Return (graph_state, paused) of a saved run: its graph state and the pause's {"review", "refused"},
    or None for paused when the run is not waiting for the dispatcher (finished, or no such thread).
    """
    snapshot = build_graph(checkpointer).get_state({"configurable": {"thread_id": thread_id}})
    return snapshot.values, snapshot.interrupts[0].value if snapshot.interrupts else None


def resume_graph(thread_id, answer, checkpointer):
    """Continue a paused run with the dispatcher's answer, until the next pause or the end.

    answer is {"decisions": [...], "then": "review_again" or "approve_all"} (see
    dispatcher_decisions.apply_answer). Returns (graph_state, steps, thread_id, paused) as run_graph.
    A thread that is not paused raises ValueError: LangGraph would otherwise do nothing for a finished
    run and fail with a recursion error for an unknown thread ID.
    """
    if paused_review(thread_id, checkpointer)[1] is None:
        raise ValueError(f"Thread {thread_id} has no paused dispatcher review.")
    config = {"recursion_limit": RESUME_RECURSION_LIMIT, "run_name": "full-pipeline",
              "configurable": {"thread_id": thread_id}}
    graph_state, steps, paused = stream_to_pause(build_graph(checkpointer), Command(resume=answer), config)
    return graph_state, steps, thread_id, paused
