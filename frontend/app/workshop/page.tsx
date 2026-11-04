"use client";

import { type FormEvent, useEffect, useState } from "react";
import { errorText, listWorkshops, reportWorkshop } from "@/lib/api";
import { chatDateTime, percent } from "@/lib/format";
import { useIdentity } from "@/lib/identity";
import type { Workshop, WorkshopReport } from "@/lib/types";

// The form's values. Number fields keep the text typed, so a field can be cleared while editing.
type Form = { takingNewWork: boolean; capacity: string; queueDays: string; leadDays: string; note: string };

function formFrom(workshop: Workshop): Form {
  const { current } = workshop;
  return {
    takingNewWork: current.taking_new_work,
    capacity: String(current.capacity),
    queueDays: String(current.queue_days),
    leadDays: String(current.lead_days),
    note: workshop.last_report?.note ?? "",
  };
}

// One workshop reports how it stands today. The values replace the factory's records (workshops.csv)
// from the dispatcher's next run on; a run already started keeps the numbers it started with. Python
// checks the values and does every calculation; this page only sends them.
export default function WorkshopPage() {
  const identity = useIdentity();
  const workshopId = identity?.workshopId;
  const [workshop, setWorkshop] = useState<Workshop | null>(null);
  const [form, setForm] = useState<Form | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState<WorkshopReport | null>(null);

  useEffect(() => {
    listWorkshops().then(
      (list) => {
        const own = list.find((option) => option.workshop_id === workshopId);
        if (!own) {
          setError("Your workshop was not found. Use Switch user and choose it again.");
          return;
        }
        setWorkshop(own);
        setForm(formFrom(own));
      },
      (caught) => setError(`Could not load your workshop: ${errorText(caught)}`),
    );
  }, [workshopId]);

  // Any edit after a save makes the "Saved" line out of date.
  function update(changes: Partial<Form>) {
    setForm((current) => (current ? { ...current, ...changes } : current));
    setSaved(null);
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!form || !workshop || !identity) {
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const updated = await reportWorkshop(workshop.workshop_id, {
        taking_new_work: form.takingNewWork,
        capacity: Number(form.capacity),
        queue_days: Number(form.queueDays),
        lead_days: Number(form.leadDays),
        note: form.note,
        reported_by: identity.name,
      });
      setWorkshop(updated);
      setSaved(updated.last_report);
    } catch (caught) {
      setError(`Could not save: ${errorText(caught)}`);
    } finally {
      setSaving(false);
    }
  }

  if (!workshop || !form) {
    return (
      <div className="workshop-page">
        <h1>{identity?.workshopName ?? "Workshop"}</h1>
        {error ? (
          <p className="error" role="alert">
            {error}
          </p>
        ) : (
          <p className="muted">Loading your workshop...</p>
        )}
      </div>
    );
  }

  const { recorded } = workshop;
  const suspended = workshop.status !== "ACTIVE";
  return (
    <div className="workshop-page">
      <h1>
        {workshop.name} <span className="muted">{workshop.workshop_id}</span>
      </h1>
      <p className="muted">
        Tell the dispatcher how your workshop stands today. What you save replaces the factory&apos;s records from the
        dispatcher&apos;s next run; a run already started keeps its numbers.
      </p>

      <section aria-label="Set by the factory">
        <h2>Set by the factory</h2>
        <dl className="facts">
          <dt>Makes</dt>
          <dd>{workshop.makes.join(", ")}</dd>
          <dt>Status</dt>
          <dd>{workshop.status}</dd>
          <dt>Price per piece</dt>
          <dd>{workshop.cost_per_piece.toFixed(2)}</dd>
          <dt>Defect rate</dt>
          <dd>{percent(workshop.defect_rate)}</dd>
          <dt>Largest batch</dt>
          <dd>{workshop.max_batch ? `${workshop.max_batch} pieces` : "No limit"}</dd>
        </dl>
        {suspended && (
          <p className="notice">
            The factory has set this workshop to {workshop.status}, so automatic planning skips it whatever you report.
            The dispatcher can still choose it.
          </p>
        )}
      </section>

      <form onSubmit={save} aria-label="Your report">
        <h2>Your report</h2>
        <label className="switch-field">
          <input
            type="checkbox"
            checked={form.takingNewWork}
            onChange={(event) => update({ takingNewWork: event.target.checked })}
          />
          Taking new work
          <span className="hint">Switch off to stop new automatic allocations to your workshop.</span>
        </label>
        <label className="report-field">
          Pieces per day
          <input
            type="number"
            min={1}
            step={1}
            required
            value={form.capacity}
            onChange={(event) => update({ capacity: event.target.value })}
          />
          <span className="hint">Factory record: {recorded.capacity}. Python works out each batch&apos;s processing time from this.</span>
        </label>
        <label className="report-field">
          Days of work already booked
          <input
            type="number"
            min={0}
            step={0.5}
            required
            value={form.queueDays}
            onChange={(event) => update({ queueDays: event.target.value })}
          />
          <span className="hint">Work you already have, not counting the dispatcher&apos;s plan. Factory record: {recorded.queue_days}.</span>
        </label>
        <label className="report-field">
          Pickup lead time (days)
          <input
            type="number"
            min={0}
            step={1}
            required
            value={form.leadDays}
            onChange={(event) => update({ leadDays: event.target.value })}
          />
          <span className="hint">Factory record: {recorded.lead_days}.</span>
        </label>
        <label className="report-field">
          Note to the dispatcher (optional)
          <textarea rows={2} value={form.note} onChange={(event) => update({ note: event.target.value })} />
        </label>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        {saved && (
          <p className="saved-note" role="status">
            Saved {chatDateTime(saved.reported_at)}. It applies from the dispatcher&apos;s next run.
          </p>
        )}
        {!saved && workshop.last_report && (
          <p className="hint">
            Last report by {workshop.last_report.reported_by}, {chatDateTime(workshop.last_report.reported_at)}.
          </p>
        )}
        <button type="submit" className="primary" disabled={saving}>
          {saving ? "Saving..." : "Save"}
        </button>
      </form>
    </div>
  );
}
