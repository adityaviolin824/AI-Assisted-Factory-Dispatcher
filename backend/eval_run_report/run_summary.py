# run_summary.py: the facts a run report needs, read from one saved run folder.
#
# Report flow: make_run_report.py -> read_run and the counts here -> score_against_key (only with a
#              key) -> report_markdown -> <run folder>/run_report.md.
# Reads:       <run folder>/manifest.json, state.json, plan.json and calls/*.json; never changes them.
# Writes:      nothing.
import json
from collections import Counter

# Dollars per million tokens, from OpenAI's model pages (checked 14 Oct 2026), as in
# docs/evaluation/PROMPT_TESTING_RESULTS.md. Reasoning tokens are billed as output tokens.
PRICES = {"gpt-5.6-luna": {"input": 0.20, "cached_input": 0.02, "output": 1.20},
          "gpt-4.1-mini": {"input": 0.40, "cached_input": 0.10, "output": 1.60}}
# The date PRICES was checked, shown beside every cost estimate made with it.
PRICES_CHECKED = "2026-10-14"
STAGES = ("intake", "link", "verify")
# Plan outcomes in the order a reader needs them: what was allocated, what needs a person, the rest.
OUTCOMES = ("recommendation", "provisional_recommendation", "review_required", "deadline_passed",
            "needs_clarification", "reference", "processing_review", "link_review", "intake_review",
            "non_task", "not_processed")


def read_run(run_dir):
    """Return the manifest, processing state, plan and model-call records of one run folder."""
    def read(name):
        return json.loads((run_dir / name).read_text(encoding="utf-8"))
    calls = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((run_dir / "calls").glob("*.json"))]
    return {"manifest": read("manifest.json"), "state": read("state.json"), "plan": read("plan.json"),
            "calls": calls}


def processing_counts(run):
    """Return the run's message, item, task and review counts, each counted in its own unit.

    Plans made before 15 October 2026 have no review_warnings; their count is None (not recorded).
    """
    state, plan = run["state"], run["plan"]
    verified = [task for task in state["tasks"].values()
                if task["verified"] is not None and task["verified_version"] == task["version"]]
    return {"messages": len(run["manifest"]["messages"]), "non_task": len(state["non_task_message_ids"]),
            "intake_review": len(state["intake_review"]), "items": len(state["items"]),
            "tasks": len(state["tasks"]), "verified": len(verified), "task_review": len(state["task_review"]),
            "link_review": len(state["unresolved_links"]), "not_processed": len(plan["not_processed"]),
            "review_warnings": len(plan["review_warnings"]) if "review_warnings" in plan else None}


def outcome_counts(plan):
    """Return {outcome: rows} for every plan outcome, zero included, in OUTCOMES order."""
    counts = Counter(row["outcome"] for row in plan["summary_rows"])
    return {outcome: counts[outcome] for outcome in OUTCOMES}


def call_cost(record):
    """Return the dollar cost of one answered call at its recorded tokens; None for an unpriced model."""
    price = PRICES.get(record["request"]["model"])
    if price is None:
        return None
    usage = record["usage"]
    cached = usage["input_token_details"].get("cache_read", 0)
    return ((usage["input_tokens"] - cached) * price["input"] + cached * price["cached_input"]
            + usage["output_tokens"] * price["output"]) / 1_000_000


def total_cost(records):
    """Return the summed cost of the records, or None when any of them has no listed price."""
    costs = [call_cost(record) for record in records]
    return None if None in costs else sum(costs)


def cost_row(name, records):
    """Return the calls, paid and failed calls, paid tokens, cost and model time of some call records.

    A reused call (reused_response) was answered from the saved-answer cache, so this run paid
    nothing for it. "fresh" prices every answered call, as a run with an empty cache would pay.
    A failed call has an error record and no usage.
    """
    answered = [record for record in records if "usage" in record]
    paid = [record for record in answered if not record.get("reused_response")]
    return {"stage": name, "models": sorted({record["request"]["model"] for record in records}),
            "calls": len(records), "paid": len(paid), "failed": len(records) - len(answered),
            "input_tokens": sum(r["usage"]["input_tokens"] for r in paid),
            "cached_tokens": sum(r["usage"]["input_token_details"].get("cache_read", 0) for r in paid),
            "output_tokens": sum(r["usage"]["output_tokens"] for r in paid),
            "reasoning_tokens": sum(r["usage"]["output_token_details"].get("reasoning", 0) for r in paid),
            "cost_this_run": total_cost(paid), "cost_fresh": total_cost(answered),
            "seconds_this_run": sum(r["elapsed_seconds"] for r in paid),
            "seconds_fresh": sum(r["elapsed_seconds"] for r in answered)}


def stage_costs(calls):
    """Return a cost_row for each stage, then one for all calls together."""
    return ([cost_row(stage, [record for record in calls if record["request"]["stage"] == stage])
             for stage in STAGES] + [cost_row("total", calls)])
