# score_dispatcher_review.py: score a run's table after the dispatcher's review against a JSON answer key.
# It makes no model call and writes only the score file, so it can be repeated freely.
#
# Run from backend/:
#   uv run python score_dispatcher_review.py <run folder> --key <key.json> --data <data folder>
#       [--plan <table.json>] [--out <score.md>]
# --plan is the table to score: by default the run's dispatcher-plan.json; a copy in plan-history/
# scores an earlier approval. A draft (a review not approved yet, such as the first review saved as
# JSON) is scored as Approve all with no choices would approve it (finalize_review). --out is where
# the score is written; by default dispatcher_review_score.md in the run folder.
#
# make_run_report.py scores the plan before the review; this file scores the table after it. The rules
# are in eval_run_report/final_plan_score.py.
import argparse
import json
from pathlib import Path

from dispatcher_review.dispatcher_plan import finalize_review
from eval_run_report.final_plan_score import final_score_lines, score_final_plan
from eval_run_report.key_reference_plan import read_data_folder, reference_workshops
from eval_run_report.run_summary import read_run
from eval_run_report.score_against_key import check_key_matches_run


def main():
    """Score the table named on the command line and write the score as Markdown."""
    parser = argparse.ArgumentParser(description="Score a run's table after the dispatcher's review.")
    parser.add_argument("run_dir", type=Path, help="a run folder, such as output/runs/<start time>")
    parser.add_argument("--key", type=Path, required=True, help="a JSON answer key for the run's chat")
    parser.add_argument("--data", type=Path, required=True, help="the data folder the run used")
    parser.add_argument("--plan", type=Path, help="the table to score (default: dispatcher-plan.json)")
    parser.add_argument("--out", type=Path, help="the score file (default: dispatcher_review_score.md)")
    args = parser.parse_args()
    plan_file = args.plan or args.run_dir / "dispatcher-plan.json"
    out_file = args.out or args.run_dir / "dispatcher_review_score.md"

    run = read_run(args.run_dir)
    key = json.loads(args.key.read_text(encoding="utf-8"))
    orders, workshops = read_data_folder(args.data)
    # A key or data folder that does not belong to this run is refused with its reason.
    try:
        check_key_matches_run(key, run, orders, workshops)
    except ValueError as error:
        parser.error(str(error))
    table = json.loads(plan_file.read_text(encoding="utf-8"))
    if table["status"] != "final":
        table = finalize_review(table)
    scores, extra = score_final_plan(key, run["state"], table, orders, reference_workshops(key, orders, workshops))
    lines = final_score_lines(f"Score of {plan_file.name}", scores, extra, table)
    out_file.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:12]))
    print(f"Saved: {out_file}")


if __name__ == "__main__":
    main()
