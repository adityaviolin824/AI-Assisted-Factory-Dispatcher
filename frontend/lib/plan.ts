// Read a plan or review for display. Nothing here calculates a date, queue, cost or ranking:
// every value comes from the backend's JSON.
import type { DecisionRecord, Plan, SummaryRow, Task } from "./types";

const OUTCOME_LABELS: Record<string, string> = {
  recommendation: "Suggested",
  provisional_recommendation: "Suggested, provisional",
  dispatcher_choice: "Dispatcher's choice",
  accepted_late: "Accepted late",
  approved: "Approved (final)",
  review_required: "Needs review",
  deadline_passed: "Deadline passed",
  needs_clarification: "Needs clarification",
  reference: "Question, not answered",
  intake_review: "Message not read reliably",
  processing_review: "Verification failed",
  link_review: "Follow-up not linked",
  non_task: "No request",
  not_processed: "Not processed",
  cancelled: "Cancelled",
};

// An unfamiliar outcome keeps its backend name, so nothing is hidden.
export function outcomeLabel(outcome: string) {
  return OUTCOME_LABELS[outcome] ?? outcome;
}

// The outcomes in which Python selected a workshop and reserved its queue time
// (RESERVING in backend/dispatcher_review/dispatcher_plan.py).
export const SELECTED_OUTCOMES = ["recommendation", "dispatcher_choice", "accepted_late"];

export type Group = "attention" | "suggested" | "approved" | "info";

// The worklist filter a row belongs to. A selected outcome with an unchecked warning still needs
// attention: approval leaves it unresolved. A request the dispatcher cancelled needs nothing more.
export function rowGroup(row: SummaryRow, plan: Plan): Group {
  if (row.final) {
    return "approved";
  }
  if (row.outcome === "non_task" || row.outcome === "cancelled") {
    return "info";
  }
  if (SELECTED_OUTCOMES.includes(row.outcome) && !plan.review_warnings?.[row.id]) {
    return "suggested";
  }
  return "attention";
}

export function decisionFor(plan: Plan, rowId: string): DecisionRecord | null {
  return [...plan.decisions, ...plan.duplicate_order_reviews].find((record) => record.task_id === rowId) ?? null;
}

export function taskFor(plan: Plan, rowId: string): Task | null {
  const others = [...plan.needs_clarification, ...plan.reference_tasks, ...(plan.cancelled_tasks ?? [])];
  return decisionFor(plan, rowId)?.task ?? others.find((task) => task.task_id === rowId) ?? null;
}

// The original chat text behind a row, as the plan quotes it.
export function rowEvidence(plan: Plan, rowId: string): { message_id: string; text: string }[] {
  const task = taskFor(plan, rowId);
  if (task) {
    return (task.source_evidence ?? []).map((item) => ({ message_id: item.message_id, text: item.text }));
  }
  const link = plan.link_review.find((review) => review.item_id === rowId);
  if (link) {
    return link.excerpts.map((text) => ({ message_id: link.message_id, text }));
  }
  const failed = plan.task_review.find((review) => review.task_id === rowId);
  if (failed) {
    return failed.evidence.flatMap((item) => item.excerpts.map((text) => ({ message_id: item.message_id, text })));
  }
  const message = [...plan.intake_review, ...plan.non_task_messages].find((item) => item.message_id === rowId);
  return message ? [{ message_id: message.message_id, text: message.raw_text }] : [];
}
