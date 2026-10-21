# run_harness_evaluation.py: score the app's allocation rules with the course harness (simulate.py).
#
# Run from backend/:  uv run python -m eval_harness.run_harness_evaluation
#
# The harness replays the 120 orders of orders.csv in date order and asks an allocator for one
# eligible workshop per batch. This file runs the app's six policies (five objectives and the
# hybrid) beside the harness's three baselines, in a normal run and a shock run, and prints:
#   1. simulate.py's own report: the six official metrics, unchanged;
#   2. a separate table of external lateness measures, taken from the same replay outcomes.
# The replay includes completed historical orders; it is separate from live dispatch and from the
# chat requests.
# Reads:  ../harness/simulate.py (never changed) and the data folder named in config.toml.
# Writes: nothing. No model calls.
import sys
from datetime import timedelta

from order_processing_into_tasks.settings_and_data import BACKEND_DIR, DATA_DIR
from task_allocation_to_workshops.rank_workshops import DEFAULT_HYBRID_WEIGHTS, rank_candidates
from task_allocation_to_workshops.workshop_rules_and_estimates import candidate_metrics, split_rejected

# simulate.py stays where the course supplied it. Its DATA folder (DSS-Project-CODES/data) does not
# exist in this project, so it is pointed at the app's data folder before any run.
sys.path.insert(0, str(BACKEND_DIR.parent / "harness"))
import simulate  # noqa: E402

simulate.DATA = DATA_DIR

# The app's objectives, each run as its own policy. The tables name them without "minimize_".
POLICIES = ["minimize_tardiness", "minimize_cost", "minimize_defects", "minimize_concentration",
            "minimize_robustness", "hybrid"]


def make_allocator(objective):
    """Return an allocator for simulate.Simulator.run that chooses like the app's recommend().

    For each batch: the hard rules, then delivery estimates from the harness's queues and the
    batch's own sent date, then the on-time workshops ranked by objective. The harness needs a
    workshop for every batch, so when none is on time the allocator returns the least-late one (the
    app's closest option) where the app would ask for review. pieces_so_far counts the pieces this
    allocator has sent to each workshop, for the share objectives, so each run needs a new allocator.
    """
    pieces_so_far = {}

    def allocator(batch, workshops, queues):
        eligible, _ = split_rejected(workshops, batch)
        total_pieces = sum(pieces_so_far.values()) + batch["pieces"]
        metrics = {w.workshop_id: candidate_metrics(w, batch, queues[w.workshop_id],
                                                    pieces_so_far.get(w.workshop_id, 0), total_pieces)
                   for w in eligible}
        on_time = {wid: row for wid, row in metrics.items() if row["on_time"]}
        if on_time:
            ranking, _ = rank_candidates(on_time, objective, DEFAULT_HYBRID_WEIGHTS)
        else:
            # The closest option: minimize_tardiness order (lateness, delivery days, then cost).
            ranking, _ = rank_candidates(metrics, "minimize_tardiness", DEFAULT_HYBRID_WEIGHTS)
        choice = ranking[0]
        pieces_so_far[choice] = pieces_so_far.get(choice, 0) + batch["pieces"]
        return choice

    return allocator


def run_comparison(shock):
    """Replay the orders with the three baselines and the app's six policies; return the Simulator."""
    sim = simulate.Simulator(shock=shock)
    sim.run(simulate.random_choice, "random")
    sim.run(simulate.greedy_biggest, "greedy_biggest")
    sim.run(simulate.cheapest, "cheapest")
    for objective in POLICIES:
        sim.run(make_allocator(objective), objective.removeprefix("minimize_"))
    return sim


def days_late(sim, name):
    """Return each batch's days late in one run of sim: max(0, completion date - due date).

    The outcomes keep no dates, so each completion date is rebuilt as Simulator.run computes it:
    the first batch's date plus the rounded completion day.
    """
    day0 = sim.batches[0]["sent_date"]
    result = []
    for batch, outcome in zip(sim.batches, sim.results[name]):
        day = (batch["sent_date"] - day0).days
        done_date = day0 + timedelta(days=round(day + outcome["turnaround"]))
        result.append(max(0, (done_date - batch["due_date"]).days))
    return result


def print_lateness(sim):
    """Print the external lateness measures of every run in sim, in days late.

    The mean over all batches, the mean over late batches only, the p90 (with the report's index
    rule) and the total. These are not simulate.py metrics.
    """
    print(f"{'policy':<16}{'mean':>8}{'mean if late':>14}{'p90':>6}{'total':>8}")
    for name in sim.results:
        late_days = sorted(days_late(sim, name))
        late_only = [days for days in late_days if days > 0]
        mean_if_late = f"{sum(late_only) / len(late_only):.1f}" if late_only else "-"
        print(f"{name:<16}{sum(late_days) / len(late_days):>8.1f}{mean_if_late:>14}"
              f"{late_days[int(0.9 * len(late_days))]:>6}{sum(late_days):>8}")


def main():
    """Print the official report and the external lateness measures, for a normal and a shock run."""
    print(f"Data folder: {DATA_DIR}")
    print("Baselines from simulate.py: random, greedy_biggest, cheapest. The app's policies: "
          f"{', '.join(POLICIES)} (hybrid weights {DEFAULT_HYBRID_WEIGHTS}).")
    for shock in (False, True):
        sim = run_comparison(shock)
        scenario = "shock run: one random workshop closed for days 30-44" if shock else "normal run"
        print(f"\nOfficial harness metrics, {scenario} (simulate.py's report, unchanged)")
        sim.report()
        print(f"\nExternal lateness measures, {scenario} (days late; not official harness metrics)")
        print_lateness(sim)


if __name__ == "__main__":
    main()
