import { useEffect, useState } from "react";
import { createSnapshot, errorText, listSnapshots, processSnapshot, readSnapshot } from "@/lib/api";
import { chatDateTime, count } from "@/lib/format";
import type { Snapshot } from "@/lib/types";

// onOpen opens a processed run on the Dispatcher page, with its paused review when there is one.
type Props = { onOpen: (runId: string, threadId: string | null) => void };

// The start-run path, in two steps, on the Dispatcher page. "Prepare chat for dispatch" captures the chat
// as a fixed snapshot, with no AI call, and asks for confirmation, because processing calls paid AI models;
// "Start dispatch workflow" then runs the pipeline on exactly that snapshot. Messages sent later go into the
// next snapshot. An empty chat is refused by the backend, and its reason is shown.
export default function ProcessPanel({ onOpen }: Props) {
  // Newest first: the first snapshot is the current one, the others are earlier runs.
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const current = snapshots[0] ?? null;
  const earlier = snapshots.slice(1).filter((snapshot) => snapshot.run_id);

  // Read the snapshots on opening, so a run in progress is not lost after a refresh.
  useEffect(() => {
    listSnapshots()
      .then(setSnapshots)
      .catch((caught) => setError(errorText(caught)));
  }, []);

  // While the pipeline runs, read the current snapshot again every five seconds. A failed read, such
  // as while the API server reloads, is shown, and the reads go on until processing ends.
  const runningId = current?.processing === "running" ? current.snapshot_id : null;
  useEffect(() => {
    if (!runningId) {
      return;
    }
    const timer = setInterval(() => {
      readSnapshot(runningId)
        .then((updated) => {
          setSnapshots((list) => [updated, ...list.slice(1)]);
          setError(null);
        })
        .catch((caught) => setError(errorText(caught)));
    }, 5000);
    return () => clearInterval(timer);
  }, [runningId]);

  async function capture() {
    setBusy(true);
    setError(null);
    try {
      const created = await createSnapshot();
      setSnapshots((list) => [created, ...list]);
    } catch (caught) {
      setError(errorText(caught));
    } finally {
      setBusy(false);
    }
  }

  async function start(snapshotId: string) {
    setBusy(true);
    setError(null);
    try {
      const started = await processSnapshot(snapshotId);
      setSnapshots((list) => [started, ...list.slice(1)]);
    } catch (caught) {
      setError(errorText(caught));
    } finally {
      setBusy(false);
    }
  }

  // One primary button at a time: "Start dispatch workflow" takes over while a snapshot waits for it.
  const waitingToStart = current?.processing === "not_started";

  return (
    <section className="process-panel" aria-label="Dispatch workflow">
      <h2>Dispatch workflow</h2>
      <p className="muted">
        First prepare a fixed copy of the chat; this makes no AI call. Then start the workflow: the AI reads the
        messages into requests, and Python checks every workshop and makes a plan for you to review.
      </p>
      <button
        className={waitingToStart ? undefined : "primary"}
        disabled={busy || current?.processing === "running"}
        onClick={capture}
      >
        Prepare chat for dispatch
      </button>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {current && (
        <SnapshotState
          snapshot={current}
          busy={busy}
          onStart={() => start(current.snapshot_id)}
          onOpen={onOpen}
        />
      )}

      {earlier.length > 0 && (
        <>
          <h3>Earlier runs from this chat</h3>
          <ul className="run-list">
            {earlier.map((snapshot) => (
              <li key={snapshot.snapshot_id}>
                <button className="link-button" onClick={() => onOpen(snapshot.run_id ?? "", null)}>
                  {snapshot.run_id}
                </button>{" "}
                <span className="muted">{count(snapshot.message_count, "message")}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

type StateProps = Props & { snapshot: Snapshot; busy: boolean; onStart: () => void };

// One snapshot: what it holds, and where its processing has got to.
function SnapshotState({ snapshot, busy, onStart, onOpen }: StateProps) {
  const first = snapshot.lines[0]?.request_label;
  const last = snapshot.lines.at(-1)?.request_label;
  return (
    <div className={snapshot.processing === "finished" ? "snapshot final" : "snapshot"}>
      <p>
        <strong>Snapshot of {count(snapshot.message_count, "message")}</strong>, {first} to {last}
        <br />
        <span className="muted">Captured {chatDateTime(snapshot.exported_at_utc)}</span>
      </p>
      <details>
        <summary>Text the AI will read</summary>
        <pre>{snapshot.text}</pre>
        <a download="dispatch_requests.txt" href={`data:text/plain;charset=utf-8,${encodeURIComponent(snapshot.text)}`}>
          Download dispatch_requests.txt
        </a>
      </details>

      {snapshot.processing === "not_started" && (
        <>
          <p>Processing sends these messages to paid AI models and takes several minutes.</p>
          <button className="primary" disabled={busy} onClick={onStart}>
            Start dispatch workflow
          </button>
        </>
      )}
      {snapshot.processing === "running" && (
        <p role="status">Processing. This takes several minutes; this panel updates by itself.</p>
      )}
      {/* The thread ID is a long random code, so it is not shown: the button below opens it. */}
      {snapshot.processing === "finished" && snapshot.run_id && (
        <p role="status">
          Processed as run {snapshot.run_id}
          {snapshot.thread_id && ", ready for your review"}.{" "}
          <button className="link-button open-run" onClick={() => onOpen(snapshot.run_id ?? "", snapshot.thread_id)}>
            Open this run
          </button>
        </p>
      )}
      {snapshot.processing === "failed" && (
        <p className="error" role="alert">
          Processing failed: {snapshot.error ?? "the backend gave no reason."} Prepare the chat again and start the
          workflow to retry.
        </p>
      )}
    </div>
  );
}
