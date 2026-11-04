# workshops.py: the routes of the Workshop page (3 November 2026, DISPATCHER_REVIEW_PLAN.md).
#
# GET /workshops lists the eight workshops with their recorded (CSV) values, current values and last
# report. PUT /workshops/{workshop_id} saves one workshop's report. The next dispatch run plans with
# it; a run already started keeps the workshop facts it started with. No route calls a model.
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from task_allocation_to_workshops import workshop_updates

router = APIRouter(tags=["workshops"])


class WorkshopReport(BaseModel):
    """One report from the Workshop page: the four values that replace the CSV's, a note and who sent it."""
    taking_new_work: bool
    capacity: int
    queue_days: float
    lead_days: int
    note: str = ""
    reported_by: str


@router.get("/workshops")
def list_workshops():
    """Return every workshop with its recorded values, current values and last report."""
    return workshop_updates.workshop_list()


@router.put("/workshops/{workshop_id}")
def report_workshop(workshop_id: str, report: WorkshopReport):
    """Save one workshop's report and return that workshop as GET /workshops shows it.

    An unknown workshop is refused with 404. A value the calculations cannot use (pieces per day below 1,
    negative days) or an empty name is refused with 422 and the reason; nothing is saved then.
    """
    if workshop_id not in workshop_updates.CSV_WORKSHOPS:
        raise HTTPException(status_code=404, detail=f"No workshop {workshop_id}.")
    try:
        return workshop_updates.save_report(workshop_id, **report.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
