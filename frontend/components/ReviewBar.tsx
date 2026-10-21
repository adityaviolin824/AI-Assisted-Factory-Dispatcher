import { type FormEvent, useState } from "react";
import { decisionText } from "@/lib/choices";
import type { Decision } from "@/lib/types";

type Props = {
  threadId: string | null;
  decisions: Decision[];
  approving: boolean;
  note: string | null;
  onOpen: (threadId: string) => void;
  onApprove: () => void;
};

// Opening a paused review and approving it. The run endpoint cannot say which thread reviews a run,
// so the thread ID is typed in; the page checks that the review belongs to the open run.
export default function ReviewBar({ threadId, decisions, approving, note, onOpen, onApprove }: Props) {
  const [typed, setTyped] = useState("");

  function open(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onOpen(typed.trim());
  }

  return (
    <section className={threadId ? "review-bar reviewing" : "review-bar"} aria-label="Dispatcher review">
      {!threadId && (
        <form className="toolbar" onSubmit={open}>
          <label>
            Paused review thread
            <input value={typed} onChange={(event) => setTyped(event.target.value)} placeholder="Thread ID from the run" />
          </label>
          <button disabled={!typed.trim()}>Open review</button>
          <span className="hint">Without a review the plan is read-only.</span>
        </form>
      )}

      {threadId && (
        <>
          <p>
            <strong>Reviewing thread {threadId}.</strong>{" "}
            {decisions.length === 0
              ? "No choices yet. Choose a row to change its workshop or correct its request."
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
            <button className="primary" disabled={approving} onClick={onApprove}>
              {approving ? "Approving..." : "Approve all"}
            </button>
            <button disabled>Reallocate</button>
            <button disabled>Review again after reallocation</button>
          </div>
          <p className="hint">
            {decisions.length > 0
              ? "Approve all sends these choices together. Python plans once with them, other tasks may move around them, and the result is saved at once. Nothing has been sent yet."
              : "Approve all saves the plan exactly as shown. Reallocation is not built yet."}
          </p>
        </>
      )}

      {note && <p className="notice">{note}</p>}
    </section>
  );
}
