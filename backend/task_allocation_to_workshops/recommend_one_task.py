# recommend_one_task.py: make one decision record for one task, without touching the plan's queues.
#
# Allocation flow: allocation_plan.plan_tasks -> [recommend], once per ready allocation task, in
#                  planning order. Order of work inside recommend: readiness checks -> order facts ->
#                  past-deadline check -> hard rules -> estimates -> on-time filter -> ranking.
# Came from:       notebook 05, Section 12.
# Reads:           the task, the plan's queue copies, ORDERS, WORKSHOPS and DISPATCH_DATE.
# Writes:          nothing. plan_tasks reserves queue time afterwards, only for a recommendation.
from datetime import date

from task_allocation_to_workshops.allocation_settings_and_data import DISPATCH_DATE, ORDERS, WORKSHOPS
from task_allocation_to_workshops.rank_workshops import (
    DEFAULT_HYBRID_WEIGHTS, OBJECTIVE_FIELDS, PREFERENCE_OBJECTIVES, rank_candidates)
from task_allocation_to_workshops.workshop_rules_and_estimates import (
    candidate_metrics, hard_rule_reason, split_rejected)


def task_deadline(task):
    """Return the deadline the plan uses for a task.

    That is the date processing confirmed from the chat, otherwise the order's due date in
    orders.csv; None when neither is known (for example a question with no order). recommend checks
    it and plan_tasks sorts by it, so the planning order and the on-time check always agree.
    """
    if task["due_date"]:
        return date.fromisoformat(task["due_date"])
    order = ORDERS.get(task["order_id"])
    return order["due_date"] if order else None


def batch_pieces(task):
    """Return a task's batch size: the quantity the dispatcher gave, otherwise the order's pieces in
    orders.csv. Processing never sets a quantity; only the dispatcher's review does (22 October 2026).
    """
    return task.get("quantity") or ORDERS[task["order_id"]]["pieces"]


def review_decision(task, reason):
    """Return a decision record with status "review_required": the task's identity and wording,
    and empty result fields, so every decision has the same fields.

    recommend fills in more fields as it goes; route_tasks uses it for duplicate-order reviews.
    """
    return {"task_id": task["task_id"], "version": task["version"], "order_id": task["order_id"],
            "task": task, "status": "review_required", "selected_workshop": None,
            "selected_metrics": None, "closest_option": None, "option_without_request": None,
            "reason": reason, "warnings": [], "candidate_metrics": {}, "ranking": [],
            "ranking_keys": {}, "rejected_candidates": [], "alternatives": []}


def option_without_request(task, batch, queues, pieces_so_far, objective):
    """Return the metrics of the best on-time workshop if the request's workshop were ignored, or
    None if no workshop is on time. The task's exclusions still apply.

    Information for the dispatcher only: the task stays in review, nothing is reserved, and the
    request is never silently replaced.
    """
    eligible, _ = split_rejected(WORKSHOPS, batch, task["excluded_workshops"])
    total_pieces = sum(pieces_so_far.values()) + batch["pieces"]
    metrics = {w.workshop_id: candidate_metrics(w, batch, queues[w.workshop_id],
                                                pieces_so_far.get(w.workshop_id, 0), total_pieces)
               for w in eligible}
    on_time = {wid: row for wid, row in metrics.items() if row["on_time"]}
    ranking, _ = rank_candidates(on_time, objective, DEFAULT_HYBRID_WEIGHTS)
    return metrics[ranking[0]] if ranking else None


def recommend(task, queues, pieces_so_far, objective=None, require_on_time=True):
    """Decide one task: the best allowed, on-time workshop, or review with a reason.

    task is a verified record; queues and pieces_so_far are the plan's working copies; objective
    None means the task's own preference. The plan always uses require_on_time=True: late workshops
    are removed before ranking. Every hard rule runs before time or price is compared, and the
    reason quotes the saved numbers, so a decision can be checked against candidate_metrics later.
    Returns the decision record, with status "recommendation", "review_required" or
    "deadline_passed" (a deadline on or before the dispatch date: review only, nothing calculated).
    """
    # 1. Readiness. A ready task can be calculated; that does not mean a workshop can take it.
    result = review_decision(task, "")
    if task["intent"] != "allocation" or not task["information_sufficient"]:
        result["reason"] = "The request still needs clarification before allocation."
        return result
    if task["wants_split"] or task["unhandled_constraints"]:
        # Name what is unsupported, so the dispatcher knows what to resolve.
        unsupported = (["split requested"] if task["wants_split"] else []) + task["unhandled_constraints"]
        result["reason"] = f"Not supported by this plan, so the dispatcher must decide: {'; '.join(unsupported)}."
        return result

    # 2. Order facts from orders.csv, with the dispatcher's quantity if one was given. The deadline
    #    comes from task_deadline, the same date plan_tasks sorts by.
    order = ORDERS[task["order_id"]]
    pieces = batch_pieces(task)
    if pieces <= 0:
        raise ValueError("Batch pieces must be a positive integer.")
    batch = {"order_id": task["order_id"], "category": order["category"], "pieces": pieces,
             "sent_date": DISPATCH_DATE, "due_date": task_deadline(task)}
    if objective is None:
        objective = PREFERENCE_OBJECTIVES[task["preference"]]
    # Completed orders stay allowed in this historical experiment, but the record says so.
    if order["status"] == "COMPLETE":
        warning = "orders.csv marks this order COMPLETE; it is allowed only in this historical experiment."
        result["warnings"].append(warning)
    # A delivery deadline on or before the dispatch date cannot be met: every workshop has a pickup
    # lead time, so every estimate is longer than 0 days. The request stays in review with its
    # original date: no estimates, no least-late option and no queue time. Only a revised deadline
    # that the dispatcher confirms can return it to allocation (decision of 18 October 2026).
    if batch["due_date"] <= DISPATCH_DATE:
        result["status"] = "deadline_passed"
        result["reason"] = (f"The delivery deadline {batch['due_date']} is on or before the dispatch date "
                            f"{DISPATCH_DATE}, so no workshop can meet it. Nothing is estimated or reserved; "
                            "only a revised deadline confirmed by the dispatcher can return this request to "
                            "allocation, and the original date stays on record.")
        return result

    # 3. Apply every hard rule, estimate the allowed workshops, then remove late workshops.
    eligible, rejected = split_rejected(WORKSHOPS, batch, task["excluded_workshops"], task["requested_workshop"])
    metrics = {w.workshop_id: candidate_metrics(w, batch, queues[w.workshop_id],
               pieces_so_far.get(w.workshop_id, 0), sum(pieces_so_far.values()) + batch["pieces"])
               for w in eligible}
    rankable = dict(metrics)
    late = []
    if require_on_time:
        late = [wid for wid, row in metrics.items() if not row["on_time"]]
        for wid in late:
            del rankable[wid]
            rejected.append({"workshop_id": wid, "reason": "estimated_delivery_after_deadline"})
    ranking, keys = rank_candidates(rankable, objective, DEFAULT_HYBRID_WEIGHTS)

    # 4. Save enough numbers to explain the result later, even after the queues change.
    result.update(objective=objective,
                  policy_settings={"hybrid_weights": DEFAULT_HYBRID_WEIGHTS if objective == "hybrid" else {},
                                   "pieces_so_far": dict(pieces_so_far)},
                  order_snapshot={**batch, "sent_date": batch["sent_date"].isoformat(),
                                  "due_date": batch["due_date"].isoformat(),
                                  "status": order["status"], "current_stage": order["current_stage"]},
                  queue_snapshot=dict(queues),
                  applied_constraints={"excluded_workshops": task["excluded_workshops"],
                                       "requested_workshop": task["requested_workshop"],
                                       "require_on_time": require_on_time},
                  candidate_metrics=metrics, rejected_candidates=rejected,
                  ranking=ranking, ranking_keys=keys)

    # 5. Nothing to recommend: explain why.
    if not ranking:
        if not eligible:
            # Name the failed hard rules.
            result["reason"] = hard_rule_reason(task["requested_workshop"], rejected)
        else:
            # Every allowed workshop is late. Name the least-late one, in minimize_tardiness order
            # (lateness, then delivery days, then cost). min() keeps file order on ties, like sorted().
            tardiness_fields = OBJECTIVE_FIELDS["minimize_tardiness"]
            closest = min(metrics.values(), key=lambda row: tuple(row[field] for field in tardiness_fields))
            result["closest_option"] = closest
            # The deadline is after the dispatch date here: earlier deadlines returned above.
            timing = (f"No workshop allowed for this request meets the deadline {batch['due_date']} "
                      f"({closest['days_until_due']} days available).")
            result["reason"] = (f"{timing} Closest option: {closest['workshop_id']} ({closest['name']}), "
                                f"delivery in {closest['eta_days']:.2f} days, "
                                f"{closest['tardiness_days']:.2f} days late.")
        # The request is kept, but the dispatcher also sees the best on-time option without it.
        if task["requested_workshop"] is not None:
            option = option_without_request(task, batch, queues, pieces_so_far, objective)
            result["option_without_request"] = option
            if option is None:
                result["reason"] += " No other allowed workshop can deliver on time either."
            else:
                result["reason"] += (f" Without the request, the best on-time option is {option['workshop_id']} "
                                     f"({option['name']}), delivery in {option['eta_days']:.2f} of "
                                     f"{option['days_until_due']} available days; using it needs the "
                                     "dispatcher's approval.")
        return result

    # 6. Recommend the top-ranked workshop, with up to three alternatives for the dispatcher.
    selected = ranking[0]
    chosen = metrics[selected]
    reason = (f"{selected} ({chosen['name']}) ranks first under {objective} (order: {', '.join(ranking)}): "
              f"delivery in {chosen['eta_days']:.2f} of {chosen['days_until_due']} available days, "
              f"cost {chosen['cost']}.")
    if late:
        reason += f" Removed as late: {', '.join(late)}."
    #    The request mentions the top workshop, but processing recorded the mention only as a
    #    reference (neither requested nor excluded), so the instruction is unclear. For example,
    #    "nothing new to QuickStitch this week" was once recorded this way. Ask instead of
    #    recommending; the reason still shows the other on-time options. Nothing is reserved.
    referenced = {rule["workshop_id"] for rule in task["workshop_rules"] if rule["role"] == "reference"}
    if selected in referenced and selected != task["requested_workshop"]:
        result["reason"] = (f"{reason} The request mentions {selected} without a clear instruction (recorded "
                            f"as a reference, not as requested or excluded); confirm it before using {selected}.")
        return result
    result.update(status="recommendation", selected_workshop=selected, selected_metrics=chosen,
                  alternatives=[metrics[wid] for wid in ranking[1:4]], reason=reason)
    #    Reachable only with require_on_time=False, an alternative policy kept for experiments.
    if chosen["tardiness_days"] > 0:
        warning = "This optional late recommendation does not meet the deadline."
        result["warnings"].append(warning)
    return result
