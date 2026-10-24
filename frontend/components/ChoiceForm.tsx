import { INTENTS, type LocalChoice, PREFERENCE_LABELS, PREFERENCES } from "@/lib/choices";
import { days } from "@/lib/format";
import type { DecisionRecord, DispatcherEntry, Task } from "@/lib/types";

export type Workshop = { workshop_id: string; name: string };

type Props = {
  task: Task;
  record: DecisionRecord | null;
  warnings: string[];
  workshops: Workshop[];
  choice: LocalChoice;
  // The dispatcher's saved choices for this task, which Review again can undo.
  saved?: DispatcherEntry;
  onChange: (choice: LocalChoice) => void;
};

// The dispatcher's choices for one task. They stay in the page until Approve all; changing them
// sends nothing and calculates nothing.
export default function ChoiceForm({ task, record, warnings, workshops, choice, saved, onChange }: Props) {
  const shown: Record<string, string> = {
    order_id: task.order_id ?? "",
    quantity: task.quantity?.toString() ?? "",
    due_date: task.due_date ?? "",
    preference: task.preference,
    intent: task.intent,
  };
  // Processing can record intent "unclear", which a correction cannot set. It is listed so the
  // select shows what was recorded; choosing it again stages nothing, as it equals the shown value.
  const intents = INTENTS.includes(task.intent) ? INTENTS : [task.intent, ...INTENTS];
  const facts = choice.facts ?? {};
  const pending = Boolean(
    choice.workshop_id ||
      choice.complete ||
      choice.clear ||
      choice.cancel ||
      Object.keys(facts).length ||
      choice.warnings_checked?.length,
  );
  // An undo or a cancellation is sent alone, and a saved cancellation takes only an undo (the backend's rule).
  const locked = Boolean(choice.clear || choice.cancel || saved?.cancelled);

  // A correction is kept only while it differs from what the review shows. An emptied box stays empty,
  // so it can be retyped; restoreIfEmpty shows the review's value again when the box is left empty.
  function changeFact(name: string, value: string) {
    const next = { ...facts };
    delete next[name];
    if (value !== shown[name]) {
      next[name] = value;
    }
    onChange({ ...choice, facts: next });
  }

  function restoreIfEmpty(name: string, value: string) {
    if (value === "") {
      changeFact(name, shown[name]);
    }
  }

  function changeWarning(rowId: string, checked: boolean) {
    const others = (choice.warnings_checked ?? []).filter((id) => id !== rowId);
    onChange({ ...choice, warnings_checked: checked ? [...others, rowId] : others });
  }

  return (
    <section className={pending ? "choices pending" : "choices"} aria-label={`Your choices for ${task.task_id}`}>
      <h3>Your choices{pending && <span className="unsaved"> (unsaved)</span>}</h3>
      {saved && (
        <label className="check">
          <input
            type="checkbox"
            checked={choice.clear ?? false}
            onChange={(event) => onChange(event.target.checked ? { clear: true } : {})}
          />
          {saved.added ? "Remove this added batch" : saved.cancelled ? "Undo the cancellation" : "Undo my saved choices for this task"}
        </label>
      )}
      {choice.clear && <p className="hint">{undoHint(saved)}</p>}
      {saved?.cancelled && !choice.clear && (
        <p className="hint">This request is cancelled. Undo the cancellation to change it.</p>
      )}
      {!task.added && !saved?.cancelled && (
        <label className="check">
          <input
            type="checkbox"
            checked={choice.cancel ?? false}
            disabled={choice.clear}
            onChange={(event) => onChange(event.target.checked ? { cancel: true } : {})}
          />
          Cancel this request: do not allocate it
        </label>
      )}
      {choice.cancel && (
        <p className="hint">
          Python leaves this request out of the plan, so it reserves no workshop time. Approval keeps it cancelled until
          you undo it.
        </p>
      )}
      <label>
        Workshop
        <select
          value={choice.workshop_id ?? ""}
          disabled={locked}
          onChange={(event) => onChange({ ...choice, workshop_id: event.target.value || undefined })}
        >
          <option value="">{record?.selected_workshop ? `Keep ${record.selected_workshop}, as shown` : "None, as shown"}</option>
          {workshops.map((workshop) => (
            <option key={workshop.workshop_id} value={workshop.workshop_id}>
              {workshop.workshop_id} {workshop.name}
            </option>
          ))}
        </select>
      </label>
      {choice.workshop_id && <p className="hint">{consequence(record, choice.workshop_id)}</p>}

      <fieldset disabled={locked}>
        <legend>Correct the request</legend>
        <label>
          Order
          <input
            value={facts.order_id ?? shown.order_id}
            onChange={(event) => changeFact("order_id", event.target.value)}
            onBlur={(event) => restoreIfEmpty("order_id", event.target.value)}
          />
        </label>
        <label>
          Quantity
          <input
            inputMode="numeric"
            placeholder="orders.csv quantity"
            value={facts.quantity ?? shown.quantity}
            onChange={(event) => changeFact("quantity", event.target.value)}
            onBlur={(event) => restoreIfEmpty("quantity", event.target.value)}
          />
        </label>
        <label>
          Deadline
          <input
            type="date"
            value={facts.due_date ?? shown.due_date}
            onChange={(event) => changeFact("due_date", event.target.value)}
            onBlur={(event) => restoreIfEmpty("due_date", event.target.value)}
          />
        </label>
        <label>
          Preference
          <select value={facts.preference ?? shown.preference} onChange={(event) => changeFact("preference", event.target.value)}>
            {PREFERENCES.map((value) => (
              <option key={value} value={value}>
                {PREFERENCE_LABELS[value] ?? value}
              </option>
            ))}
          </select>
        </label>
        <label>
          Intent
          <select value={facts.intent ?? shown.intent} onChange={(event) => changeFact("intent", event.target.value)}>
            {intents.map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </label>
        {/* A batch the dispatcher added is already complete. */}
        {!task.added && (
          <label className="check">
            <input
              type="checkbox"
              checked={choice.complete ?? false}
              onChange={(event) => onChange({ ...choice, complete: event.target.checked || undefined })}
            />
            The request is complete: plan it with these facts
          </label>
        )}
        {choice.complete && (
          <p className="hint">
            Python plans this request as an allocation and treats its open questions as answered. It needs the order; an
            empty quantity or deadline means the order&apos;s own, from orders.csv.
          </p>
        )}
      </fieldset>

      {warnings.length > 0 && (
        <fieldset disabled={locked}>
          <legend>Unresolved inputs that may change this request</legend>
          {warnings.map((rowId) => (
            <label key={rowId} className="check">
              <input
                type="checkbox"
                checked={choice.warnings_checked?.includes(rowId) ?? false}
                onChange={(event) => changeWarning(rowId, event.target.checked)}
              />
              {rowId} does not change this request
            </label>
          ))}
        </fieldset>
      )}

      <button disabled={!pending} onClick={() => onChange({})}>
        Reset my choices for this task
      </button>
    </section>
  );
}

// What an undo of the dispatcher's saved choices does.
function undoHint(saved?: DispatcherEntry) {
  if (saved?.added) {
    return "Python plans without this batch, so its queue time is freed.";
  }
  if (saved?.cancelled) {
    return "Python plans this request again, as processing recorded it.";
  }
  return "Python plans this task as processing recorded it, without your earlier workshop choice or corrections.";
}

// What the review already records about a chosen workshop. Python calculates the choice itself
// when the plan is approved; the dispatcher's choice is used even when it breaks a rule or is late.
function consequence(record: DecisionRecord | null, workshopId: string) {
  if (workshopId === record?.selected_workshop) {
    return "This is the workshop the review already shows.";
  }
  const metrics = record?.candidate_metrics[workshopId];
  const rejected = record?.rejected_candidates.find((item) => item.workshop_id === workshopId);
  const estimate = metrics
    ? `Python estimated delivery in ${days(metrics.eta_days)} of ${metrics.days_until_due} days. `
    : "Python made no estimate for this workshop. ";
  if (rejected) {
    return `${estimate}It ruled the workshop out (${rejected.reason}). Your choice is used anyway, and the rule it breaks is recorded.`;
  }
  return `${estimate}Your choice is used, and Python calculates it when the plan is approved.`;
}
