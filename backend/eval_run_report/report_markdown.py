# report_markdown.py: turn a run's facts (run_summary) and, with a key, its score (score_against_key)
# into the Markdown text of run_report.md.
#
# Report flow: make_run_report.py -> run_summary -> score_against_key (only with a key)
#              -> report_text (this file) -> <run folder>/run_report.md.
# Reads and writes nothing; make_run_report.py saves the text. score_section is used only with a key.
from collections import Counter

from eval_run_report.run_summary import PRICES, outcome_counts, processing_counts, stage_costs
from eval_run_report.score_against_key import FIELDS, PROBLEM_CLASSES

# One line per plan outcome, so a reader does not need the code to understand the table.
MEANINGS = {
    "recommendation": "a workshop is recommended (a preview, not an assignment)",
    "provisional_recommendation": "recommended, but an unresolved message may modify the request",
    "review_required": "the rules found no acceptable workshop, or another request names the same order",
    "deadline_passed": "the deadline is on or before the dispatch date",
    "needs_clarification": "a fact is missing or conflicts; the reason is the question to ask",
    "reference": "an information question, recorded and not answered",
    "processing_review": "the model's check of this task could not be trusted",
    "link_review": "a follow-up whose task is uncertain",
    "intake_review": "a message the model could not read reliably",
    "non_task": "no request or question found",
    "not_processed": "processing stopped before this input (partial plan only)",
}


def money(value):
    """Return a dollar amount to four decimals, or "unpriced" for a model without a listed price."""
    return "unpriced" if value is None else f"${value:.4f}"


def table(header, rows):
    """Return Markdown table lines; "|" and line breaks in a cell are escaped so the table stays intact."""
    def cell(value):
        return "-" if value is None or value == "" else str(value).replace("|", "\\|").replace("\n", " ")
    return (["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
            + ["| " + " | ".join(cell(value) for value in row) + " |" for row in rows] + [""])


def header_section(run_name, run):
    """Return the title and the lines that say which run, plan and settings the report describes."""
    manifest, plan = run["manifest"], run["plan"]
    efforts = manifest.get("reasoning_effort", {})
    complete = "yes" if plan["processing_complete"] else "no; this plan is partial, so evaluate complete runs only"
    objective = plan["objective_setting"] or "each request's own preference"
    lines = [f"# Run report: {manifest['label']}", "",
             f"- Run folder: `{run_name}`",
             f"- Plan made {plan['created_at'][:19]}; dispatch date {plan['dispatch_date']}; objective: {objective}.",
             f"- Message date: {manifest.get('message_date', 'not recorded')}. Processing complete: {complete}.",
             "- Written by `make_run_report.py` from the saved run files, with no model call.", "",
             "## Settings", ""]
    lines += table(["Stage", "Model", "Reasoning effort"],
                   [[stage, model, efforts.get(stage, f"none (temperature {manifest['temperature']})")]
                    for stage, model in manifest["models"].items()])
    lines += [f"Batches: {manifest['target_size']} target and {manifest['context_size']} context messages per "
              f"extraction call; up to {manifest['verify_batch_size']} tasks per verification call; "
              f"payload limit {manifest['max_payload_chars']:,} characters.", ""]
    return lines


def counts_section(run):
    """Return the processing counts: messages, items and tasks are counted separately."""
    counts = processing_counts(run)
    if counts["review_warnings"] is None:
        counts["review_warnings"] = "not recorded (this plan was made before review warnings, 15 October 2026)"
    return ["## Processing", "",
            f"- Chat messages: {counts['messages']}. No request found: {counts['non_task']}; "
            f"intake review: {counts['intake_review']}.",
            f"- Items extracted: {counts['items']}. Tasks: {counts['tasks']}, of which {counts['verified']} "
            f"verified at their current version and {counts['task_review']} in processing review.",
            f"- Follow-ups in link review: {counts['link_review']}. Inputs without an outcome: "
            f"{counts['not_processed']}.",
            f"- Tasks marked provisional by review warnings: {counts['review_warnings']}.", ""]


def outcomes_section(plan):
    """Return the outcome table, the recommendations and every other row grouped by outcome."""
    counts = outcome_counts(plan)
    lines = ["## Plan outcomes", ""]
    lines += table(["Outcome", "Rows", "Meaning"],
                   [[outcome, rows, MEANINGS[outcome]] for outcome, rows in counts.items() if rows]
                   + [["total", sum(counts.values()), "one row per task, follow-up or message"]])
    recommended = [row for row in plan["summary_rows"]
                   if row["outcome"] in ("recommendation", "provisional_recommendation")]
    lines += ["### Recommendations", ""]
    lines += table(["Row", "Order", "Outcome", "Workshop", "Delivery days", "Days available", "Messages"],
                   [[row["id"], row["order_id"], row["outcome"], row["workshop"],
                     None if row["delivery_days"] is None else f"{row['delivery_days']:.2f}",
                     row["days_available"], ", ".join(row["messages"])] for row in recommended])
    lines += ["### Every other row, by outcome", ""]
    for outcome, rows in counts.items():
        if rows and outcome not in ("recommendation", "provisional_recommendation"):
            lines += [f"**{outcome}** ({rows})", ""]
            lines += table(["Row", "Order", "Reason"],
                           [[row["id"], row["order_id"], row["reason"]]
                            for row in plan["summary_rows"] if row["outcome"] == outcome])
    return lines


def cost_section(calls):
    """Return the model-call table: what this run paid, and what a run with no saved answers would pay."""
    rows = stage_costs(calls)
    lines = ["## Model calls, cost and time", ""]
    lines += table(["Stage", "Model", "Calls", "Paid in this run", "Failed", "Paid input tokens (cached)",
                    "Paid output tokens (reasoning)", "Cost in this run", "Cost of a fresh run",
                    "Model seconds in this run (fresh)"],
                   [[row["stage"], ", ".join(row["models"]), row["calls"], row["paid"], row["failed"],
                     f"{row['input_tokens']:,} ({row['cached_tokens']:,})",
                     f"{row['output_tokens']:,} ({row['reasoning_tokens']:,})",
                     money(row["cost_this_run"]), money(row["cost_fresh"]),
                     f"{row['seconds_this_run']:.0f} ({row['seconds_fresh']:.0f})"] for row in rows])
    prices = "; ".join(f"`{model}` ${p['input']:.2f} input, ${p['cached_input']:.2f} cached input, "
                       f"${p['output']:.2f} output" for model, p in PRICES.items())
    return lines + [
        "A reused call was answered from the saved-answer cache, so this run paid nothing for it. "
        "A fresh run prices every answered call at its recorded tokens. Model seconds add up the recorded "
        "call times; they exclude Python time.", "",
        f"Prices per million tokens (checked 14 Oct 2026): {prices}. Reasoning tokens are billed as output.", ""]


def score_section(key_name, key_hash, key, data_name, scores, labels):
    """Return the score sections: decisions first, then why allocations were missed, then the details."""
    count = Counter(score["decision"] for score in scores)
    should = [s for s in scores if s["expected_outcome"] == "recommendation"]
    should_not = [s for s in scores if s["expected_outcome"] != "recommendation"]
    provenance = key.get("provenance", {})
    review = provenance.get("human_review", {})
    review_note = "- Who wrote and reviewed the key is recorded with the key, not by this script."
    if review.get("status") == "completed":
        review_note = (f"- Review recorded with the key: {review['method']} "
                       f"Reviewers: {review['reviewer_count']} human team members. "
                       f"Draft author: {provenance['draft_author']}. "
                       f"Confirmation source: {review['confirmation_source']}.")
    lines = ["## Score against the key", "",
             f"- Key: `{key_name}`, version {key.get('version')}, SHA-256 `{key_hash[:16]}...`; "
             f"{len(scores)} cases in {len(labels)} messages.",
             f"- Key's own description: {key.get('dataset')}. {key.get('evaluation_boundary', '')}".rstrip(),
             review_note,
             f"- The key's own plan is calculated by the app's routing and allocation rules from `{data_name}`.",
             "- A case is matched to the app task created from its first message; with two jobs in that message, "
             "to the task whose excerpts name its order. Not allocating an exception is correct, whatever the route.",
             "", "### Decisions", ""]
    lines += table(["Decision", "Cases"], [
        ["Should allocate (key: recommendation)", len(should)],
        ["- allocated, obeying the key's requested and excluded workshops", count["correct allocation"]],
        ["- not allocated (missed)", count["missed allocation"]],
        ["- allocated against the key's workshop rules (unsafe)",
         sum(s["decision"] == "unsafe allocation" for s in should)],
        ["Should not allocate (key: exception)", len(should_not)],
        ["- not allocated (correct)", count["correct non-allocation"]],
        ["- allocated anyway (unsafe)", sum(s["decision"] == "unsafe allocation" for s in should_not)]])
    provisional = [s["case_id"] for s in scores if s["outcome"] == "provisional_recommendation"]
    lines += [f"Provisional recommendations, counted as allocations above: {len(provisional)}"
              + (f" ({', '.join(provisional)})." if provisional else "."), ""]
    unsafe = [s for s in scores if s["decision"] == "unsafe allocation"]
    if unsafe:
        lines += ["**Unsafe allocations**", ""]
        lines += table(["Case", "Order", "Key outcome", "App workshop", "Scenario"],
                       [[s["case_id"], s["order"], s["expected_outcome"], s["workshop"], s["scenario"]] for s in unsafe])
    problems = [s for s in scores if s["problem"]]
    lines += ["### Missed allocations and other workshops, by cause", ""]
    lines += table(["Cause", "Missed", "Other workshop than the key's plan", "Meaning"],
                   [[name, sum(s["problem"] == name and s["decision"] == "missed allocation" for s in problems),
                     sum(s["problem"] == name and s["decision"] == "correct allocation" for s in problems), meaning]
                    for name, meaning in PROBLEM_CLASSES.items()])
    if problems:
        lines += table(["Case", "Order", "Scenario", "App task", "App outcome", "App workshop (key plan)", "Cause",
                        "App reason"],
                       [[s["case_id"], s["order"], s["scenario"], s["task_id"], s["outcome"],
                         f"{s['workshop']} ({s['reference_workshop']})" if s["workshop"] else None, s["problem"],
                         s["reason"]] for s in problems])
    allocated = [s for s in scores if s["decision"] == "correct allocation"]
    same = sum(s["workshop"] == s["reference_workshop"] for s in allocated)
    lines += [f"Workshop choice: {same} of {len(allocated)} correct allocations chose the workshop of the key's own plan.", ""]
    lines += fields_lines(scores) + labels_lines(labels) + links_lines(scores)
    lines += ["### Exception cases", ""]
    lines += table(["Case", "Order", "Scenario", "Key outcome", "App outcome", "Decision"],
                   [[s["case_id"], s["order"], s["scenario"], s["expected_outcome"], s["outcome"], s["decision"]]
                    for s in should_not])
    return lines


def fields_lines(scores):
    """Return how often each allocator field matched the key, on tasks verified at their current version."""
    verified = [s for s in scores if s["verified"]]
    lines = ["### Fields of verified matched tasks", ""]
    lines += table(["Field", "Matches key", "Tasks compared"],
                   [[field, sum(field not in s["differences"] for s in verified), len(verified)] for field in FIELDS])
    differences = [[s["case_id"], field, app, wanted] for s in verified for field, (app, wanted) in s["differences"].items()]
    if differences:
        lines += table(["Case", "Field", "App", "Key"], differences)
    return lines


def labels_lines(labels):
    """Return the message-label agreement and a table of every key label against the app's label."""
    pairs = Counter((wanted, app) for _, wanted, app in labels)
    lines = ["### Message labels", "",
             f"{sum(wanted == app for _, wanted, app in labels)} of {len(labels)} messages have the key's label.", ""]
    lines += table(["Key label", "App label", "Messages"], [[wanted, app, n] for (wanted, app), n in sorted(pairs.items())])
    wrong = [message_id for message_id, wanted, app in labels if wanted != app]
    if wrong:
        lines += [f"Messages with another label: {', '.join(wrong)}.", ""]
    return lines


def links_lines(scores):
    """Return how many of the key's follow-ups joined their case's task, and where the others went."""
    joined = [done for s in scores for done in s["joined"].values()]
    lines = ["### Follow-up links", "",
             f"{sum(joined)} of {len(joined)} follow-ups joined their case's task.", ""]
    missing = [[s["case_id"], message_id, where] for s in scores for message_id, where in s["unjoined"].items()]
    if missing:
        lines += table(["Case", "Follow-up", "Where it went"], missing)
    return lines


def report_text(run_name, run, score_lines=()):
    """Return the whole report. score_lines are the key's score sections, when a key was given."""
    lines = header_section(run_name, run) + counts_section(run)
    lines += list(score_lines) + outcomes_section(run["plan"]) + cost_section(run["calls"])
    return "\n".join(lines).rstrip() + "\n"
