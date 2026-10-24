// The FastAPI endpoints, reached through the Next.js rewrite /api/backend (next.config.ts).
// Each function returns the backend's JSON unchanged. A response that is not 2xx is thrown as an
// Error carrying the backend's own "detail" message when it has one.
import type {
  Answer,
  ChatDates,
  ChatMessage,
  Decision,
  NewMessage,
  PreviewEnvelope,
  ReviewEnvelope,
  RunDetails,
  RunSummary,
  Snapshot,
} from "./types";

const BASE = "/api/backend";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(BASE + path, { cache: "no-store", ...init });
  if (!response.ok) {
    throw new Error(await failureText(response));
  }
  return response.json();
}

// FastAPI errors are {"detail": "..."}. When the backend cannot be reached, the Next.js server
// answers with its own error page, which is not JSON.
async function failureText(response: Response) {
  const body = await response.json().catch(() => null);
  if (typeof body?.detail === "string") {
    return body.detail;
  }
  return `The backend answered HTTP ${response.status}. Check that the FastAPI server is running.`;
}

export function errorText(error: unknown) {
  return error instanceof Error ? error.message : String(error);
}

export function listRuns() {
  return request<RunSummary[]>("/runs");
}

export function readRun(runId: string, signal?: AbortSignal) {
  return request<RunDetails>(`/runs/${encodeURIComponent(runId)}`, { signal });
}

export function readReview(threadId: string, signal?: AbortSignal) {
  return request<ReviewEnvelope>(`/reviews/${encodeURIComponent(threadId)}`, { signal });
}

// Mutations are never retried: after a failure the page reads the review again first.
export function sendAnswer(threadId: string, answer: Answer) {
  return request<ReviewEnvelope>(`/reviews/${encodeURIComponent(threadId)}/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(answer),
  });
}

// Approves the review with all the dispatcher's choices: the backend applies them together, plans once
// and saves at once, or refuses the whole batch and saves nothing.
export function finalize(threadId: string, decisions: Decision[]) {
  return request<ReviewEnvelope>(`/reviews/${encodeURIComponent(threadId)}/finalize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decisions }),
  });
}

// Calculates the dispatcher's choices as finalize would, without saving or approving anything: the
// review stays paused and the run folder is unchanged. Sent only when the dispatcher asks for it.
export function previewReview(threadId: string, decisions: Decision[]) {
  return request<PreviewEnvelope>(`/reviews/${encodeURIComponent(threadId)}/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decisions }),
  });
}

// Review again, on a run's approved plan: the backend adds these choices to the saved ones and plans once.
// previewRun saves nothing; finalizeRun saves a new version, or refuses the whole set and saves nothing.
export function previewRun(runId: string, decisions: Decision[]) {
  return request<PreviewEnvelope>(`/runs/${encodeURIComponent(runId)}/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decisions }),
  });
}

export function finalizeRun(runId: string, decisions: Decision[]) {
  return request<PreviewEnvelope>(`/runs/${encodeURIComponent(runId)}/finalize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decisions }),
  });
}

// Chat bridge: backend/fastapi_routes/chat.py (BACKEND_PROPOSAL.md, section 1).

export function listMessages() {
  return request<ChatMessage[]>("/chat/messages");
}

// The date relative words in the chat count from, and the date plans start from.
export function readChatDates() {
  return request<ChatDates>("/chat/dates");
}

// Saves one message. It makes no model call.
export function sendMessage(message: NewMessage) {
  return request<ChatMessage>("/chat/messages", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(message),
  });
}

export function listSnapshots() {
  return request<Snapshot[]>("/chat/snapshots");
}

// Captures the whole conversation as a fixed processing input. It makes no model call.
export function createSnapshot() {
  return request<Snapshot>("/chat/snapshots", { method: "POST" });
}

export function readSnapshot(snapshotId: string) {
  return request<Snapshot>(`/chat/snapshots/${encodeURIComponent(snapshotId)}`);
}

// Starts the pipeline on one snapshot and returns at once; processing calls paid models.
// The page then reads the snapshot until processing has finished or failed.
export function processSnapshot(snapshotId: string) {
  return request<Snapshot>(`/chat/snapshots/${encodeURIComponent(snapshotId)}/process`, { method: "POST" });
}
