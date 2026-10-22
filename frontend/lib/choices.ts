// The dispatcher's unsaved choices. They live only in page memory until Approve all: nothing here
// sends a request, recalculates or stores anything (FRONTEND_PLAN.md, section 7).
import type { Decision } from "./types";

// One task's pending choices. A field left out means "keep what the review shows".
export type LocalChoice = {
  workshop_id?: string;
  facts?: Record<string, string>;
  // The request is complete: Python plans it with these facts and treats its open questions as answered.
  complete?: boolean;
  warnings_checked?: string[];
  // Undo the dispatcher's saved choices for this row, or remove a saved added batch (Review again).
  // It is sent alone, so Python plans the row as processing recorded it.
  clear?: boolean;
};

export type Choices = Record<string, LocalChoice>;

// A batch that no row covers, such as one part of a split or a request processing missed. Only the
// order is required; a fact left out is the order's own in orders.csv. Python names it ADD-1, ADD-2,
// ... when the plan is approved.
export type AddedBatch = { facts: Record<string, string>; workshop_id?: string };

// The facts a dispatcher may correct, with the values the backend accepts (dispatcher_decisions.py).
export const PREFERENCES = ["none", "fastest", "cheapest", "quality"];
// "quality" ranks the workshops by lowest defect rate first.
export const PREFERENCE_LABELS: Record<string, string> = { quality: "quality (expensive or delicate item)" };
export const INTENTS = ["allocation", "question"];

// Replace one task's choices; a task without any choice left is removed.
export function withChoice(choices: Choices, taskId: string, choice: LocalChoice): Choices {
  const rest = { ...choices };
  delete rest[taskId];
  const empty =
    !choice.workshop_id &&
    !choice.complete &&
    !choice.clear &&
    !Object.keys(choice.facts ?? {}).length &&
    !choice.warnings_checked?.length;
  return empty ? rest : { ...rest, [taskId]: choice };
}

// The decisions Approve all would submit, in the backend's vocabulary. Corrections come first,
// because a correction can change the request that a workshop choice is for. An undo (clear) replaces
// the row's other choices. Added batches come last.
export function decisionsFrom(choices: Choices, added: AddedBatch[] = []): Decision[] {
  const decisions: Decision[] = [];
  for (const [taskId, choice] of Object.entries(choices)) {
    if (choice.clear) {
      decisions.push({ decision: "clear", task_id: taskId });
      continue;
    }
    if (choice.complete) {
      decisions.push({ decision: "complete", task_id: taskId, facts: choice.facts ?? {} });
    } else if (choice.facts && Object.keys(choice.facts).length) {
      decisions.push({ decision: "correct", task_id: taskId, facts: choice.facts });
    }
    if (choice.workshop_id) {
      decisions.push({ decision: "choose_workshop", task_id: taskId, workshop_id: choice.workshop_id });
    }
    if (choice.warnings_checked?.length) {
      decisions.push({ decision: "warnings_checked", task_id: taskId, row_ids: choice.warnings_checked });
    }
  }
  for (const batch of added) {
    decisions.push({ decision: "add_batch", ...batch });
  }
  return decisions;
}

// A plain sentence for one decision, for the list of what Approve all would send.
export function decisionText(decision: Decision) {
  switch (decision.decision) {
    case "correct":
      return `${decision.task_id}: correct ${Object.entries(decision.facts)
        .map(([name, value]) => `${name} to ${value}`)
        .join(", ")}`;
    case "complete": {
      const facts = Object.entries(decision.facts).map(([name, value]) => `${name} ${value}`);
      return `${decision.task_id}: complete the request${facts.length ? ` with ${facts.join(", ")}` : ""}`;
    }
    case "add_batch": {
      const { order_id, ...rest } = decision.facts;
      const details = Object.entries(rest).map(([name, value]) => `${name} ${value}`);
      if (decision.workshop_id) {
        details.push(`send to ${decision.workshop_id}`);
      }
      return `New batch of ${order_id}${details.length ? `: ${details.join(", ")}` : ""}`;
    }
    case "choose_workshop":
      return `${decision.task_id}: send to ${decision.workshop_id}`;
    case "warnings_checked":
      return `${decision.task_id}: not changed by ${decision.row_ids.join(", ")}`;
    // Python names added batches ADD-1, ADD-2, ...; undoing one removes it.
    case "clear":
      return decision.task_id.startsWith("ADD-")
        ? `${decision.task_id}: remove this added batch`
        : `${decision.task_id}: undo your saved choices`;
    default:
      return `${decision.task_id}: ${decision.decision}`;
  }
}
