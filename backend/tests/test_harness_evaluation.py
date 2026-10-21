"""Offline checks of eval_harness/run_harness_evaluation.py, the adapter between the app's allocation
rules and the course harness. The harness (../harness/simulate.py) is only read.

Run from backend/: uv run python -m unittest discover -s tests -v
"""
import contextlib
import io
import unittest
from dataclasses import asdict
from datetime import date, timedelta
from types import SimpleNamespace

from test_allocation_modules import check_task, pinned_settings
from test_processing_modules import undefined_names

from eval_harness import run_harness_evaluation
from eval_harness.run_harness_evaluation import POLICIES, days_late, make_allocator, run_comparison, simulate
from order_processing_into_tasks.settings_and_data import BACKEND_DIR, DATA_DIR
from task_allocation_to_workshops import recommend_one_task
from task_allocation_to_workshops.allocation_settings_and_data import INITIAL_QUEUES, ORDERS, WORKSHOPS

SUPPLIED_HARNESS = BACKEND_DIR.parents[1] / "project-material" / "harness" / "simulate.py"
RUN_NAMES = ["random", "greedy_biggest", "cheapest"] + [objective.removeprefix("minimize_") for objective in POLICIES]


def made_up_workshop(workshop_id, capacity, lead_days, cost, status="ACTIVE", makes=("TOPS",), max_batch=None):
    """Return a harness Workshop with no defects and no starting queue."""
    return simulate.Workshop(workshop_id, workshop_id, capacity, lead_days, 0.0, cost, set(makes),
                             status, max_batch, 0.0, "")


# FAST delivers 100 pieces in 2 days for 1000; CHEAP in 7 days for 500. The other three would be
# best on every number, but a hard rule blocks each of them.
MADE_UP_WORKSHOPS = {
    "FAST": made_up_workshop("FAST", 100, 1, 10.0),
    "CHEAP": made_up_workshop("CHEAP", 20, 2, 5.0),
    "CLOSED": made_up_workshop("CLOSED", 1000, 0, 1.0, status="SUSPENDED"),
    "SMALL": made_up_workshop("SMALL", 1000, 0, 1.0, max_batch=50),
    "NO_TOPS": made_up_workshop("NO_TOPS", 1000, 0, 1.0, makes=("BOTTOMS",)),
}
EMPTY_QUEUES = {workshop_id: 0.0 for workshop_id in MADE_UP_WORKSHOPS}


def made_up_batch(days_available):
    """Return a batch of 100 tops sent on 1 May 2026, due days_available days later."""
    sent = date(2026, 5, 1)
    return {"order_id": "ORD-X", "category": "TOPS", "pieces": 100, "sent_date": sent,
            "due_date": sent + timedelta(days=days_available)}


def choose(objective, days_available, queues=EMPTY_QUEUES):
    """Return a new allocator's choice for one made-up batch."""
    return make_allocator(objective)(made_up_batch(days_available), MADE_UP_WORKSHOPS, queues)


class HarnessSetup(unittest.TestCase):
    """The harness is the supplied file, reading the app's data."""

    def test_harness_file_is_unchanged(self):
        if not SUPPLIED_HARNESS.is_file():
            self.skipTest("project-material/ is not here")
        self.assertEqual(simulate.__file__, str(BACKEND_DIR.parent / "harness" / "simulate.py"))
        self.assertEqual((BACKEND_DIR.parent / "harness" / "simulate.py").read_bytes(), SUPPLIED_HARNESS.read_bytes())

    def test_harness_reads_the_app_data(self):
        self.assertEqual(simulate.DATA, DATA_DIR)
        sim = simulate.Simulator()
        self.assertEqual(len(sim.batches), len(ORDERS))
        self.assertEqual({wid: asdict(w) for wid, w in sim.workshops.items()},
                         {wid: asdict(w) for wid, w in WORKSHOPS.items()})

    def test_every_name_is_defined(self):
        self.assertEqual(undefined_names(run_harness_evaluation), set())


class AdapterRules(unittest.TestCase):
    """Hand-worked decisions on made-up workshops (delivery days = queue + pieces/capacity + lead)."""

    def test_hard_rules_come_first(self):
        for objective in POLICIES:
            with self.subTest(objective=objective):
                self.assertIn(choose(objective, 10), {"FAST", "CHEAP"})

    def test_objective_ranks_the_on_time_workshops(self):
        # 10 days available: both are on time.
        self.assertEqual(choose("minimize_tardiness", 10), "FAST")
        self.assertEqual(choose("minimize_cost", 10), "CHEAP")

    def test_late_workshops_are_removed_before_ranking(self):
        # 3 days after the batch's own sent date: CHEAP (7 days) is late, so minimize_cost takes FAST.
        # Counted from the app's dispatch date (1 April) instead, CHEAP would be on time.
        self.assertEqual(choose("minimize_cost", 3), "FAST")

    def test_least_late_when_no_workshop_is_on_time(self):
        # 1 day available: FAST is 1 day late, CHEAP 6, so every policy takes FAST.
        for objective in POLICIES:
            with self.subTest(objective=objective):
                self.assertEqual(choose(objective, 1), "FAST")

    def test_the_harness_queues_are_used(self):
        # FAST holds 9 days of work: 11 days to deliver, so it is late and CHEAP (7 days) is chosen.
        self.assertEqual(choose("minimize_tardiness", 10, {**EMPTY_QUEUES, "FAST": 9.0}), "CHEAP")

    def test_each_allocator_counts_its_own_pieces(self):
        # One allocator, three batches: both shares start at 100%, so the faster FAST wins; then FAST
        # would hold 100% and CHEAP 50%, so CHEAP wins; then both would hold 67%, so FAST wins again.
        # A new allocator starts from zero, so FAST wins (counting the first one's pieces, CHEAP would).
        allocator = make_allocator("minimize_concentration")
        choices = [allocator(made_up_batch(10), MADE_UP_WORKSHOPS, EMPTY_QUEUES) for _ in range(3)]
        self.assertEqual(choices, ["FAST", "CHEAP", "FAST"])
        self.assertEqual(choose("minimize_concentration", 10), "FAST")


class SameChoiceAsTheApp(unittest.TestCase):
    """For every order in orders.csv, under every policy, from the app's starting queues: the adapter
    chooses the app's recommendation, or its closest option when every allowed workshop is late.
    An order already due on the app's dispatch date has no app choice (review only), and the replay
    never sends such a batch."""

    def test_every_order_and_policy(self):
        branches = set()
        for order_id in ORDERS:
            for objective in POLICIES:
                with self.subTest(order=order_id, objective=objective), pinned_settings():
                    decision = recommend_one_task.recommend(check_task("T:H", order_id), INITIAL_QUEUES, {}, objective)
                    branches.add(decision["status"])
                    if decision["status"] == "deadline_passed":
                        # Due on or before 1 April: the app calculates nothing, so there is no choice
                        # to compare (decision of 18 October 2026).
                        self.assertEqual(decision["candidate_metrics"], {})
                        continue
                    snapshot = decision["order_snapshot"]
                    batch = {**snapshot, "sent_date": date.fromisoformat(snapshot["sent_date"]),
                             "due_date": date.fromisoformat(snapshot["due_date"])}
                    if decision["status"] == "recommendation":
                        expected = decision["selected_workshop"]
                    else:
                        expected = decision["closest_option"]["workshop_id"]
                    self.assertEqual(make_allocator(objective)(batch, WORKSHOPS, INITIAL_QUEUES), expected)
        self.assertEqual(branches, {"recommendation", "review_required", "deadline_passed"})

    def test_the_replay_never_sends_a_batch_after_its_deadline(self):
        # Each batch is sent on its own order date, before it is due, so the app's past-deadline rule
        # never applies in the replay and cannot change the harness scores.
        self.assertTrue(all(batch["sent_date"] < batch["due_date"] for batch in simulate.load_batches()))


class HarnessReplay(unittest.TestCase):
    """The full replay, normal and shock: every policy finishes, and the rebuilt lateness agrees with
    the harness's own late flag."""

    @classmethod
    def setUpClass(cls):
        cls.sims = {shock: run_comparison(shock) for shock in (False, True)}

    def test_every_policy_finishes_both_runs(self):
        # Simulator.run raises ValueError for an ineligible workshop, so finishing proves eligibility.
        for shock, sim in self.sims.items():
            with self.subTest(shock=shock):
                self.assertEqual(list(sim.results), RUN_NAMES)
                self.assertTrue(all(len(outcomes) == len(ORDERS) for outcomes in sim.results.values()))

    def test_days_late_agree_with_the_harness(self):
        for shock, sim in self.sims.items():
            for name, outcomes in sim.results.items():
                with self.subTest(shock=shock, policy=name):
                    self.assertEqual([days > 0 for days in days_late(sim, name)],
                                     [outcome["late"] for outcome in outcomes])

    def test_days_late_by_hand(self):
        # Sent on day 0, done after 5.6 days (rounded to 6): 7 January, 2 days after its due date.
        # Sent on day 2, done after 4.4 days (day 6.4, rounded to 6): 7 January, before its due date.
        batches = [{"sent_date": date(2026, 1, 1), "due_date": date(2026, 1, 5)},
                   {"sent_date": date(2026, 1, 3), "due_date": date(2026, 1, 10)}]
        sim = SimpleNamespace(batches=batches, results={"x": [{"turnaround": 5.6}, {"turnaround": 4.4}]})
        self.assertEqual(days_late(sim, "x"), [2, 0])

    def test_main_prints_both_tables_for_both_runs(self):
        with contextlib.redirect_stdout(io.StringIO()) as printed:
            run_harness_evaluation.main()
        text = printed.getvalue()
        for scenario in ("normal run", "shock run"):
            self.assertIn(f"Official harness metrics, {scenario}", text)
            self.assertIn(f"External lateness measures, {scenario}", text)


if __name__ == "__main__":
    unittest.main()
