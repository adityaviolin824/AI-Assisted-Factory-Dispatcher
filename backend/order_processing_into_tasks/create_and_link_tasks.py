# create_and_link_tasks.py: items -> tasks. Each request item becomes a task; each follow-up (a
# correction, reply or repeat) is attached to the task it belongs to, or sent to link review.
#
# Processing flow: read_chat_messages -> extract_items -> [create_and_link_tasks] -> verify_tasks
#                  -> processing_run
# Came from:       notebook 05, Section 7.
# Changes:         the processing state: tasks, task versions, lookup lists, link reviews.
#
# Extraction and linking take turns, one batch at a time, so a follow-up is compared with the tasks
# that exist when it arrives. Order of calls for one follow-up:
#   link_pending_items -> link_or_create_task -> candidate_task_ids -> model decision -> apply_link
#
# IDs stay separate: a task ID (T:L0003:J1) comes from its first item; an order ID (ORD-061) is
# only a hint for finding candidates and never merges two tasks.


import json
import re
from typing import Literal

from order_processing_into_tasks.model_calls_with_cache import ReviewRequired, StrictModel
from order_processing_into_tasks.model_prompts import LINK_PROMPT
from order_processing_into_tasks.settings_and_data import (
    MAX_CANDIDATES, MAX_PAYLOAD_CHARS, order_references)


# ---------------------------------------------------------------------------------------------
# Tasks: create a task from a request item, and keep the lookup lists used to find it later.
# ---------------------------------------------------------------------------------------------


def task_evidence(state, task):
    """Return the original messages of a task: one {"message_id", "excerpts"} per item, request first.

    Linking and verification read this original text, never wording written by the model.
    """
    evidence = []

    for item_id in task["item_ids"]:
        item = state["items"][item_id]

        evidence.append({
            "message_id": item["message_id"],
            "excerpts": item["excerpts"]
        })

    return evidence


def evidence_text(evidence):
    """Join a task's original quotes into one text, one quote per line (used to search for order IDs)."""
    return "\n".join(
        q for item in evidence
        for q in item["excerpts"]
    )


def index_task(state, task):
    """Update the lookup lists that suggest this task when a later message arrives.

    Changes state["recent_task_ids"] (the last 4 tasks used), state["source_index"] (message ID ->
    task IDs) and state["order_index"] (order ID -> task IDs). The lists only suggest candidates:
    they never merge tasks, and shortening the recent list deletes no task.
    """
    # 1. Move this task to the end of the recent list and keep the last 4.
    recent = [
        tid for tid in state["recent_task_ids"]
        if tid != task["task_id"]
    ]

    state["recent_task_ids"] = (recent + [task["task_id"]])[-4:]

    # 2. Add the task, once, under each of its message IDs and order IDs.
    evidence = task_evidence(state, task)

    indexes = [
        ("source_index", [item["message_id"] for item in evidence]),
        ("order_index", order_references(evidence_text(evidence)))
    ]

    for name, keys in indexes:
        for key in keys:
            ids = state[name].setdefault(key, [])

            if task["task_id"] not in ids:
                ids.append(task["task_id"])


def create_task(state, item):
    """Create and save a task from a request item, such as T:L0004:J1 at version 1, not yet verified.

    Changes state["tasks"] and the lookup lists. The task ID comes from the item ID, so the same
    item can never create a second task; an existing task is returned instead.
    """
    task_id = "T:" + item["item_id"]

    if task_id in state["tasks"]:
        print(f"  {task_id} already exists; no second task was created.")
        return state["tasks"][task_id]

    # verified_version and verified stay None until verification accepts this version.
    task = {
        "task_id": task_id,
        "item_ids": [item["item_id"]],
        "version": 1,
        "verified_version": None,
        "verified": None
    }

    state["tasks"][task_id] = task

    index_task(state, task)

    print(f"  {item['item_id']} -> new task {task_id} v1")
    return task


# ---------------------------------------------------------------------------------------------
# Linking: connect a follow-up to the earlier task it belongs to. A request skips this and
# becomes a new task.
# ---------------------------------------------------------------------------------------------


# Response format: the model's answer about one follow-up. apply_link checks it before anything changes.
class LinkDecision(StrictModel):
    # "attach": the follow-up belongs to the task(s) in task_ids.
    # "needs_review": the link is unclear, so a person must decide.
    action: Literal["attach", "needs_review"]
    # Tasks to update. They must come from the candidate list we sent.
    # The prompt asks for an empty list when the action is "needs_review".
    task_ids: list[str]
    # Exact words from the follow-up that show the link.
    evidence_quote: str
    # Short explanation in plain words, saved if the follow-up goes to review.
    reason: str


def candidate_task_ids(state, item):
    """Return the earlier tasks a follow-up might belong to, without repeats, in the order found.

    First tasks from message IDs written in the follow-up (such as "L0003"), then tasks with the same
    order ID (such as "ORD-061"), then the 4 most recently used tasks, for replies that name no ID.
    The model may only choose from this list; being on the list merges nothing.
    """
    text = "\n".join(item["excerpts"])
    candidates = []
    for source_id in re.findall(r"\bL\d{4}\b", text):
        candidates.extend(state["source_index"].get(source_id, []))
    for order_id in order_references(text):
        candidates.extend(state["order_index"].get(order_id, []))
    candidates.extend(state["recent_task_ids"])
    return list(dict.fromkeys(candidates))


def record_link_review(state, item, candidates, reason, response_trace=None):
    """Save a follow-up that could not be linked in state["unresolved_links"].

    Keeps the original text and the candidates, for the dispatcher. The candidates are not confirmed
    links. When the plan is made, possibly_affected_tasks (verify_tasks) finds the tasks this
    follow-up may modify, and the plan marks them provisional.
    """
    state["unresolved_links"][item["item_id"]] = {
        "item_id": item["item_id"], "message_id": item["message_id"],
        "excerpts": list(item["excerpts"]), "candidate_task_ids": list(candidates),
        "reason": reason, "response_trace": response_trace,
    }
    print(f"  {item['item_id']} -> link review: {reason}")


def apply_link(state, item, decision, candidates, response_trace=None):
    """Check the model's link decision for one follow-up, then apply it.

    "attach": each chosen task gets the item, its version rises by 1 and its verification is cleared,
    because the earlier check never saw this evidence. "needs_review": the follow-up is saved for
    review. Raises ReviewRequired when a check fails; link_or_create_task then sends it to review.
    """
    targets = decision.task_ids
    text = "\n".join(item["excerpts"])
    # 1. Chosen task IDs must be unique and come from the candidate list, so the model cannot
    #    invent or repeat a task ID.
    if len(targets) != len(set(targets)) or not set(targets).issubset(candidates):
        raise ReviewRequired("Link targets must be unique supplied task IDs.")
    # 2. Unclear link: save the follow-up for review and attach nothing. The tasks it may modify are
    #    still verified and planned, marked provisional.
    if decision.action == "needs_review":
        record_link_review(state, item, candidates, decision.reason, response_trace)
        return
    # 3. An attachment needs at least one task and a quote copied exactly from the follow-up.
    if not targets or not decision.evidence_quote.strip() or decision.evidence_quote not in text:
        raise ReviewRequired("An attachment needs targets and verbatim relationship evidence.")
    #    If the quote names a message ID, such as "L0003", every chosen task must come from it.
    mentioned_sources = re.findall(r"\bL\d{4}\b", decision.evidence_quote)
    explicit_targets = {tid for sid in mentioned_sources for tid in state["source_index"].get(sid, [])}
    if mentioned_sources and not set(targets).issubset(explicit_targets):
        raise ReviewRequired("Attachment contradicts the explicitly referenced source.")
    # 4. Add the follow-up to each chosen task: a new version with no verification yet.
    for tid in targets:
        task = state["tasks"][tid]
        if item["item_id"] not in task["item_ids"]:
            task["item_ids"].append(item["item_id"])
            task.update(version=task["version"] + 1, verified_version=None, verified=None)
            state["task_review"].pop(tid, None)
            index_task(state, task)
            print(f"  {item['item_id']} -> attached to {tid}, now v{task['version']} "
                  f"(verification cleared): \"{decision.evidence_quote}\"")
    # The follow-up is linked, so it no longer waits for review.
    state["unresolved_links"].pop(item["item_id"], None)


def link_or_create_task(state, item, ask):
    """Handle one new item: a request becomes its own task (no model call); a follow-up is linked.

    The model compares the follow-up with each candidate's original messages, not a summary. With no
    candidates, too many, or a request that is too large, the follow-up goes to review with no call.
    Writes calls/link-*.json for each linking request.
    """
    # 1. New request: create its task.
    if item["kind"] == "request":
        create_task(state, item)
        return
    # 2. Follow-up: the payload holds the follow-up and each candidate's original messages.
    candidates = candidate_task_ids(state, item)
    payload = {"follow_up": item, "candidates": [
        {"task_id": tid, "evidence": task_evidence(state, state["tasks"][tid])}
        for tid in candidates]}
    # 3. No candidates, more than MAX_CANDIDATES or a request over MAX_PAYLOAD_CHARS: review, with
    #    no model call. Cutting the list could drop the right task.
    if not candidates or len(candidates) > MAX_CANDIDATES or len(json.dumps(payload)) > MAX_PAYLOAD_CHARS:
        record_link_review(state, item, candidates, "No bounded, unambiguous candidate set; identify the intended request.")
        return
    # 4. Ask the model, then check and apply its decision. A failed check sends it to review.
    try:
        decision = ask("link", LINK_PROMPT, payload, LinkDecision)
        apply_link(state, item, decision, candidates, getattr(ask, "last_trace_file", None))
    except ReviewRequired as error:
        record_link_review(state, item, candidates, str(error), getattr(ask, "last_trace_file", None))


def link_pending_items(state, ask, checkpoint):
    """Give every saved item that has no task yet a task, or link it; save state.json after each item.

    Items that already have a task, or wait for link review, are skipped, so running it again is safe.
    """
    assigned = {item_id for task in state["tasks"].values() for item_id in task["item_ids"]}
    for item_id, item in state["items"].items():
        if item_id not in assigned and item_id not in state["unresolved_links"]:
            link_or_create_task(state, item, ask)
            checkpoint()
