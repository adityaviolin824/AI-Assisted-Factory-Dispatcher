// The JSON that the FastAPI server returns, with only the fields this frontend reads.
// Field names are exactly those of the Python records (backend/task_allocation_to_workshops/ and
// backend/dispatcher_review/). A null number means the value is unavailable, not zero.

export type RunSummary = { run_id: string; label: string; messages: number };

// One workshop's estimate for one batch (workshop_rules_and_estimates.candidate_metrics).
export type Metrics = {
  workshop_id: string;
  name: string;
  queue_days: number;
  processing_days: number;
  expected_rework_days: number;
  lead_days: number;
  eta_days: number;
  days_until_due: number;
  tardiness_days: number;
  on_time: boolean;
  defect_rate: number;
  cost_per_piece: number;
  cost: number;
  share: number;
};

export type Evidence = { evidence_id: string; message_id: string; text: string };

// A verified task. "dispatcher" is present only after the dispatcher corrected a fact.
export type Task = {
  task_id: string;
  version: number;
  description: string;
  source_message_ids: string[];
  intent: string;
  order_id: string | null;
  due_date: string | null;
  urgency_phrase: string | null;
  deadline_phrase: string | null;
  preference: string;
  requested_workshop: string | null;
  excluded_workshops: string[];
  wants_split: boolean;
  missing_details: string[];
  doubts_to_clarify: string[];
  unhandled_constraints: string[];
  information_sufficient: boolean;
  source_evidence?: Evidence[];
  dispatcher?: {
    facts: Record<string, string>;
    resolved: string[];
    recorded: Record<string, string | null>;
    recorded_deadline: string | null;
  };
};

// One allocation decision (recommend_one_task.recommend, or the dispatcher's version of it).
export type DecisionRecord = {
  task_id: string;
  version: number;
  order_id: string | null;
  task: Task;
  status: string;
  selected_workshop: string | null;
  selected_metrics: Metrics | null;
  closest_option: Metrics | null;
  option_without_request: Metrics | null;
  late_option?: Metrics;
  reason: string;
  warnings: string[];
  candidate_metrics: Record<string, Metrics>;
  ranking: string[];
  rejected_candidates: { workshop_id: string; reason: string }[];
  objective?: string;
  order_snapshot?: {
    order_id: string;
    category: string;
    pieces: number;
    due_date: string;
    status: string;
    current_stage: string;
  };
};

// One row of the plan table: one task, item or message, with its outcome.
export type SummaryRow = {
  id: string;
  order_id: string | null;
  outcome: string;
  workshop: string | null;
  delivery_days: number | null;
  days_available: number | null;
  reason: string;
  messages: string[];
  final?: boolean;
};

export type WorkshopProfile = {
  workshop_id: string;
  name: string;
  capacity: number;
  lead_days: number;
  defect_rate: number;
  cost: number;
  makes: string[];
  status: string;
  max_batch: number | null;
  queue0: number;
  notes: string;
};

// The fields that plan.json and a dispatcher review share.
export type Plan = {
  dispatch_date: string;
  processing_complete: boolean;
  summary_rows: SummaryRow[];
  decisions: DecisionRecord[];
  duplicate_order_reviews: DecisionRecord[];
  needs_clarification: Task[];
  reference_tasks: Task[];
  intake_review: { message_id: string; raw_text: string; reason: string }[];
  task_review: {
    task_id: string;
    version: number;
    reason: string;
    evidence: { message_id: string; excerpts: string[] }[];
  }[];
  link_review: {
    item_id: string;
    message_id: string;
    excerpts: string[];
    candidate_task_ids: string[];
    reason: string;
  }[];
  non_task_messages: { message_id: string; raw_text: string }[];
  not_processed: { id: string; kind: string; messages: string[]; reason: string }[];
  // Plans made before 15 October 2026 have no review_warnings: not recorded, which is not "none".
  review_warnings?: Record<string, string[]>;
  queues_before_plan: Record<string, number>;
  queues_after_plan: Record<string, number>;
  // Only plan.json has the workshop profiles.
  workshop_profiles?: Record<string, WorkshopProfile>;
};

// What the dispatcher has decided for one task (dispatcher_decisions.py).
export type DispatcherEntry = {
  source_version: number;
  workshop?: string;
  facts?: Record<string, string>;
  resolves?: string[];
  accept_late?: { workshop: string; version: number; days: number };
  warnings_checked?: string[];
};

// One side of a changed row (dispatcher_decisions.changed_rows).
export type RowState = { outcome: string; workshop: string | null; delivery_days: number | null; reason: string };

// A row whose outcome, workshop or delivery estimate the dispatcher's batch changed.
export type RowChange = { id: string; order_id: string | null; before: RowState; after: RowState };

// A dispatcher review: a draft while the thread waits, or the final approved plan.
// changes is only in a final plan approved together with the dispatcher's choices.
export type Review = Plan & {
  source_run: string;
  status: string;
  dispatcher_entries: Record<string, DispatcherEntry>;
  decision_problems: Record<string, string[]>;
  final_ids: string[];
  unresolved_ids: string[];
  changes?: RowChange[];
};

export type RunDetails = { run_id: string; plan: Plan | null; dispatcher_plan: Review | null };

export type ReviewEnvelope = { status: "waiting" | "finished"; review: Review; refused: string | null };

// One decision of a dispatcher's answer, named after its backend helper.
export type Decision =
  | { decision: "choose_workshop"; task_id: string; workshop_id: string }
  | { decision: "correct"; task_id: string; facts: Record<string, string> }
  | { decision: "accept_late"; task_id: string; max_days?: number }
  | { decision: "warnings_checked"; task_id: string; row_ids: string[] }
  | { decision: "clear"; task_id: string };

export type Answer = { decisions: Decision[]; then: "review_again" | "approve_all" };

// Chat bridge: PROPOSED endpoints, not yet in the backend (BACKEND_PROPOSAL.md). The fields follow
// the mock chat's storage and export (backend/experimentation_notebooks/mock_frontend/PLAN.md).
export type ChatMessage = { message_id: number; sender: string; raw_text: string; received_at_utc: string };

// One send attempt. Sending it again with the same submission_id saves nothing new.
export type NewMessage = { submission_id: string; sender: string; raw_text: string };

// How one exported line maps a chat message to its R label and the pipeline's L message ID.
export type SnapshotLine = { message_id: number; request_label: string; processing_message_id: string };

export type Snapshot = {
  snapshot_id: string;
  exported_at_utc: string;
  message_count: number;
  text: string;
  lines: SnapshotLine[];
  processing: "not_started" | "running" | "finished" | "failed";
  run_id: string | null;
  thread_id: string | null;
  error: string | null;
};
