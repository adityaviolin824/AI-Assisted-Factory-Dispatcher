import { useEffect, useState } from "react";
import { errorText, listWorkshops } from "@/lib/api";
import { chatDateTime } from "@/lib/format";
import type { Workshop } from "@/lib/types";

// What changed in one workshop's report, against the factory's records, in plain words.
function changes(workshop: Workshop) {
  const { recorded, current } = workshop;
  const parts = [];
  if (recorded.taking_new_work && !current.taking_new_work) {
    parts.push("not taking new work");
  }
  if (current.capacity !== recorded.capacity) {
    parts.push(`pieces per day from ${recorded.capacity} to ${current.capacity}`);
  }
  if (current.queue_days !== recorded.queue_days) {
    parts.push(`days of work booked from ${recorded.queue_days} to ${current.queue_days}`);
  }
  if (current.lead_days !== recorded.lead_days) {
    parts.push(`pickup lead time from ${recorded.lead_days} to ${current.lead_days} days`);
  }
  return parts;
}

function readError(caught: unknown) {
  return `Could not read the workshop updates: ${errorText(caught)}`;
}

// The workshops whose own report differs from the factory's records or carries a note. A report applies
// from the next dispatch run, so the run on screen keeps the numbers it started with. Read when the page
// opens and on "Check for new reports" (named apart from the run toolbar's Refresh).
export default function WorkshopUpdates() {
  const [workshops, setWorkshops] = useState<Workshop[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listWorkshops().then(setWorkshops, (caught) => setError(readError(caught)));
  }, []);

  function refresh() {
    setError(null);
    listWorkshops().then(setWorkshops, (caught) => setError(readError(caught)));
  }

  // Each reported workshop with its last report and what changed.
  const reported = (workshops ?? []).flatMap((workshop) => {
    const report = workshop.last_report;
    const changed = changes(workshop);
    return report && (changed.length > 0 || report.note) ? [{ workshop, report, changed }] : [];
  });

  return (
    <section className="workshop-updates" aria-label="Workshop updates">
      <div className="workshop-updates-head">
        <h2>Workshop updates</h2>
        <button type="button" className="link-button" onClick={refresh}>
          Check for new reports
        </button>
      </div>
      <p className="hint">
        Reported by the workshops themselves. A report applies from the next dispatch run; a run already started keeps
        its numbers.
      </p>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {workshops && reported.length === 0 && <p className="muted">No workshop has reported a change.</p>}
      {reported.length > 0 && (
        <ul>
          {reported.map(({ workshop, report, changed }) => (
            <li key={workshop.workshop_id}>
              <strong>
                {workshop.workshop_id} {workshop.name}
              </strong>
              {changed.length > 0 && `: ${changed.join("; ")}`}.{" "}
              <span className="muted">
                Reported by {report.reported_by}, {chatDateTime(report.reported_at)}.
              </span>{" "}
              {report.note && <q>{report.note}</q>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
