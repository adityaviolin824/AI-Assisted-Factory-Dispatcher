# verify_tasks.py: tasks -> verified records or reviews. After every message is read and linked, the
# model checks each task's current version against its original messages; Python checks every answer,
# copies the exact text, reads the dates and decides whether the task is ready for allocation.
#
# Processing flow: read_chat_messages -> extract_items -> create_and_link_tasks -> [verify_tasks]
#                  -> processing_run
# Came from:       notebook 05, Section 8.
# Changes:         the processing state: each task's verified record and task reviews.
#
# Order of calls: run_verification -> verification_batches -> verification_payload -> model call
#   -> finish_verification_batch -> finish_verification -> stated_piece_counts, resolve_scheduling
# possibly_affected_tasks is called by allocation: it finds the tasks an unresolved input may modify.
#
# Two expected outcomes that are not errors:
#   ReviewRequired  the model answer cannot be trusted. Save the task and the reason for review,
#                   and continue with the other tasks.
#   Blocker         (added to missing_details) the request lacks a fact. Keep the checked
#                   assessment, but do not mark the task ready.
# API, file and programming errors still stop the run and stay visible.


import calendar
import json
import re
from datetime import datetime, timedelta
from typing import Literal

from order_processing_into_tasks.create_and_link_tasks import evidence_text, task_evidence
from order_processing_into_tasks.extract_items import review_targets
from order_processing_into_tasks.model_calls_with_cache import ReviewRequired, StrictModel
from order_processing_into_tasks.model_prompts import VERIFY_PROMPT
from order_processing_into_tasks.settings_and_data import (
    DATA_YEAR, MAX_PAYLOAD_CHARS, MESSAGE_DATE, ORDER_INDEX, VERIFY_BATCH_SIZE, WORKSHOP_INDEX,
    WORKSHOP_NAMES, order_references, save_checkpoint)


# ---------------------------------------------------------------------------------------------
# Response formats of verification. Never add docstrings or Field descriptions to these classes,
# and never rename a class or field: they are part of every request's key, so saved answers would
# stop matching.
# ---------------------------------------------------------------------------------------------


# Allowed workshop IDs, taken from workshops.csv (such as "W1").
# The model cannot return a workshop ID outside this list.
WorkshopId = Literal[tuple(WORKSHOP_INDEX)]


# How the model reads one workshop mention in a task's evidence.
class WorkshopRule(StrictModel):
    # The workshop that was mentioned.
    workshop_id: WorkshopId
    # The evidence entry that mentions it, such as "T:L0003:J1:E1".
    evidence_id: str
    # requested:  the request asks for this workshop.
    # excluded:   the request rules this workshop out.
    # reference:  only mentioned (for example as history); not a current rule.
    # superseded: an old rule that later evidence replaced.
    role: Literal["requested", "excluded", "reference", "superseded"]
    # Only for "superseded": the later evidence entry that replaced it. Otherwise None.
    superseded_by: str | None


# The current scheduling facts of one task, as read by the model. resolve_scheduling checks them
# before the allocator can use them.
class SchedulingDetails(StrictModel):
    # Deadline words copied from the deadline evidence, such as "Apr 2".
    # None means the allocator uses the order's due date from orders.csv.
    due_date_text: str | None
    # Ranking preference stated in the request; "none" if nothing was stated.
    preference: Literal["none", "fastest", "cheapest", "quality"]
    # The evidence entry that states the preference.
    preference_evidence_id: str | None
    # One rule for every workshop mention in the evidence.
    workshop_rules: list[WorkshopRule]
    # The evidence entry asking to split the order across workshops; None if no split.
    split_evidence_id: str | None
    # Conditions these fields cannot hold, such as a budget or a partial quantity.
    # Any entry here blocks the task until it is clarified.
    unhandled_constraints: list[str]


# The model's full assessment of one task. Fields ending in _evidence_id point to entries in the
# task's evidence catalog; Python copies the exact text from there, so a quote is never retyped.
class EvidenceAssessment(StrictModel):
    # allocation: asks to place the order with a workshop.
    # question:   asks for information only, so it is never allocated.
    # unclear:    the requested action cannot be worked out.
    intent: Literal["allocation", "question", "unclear"]
    # The order ID written in the evidence, such as "ORD-061"; None if no order is named.
    order_id: str | None
    # Evidence entries that state urgency, the current deadline and a quality preference.
    urgency_evidence_id: str | None
    deadline_evidence_id: str | None
    quality_evidence_id: str | None
    # Evidence entries for every current destination, exclusion, preference or condition.
    constraint_evidence_ids: list[str]
    # Facts still missing and questions to ask. Any entry blocks the task.
    missing_details: list[str]
    doubts_to_clarify: list[str]
    # The current scheduling fields for the allocator.
    scheduling: SchedulingDetails


# One answer: the task ID and version it is about, plus the assessment. Checking the version stops
# an answer about an older version from being saved.
class TaskAssessment(StrictModel):
    task_id: str
    version: int
    assessment: EvidenceAssessment


# The model's full answer for one verification call (up to VERIFY_BATCH_SIZE tasks).
class VerificationBatch(StrictModel):
    results: list[TaskAssessment]


# ---------------------------------------------------------------------------------------------
# What the model sees for each task.
# ---------------------------------------------------------------------------------------------


def verification_payload(state, task):
    """Build the model input for one task: its evidence, an evidence catalog, anchor order IDs, order
    lookups from orders.csv and the workshop mentions.

    Python does the lookups first, so the model reads facts instead of guessing them.
    finish_verification later checks the answer against this same payload.
    """
    # 1. Look up every order ID written in the evidence. "found" is False for an unknown order ID.
    evidence = task_evidence(state, task)
    order_ids = order_references(evidence_text(evidence))
    lookups = [{"order_id": order_id, "found": order_id in ORDER_INDEX,
                "order": ORDER_INDEX.get(order_id)} for order_id in order_ids]

    # 2. Give each original quote an ID, such as "T:L0003:J1:E1". The model answers with these IDs
    #    and Python copies the exact text later, so a quote is never retyped.
    catalog = []
    for item in evidence:
        for quote in item["excerpts"]:
            catalog.append({
                "evidence_id": f"{task['task_id']}:E{len(catalog) + 1}",
                "message_id": item["message_id"],
                "text": quote,
            })

    # 3. anchor_order_ids: the order IDs in the task's first item only. They tell this task apart
    #    from other tasks that share the same follow-up message.
    #    workshop_mentions: every workshop name or ID found; the model must give each one a role.
    anchor_text = "\n".join(evidence[0]["excerpts"])
    return {"task_id": task["task_id"], "version": task["version"], "evidence": evidence,
            "evidence_catalog": catalog, "anchor_order_ids": order_references(anchor_text),
            "order_lookups": lookups,
            "workshop_mentions": [{"evidence_id": row["evidence_id"], "workshop_id": wid,
                                   "name": WORKSHOP_INDEX[wid]["name"]}
                                  for row in catalog for wid in workshop_references(row["text"])]}


def workshop_references(text):
    """Return the workshops mentioned in a text, by ID ("W3") or by name ("BudgetWorks"), in CSV order.

    Whole words only, any letter case. It never guesses nicknames or typos.
    """
    return [wid for wid, row in WORKSHOP_INDEX.items()
            if any(re.search(r"(?<!\w)" + re.escape(label) + r"(?!\w)", text, re.IGNORECASE)
                   for label in (wid, row["name"]))]


# ---------------------------------------------------------------------------------------------
# Check one task's answer and build its verified record.
# ---------------------------------------------------------------------------------------------


# DATE_PATTERN finds whole written dates, with the year when one is written straight after:
#   month first "Apr 2", "April 2, 2027"    day first "2 Apr", "2 April 2027"    ISO "2026-04-02".
# Only non-capturing groups (?:...) are used, so re.findall returns each whole date.
# Limits: a 19xx or 20xx number straight after a date is read as its year ("Apr 13 2000 pcs"), and
# a phrase such as "2 may" can look like a date.
MONTH_NAMES = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
OPTIONAL_YEAR = r"(?:,?\s+(?:19|20)\d{2}\b)?"
DATE_PATTERN = (r"\b" + MONTH_NAMES + r"\s+\d{1,2}\b" + OPTIONAL_YEAR       # month first
                + r"|\b\d{1,2}\s+" + MONTH_NAMES + r"\b" + OPTIONAL_YEAR    # day first
                + r"|\b\d{4}-\d{2}-\d{2}\b")                                # ISO


def read_date(text):
    """Turn written deadline words into an ISO date, for example "Apr 2" -> "2026-04-02", or None.

    Accepts "2026-04-02", "Apr 2 2026", "April 2 2026", "2 Apr 2026" and "2 April 2026", with or
    without commas. A date without a year gets DATA_YEAR. None (for example "next week") leaves the
    words to read_relative_date; a date is never guessed.
    """
    text = text.strip().replace(",", "")
    formats = ("%Y-%m-%d", "%b %d %Y", "%B %d %Y", "%d %b %Y", "%d %B %Y")
    # Try the text as written first; then try again with DATA_YEAR added.
    for value, options in [(text, formats), (f"{text} {DATA_YEAR}", formats[1:])]:
        for fmt in options:
            try:
                return datetime.strptime(value, fmt).date().isoformat()
            except ValueError:
                # Not this format; try the next one.
                continue
    return None


# Relative delivery words that Python counts from MESSAGE_DATE (decision of 18 October 2026): a week
# ends on Friday, a month on its last calendar day. Any other words, such as "by Friday" or "next
# Friday", still ask for a calendar date. The prefix allows "by", "end of" and "by the end of".
RELATIVE_PREFIX = r"^(?:by\s+)?(?:the\s+)?(?:end\s+of\s+)?"


def last_day_of_month(day):
    """Return the last calendar day of day's month."""
    return day.replace(day=calendar.monthrange(day.year, day.month)[1])


def read_relative_date(text):
    """Turn relative delivery words into an ISO date counted from MESSAGE_DATE, or None.

    Accepts today, tomorrow, this week, next week, this month and next month, each also after "by",
    "end of" or "by the end of". From Wednesday 1 April 2026, "by end of next week" -> "2026-04-10".
    Week words return None when MESSAGE_DATE is a Saturday or Sunday: which Friday is meant is unclear.
    """
    words = re.sub(RELATIVE_PREFIX, "", " ".join(text.lower().split()))
    day = MESSAGE_DATE
    friday = day + timedelta(days=4 - day.weekday())
    dates = {"today": day, "tomorrow": day + timedelta(days=1),
             "this month": last_day_of_month(day),
             "next month": last_day_of_month(last_day_of_month(day) + timedelta(days=1))}
    if day.weekday() <= 4:
        dates.update({"this week": friday, "next week": friday + timedelta(days=7)})
    return dates[words].isoformat() if words in dates else None


# When the model selects no deadline, these fixed lists decide whether to ask which written date or
# time word is the deadline (decision of 19 October 2026). They can only add that question; they never
# set or remove a deadline. TIME_WORDS covers read_relative_date's words, weekday names and other week
# and month words, except after "last" ("last week" is in the past). A clause with a dispatch phrase
# and no delivery word only says when to send the work, so its dates are skipped. Clauses end at
# punctuation and at a dash between spaces.
TIME_WORDS = (r"(?<!last\s)\b(?:today|tonight|tomorrow|week|weekend|month|monday|tuesday|wednesday|thursday"
              r"|friday|saturday|sunday|mon|tue|tues|wed|thu|thur|thurs|fri)\b")
DISPATCH_WORDS = r"\b(?:send|sent|sending|go|goes|going)\s+(?:it\s+|them\s+)?out\b|\bdispatch\w*|\bplac(?:e|ed|ing)\b"
DELIVERY_WORDS = r"\b(?:deliver\w*|due|back|ship\w*|arriv\w*|deadline)\b"
CLAUSE_BREAK = r"[.,;:!?\n]|\s[-–—]\s"


def possible_deadline_words(text):
    """Return the written dates and time words in text that may state a delivery deadline.

    "Send out ORD-045 on April 2." returns [] (dispatch timing only); "Deliver ORD-045 tomorrow."
    returns ["tomorrow"]; "Send out on April 2 so it arrives by April 5" returns both dates.
    """
    words = []
    for clause in re.split(CLAUSE_BREAK, text):
        if (re.search(DISPATCH_WORDS, clause, re.IGNORECASE)
                and not re.search(DELIVERY_WORDS, clause, re.IGNORECASE)):
            continue
        words += re.findall(f"{DATE_PATTERN}|{TIME_WORDS}", clause, re.IGNORECASE)
    return words


def resolve_scheduling(payload, assessment):
    """Check the model's scheduling fields and turn them into the fields the allocator reads.

    Returns (fields, issues): the current due date, requested and excluded workshops, preference,
    split flag and original evidence; and the blockers that keep the task from being ready. Raises
    ReviewRequired when an answer points outside this task's evidence. The model only points at
    evidence; Python reads the dates and checks every rule.
    """
    # 1. Every evidence ID chosen for scheduling must belong to this task (review if not).
    #    Unhandled conditions are the first blockers.
    details = assessment.scheduling
    catalog = {row["evidence_id"]: row["text"] for row in payload["evidence_catalog"]}
    # Position of each evidence entry, used to check that a replacement comes later.
    positions = {key: index for index, key in enumerate(catalog)}
    issues = list(details.unhandled_constraints)
    selected = [details.preference_evidence_id, details.split_evidence_id]
    selected += [key for rule in details.workshop_rules for key in (rule.evidence_id, rule.superseded_by)]
    if any(key is not None and key not in catalog for key in selected):
        raise ReviewRequired("Scheduling evidence must belong to this task.")

    # 2. Deadline. Python reads the proposed date itself. A readable date must equal a date written
    #    in the chosen deadline evidence; each written date is read whole, year included, so "April 2"
    #    taken from "April 2, 2027" is not accepted as 2026. (The model sometimes rewrites "Mar 23"
    #    as "March 23, 2026": the same date, so it is accepted.) Relative words must be copied
    #    exactly: Python counts the agreed ones, such as "by end of next week", from MESSAGE_DATE,
    #    and any other, such as "next Friday", becomes a blocker. Anything else goes to review.
    #    A date returned without deadline evidence cannot be checked, so it is ignored and the
    #    checks below apply instead. With no deadline in the chat, the allocator uses the CSV date.
    #    A copy that keeps its delivery word, such as "due Apr 13", is read by its one written date
    #    (Test 7, 19 October 2026); that date must still be written in the evidence.
    due_date = None
    if details.due_date_text and assessment.deadline_evidence_id:
        quote = catalog.get(assessment.deadline_evidence_id, "")
        due_date = read_date(details.due_date_text)
        dates_inside = re.findall(DATE_PATTERN, details.due_date_text, re.IGNORECASE)
        if due_date is None and len(dates_inside) == 1:
            due_date = read_date(dates_inside[0])
        written_dates = {read_date(words) for words in re.findall(DATE_PATTERN, quote, re.IGNORECASE)}
        if due_date is None and details.due_date_text in quote:
            due_date = read_relative_date(details.due_date_text)
            if due_date is None:
                issues.append("Confirm the deadline as an explicit calendar date.")
        elif due_date is None or due_date not in written_dates:
            raise ReviewRequired("The deadline date must be copied from its selected evidence.")
    elif assessment.deadline_evidence_id:
        # Deadline evidence was chosen, but no date words were copied.
        issues.append("Copy the current deadline date from the selected source.")
    elif assessment.intent == "allocation":
        # No deadline was chosen, but the text has a written date such as "Apr 2" or a time word
        # such as "tomorrow" outside dispatch timing. Ask which date applies instead of quietly
        # using the CSV due date.
        if possible_deadline_words(evidence_text(payload["evidence"])):
            issues.append("Confirm which written date is the current deadline.")

    # 3. Workshops. Each mention needs exactly one rule, from its own evidence (review if not).
    #    A "superseded" rule must name a later replacement.
    #    Only current "requested" and "excluded" rules reach the allocator.
    expected = {(row["evidence_id"], wid) for row in payload["evidence_catalog"]
                for wid in workshop_references(row["text"])}
    seen, requested, excluded = set(), set(), set()
    for rule in details.workshop_rules:
        key = (rule.evidence_id, rule.workshop_id)
        if key not in expected or key in seen:
            raise ReviewRequired("Workshop rules must identify unique mentions in their own source evidence.")
        seen.add(key)
        if rule.role == "superseded":
            if rule.superseded_by is None or positions[rule.superseded_by] <= positions[rule.evidence_id]:
                raise ReviewRequired("A superseded workshop rule needs later replacement evidence.")
        elif rule.superseded_by is not None:
            raise ReviewRequired("Only a superseded rule can name replacement evidence.")
        elif rule.role == "requested":
            requested.add(rule.workshop_id)
        elif rule.role == "excluded":
            excluded.add(rule.workshop_id)
    #    Blockers: a mention without a rule, more than one requested workshop,
    #    or a workshop that is both requested and excluded.
    if seen != expected:
        issues.append("Confirm the missing workshop instruction before allocating.")
    if len(requested) > 1 or requested & excluded:
        issues.append("Resolve the conflicting requested and excluded workshops.")

    # 4. A preference needs its own evidence, and quality evidence needs a "quality" preference.
    #    Otherwise ask before choosing how to rank workshops.
    if details.preference != "none" and details.preference_evidence_id is None:
        issues.append("Provide source evidence for the scheduling preference.")
    if assessment.quality_evidence_id and details.preference != "quality":
        issues.append("Resolve the quality preference before selecting an objective.")
    # 5. The fields the allocator reads. source_evidence keeps the original text for audit.
    fields = {"due_date": due_date,
              "requested_workshop": next(iter(requested)) if len(requested) == 1 else None,
              "excluded_workshops": sorted(excluded), "preference": details.preference,
              "wants_split": details.split_evidence_id is not None,
              "workshop_rules": [rule.model_dump() for rule in details.workshop_rules],
              "unhandled_constraints": details.unhandled_constraints,
              "source_evidence": payload["evidence_catalog"]}
    return fields, issues


# A piece count is a number written before a product word or "pieces", with up to two words between
# them: "1300 vests", "1,250 cardigan pieces", "120 crewneck sweater pieces", "400 pcs". A number
# straight after a letter or hyphen, such as ORD-105 or W8, is never a count (19 October 2026).
PIECE_WORDS = (r"(?:pieces?|pcs|units?|sweaters?|hoodies?|scarf|scarves|vests?|beanies?|cardigans?"
               r"|polos?|shirts?|t-shirts?|tops|jackets?|tees?)")
PIECE_COUNT = r"(?<![\w-])(\d[\d,]*)\s+(?:[a-z&-]+\s+){0,2}?" + PIECE_WORDS + r"\b"


def stated_piece_counts(quote, order_id):
    """Return the piece counts written for order_id in one quote, such as [1300] for "ORD-105, 1300 vests".

    Text after another order ID belongs to that order, so in "ORD-281, 120 sweaters. Also ORD-282,
    180 hoodies" ORD-281 gets [120]. Text before any order ID belongs to every order, so a count
    written before its order ID is found only when the quote names one order.
    """
    counts, owner = [], None
    for part in re.split(r"((?<![\w-])ORD-\d+(?![\w-]))", quote):
        if re.fullmatch(r"ORD-\d+", part):
            owner = part
        elif owner in (None, order_id):
            counts += [int(number.replace(",", "")) for number in re.findall(PIECE_COUNT, part, re.IGNORECASE)]
    return counts


def finish_verification(task, payload, assessment):
    """Check one task's assessment and build its verified record (on the copy of the task it is given).

    Changes task["verified"] and task["verified_version"]. The record holds the order, the current
    scheduling fields, the blockers and information_sufficient (True = ready for the allocation
    checks, not yet allocated). Raises ReviewRequired when the answer names an order or evidence
    outside this task. Python adds its own blockers to the model's.
    """
    # 1. The order ID must be written in this task's evidence, and every chosen evidence ID must be
    #    in this task's catalog (review if not).
    text = evidence_text(payload["evidence"])
    refs = {row["order_id"] for row in payload["order_lookups"]}
    if assessment.order_id is not None and assessment.order_id not in refs:
        raise ReviewRequired("The returned order ID is not a complete reference in this task's evidence.")
    catalog = {item["evidence_id"]: item["text"] for item in payload["evidence_catalog"]}
    selected = [assessment.urgency_evidence_id, assessment.deadline_evidence_id,
                assessment.quality_evidence_id, *assessment.constraint_evidence_ids]
    if any(key is not None and key not in catalog for key in selected):
        raise ReviewRequired("Selected evidence must belong to this task's supplied catalog.")
    # 2. Python's own blockers: an allocation with no order ID, an order ID that is not in
    #    orders.csv, several orders in the task's first item, or a piece count written for the order
    #    that differs from orders.csv (19 October 2026: in Test 8 the model marked "ORD-105, 1300
    #    vests" ready, and the CSV has 200). The CSV quantity is never replaced; the task asks.
    missing = list(assessment.missing_details)
    questions = list(assessment.doubts_to_clarify)
    if assessment.intent == "allocation" and assessment.order_id not in ORDER_INDEX:
        if assessment.order_id is None:
            missing.append("order ID")
            questions.append("What is the order ID?")
        else:
            missing.append("valid order ID")
            questions.append(f"{assessment.order_id} was not found. What is the correct order ID?")
    if assessment.intent == "allocation" and len(payload["anchor_order_ids"]) > 1:
        missing.append("request split or target-order clarification")
        questions.append("Does this source contain separate allocation jobs, or which single order is intended?")
    if assessment.intent == "allocation" and assessment.order_id in ORDER_INDEX:
        recorded = int(ORDER_INDEX[assessment.order_id]["pieces"])
        stated = {count for item in payload["evidence"] for quote in item["excerpts"]
                  for count in stated_piece_counts(quote, assessment.order_id)} - {recorded}
        if stated:
            written = ", ".join(str(count) for count in sorted(stated))
            missing.append(f"The chat states {written} pieces for {assessment.order_id}, "
                           f"but orders.csv records {recorded}; confirm the quantity.")
    # 3. constraints: original sentences kept for audit only; the allocator does not read them.
    #    They are the chosen constraint sentences, every sentence that names a workshop, and the
    #    quality sentence.
    constraints = [catalog[key] for key in assessment.constraint_evidence_ids]
    for item in payload["evidence"]:
        for quote in item["excerpts"]:
            if any(name.casefold() in quote.casefold() for name in WORKSHOP_NAMES):
                constraints.append(quote)
    if assessment.quality_evidence_id:
        constraints.append(catalog[assessment.quality_evidence_id])
    # 4. Check the scheduling fields; their issues are added to the blockers.
    scheduling, issues = resolve_scheduling(payload, assessment)
    missing.extend(issues)
    # 5. Build the verified record. dict.fromkeys removes repeats but keeps the order.
    result = {"description": text,
              "source_message_ids": list(dict.fromkeys(e["message_id"] for e in payload["evidence"])),
              "intent": assessment.intent, "order_id": assessment.order_id,
              "urgency_phrase": catalog.get(assessment.urgency_evidence_id),
              "deadline_phrase": catalog.get(assessment.deadline_evidence_id),
              "prioritize_quality": scheduling["preference"] == "quality",
              "constraints": list(dict.fromkeys(constraints)),
              "missing_details": list(dict.fromkeys(missing)),
              "doubts_to_clarify": list(dict.fromkeys(questions)),
              "information_sufficient": assessment.intent == "allocation"
                  and assessment.order_id in ORDER_INDEX and not missing and not questions}
    result.update(task_id=task["task_id"], version=task["version"], **scheduling)
    # 6. Save the record on the task, marked as verified for its current version.
    task.update(verified=result, verified_version=task["version"])
    return result


# ---------------------------------------------------------------------------------------------
# Review records and the tasks an unresolved input may modify.
# ---------------------------------------------------------------------------------------------


def record_task_review(state, task, reason, response_trace=None):
    """Save a review record for the task's current version and clear its verification.

    Changes state["task_review"]. Used for a failed check, an unmatched batch or a task too large to
    verify. The original evidence is kept for a person to check, and no verified result is made up,
    so the task can never reach the plan.
    """
    evidence = task_evidence(state, task)
    state["task_review"][task["task_id"]] = {
        "task_id": task["task_id"], "version": task["version"], "stage": "verify",
        "reason": reason, "evidence": evidence,
        "source_message_ids": list(dict.fromkeys(row["message_id"] for row in evidence)),
        "response_trace": response_trace,
    }
    task.update(verified=None, verified_version=None)
    print(f"  REVIEW {task['task_id']} v{task['version']}: {reason}")


def possibly_affected_tasks(state):
    """Return task ID -> the IDs of the plan rows that may modify the task, and change nothing.

    The rows are unresolved inputs (an intake review's message ID, a link review's item ID), failed
    tasks, and two kinds of verified task (a task ID): an allocation with no order ID that requests
    or excludes a workshop, and an unclear task naming an order. Each one affects the tasks
    review_targets finds for it: the tasks of the IDs it names, otherwise (inputs and the workshop
    rule only) those of the HOLD_WINDOW messages before it. Other requests for an affected order
    are affected too. Nothing is held: the affected tasks are verified and planned, and the plan
    marks them provisional (decision of 15 October 2026).
    """
    # 1. affected: task ID -> the rows that may modify it.
    affected = {}
    for review in state["intake_review"]:
        for tid in review_targets(state, review["raw_text"], review["message_id"]):
            affected.setdefault(tid, []).append(review["message_id"])
    for review in state["unresolved_links"].values():
        for tid in review_targets(state, "\n".join(review["excerpts"]), review["message_id"]):
            affected.setdefault(tid, []).append(review["item_id"])
    #    A failed task may modify the other tasks it names. Runs saved before 15 October also have
    #    "related_review" records: those were holds, not failures, so they are skipped.
    for review in state["task_review"].values():
        if review["stage"] == "verify" and review["version"] == state["tasks"][review["task_id"]]["version"]:
            for tid in review_targets(state, evidence_text(review["evidence"]), None):
                affected.setdefault(tid, []).append(review["task_id"])
    #    Two kinds of verified task may modify others too.
    for task in state["tasks"].values():
        record = task["verified"]
        if record is None or task["verified_version"] != task["version"]:
            continue
        if (record["intent"] == "allocation" and record["order_id"] is None
                and (record["requested_workshop"] or record["excluded_workshops"])):
            # A workshop rule without its job, such as "Fastest workshop excluding QuickStitch",
            # applies to the messages just before it.
            targets = review_targets(state, record["description"], record["source_message_ids"][0])
        elif record["intent"] == "unclear" and record["order_id"] is not None:
            # An unclear message naming an order, such as a cancellation, applies to that order.
            targets = review_targets(state, record["description"], None)
        else:
            targets = []
        for tid in targets:
            affected.setdefault(tid, []).append(task["task_id"])
    # 2. Spread to every task that shares an order ID with an affected task. pending is the work
    #    list: each newly affected task is checked for its own order IDs in turn.
    pending = list(affected)
    while pending:
        tid = pending.pop()
        text = evidence_text(task_evidence(state, state["tasks"][tid]))
        for order_id in order_references(text):
            for other in state["order_index"].get(order_id, []):
                if other not in affected:
                    affected[other] = list(affected[tid])
                    pending.append(other)
    # 3. A task never warns itself: a failed task can name its own order.
    warnings = {tid: [row_id for row_id in row_ids if row_id != tid] for tid, row_ids in affected.items()}
    return {tid: row_ids for tid, row_ids in warnings.items() if row_ids}


# ---------------------------------------------------------------------------------------------
# Batch the tasks, check the answers and run verification.
# ---------------------------------------------------------------------------------------------


def verification_batches(state):
    """Yield the payloads of the tasks that still need verification, in batches.

    A task needs verification when its current version is neither verified nor reviewed. Each batch
    has at most VERIFY_BATCH_SIZE tasks and MAX_PAYLOAD_CHARS characters. A task too large on its
    own goes to review; its evidence is never cut short. Batches are given out one at a time, so
    each is checked and saved before the next is built.
    """
    batch = []
    for task in state["tasks"].values():
        # 1. Skip tasks already reviewed or verified at their current version. A new version
        #    (after an accepted correction) needs a new check, so its old review is dropped.
        review = state["task_review"].get(task["task_id"])
        if review and review["version"] == task["version"]:
            continue
        state["task_review"].pop(task["task_id"], None)
        if task["verified_version"] == task["version"]:
            continue
        payload = verification_payload(state, task)
        # 2. A task too large to send even on its own goes to review. Its evidence is never cut
        #    short to make it fit.
        if len(json.dumps({"tasks": [payload]})) > MAX_PAYLOAD_CHARS:
            record_task_review(state, task, "The task exceeds the verification context limit; review its complete evidence.")
            continue
        # 3. If adding this task would break the count or size limit, give out the current batch
        #    first and start a new one.
        if batch and (len(batch) >= VERIFY_BATCH_SIZE
                      or len(json.dumps({"tasks": batch + [payload]})) > MAX_PAYLOAD_CHARS):
            yield batch
            batch = []
        batch.append(payload)
    # 4. Give out the last batch, even if it is smaller.
    if batch:
        yield batch


def finish_verification_batch(state, payloads, result, response_trace=None):
    """Match the model's answers to the batch's tasks, then check each assessment.

    Answers that cannot be matched send the whole batch to review. Otherwise each assessment is
    checked on a copy of its task, so a failed check never half-updates the real task, and valid
    answers are accepted independently.
    """
    # 1. The model must answer each task we sent exactly once, for the same version.
    payload_by_id = {p["task_id"]: p for p in payloads}
    expected = {task_id: p["version"] for task_id, p in payload_by_id.items()}
    for task_id, version in expected.items():
        if state["tasks"][task_id]["version"] != version:
            raise ValueError("Task evidence changed after this verification was requested.")
    received = {r.task_id: r.version for r in result.results}
    if len(result.results) != len(expected) or received != expected:
        print(f"  Cannot match the answers to the tasks: expected {expected}, received {received}")
        for task_id in expected:
            record_task_review(state, state["tasks"][task_id],
                               "The response did not identify every requested task and version exactly once.",
                               response_trace=response_trace)
        return
    # 2. Check each assessment on a copy, then copy the result onto the real task.
    for item in result.results:
        task = state["tasks"][item.task_id]
        updated = dict(task)
        try:
            finish_verification(updated, payload_by_id[item.task_id], item.assessment)
        except ReviewRequired as error:
            record_task_review(state, task, str(error), response_trace=response_trace)
            continue
        task.update(updated)
        state["task_review"].pop(item.task_id, None)
        print(f"  ACCEPTED {item.task_id} v{task['version']}: intent {task['verified']['intent']}, "
              f"ready {task['verified']['information_sufficient']}")
        for blocker in task["verified"]["missing_details"]:
            print(f"    blocker: {blocker}")
        for question in task["verified"]["doubts_to_clarify"]:
            print(f"    question: {question}")


def run_verification(run_dir, state, ask):
    """Verify every task that needs it, one batch at a time; save state.json after each batch.

    A task that an unresolved input may modify is verified too; the plan marks it provisional. An
    unreadable answer sends its whole batch to review; the other batches continue. Writes
    calls/verify-*.json.
    """
    for payloads in verification_batches(state):
        print(f"[Verify] batch: {[payload['task_id'] for payload in payloads]}")
        try:
            result = ask("verify", VERIFY_PROMPT, {"tasks": payloads}, VerificationBatch)
        except ReviewRequired as error:
            for payload in payloads:
                record_task_review(state, state["tasks"][payload["task_id"]], str(error),
                                   response_trace=getattr(ask, "last_trace_file", None))
        else:
            finish_verification_batch(state, payloads, result, getattr(ask, "last_trace_file", None))
        save_checkpoint(run_dir, state)
