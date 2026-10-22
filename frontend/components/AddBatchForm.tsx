import { type FormEvent, useState } from "react";
import { type AddedBatch, decisionText, PREFERENCE_LABELS, PREFERENCES } from "@/lib/choices";
import type { Workshop } from "./ChoiceForm";

type Props = { added: AddedBatch[]; workshops: Workshop[]; onChange: (added: AddedBatch[]) => void };

// Batches that no row covers: one part of a split, a request processing missed, or a message that
// never became a task. Like every choice, they stay in this page until Approve all, when Python names
// and plans each one; adding, changing or removing a batch sends nothing. A staged batch's workshop
// can be changed in its list entry, for example after Check workshop options compares its workshops.
export default function AddBatchForm({ added, workshops, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const [facts, setFacts] = useState<Record<string, string>>({});
  const [workshopId, setWorkshopId] = useState("");

  // An empty field is left out, so Python uses the order's own value from orders.csv.
  function changeFact(name: string, value: string) {
    const next = { ...facts };
    delete next[name];
    if (value) {
      next[name] = value;
    }
    setFacts(next);
  }

  function close() {
    setFacts({});
    setWorkshopId("");
    setOpen(false);
  }

  function add(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onChange([...added, batchFor(facts, workshopId)]);
    close();
  }

  function changeWorkshop(index: number, value: string) {
    onChange(added.map((batch, other) => (other === index ? batchFor(batch.facts, value) : batch)));
  }

  return (
    <section className={added.length ? "choices pending" : "choices"} aria-label="Added batches">
      <h3>Added batches{added.length > 0 && <span className="unsaved"> (unsaved)</span>}</h3>
      {added.length > 0 && (
        <ul className="decision-list">
          {added.map((batch, index) => (
            <li key={index}>
              {decisionText({ decision: "add_batch", facts: batch.facts })}{" "}
              <select
                aria-label={`Workshop for the new batch of ${batch.facts.order_id}`}
                value={batch.workshop_id ?? ""}
                onChange={(event) => changeWorkshop(index, event.target.value)}
              >
                <WorkshopOptions workshops={workshops} />
              </select>{" "}
              <button className="link-button" onClick={() => onChange(added.filter((_, other) => other !== index))}>
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
      {open ? (
        <form onSubmit={add}>
          <fieldset>
            <legend>New batch</legend>
            <label>
              Order
              <input
                required
                placeholder="Order ID in orders.csv"
                value={facts.order_id ?? ""}
                onChange={(event) => changeFact("order_id", event.target.value)}
              />
            </label>
            <label>
              Quantity
              <input
                inputMode="numeric"
                placeholder="orders.csv quantity"
                value={facts.quantity ?? ""}
                onChange={(event) => changeFact("quantity", event.target.value)}
              />
            </label>
            <label>
              Deadline
              <input type="date" value={facts.due_date ?? ""} onChange={(event) => changeFact("due_date", event.target.value)} />
            </label>
            <label>
              Preference
              <select
                value={facts.preference ?? "none"}
                onChange={(event) => changeFact("preference", event.target.value === "none" ? "" : event.target.value)}
              >
                {PREFERENCES.map((value) => (
                  <option key={value} value={value}>
                    {PREFERENCE_LABELS[value] ?? value}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Workshop
              <select value={workshopId} onChange={(event) => setWorkshopId(event.target.value)}>
                <WorkshopOptions workshops={workshops} />
              </select>
            </label>
          </fieldset>
          <p className="hint">
            Python plans the batch like any other when the plan is approved. An empty quantity or deadline means the
            order&apos;s own, from orders.csv. Another batch of the same order blocks nothing; its reason names it.
          </p>
          <div className="toolbar">
            <button disabled={!facts.order_id}>Add to my choices</button>
            <button type="button" onClick={close}>
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <button onClick={() => setOpen(true)}>Add a batch</button>
      )}
    </section>
  );
}

// An empty workshop is left out, so Python suggests one.
function batchFor(facts: Record<string, string>, workshopId: string): AddedBatch {
  return workshopId ? { facts, workshop_id: workshopId } : { facts };
}

function WorkshopOptions({ workshops }: { workshops: Workshop[] }) {
  return (
    <>
      <option value="">Python suggests one</option>
      {workshops.map((workshop) => (
        <option key={workshop.workshop_id} value={workshop.workshop_id}>
          {workshop.workshop_id} {workshop.name}
        </option>
      ))}
    </>
  );
}
