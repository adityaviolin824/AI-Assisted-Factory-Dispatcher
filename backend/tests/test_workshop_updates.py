"""Tests for the workshops' own reports (task_allocation_to_workshops/workshop_updates.py and
fastapi_routes/workshops.py), called through FastAPI's TestClient. Fully offline.

Run from backend/:  uv run python -m unittest discover -s tests -v

What they prove, with the reports file and the run folders in a temporary folder:
- GET /workshops lists the eight workshops in workshops.csv order with their CSV values, and reading
  creates no file;
- PUT /workshops/{workshop_id} saves a report after the earlier ones, and the latest one is shown;
- an unknown workshop gets 404, and a value the calculations cannot use, an empty name or a missing
  field gets 422; nothing is saved then;
- a run keeps the workshop facts it started with: a later report changes only the next run, and a run
  without workshops.json plans with the CSV values;
- "not taking new work" only changes an active workshop: it cannot lift W7's suspension;
- the planner skips a workshop that is not taking new work, with that status as the reason, but a
  dispatcher's own choice of it is still estimated, with the broken rule recorded; a lower reported
  capacity lengthens the processing estimate.
No model is called.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from test_allocation_modules import check_task, pinned_settings

import main
from dispatcher_review.dispatcher_plan import named_option
from task_allocation_to_workshops import workshop_updates
from task_allocation_to_workshops.allocation_settings_and_data import INITIAL_QUEUES, WORKSHOPS
from task_allocation_to_workshops.recommend_one_task import recommend

# A report that changes nothing but the fields a test names.
REPORT = {"taking_new_work": True, "capacity": 130, "queue_days": 1.0, "lead_days": 1, "note": "",
          "reported_by": "Alex"}


class WorkshopTestCase(unittest.TestCase):
    """A temporary reports file and run folders; the planner goes back to the CSV values afterwards."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.work_dir = Path(temp.name)
        self.enterContext(mock.patch.object(workshop_updates, "REPORTS_FILE", self.work_dir / "reports.json"))
        # work_dir has no workshops.json, so this sets the CSV values again.
        self.addCleanup(workshop_updates.use_run_workshops, self.work_dir)
        self.client = TestClient(main.app)

    def report(self, workshop_id, **changes):
        """Send one report through the API and return the response."""
        return self.client.put(f"/workshops/{workshop_id}", json={**REPORT, **changes})

    def run_folder(self, name):
        """Return a new run folder whose workshop facts are fixed now, as start_run fixes them."""
        run_dir = self.work_dir / name
        run_dir.mkdir()
        workshop_updates.freeze_for_run(run_dir)
        return run_dir


class Routes(WorkshopTestCase):

    def test_list_before_any_report(self):
        workshops = self.client.get("/workshops").json()
        self.assertEqual([w["workshop_id"] for w in workshops], [f"W{n}" for n in range(1, 9)])
        quickstitch = workshops[0]
        self.assertEqual(quickstitch["recorded"],
                         {"taking_new_work": True, "capacity": 300, "queue_days": 4.0, "lead_days": 1})
        self.assertEqual(quickstitch["current"], quickstitch["recorded"])
        self.assertIsNone(quickstitch["last_report"])
        self.assertEqual(workshops[6]["status"], "SUSPENDED")
        self.assertFalse(workshop_updates.REPORTS_FILE.exists())

    def test_reports_are_kept_and_the_latest_is_shown(self):
        response = self.report("W1", taking_new_work=False, capacity=150, queue_days=6, lead_days=2,
                               note="  two machines down ", reported_by=" Ravi ")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["current"],
                         {"taking_new_work": False, "capacity": 150, "queue_days": 6.0, "lead_days": 2})
        self.assertEqual(response.json()["last_report"]["note"], "two machines down")
        self.assertEqual(response.json()["last_report"]["reported_by"], "Ravi")
        self.report("W1", capacity=200)
        shown = self.client.get("/workshops").json()[0]
        self.assertEqual(shown["current"]["capacity"], 200)
        self.assertEqual(shown["recorded"]["capacity"], 300)
        saved = json.loads(workshop_updates.REPORTS_FILE.read_text(encoding="utf-8"))
        self.assertEqual([r["capacity"] for r in saved], [150, 200])

    def test_refusals_save_nothing(self):
        self.assertEqual(self.report("W9").status_code, 404)
        for changes, reason in [({"capacity": 0}, "Pieces per day must be at least 1"),
                                ({"queue_days": -1}, "Days of work already booked cannot be negative"),
                                ({"lead_days": -1}, "Pickup lead time cannot be negative"),
                                ({"reported_by": "  "}, "Enter your name")]:
            with self.subTest(changes=changes):
                response = self.report("W1", **changes)
                self.assertEqual(response.status_code, 422)
                self.assertIn(reason, response.json()["detail"])
        self.assertEqual(self.report("W1", capacity=1.5).status_code, 422)
        self.assertEqual(self.client.put("/workshops/W1", json={"capacity": 100}).status_code, 422)
        # Python's JSON reader accepts NaN and Infinity, but a saved one would break every later
        # GET /workshops and the next run's estimates, so they are refused like any other bad value.
        for value in ("NaN", "Infinity"):
            body = ('{"taking_new_work": true, "capacity": 100, "queue_days": ' + value
                    + ', "lead_days": 1, "reported_by": "Arun"}')
            response = self.client.put("/workshops/W1", content=body, headers={"Content-Type": "application/json"})
            self.assertEqual(response.status_code, 422, value)
        self.assertFalse(workshop_updates.REPORTS_FILE.exists())


class RunFacts(WorkshopTestCase):

    def test_a_run_keeps_the_facts_it_started_with(self):
        self.report("W6", capacity=20, queue_days=3)
        first = self.run_folder("first")
        self.report("W6", capacity=100)
        second = self.run_folder("second")
        workshop_updates.use_run_workshops(first)
        self.assertEqual((WORKSHOPS["W6"].capacity, INITIAL_QUEUES["W6"]), (20, 3.0))
        # The planner's values never change what GET /workshops shows.
        self.assertEqual(self.client.get("/workshops").json()[5]["recorded"]["capacity"], 130)
        workshop_updates.use_run_workshops(second)
        self.assertEqual(WORKSHOPS["W6"].capacity, 100)
        workshop_updates.use_run_workshops(self.work_dir)
        self.assertEqual((WORKSHOPS["W6"].capacity, INITIAL_QUEUES["W6"]), (130, 1.0))

    def test_not_taking_new_work_only_changes_an_active_workshop(self):
        self.report("W1", taking_new_work=False, capacity=300, queue_days=4)
        self.report("W7", taking_new_work=True, capacity=200, queue_days=0, lead_days=2)
        profiles = json.loads((self.run_folder("run") / "workshops.json").read_text(encoding="utf-8"))
        self.assertEqual(profiles["W1"]["status"], workshop_updates.NOT_TAKING_NEW_WORK)
        self.assertEqual(profiles["W7"]["status"], "SUSPENDED")
        self.assertEqual({profiles[w]["status"] for w in ("W2", "W3", "W4", "W5", "W6", "W8")}, {"ACTIVE"})

    def test_the_planner_uses_the_reports(self):
        task = check_task("C1", "ORD-045")  # 150 TOPS pieces in 8 days; W6 wins with the CSV values
        with pinned_settings():
            self.assertEqual(recommend(task, dict(INITIAL_QUEUES), {})["selected_workshop"], "W6")

            self.report("W6", taking_new_work=False)
            workshop_updates.use_run_workshops(self.run_folder("closed"))
            closed = recommend(task, dict(INITIAL_QUEUES), {})
            self.assertNotEqual(closed["selected_workshop"], "W6")
            self.assertIn({"workshop_id": "W6", "reason": "status=NOT_TAKING_NEW_WORK"},
                          closed["rejected_candidates"])
            # The dispatcher decides: choosing W6 anyway is estimated, and the broken rule is recorded.
            _, broken_rule = named_option(task, "W6", dict(INITIAL_QUEUES), {})
            self.assertEqual(broken_rule, "status=NOT_TAKING_NEW_WORK")

            self.report("W6", capacity=65)
            workshop_updates.use_run_workshops(self.run_folder("slower"))
            slower = recommend(task, dict(INITIAL_QUEUES), {})
            self.assertEqual(slower["candidate_metrics"]["W6"]["processing_days"], 150 / 65)


if __name__ == "__main__":
    unittest.main()
