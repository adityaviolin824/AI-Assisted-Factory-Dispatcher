import { type FormEvent, useState } from "react";
import { decisionText } from "@/lib/choices";
import type { Decision } from "@/lib/types";

type Props = {
  threadId: string | null;
  // Review again: the run's approved plan is open for new choices, with no thread.
  savedPlan: boolean;
  decisions: Decision[];
  approving: boolean;
  previewing: boolean;
  note: string | null;
  onOpen: (threadId: string) => void;
  onApprove: () => void;
  onPreview: () => void;
  onClose: () => void;
};

// Opening a paused review, checking the choices and approving them. The run endpoint cannot say which
// thread reviews a run, so the thread ID is typed in; the page checks that the review belongs to the open run.
// Review again uses the same bar on an approved plan; Approve all then saves a new version.
export default function ReviewBar({
  threadId,
  savedPlan,
  decisions,
  approving,
  previewing,
  note,
  onOpen,
  onApprove,
  onPreview,
  onClose,
}: Props) {
  const [typed, setTyped] = useState("");
  const reviewing = Boolean(threadId) || savedPlan;

  function open(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onOpen(typed.trim());
  }

  let hint = "Approve all saves the plan exactly as shown.";
  if (decisions.length > 0) {
    hint =
      "Approve all sends these choices together. Python plans once with them, other tasks may move around them, and the result is saved at once. Check workshop options shows that result first without saving it. Nothing has been saved yet.";
  } else if (savedPlan) {
    hint = "Approve all saves a new version once you have made a choice. Nothing has been saved yet.";
  }

  return (
    <section className={reviewing ? "review-bar reviewing" : "review-bar"} aria-label="Dispatcher review">
      {!reviewing && (
        <form className="toolbar" onSubmit={open}>
          <label>
            Paused review thread
            <input value={typed} onChange={(event) => setTyped(event.target.value)} placeholder="Thread ID from the run" />
          </label>
          <button disabled={!typed.trim()}>Open review</button>
          <span className="hint">Without a review the plan is read-only.</span>
        </form>
      )}

      {reviewing && (
        <>
          <p>
            <strong>{savedPlan ? "Reviewing the approved plan again." : `Reviewing thread ${threadId}.`}</strong>{" "}
            {decisions.length === 0
              ? `No choices yet. Choose a row to change its workshop or correct its request${savedPlan ? ", undo a saved choice" : ""}, or add a batch.`
              : `${decisions.length} unsaved ${decisions.length === 1 ? "choice" : "choices"}, kept in this page only: closing it discards them.`}
          </p>
          {decisions.length > 0 && (
            <ul className="decision-list" aria-label="What Approve all would send">
              {decisions.map((decision, index) => (
                <li key={index}>{decisionText(decision)}</li>
              ))}
            </ul>
          )}
          <div className="toolbar">
            <button
              className="primary"
              disabled={approving || previewing || (savedPlan && decisions.length === 0)}
              onClick={onApprove}
            >
              {approving ? "Approving..." : "Approve all"}
            </button>
            <button disabled={decisions.length === 0 || approving || previewing} onClick={onPreview}>
              {previewing ? "Checking..." : "Check workshop options"}
            </button>
            {savedPlan && (
              <button disabled={approving} onClick={onClose}>
                Close without saving
              </button>
            )}
          </div>
          <p className="hint">{hint}</p>
        </>
      )}

      {note && <p className="notice">{note}</p>}
    </section>
  );
}
