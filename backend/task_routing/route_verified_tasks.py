# route_verified_tasks.py: decide where each verified task goes, before any workshop is considered.
#
# Flow:      processing (verified_tasks) -> [route_tasks] -> allocation_plan.plan_tasks plans the
#            "allocate" tasks; the other routes are kept in the plan as records for the dispatcher.
# Came from: notebook 05, Section 13: plan_tasks's duplicate-order count and its two routing conditions.
# Reads:     verified task records only. No queues, files or model calls.
# Writes:    nothing.
from task_allocation_to_workshops.recommend_one_task import review_decision


def route_task(task):
    """Return where one verified task goes: "reference", "needs_clarification" or "allocate".

    Only a question with nothing left to clarify is reference material: it is recorded, not answered.
    A question with an open doubt, or a task missing a fact, needs clarification. Routing reads these
    recorded fields, not the intent label alone: many requests labelled "question" only lack an
    order ID or a date.
    """
    open_questions = task["doubts_to_clarify"] or task["missing_details"]
    if task["intent"] == "question" and not open_questions:
        return "reference"
    if task["intent"] == "question" or not task["information_sufficient"]:
        return "needs_clarification"
    return "allocate"


def route_tasks(tasks):
    """Route every verified task, keeping their order.

    Returns {"allocate": tasks, "duplicate_order": review records, "needs_clarification": tasks,
    "reference": tasks}. The duplicate-order count runs over every verified allocation task with an
    order ID, ready or not, so a ready task that shares its order with an unclear request is reviewed
    instead of allocated. A duplicate-order review reserves nothing.
    """
    # The allocation tasks of each order, in task order, so a duplicate-order review can name all
    # of them.
    tasks_by_order = {}
    for task in tasks:
        if task["intent"] == "allocation" and task["order_id"] is not None:
            tasks_by_order.setdefault(task["order_id"], []).append(task["task_id"])
    routes = {"allocate": [], "duplicate_order": [], "needs_clarification": [], "reference": []}
    for task in tasks:
        route = route_task(task)
        # A ready task is an allocation with a known order, so tasks_by_order lists it.
        if route == "allocate" and len(tasks_by_order[task["order_id"]]) > 1:
            same_order = tasks_by_order[task["order_id"]]
            routes["duplicate_order"].append(review_decision(
                task, f"Allocation requests {', '.join(same_order)} all name "
                      f"{task['order_id']}; clarify the intended batches."))
        else:
            routes[route].append(task)
    return routes
