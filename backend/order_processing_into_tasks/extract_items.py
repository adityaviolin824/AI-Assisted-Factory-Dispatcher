# extract_items.py: messages -> items. The model splits each batch of messages into items (jobs and
# follow-ups); Python checks the answer against the original text; only then are the items saved.
#
# Processing flow: read_chat_messages -> [extract_items] -> create_and_link_tasks -> verify_tasks
#                  -> processing_run
# Came from:       notebook 05, Section 6 ("Intake"; renamed here because the model extracts items).
# Changes:         the processing state: items, processed and non-task message IDs, intake reviews.
#
# A batch has TARGET_SIZE new messages, plus the CONTEXT_SIZE messages before them as context only.
# Context messages help the model read replies and corrections; they are never extracted again.
# A rejected batch sends its original messages to intake review, and the run continues.


import re
from typing import Literal

from order_processing_into_tasks.model_calls_with_cache import ReviewRequired, StrictModel
from order_processing_into_tasks.model_prompts import INTAKE_PROMPT
from order_processing_into_tasks.settings_and_data import (
    CONTEXT_SIZE, HOLD_WINDOW, TARGET_SIZE, order_references)


# Response format: one job or update the model found in a message. message_id is the source message;
# excerpts are exact quotes from it. kind="request" becomes a new task; kind="follow_up" goes to
# linking. An item is only extracted text, not yet a verified task.
class ExtractedItem(StrictModel):
    message_id: str
    kind: Literal["request", "follow_up"]
    excerpts: list[str]


# Response format: the full answer of one extraction call. Each target message must give items or be
# listed as non-task; validate_intake checks that every target is covered exactly once.
class IntakeBatch(StrictModel):
    items: list[ExtractedItem]
    non_task_message_ids: list[str]


def owned_windows(messages, processed_ids):
    """Yield one (context, targets) pair per extraction batch that still has unprocessed messages.

    targets: up to TARGET_SIZE messages to extract. context: the CONTEXT_SIZE messages before them,
    shown to the model only. A batch whose targets are all processed is skipped, so the first pair
    is always the next batch to extract.
    """
    for start in range(0, len(messages), TARGET_SIZE):
        targets = [
            m for m in messages[start:start + TARGET_SIZE]
            if m["message_id"] not in processed_ids
        ]

        if targets:
            yield messages[max(0, start - CONTEXT_SIZE):start], targets


def validate_intake(targets, result):
    """Check the model's extraction answer for one batch before anything is saved.

    Returns the non-task message IDs that belong to this batch. Raises ReviewRequired if a target is
    not covered, an item comes from a context message, a quote is not exact, an item repeats or a
    written order ID was dropped. These checks prove the answer matches the source text; they do not
    prove the model understood it (verify_tasks checks that later).
    """
    original = {m["message_id"]: m["raw_text"] for m in targets}
    # 1. Coverage. The batch owns only its target messages. The model sometimes also lists context
    #    messages as non-task (5 of 10 batches in the first real run); those belong to earlier
    #    batches, so their IDs are ignored. Every target must give items or be non-task, never both.
    non_task = [message_id for message_id in result.non_task_message_ids if message_id in original]
    covered = {d.message_id for d in result.items}

    if len(non_task) != len(set(non_task)) or covered & set(non_task):
        raise ReviewRequired("A source cannot be non_task twice or also produce items.")

    # An item taken from a context message also fails here: items must come from the targets.
    if covered | set(non_task) != set(original):
        raise ReviewRequired("Intake must account for exactly the owned messages.")

    # 2. Every quote must appear exactly in its message, and the same item cannot appear twice.
    seen = set()
    for item in result.items:
        if not item.excerpts or any(
            not q.strip() or q not in original[item.message_id]
            for q in item.excerpts
        ):
            raise ReviewRequired(
                "ExtractedItem evidence must be nonempty verbatim source text."
            )

        key = (item.message_id, tuple(item.excerpts))
        if key in seen:
            raise ReviewRequired("The same source job was returned twice.")
        seen.add(key)

    # 3. Every order ID written in a message must also appear in its extracted quotes.
    for message_id, text in original.items():
        extracted = "\n".join(
            quote
            for item in result.items
            if item.message_id == message_id
            for quote in item.excerpts
        )

        if set(order_references(text)) - set(order_references(extracted)):
            raise ReviewRequired(
                "Intake omitted a written order reference; inspect the batch response."
            )

    return non_task


def accept_intake(state, targets, result):
    """Save one checked batch into the processing state and return the saved items.

    Changes state["items"], state["non_task_message_ids"] and state["processed_message_ids"]. Each
    item gets an ID from its message and position (L0003:J1, L0003:J2, ...). Items are saved before
    their messages are marked processed, so a stop never marks a message done while losing its items.
    """
    # 1. Check the answer, and refuse messages that were already processed.
    non_task = validate_intake(targets, result)
    if set(state["processed_message_ids"]) & {
        m["message_id"] for m in targets
    }:
        raise ValueError("An owned message was already processed.")

    # 2. Number each message's items in the order their first quote appears in the message.
    accepted = []
    for message in targets:
        jobs = [
            d for d in result.items
            if d.message_id == message["message_id"]
        ]
        jobs.sort(key=lambda d: message["raw_text"].index(d.excerpts[0]))

        for number, job in enumerate(jobs, 1):
            record = job.model_dump()

            # A message with only one item keeps its full original text as evidence.
            if len(jobs) == 1:
                record["excerpts"] = [message["raw_text"]]

            record["item_id"] = f"{job.message_id}:J{number}"
            accepted.append(record)

    # 3. Save every item, then mark the messages processed.
    state["items"].update({d["item_id"]: d for d in accepted})
    state["non_task_message_ids"].extend(non_task)
    state["processed_message_ids"].extend(m["message_id"] for m in targets)

    for item in accepted:
        print(f"  {item['item_id']} ({item['kind']}): {' | '.join(item['excerpts'])}")
    if non_task:
        print(f"  non-task: {non_task}")
    ignored = [message_id for message_id in result.non_task_message_ids if message_id not in non_task]
    if ignored:
        print(f"  ignored non-task IDs from outside this batch: {ignored}")
    return accepted


def review_targets(state, text, message_id):
    """Return the task IDs that a message under review could affect, using only its text.

    A message naming message IDs (L0003) or order IDs (ORD-061) affects only the tasks linked to them.
    A message naming neither most likely continues the conversation just before it, so it affects
    the tasks of the HOLD_WINDOW messages before message_id. With message_id None (a failed task's
    evidence), it affects no other task.
    Used by possibly_affected_tasks (verify_tasks), whose tasks the plan marks provisional.
    """
    source_ids = re.findall(r"\bL\d{4}\b", text)
    order_ids = order_references(text)
    if not (source_ids or order_ids) and message_id:
        number = int(message_id[1:])
        source_ids = [f"L{n:04d}" for n in range(max(1, number - HOLD_WINDOW), number)]
    targets = [tid for sid in source_ids for tid in state["source_index"].get(sid, [])]
    targets += [tid for oid in order_ids for tid in state["order_index"].get(oid, [])]
    return list(dict.fromkeys(targets))


def intake_window(state, context, targets, ask):
    """Extract one batch: ask the model, then check and save its answer.

    Changes the processing state (items and non-task IDs, or intake reviews) and writes
    calls/intake-*.json. An unreadable answer or a failed check sends the batch's original messages
    to intake review, and the run continues. API, file and programming errors are not caught here,
    so they stop the run.
    """
    try:
        result = ask("intake", INTAKE_PROMPT,
                     {"context_messages": context, "target_messages": targets}, IntakeBatch)
        accept_intake(state, targets, result)
    except ReviewRequired as error:
        state["intake_review"].extend(
            {"message_id": m["message_id"], "raw_text": m["raw_text"],
             "reason": "The system could not read this message reliably; please review it.",
             "failed_check": str(error), "response_trace": getattr(ask, "last_trace_file", None)}
            for m in targets)
        # Count them as processed, so the run can go on to the next batch.
        state["processed_message_ids"].extend(m["message_id"] for m in targets)
        print(f"  REJECTED batch: {error} Its messages go to intake review as written.")
