# workshop_rules_and_estimates.py: the hard rules that decide which workshops may take a batch, and
# the estimates for one allowed workshop.
#
# Allocation flow: allocation_plan -> recommend_one_task -> [workshop_rules_and_estimates], then
#                  rank_workshops ranks the allowed workshops.
# Came from:       notebook 05, Section 10.
# Reads:           workshops and batches given as arguments; hard_rule_reason also reads WORKSHOPS.
# Writes:          nothing (pure calculations).
#
# A batch is {"order_id", "category", "pieces", "sent_date", "due_date"}, the same keys the harness
# (../harness/simulate.py) passes to an allocator.
from task_allocation_to_workshops.allocation_settings_and_data import WORKSHOPS


def rejection_reason(workshop, batch, excluded_ids=(), requested_workshop_id=None):
    """Return the first hard rule that stops this workshop taking the batch, such as
    "status=SUSPENDED", or None if every rule passes.

    Request exclusions and workshop limits come before the requested workshop, so a request can
    narrow the choice but never override a limit.
    """
    if workshop.workshop_id in excluded_ids:
        return "excluded_by_request"
    if workshop.status != "ACTIVE":
        return f"status={workshop.status}"
    if batch["category"] not in workshop.makes:
        return f"cannot_make_category={batch['category']}"
    if workshop.max_batch is not None and batch["pieces"] > workshop.max_batch:
        return f"exceeds_batch_cap={batch['pieces']}>{workshop.max_batch}"
    if requested_workshop_id is not None and workshop.workshop_id != requested_workshop_id:
        return "not_the_requested_workshop"
    return None


def split_rejected(workshops, batch, excluded_ids=(), requested_workshop_id=None):
    """Split the workshops into allowed and rejected ones.

    Returns (eligible, rejected): the allowed Workshop objects, and one {"workshop_id", "reason"}
    per rejected workshop. Only allowed workshops get estimates; the rejections explain the decision.
    """
    eligible, rejected = [], []
    for workshop in workshops.values():
        reason = rejection_reason(workshop, batch, excluded_ids, requested_workshop_id)
        if reason is None:
            eligible.append(workshop)
        else:
            rejected.append({"workshop_id": workshop.workshop_id, "reason": reason})
    return eligible, rejected


def hard_rule_reason(requested_workshop_id, rejected):
    """Return one sentence for the dispatcher explaining why no workshop passed the hard rules.

    With a requested workshop, it names that workshop and its failed rule (the others were not
    requested). Without one, it lists each failed rule with the workshops it removed.
    """
    reasons = {row["workshop_id"]: row["reason"] for row in rejected}
    if requested_workshop_id is not None:
        workshop = WORKSHOPS[requested_workshop_id]
        return (f"Requested {workshop.workshop_id} ({workshop.name}) cannot take this batch: "
                f"{reasons[requested_workshop_id]}.")
    workshops_by_rule = {}
    for workshop_id, reason in reasons.items():
        workshops_by_rule.setdefault(reason, []).append(workshop_id)
    details = "; ".join(f"{reason} ({', '.join(ids)})" for reason, ids in workshops_by_rule.items())
    return f"No workshop satisfies the hard rules: {details}."


def candidate_metrics(workshop, batch, queue_days, cumulative_pieces, total_pieces):
    """Return the delivery days, lateness, cost and workload share for one allowed workshop.

    queue_days is this plan's queue copy, cumulative_pieces the pieces this workshop already holds in
    the plan, and total_pieces every planned piece, this batch included. Delivery days = queue +
    production + expected rework + transport, compared unrounded with the calendar days available.
    Rework is an expected value, not a guarantee.
    """
    pieces = batch["pieces"]
    processing = pieces / workshop.capacity
    expected_rework = processing * workshop.defect_rate * 0.5
    # A queue below zero counts as zero.
    queue = max(0.0, queue_days)
    eta = queue + processing + expected_rework + workshop.lead_days
    # Early delivery has zero lateness.
    days_until_due = (batch["due_date"] - batch["sent_date"]).days
    tardiness = max(0.0, eta - days_until_due)
    cost = round(pieces * workshop.cost, 2)
    # This workshop's share of all planned pieces if it takes this batch.
    share = (cumulative_pieces + pieces) / total_pieces

    return {
        "workshop_id": workshop.workshop_id,
        "name": workshop.name,
        # The parts of the delivery time are kept next to the total, to explain decisions later.
        "queue_days": queue,
        "processing_days": processing,
        "expected_rework_days": expected_rework,
        "lead_days": workshop.lead_days,
        "eta_days": eta,
        "days_until_due": days_until_due,
        "tardiness_days": tardiness,
        "on_time": tardiness == 0.0,
        # The defect rate is a probability (0 to 1).
        "defect_rate": workshop.defect_rate,
        "cost_per_piece": workshop.cost,
        "cost": cost,
        "share": share,
    }
