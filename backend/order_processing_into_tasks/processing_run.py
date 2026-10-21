# processing_run.py: one processing run, from the message list to the saved, checked tasks.
#
# Processing flow: read_chat_messages -> extract_items -> create_and_link_tasks -> verify_tasks
#                  -> [processing_run]
#                  process_messages below calls the other steps in this order.
# Came from:       notebook 05, Sections 5 and 9. process_messages is new: it runs the steps in the
#                  same order as the notebook's LangGraph nodes (start_run, then extract_batch and
#                  link_items in turns, verify_tasks, save_outputs), without the graph.
# Writes:          RUNS_DIR/<start time>/manifest.json, state.json and calls/ (one folder per run).
#
# Allocation (task_allocation_to_workshops/allocation_plan.py) plans verified_tasks(state); the plan
# of an incomplete run is marked partial.


from datetime import datetime

from order_processing_into_tasks.create_and_link_tasks import link_pending_items
from order_processing_into_tasks.extract_items import intake_window, owned_windows
from order_processing_into_tasks.model_calls_with_cache import RecordedModel
from order_processing_into_tasks.model_prompts import INTAKE_PROMPT, LINK_PROMPT, VERIFY_PROMPT
from order_processing_into_tasks.settings_and_data import (
    CONTEXT_SIZE, DATA_YEAR, MAX_CANDIDATES, MAX_PAYLOAD_CHARS, MESSAGE_DATE, REASONING_EFFORTS,
    RUNS_DIR, STAGE_MODELS, TARGET_SIZE, TEMPERATURE, VERIFY_BATCH_SIZE, save_checkpoint, write_json)
from order_processing_into_tasks.verify_tasks import run_verification


# ---------------------------------------------------------------------------------------------
# The run folder and the processing state.
# ---------------------------------------------------------------------------------------------


def new_state():
    """Return the empty processing state of a new run, saved as state.json.

    processed_message_ids  messages that went through extraction, with or without items
    non_task_message_ids   messages with no request or question (greetings, headers)
    intake_review          messages whose extraction batch failed a check, with the reason
    items                  item ID -> extracted item (extract_items)
    tasks                  task ID -> task, its version and its verification
                           (create_and_link_tasks, verify_tasks)
    task_review            task ID -> review record of its current version (verify_tasks)
    unresolved_links       item ID -> follow-up that could not be linked (create_and_link_tasks)
    source_index, order_index, recent_task_ids: lookup lists for link candidates
    """
    return {
        "processed_message_ids": [],
        "non_task_message_ids": [],
        "intake_review": [],
        "items": {},
        "tasks": {},
        "task_review": {},
        "unresolved_links": {},
        "source_index": {},
        "order_index": {},
        "recent_task_ids": []
    }


def run_configuration(messages, label):
    """Return the input record of a run, saved as manifest.json: the messages, the label, each stage's
    model and reasoning effort, the message date, the batch settings and the prompts, so a saved run
    can always be read with what made it.
    """
    return {"label": label, "messages": messages, "models": STAGE_MODELS, "temperature": TEMPERATURE,
            "reasoning_effort": REASONING_EFFORTS, "data_year": DATA_YEAR,
            "message_date": MESSAGE_DATE.isoformat(),
            "target_size": TARGET_SIZE, "context_size": CONTEXT_SIZE,
            "max_candidates": MAX_CANDIDATES, "max_payload_chars": MAX_PAYLOAD_CHARS,
            "verify_batch_size": VERIFY_BATCH_SIZE,
            "prompts": {"intake": INTAKE_PROMPT, "link": LINK_PROMPT, "verify": VERIFY_PROMPT}}


def prepare_run(messages, label):
    """Create a new run folder, RUNS_DIR/<start time>/, with manifest.json and an empty state.json.

    Returns (run_dir, state). A new run never overwrites an earlier one; two runs started in the
    same second would clash, and mkdir then raises an error instead of mixing their files.
    """
    run_dir = RUNS_DIR / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir.mkdir(parents=True)
    write_json(run_dir / "manifest.json", run_configuration(messages, label))
    state = new_state()
    write_json(run_dir / "state.json", state)
    return run_dir, state


# ---------------------------------------------------------------------------------------------
# The completeness check and the final save.
# ---------------------------------------------------------------------------------------------


def pipeline_complete(state, messages):
    """Return True only if processing gave every input an outcome (the three checks below).

    A review counts as an outcome. The plan of an incomplete run is marked partial.
    """
    # 1. Every input message went through intake. This includes non-task messages
    #    and messages sent to intake review after a rejected batch.
    assigned = {item_id for task in state["tasks"].values() for item_id in task["item_ids"]}
    input_ids = {message["message_id"] for message in messages}
    if set(state["processed_message_ids"]) != input_ids:
        return False
    accounted = {item["message_id"] for item in state["items"].values()}
    accounted.update(state["non_task_message_ids"])
    accounted.update(review["message_id"] for review in state["intake_review"])
    if accounted != input_ids:
        return False

    # 2. Every item is either in a task or waiting for link review. A link review counts as an outcome.
    unresolved = set(state["unresolved_links"])
    if assigned & unresolved or assigned | unresolved != set(state["items"]):
        return False

    # 3. Every current task has either an accepted verification or a review record, never both,
    #    and for its current version. A review is a finished outcome; it never makes a task ready.
    if set(state["task_review"]) - set(state["tasks"]):
        return False
    for task in state["tasks"].values():
        review = state["task_review"].get(task["task_id"])
        if review:
            if (review["version"] != task["version"] or task["verified"] is not None
                    or task["verified_version"] is not None):
                return False
        elif task["verified"] is None or task["verified_version"] != task["version"]:
            return False
    return True


def verified_tasks(state):
    """Return the verified records of the tasks verified at their current version, in task order.

    These are the only tasks allocation plans. A verification of an older version never saw the
    newest follow-up, so it is never used.
    """
    return [task["verified"] for task in state["tasks"].values()
            if task["verified"] is not None and task["verified_version"] == task["version"]]


def save_run_outputs(run_dir, state, messages):
    """Finish processing: save state.json and return the summary counts.

    The summary includes "complete" (from pipeline_complete).
    """
    write_json(run_dir / "state.json", state)
    verified = verified_tasks(state)
    complete = pipeline_complete(state, messages)
    # ready: tasks with information_sufficient=True (ready for the allocation checks).
    # allocation_review: allocation tasks still blocked by a missing fact or a question.
    # reference_questions: information questions; these are never ready.
    summary = {"complete": complete, "input_messages": len(messages),
               "processed_messages": len(state["processed_message_ids"]),
               "non_task_messages": len(state["non_task_message_ids"]),
               "intake_review_messages": len(state["intake_review"]), "extracted_items": len(state["items"]),
               "tasks": len(state["tasks"]), "verified_tasks": len(verified),
               "review_tasks": len(state["task_review"]),
               "unresolved_links": len(state["unresolved_links"]),
               "ready": sum(t["information_sufficient"] for t in verified),
               "allocation_review": sum(t["intent"] == "allocation" and not t["information_sufficient"] for t in verified),
               "reference_questions": sum(t["intent"] == "question" for t in verified),
               "unclear": sum(t["intent"] == "unclear" for t in verified)}
    print(f"[Save] {summary['input_messages']} messages -> {summary['extracted_items']} items -> "
          f"{summary['tasks']} tasks ({summary['verified_tasks']} verified, {summary['review_tasks']} in review); "
          f"non-task messages {summary['non_task_messages']}; intake reviews {summary['intake_review_messages']}; "
          f"unresolved links {summary['unresolved_links']}.")
    print(f"[Save] Ready for allocation {summary['ready']}; need clarification {summary['allocation_review']}; "
          f"questions {summary['reference_questions']}; unclear {summary['unclear']}. Complete: {complete}.")
    if not complete:
        print("[Save] Incomplete: some input has no outcome, so a plan of this run is partial. See state.json.")
    return summary


# ---------------------------------------------------------------------------------------------
# The run: every processing step in order.
# ---------------------------------------------------------------------------------------------


def process_messages(messages, label):
    """Process the messages from read_messages in one new run, in the order of notebook 05's graph.

    Returns (run_dir, state, summary): the run folder, the processing state (also saved as
    state.json) and the summary counts. Returns (None, None, None) for an empty chat file.
    API, file and programming errors stop the run; state.json then shows how far it got.
    """
    # An empty chat file has nothing to process, so no run folder is made (repair I03).
    if not messages:
        print("No messages to process: no run folder was created.")
        return None, None, None

    # 1. Open the run folder. One RecordedModel serves every step; it creates an API client only
    #    for a request that has no saved answer.
    run_dir, state = prepare_run(messages, label)
    print(f"[Run] {len(messages)} messages; run folder {run_dir}")
    ask = RecordedModel(run_dir)

    # 2. Extraction and linking take turns, one batch at a time, so a follow-up is compared with the
    #    tasks that exist when it arrives. No message is processed yet (set()), and each batch marks
    #    only its own messages processed, so the batches come out in chat order.
    for context, targets in owned_windows(messages, set()):
        print(f"\n[Run] extract items: {', '.join(message['message_id'] for message in targets)}")
        intake_window(state, context, targets, ask)
        save_checkpoint(run_dir, state)
        print("[Run] create and link tasks")
        link_pending_items(state, ask, lambda: save_checkpoint(run_dir, state))

    # 3. Verify only after every message is read and linked, so each task is checked with its
    #    latest correction.
    print("\n[Run] verify tasks")
    run_verification(run_dir, state, ask)

    # 4. Save state.json and count the outcomes.
    print("\n[Run] save")
    summary = save_run_outputs(run_dir, state, messages)
    return run_dir, state, summary
