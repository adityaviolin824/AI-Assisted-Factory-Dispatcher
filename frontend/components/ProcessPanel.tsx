import Link from "next/link";
import { useEffect, useState } from "react";
import { createSnapshot, errorText, listSnapshots, processSnapshot, readSnapshot } from "@/lib/api";
import { chatDateTime, count } from "@/lib/format";
import type { Snapshot } from "@/lib/types";

type Props = { messageCount: number };

// The start-run path. "Process conversation" first captures the chat as a fixed snapshot and asks
// for confirmation, because processing calls paid AI models; "Start processing" then runs the
// pipeline on exactly that snapshot. Messages sent later go into the next snapshot.
export default function ProcessPanel({ messageCount }: Props) {
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

  // One primary button at a time: "Start processing" takes over while a snapshot waits for it.
  const waitingToStart = current?.processing === "not_started";

  return (
    <section className="process-panel" aria-label="Process conversation">
      <h2>Process conversation</h2>
      <p className="muted">
        The AI reads the messages into requests, then Python checks every workshop and makes a plan for the
        dispatcher.
      </p>
      <button
        className={waitingToStart ? undefined : "primary"}
        disabled={busy || messageCount === 0 || current?.processing === "running"}
        onClick={capture}
      >
        Process conversation
      </button>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {current && <SnapshotState snapshot={current} busy={busy} onStart={() => start(current.snapshot_id)} />}

      {earlier.length > 0 && (
        <>
          <h3>Earlier runs from this chat</h3>
          <ul className="run-list">
            {earlier.map((snapshot) => (
              <li key={snapshot.snapshot_id}>
                <Link href={`/dispatcher?run=${encodeURIComponent(snapshot.run_id ?? "")}`}>{snapshot.run_id}</Link>{" "}
                <span className="muted">{count(snapshot.message_count, "message")}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

// Dispatcher opens the run and, when the pipeline paused it for review, that review as well.
function dispatcherLink(runId: string, threadId: string | null) {
  const thread = threadId ? `&thread=${encodeURIComponent(threadId)}` : "";
  return `/dispatcher?run=${encodeURIComponent(runId)}${thread}`;
}

type StateProps = { snapshot: Snapshot; busy: boolean; onStart: () => void };

// One snapshot: what it holds, and where its processing has got to.
function SnapshotState({ snapshot, busy, onStart }: StateProps) {
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
            Start processing
          </button>
        </>
      )}
      {snapshot.processing === "running" && (
        <p role="status">Processing. This takes several minutes; you can keep chatting meanwhile.</p>
      )}
      {/* The thread ID is a long random code, so it is not shown: the link below carries it. */}
      {snapshot.processing === "finished" && snapshot.run_id && (
        <p role="status">
          Processed as run {snapshot.run_id}
          {snapshot.thread_id && ", ready for the dispatcher's review"}.{" "}
          <Link className="open-run" href={dispatcherLink(snapshot.run_id, snapshot.thread_id)}>
            Open in Dispatcher
          </Link>
        </p>
      )}
      {snapshot.processing === "failed" && (
        <p className="error" role="alert">
          Processing failed: {snapshot.error ?? "the backend gave no reason."} Process the conversation again to
          retry.
        </p>
      )}
    </div>
  );
}
