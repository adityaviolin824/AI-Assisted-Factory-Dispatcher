# make_run_report.py: write a readable report of one saved run into its folder, as run_report.md.
# It makes no model call and changes no run file except run_report.md, so it can be repeated freely.
#
# Run from backend/:
#   uv run python make_run_report.py output/runs/<start time>
#   uv run python make_run_report.py output/runs/<start time> --key <key.json> --data <data folder>
# --key and --data go together: the key is a JSON answer key for the run's chat, such as
# docs/evaluation/extended_dispatch_100_human_team_golden.json, and the data folder holds the orders.csv and
# workshops.csv the run used, such as data/extended_dispatch_100. config.toml is not read for them,
# because it is restored to the supplied files after every test run.
#
# Steps: read_run (eval_run_report/run_summary.py) reads the run's manifest, state, plan and model
# calls; with a key, score_cases and message_labels (score_against_key.py) score the run against it;
# report_text (report_markdown.py) writes the settings, processing counts, the score, the plan
# outcomes with every reason, and the cost and time of each stage.
import argparse
import hashlib
import json
from pathlib import Path

from eval_run_report.key_reference_plan import read_data_folder
from eval_run_report.report_markdown import report_text, score_section
from eval_run_report.run_summary import read_run
from eval_run_report.score_against_key import message_labels, score_cases
from order_processing_into_tasks.settings_and_data import BACKEND_DIR


def short_path(path):
    """Return a path inside backend/ relative to it, so the report holds no machine-specific path."""
    path = path.resolve()
    return path.relative_to(BACKEND_DIR) if path.is_relative_to(BACKEND_DIR) else path.name


def main():
    """Write run_report.md for the run folder named on the command line, scored when a key is given."""
    parser = argparse.ArgumentParser(description="Write run_report.md for one saved run folder.")
    parser.add_argument("run_dir", type=Path, help="a run folder, such as output/runs/<start time>")
    parser.add_argument("--key", type=Path, help="a JSON answer key for the run's chat")
    parser.add_argument("--data", type=Path, help="the data folder the run used (with --key)")
    args = parser.parse_args()
    if (args.key is None) != (args.data is None):
        parser.error("--key and --data go together.")
    # A processing-only run (run_intake_and_processing.py) has no plan yet.
    if not (args.run_dir / "plan.json").exists():
        parser.error(f"{args.run_dir} has no plan.json; plan it first with run_allocation.py.")

    run = read_run(args.run_dir)
    score_lines = []
    if args.key:
        key_bytes = args.key.read_bytes()
        key = json.loads(key_bytes)
        orders, workshops = read_data_folder(args.data)
        # A key or data folder that does not belong to this run is refused with its reason.
        try:
            scores = score_cases(key, run, orders, workshops)
        except ValueError as error:
            parser.error(str(error))
        score_lines = score_section(short_path(args.key), hashlib.sha256(key_bytes).hexdigest(), key,
                                    short_path(args.data), scores, message_labels(key, run["state"]))
    report_file = args.run_dir / "run_report.md"
    report_file.write_text(report_text(short_path(args.run_dir), run, score_lines), encoding="utf-8")
    print(f"Saved: {report_file}")


if __name__ == "__main__":
    main()
