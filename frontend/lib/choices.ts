// The dispatcher's unsaved choices. They live only in page memory until Approve all: nothing here
// sends a request, recalculates or stores anything (FRONTEND_PLAN.md, section 7).
import type { Decision } from "./types";

// One task's pending choices. A field left out means "keep what the review shows".
export type LocalChoice = {
  workshop_id?: string;
  facts?: Record<string, string>;
  warnings_checked?: string[];
};

export type Choices = Record<string, LocalChoice>;

// The facts a dispatcher may correct, with the values the backend accepts (dispatcher_decisions.py).
export const PREFERENCES = ["none", "fastest", "cheapest", "quality"];
export const INTENTS = ["allocation", "question"];

// Replace one task's choices; a task without any choice left is removed.
export function withChoice(choices: Choices, taskId: string, choice: LocalChoice): Choices {
  const rest = { ...choices };
  delete rest[taskId];
  const empty = !choice.workshop_id && !Object.keys(choice.facts ?? {}).length && !choice.warnings_checked?.length;
  return empty ? rest : { ...rest, [taskId]: choice };
}

// The decisions Approve all would submit, in the backend's vocabulary. Corrections come first,
// because a correction can change the request that a workshop choice is for.
export function decisionsFrom(choices: Choices): Decision[] {
  const decisions: Decision[] = [];
  for (const [taskId, choice] of Object.entries(choices)) {
    if (choice.facts && Object.keys(choice.facts).length) {
      decisions.push({ decision: "correct", task_id: taskId, facts: choice.facts });
    }
    if (choice.workshop_id) {
      decisions.push({ decision: "choose_workshop", task_id: taskId, workshop_id: choice.workshop_id });
    }
    if (choice.warnings_checked?.length) {
      decisions.push({ decision: "warnings_checked", task_id: taskId, row_ids: choice.warnings_checked });
    }
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
    case "choose_workshop":
      return `${decision.task_id}: send to ${decision.workshop_id}`;
    case "warnings_checked":
      return `${decision.task_id}: not changed by ${decision.row_ids.join(", ")}`;
    default:
      return `${decision.task_id}: ${decision.decision}`;
  }
}
