# workshop_updates.py: the workshops' own reports of their current state, and the fixed copy of the
# workshop facts that each dispatch run plans with (3 November 2026, DISPATCHER_REVIEW_PLAN.md).
#
# Flow:   PUT /workshops/{workshop_id} -> save_report -> REPORTS_FILE.
#         start_run (pipeline_graph.py) -> freeze_for_run -> <run folder>/workshops.json.
#         plan_allocation and build_dispatcher_plan -> use_run_workshops(run folder) before planning,
#         so every calculation of one run uses the facts from when that run started.
# Reads:  workshops.csv (through allocation_settings_and_data), REPORTS_FILE and a run's workshops.json.
# Writes: REPORTS_FILE (save_report) and a run's workshops.json (freeze_for_run). No model is called.
import json
import math
from dataclasses import asdict, replace
from datetime import datetime, timezone

from order_processing_into_tasks.settings_and_data import OUTPUT_DIR, write_json
from task_allocation_to_workshops.allocation_settings_and_data import INITIAL_QUEUES, WORKSHOPS

# Every report the workshops have saved, oldest first, in the output folder (gitignored).
REPORTS_FILE = OUTPUT_DIR / "workshop_reports.json"
# The values a workshop can report. Each one replaces a workshops.csv value when a run starts.
REPORTED = ("taking_new_work", "capacity", "queue_days", "lead_days")
# The planning status of an active workshop that is not taking new work. The status rule rejects any
# status other than ACTIVE, so automatic selection skips the workshop and names this status.
NOT_TAKING_NEW_WORK = "NOT_TAKING_NEW_WORK"
# The CSV profiles as loaded, kept apart from WORKSHOPS, whose values use_run_workshops replaces.
CSV_WORKSHOPS = {wid: replace(workshop) for wid, workshop in WORKSHOPS.items()}


def read_reports():
    """Return every saved report, oldest first; [] before the first report."""
    if not REPORTS_FILE.exists():
        return []
    return json.loads(REPORTS_FILE.read_text(encoding="utf-8"))


def recorded_values(workshop_id):
    """Return the four reportable values as workshops.csv records them."""
    workshop = CSV_WORKSHOPS[workshop_id]
    return {"taking_new_work": True, "capacity": workshop.capacity, "queue_days": workshop.queue0,
            "lead_days": workshop.lead_days}


def current_values(workshop_id, report):
    """Return the four reportable values as they stand: the report's, or the CSV's before any report."""
    if report is None:
        return recorded_values(workshop_id)
    return {name: report[name] for name in REPORTED}


def describe(workshop_id, report):
    """Return one workshop as GET /workshops shows it: its fixed facts, the recorded and current
    values of what it can report, and its last report (None before any)."""
    workshop = CSV_WORKSHOPS[workshop_id]
    return {"workshop_id": workshop_id, "name": workshop.name, "status": workshop.status,
            "makes": sorted(workshop.makes), "cost_per_piece": workshop.cost,
            "defect_rate": workshop.defect_rate, "max_batch": workshop.max_batch,
            "recorded": recorded_values(workshop_id), "current": current_values(workshop_id, report),
            "last_report": report}


def latest_reports():
    """Return each workshop's most recent report, by workshop ID."""
    return {report["workshop_id"]: report for report in read_reports()}


def workshop_list():
    """Return every workshop, in workshops.csv order, as describe shows it."""
    reports = latest_reports()
    return [describe(workshop_id, reports.get(workshop_id)) for workshop_id in CSV_WORKSHOPS]


def save_report(workshop_id, taking_new_work, capacity, queue_days, lead_days, note, reported_by):
    """Check one workshop's report, save it after the earlier ones and return the workshop as
    describe shows it. It applies from the next run; a run already started keeps its facts.

    Raises ValueError, with a reason the page can show, for a value the calculations cannot use.
    """
    if capacity < 1:
        raise ValueError("Pieces per day must be at least 1. To stop new work, switch off taking new work.")
    # The API reads NaN and Infinity as floats; saved, they would break GET /workshops and the next run.
    if not math.isfinite(queue_days):
        raise ValueError("Days of work already booked must be a number.")
    if queue_days < 0:
        raise ValueError("Days of work already booked cannot be negative.")
    if lead_days < 0:
        raise ValueError("Pickup lead time cannot be negative.")
    if not reported_by.strip():
        raise ValueError("Enter your name before saving.")
    report = {"workshop_id": workshop_id, "taking_new_work": taking_new_work, "capacity": capacity,
              "queue_days": queue_days, "lead_days": lead_days, "note": note.strip(),
              "reported_by": reported_by.strip(), "reported_at": datetime.now(timezone.utc).isoformat()}
    REPORTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    write_json(REPORTS_FILE, read_reports() + [report])
    return describe(workshop_id, report)


def planning_profile(workshop_id, values):
    """Return the workshop's CSV profile with the reported values in place, as the planner uses it.

    Only an ACTIVE workshop can become NOT_TAKING_NEW_WORK: switching taking new work back on never
    lifts a status the factory set, such as SUSPENDED.
    """
    workshop = CSV_WORKSHOPS[workshop_id]
    status = workshop.status
    if status == "ACTIVE" and not values["taking_new_work"]:
        status = NOT_TAKING_NEW_WORK
    return replace(workshop, status=status, capacity=values["capacity"], queue0=values["queue_days"],
                   lead_days=values["lead_days"])


def freeze_for_run(run_dir):
    """Save the workshop facts this run plans with as run_dir/workshops.json: the CSV profiles with
    each workshop's latest report in place. Reports saved later apply to the next run."""
    reports = latest_reports()
    profiles = {}
    for workshop_id in CSV_WORKSHOPS:
        values = current_values(workshop_id, reports.get(workshop_id))
        profiles[workshop_id] = {**asdict(planning_profile(workshop_id, values)),
                                 "makes": sorted(CSV_WORKSHOPS[workshop_id].makes)}
    write_json(run_dir / "workshops.json", profiles)


def use_run_workshops(run_dir):
    """Set the planner's workshop values (WORKSHOPS and INITIAL_QUEUES) to this run's fixed facts.

    A run without workshops.json, such as every run made before 3 November 2026, plans with the CSV
    values, exactly as before. Only the reportable values differ between runs.
    """
    path = run_dir / "workshops.json"
    if path.exists():
        profiles = json.loads(path.read_text(encoding="utf-8"))
    else:
        profiles = {wid: asdict(workshop) for wid, workshop in CSV_WORKSHOPS.items()}
    for workshop_id, workshop in WORKSHOPS.items():
        profile = profiles[workshop_id]
        workshop.status, workshop.capacity = profile["status"], profile["capacity"]
        workshop.queue0, workshop.lead_days = profile["queue0"], profile["lead_days"]
        INITIAL_QUEUES[workshop_id] = profile["queue0"]
