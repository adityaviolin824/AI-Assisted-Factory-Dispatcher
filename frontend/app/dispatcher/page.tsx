"use client";

import { useEffect, useRef, useState } from "react";
import ChangesTable from "@/components/ChangesTable";
import ChoiceForm from "@/components/ChoiceForm";
import QueueTable from "@/components/QueueTable";
import ReviewBar from "@/components/ReviewBar";
import RunPicker from "@/components/RunPicker";
import TaskDetails from "@/components/TaskDetails";
import TaskTable from "@/components/TaskTable";
import { errorText, finalize, listRuns, readReview, readRun, sendAnswer } from "@/lib/api";
import { type Choices, decisionsFrom, withChoice } from "@/lib/choices";
import { decisionFor, taskFor } from "@/lib/plan";
import type { Review, RunDetails, RunSummary } from "@/lib/types";

// The dispatcher console. A saved run shows its approved dispatcher plan when there is one,
// otherwise the plan made before the dispatcher's review. Opening a paused review shows its draft
// and lets the dispatcher make choices, which stay in this page until Approve all.
export default function DispatcherPage() {
  const [runs, setRuns] = useState<RunSummary[] | null>(null);
  const [runId, setRunId] = useState("");
  const [details, setDetails] = useState<RunDetails | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [review, setReview] = useState<Review | null>(null);
  const [choices, setChoices] = useState<Choices>({});
  const [approving, setApproving] = useState(false);
  const [reviewNote, setReviewNote] = useState<string | null>(null);
  // The open run's reads (its plan, then any review), aborted when another run is opened so a slow
  // answer cannot replace it.
  const runRequest = useRef<AbortController | null>(null);
  const desk = useRef<HTMLDivElement>(null);
  // What Approve all would send: the tray lists it, and discarding asks about it.
  const decisions = decisionsFrom(choices);

  // Below 1100px (the breakpoint in globals.css) the details come after the whole worklist,
  // so a chosen row's details are scrolled into view. On wide screens they are always in view.
  useEffect(() => {
    if (selectedId && window.matchMedia("(max-width: 1100px)").matches) {
      desk.current?.scrollIntoView();
    }
  }, [selectedId]);

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

  // Opening a run also closes any review, with its unsaved choices: they belong to that review.
  function openRun(id: string) {
    runRequest.current?.abort();
    // Keep the open run in the address, so a refresh or a shared link shows the same run.
    window.history.replaceState(null, "", id ? `?run=${encodeURIComponent(id)}` : "/dispatcher");
    setRunId(id);
    setDetails(null);
    setSelectedId(null);
    setError(null);
    setThreadId(null);
    setReview(null);
    setChoices({});
    setReviewNote(null);
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

  // Refresh and choosing another run close the review, so unsaved choices are only discarded on request.
  function discardConfirmed() {
    const count = decisions.length;
    return count === 0 || window.confirm(`Discard your ${count} unsaved ${count === 1 ? "choice" : "choices"}?`);
  }

  function changeRun(id: string) {
    if (discardConfirmed()) {
      openRun(id);
    }
  }

  function refresh() {
    if (!discardConfirmed()) {
      return;
    }
    listRuns()
      .then(setRuns)
      .catch((caught) => setError(errorText(caught)));
    openRun(runId);
  }

  // A review is used only when it belongs to the open run (review.source_run).
  function openReview(id: string) {
    setReviewNote(null);
    const signal = runRequest.current?.signal;
    readReview(id, signal)
      .then((envelope) => {
        if (envelope.review.source_run !== runId) {
          setReviewNote(`Thread ${id} reviews run ${envelope.review.source_run}, not the open run ${runId}.`);
          return;
        }
        setThreadId(id);
        setReview(envelope.review);
        if (envelope.refused) {
          setReviewNote(`The backend refused the last answer to this review: ${envelope.refused}`);
        }
      })
      .catch((caught) => {
        if (!signal?.aborted) {
          setReviewNote(errorText(caught));
        }
      });
  }

  // Approve all, in one request: with no choices the review is saved exactly as shown; with choices
  // the backend applies them together, plans once and saves, or refuses them all and the choices stay.
  // A refusal can come back with HTTP 200, so success is read from status, never from the status code.
  async function approve() {
    if (!threadId) {
      return;
    }
    setApproving(true);
    setReviewNote(null);
    try {
      const envelope = decisions.length
        ? await finalize(threadId, decisions)
        : await sendAnswer(threadId, { decisions: [], then: "approve_all" });
      if (envelope.status === "finished") {
        openRun(runId);
        setReviewNote("Approved and saved. The table now shows the approved dispatcher plan.");
      } else {
        setReview(envelope.review);
        setReviewNote(`Not approved: nothing was saved. ${envelope.refused ?? "The review is still waiting."}`);
      }
    } catch (caught) {
      // The outcome is unknown, so the review is closed: opening it again reads what was saved.
      setThreadId(null);
      setReview(null);
      setReviewNote(`The approval may not have been saved: ${errorText(caught)} Open the review again before retrying.`);
    } finally {
      setApproving(false);
    }
  }

  const shown = review ?? details?.dispatcher_plan ?? details?.plan ?? null;
  const selectedRow = shown?.summary_rows.find((row) => row.id === selectedId);
  const selectedTask = shown && selectedRow ? taskFor(shown, selectedRow.id) : null;
  const workshops = shown
    ? Object.keys(shown.queues_before_plan).map((id) => ({
        workshop_id: id,
        name: details?.plan?.workshop_profiles?.[id]?.name ?? "",
      }))
    : [];
  // Shown above the worklist until a review is open, then under the task details, where choices are made.
  const reviewBar = (
    <ReviewBar
      threadId={threadId}
      decisions={decisions}
      approving={approving}
      note={reviewNote}
      onOpen={openReview}
      onApprove={approve}
    />
  );

  return (
    <>
      <div className="page-head">
        <h1>Dispatcher</h1>
        <div className="toolbar">
          {/* While Approve all runs, the run stays open: its answer belongs to this run. */}
          {runs && <RunPicker runs={runs} runId={runId} onChange={changeRun} disabled={approving} />}
          <button onClick={refresh} disabled={approving}>
            Refresh
          </button>
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
          <p className={details.dispatcher_plan && !review ? "run-state final" : "run-state"}>
            <strong>{planName(details, review)}</strong> <span className="muted">planned from {shown.dispatch_date}</span>
          </p>
          {!details.dispatcher_plan && !threadId && reviewBar}
          {details.dispatcher_plan && reviewNote && <p className="notice">{reviewNote}</p>}
          {details.dispatcher_plan?.changes && !review && <ChangesTable changes={details.dispatcher_plan.changes} />}
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
            <TaskTable plan={shown} selectedId={selectedId} onSelect={setSelectedId} choices={choices} />
            <div className="desk" ref={desk}>
              {selectedRow ? (
                <TaskDetails plan={shown} row={selectedRow} onSelect={setSelectedId}>
                  {review && selectedTask && (
                    <ChoiceForm
                      task={selectedTask}
                      record={decisionFor(shown, selectedRow.id)}
                      warnings={shown.review_warnings?.[selectedRow.id] ?? []}
                      workshops={workshops}
                      choice={choices[selectedRow.id] ?? {}}
                      onChange={(choice) => setChoices(withChoice(choices, selectedRow.id, choice))}
                    />
                  )}
                </TaskDetails>
              ) : (
                <p className="muted empty-details">Choose a row to see its messages, facts and workshop comparison.</p>
              )}
              {threadId && reviewBar}
            </div>
          </div>
          <QueueTable plan={shown} profiles={details.plan?.workshop_profiles} />
        </>
      )}
    </>
  );
}

function planName(details: RunDetails, review: Review | null) {
  if (review) {
    return "Draft under review";
  }
  return details.dispatcher_plan ? "Approved dispatcher plan" : "Plan before the dispatcher's review";
}
