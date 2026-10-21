"use client";

import { useEffect, useRef, useState } from "react";
import QueueTable from "@/components/QueueTable";
import RunPicker from "@/components/RunPicker";
import TaskDetails from "@/components/TaskDetails";
import TaskTable from "@/components/TaskTable";
import { errorText, listRuns, readRun } from "@/lib/api";
import type { RunDetails, RunSummary } from "@/lib/types";

// The dispatcher console. A saved run shows its approved dispatcher plan when there is one,
// otherwise the plan made before the dispatcher's review.
export default function DispatcherPage() {
  const [runs, setRuns] = useState<RunSummary[] | null>(null);
  const [runId, setRunId] = useState("");
  const [details, setDetails] = useState<RunDetails | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  // The run request in progress, aborted when another run is opened so a slow answer cannot replace it.
  const runRequest = useRef<AbortController | null>(null);

  // The run named in the address (/dispatcher?run=<id>) opens straight away, as when Chat links here.
  useEffect(() => {
    listRuns()
      .then(setRuns)
      .catch((caught) => setError(errorText(caught)));
    const runInUrl = new URLSearchParams(window.location.search).get("run");
    if (runInUrl) {
      openRun(runInUrl);
    }
  }, []);

  function openRun(id: string) {
    runRequest.current?.abort();
    // Keep the open run in the address, so a refresh or a shared link shows the same run.
    window.history.replaceState(null, "", id ? `?run=${encodeURIComponent(id)}` : "/dispatcher");
    setRunId(id);
    setDetails(null);
    setSelectedId(null);
    setError(null);
    if (!id) {
      return;
    }
    const controller = new AbortController();
    runRequest.current = controller;
    readRun(id, controller.signal)
      .then(setDetails)
      .catch((caught) => {
        if (!controller.signal.aborted) {
          setError(errorText(caught));
        }
      });
  }

  function refresh() {
    listRuns()
      .then(setRuns)
      .catch((caught) => setError(errorText(caught)));
    openRun(runId);
  }

  const shown = details?.dispatcher_plan ?? details?.plan ?? null;
  const selectedRow = shown?.summary_rows.find((row) => row.id === selectedId);

  return (
    <>
      <div className="page-head">
        <h1>Dispatcher</h1>
        <div className="toolbar">
          {runs && <RunPicker runs={runs} runId={runId} onChange={openRun} />}
          <button onClick={refresh}>Refresh</button>
        </div>
      </div>
      <p className="muted lede">
        The AI only read the chat. Python calculated every date, queue, cost and ranking shown here. Approving a
        plan saves it as JSON files; nothing is sent to a workshop.
      </p>

      {runs?.length === 0 && <p className="muted">The backend has no saved runs.</p>}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {runId && !details && !error && <p className="muted">Loading {runId}...</p>}
      {details && !shown && <p className="notice">Run {runId} has no plan: processing did not save plan.json.</p>}

      {details && shown && (
        <>
          <p className={details.dispatcher_plan ? "run-state final" : "run-state"}>
            <strong>{details.dispatcher_plan ? "Approved dispatcher plan" : "Plan before the dispatcher's review"}</strong>{" "}
            <span className="muted">planned from {shown.dispatch_date}</span>
          </p>
          {!shown.processing_complete && (
            <p className="notice">
              Processing did not finish, so this plan is a partial preview: inputs without an outcome are listed as
              Not processed, and the queues and duplicate-order checks may change.
            </p>
          )}
          {!shown.review_warnings && (
            <p className="notice">
              This plan was made before review warnings were recorded (15 October 2026), so it does not mark which
              suggestions an unresolved message may change.
            </p>
          )}
          <div className="workspace">
            <TaskTable plan={shown} selectedId={selectedId} onSelect={setSelectedId} />
            {selectedRow ? (
              <TaskDetails plan={shown} row={selectedRow} onSelect={setSelectedId} />
            ) : (
              <p className="muted empty-details">Choose a row to see its messages, facts and workshop comparison.</p>
            )}
          </div>
          <QueueTable plan={shown} profiles={details.plan?.workshop_profiles} />
        </>
      )}
    </>
  );
}
