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
  // Only a dispatcher's correction sets a quantity; without one, orders.csv gives it.
  quantity?: number;
  // Only a batch the dispatcher added (ADD-1, ...) has added: true. No chat message covers it.
  added?: boolean;
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
  // Only a dispatcher review has the requests the dispatcher cancelled (24 October 2026).
  cancelled_tasks?: Task[];
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

// What the dispatcher has decided for one task (dispatcher_decisions.py). "added" marks a batch the
// dispatcher added (ADD-1, ADD-2, ...), which no chat message covers.
export type DispatcherEntry = {
  source_version: number;
  added?: boolean;
  complete?: boolean;
  workshop?: string;
  facts?: Record<string, string>;
  resolves?: string[];
  accept_late?: { workshop: string; version: number; days: number };
  warnings_checked?: string[];
  // The dispatcher cancelled the request: it is not planned and reserves no queue time.
  cancelled?: boolean;
};

// One side of a changed row (dispatcher_decisions.changed_rows).
export type RowState = { outcome: string; workshop: string | null; delivery_days: number | null; reason: string };

// A row whose outcome, workshop or delivery estimate the dispatcher's batch changed. A batch the
// dispatcher added has no earlier row, so before is null; an added batch removed in Review again has
// no later row, so after is null.
export type RowChange = { id: string; order_id: string | null; before: RowState | null; after: RowState | null };

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

// One stage's model calls (eval_run_report/run_summary.cost_row), or the "total" row for all stages.
// "this_run" covers the calls this run paid for; "fresh" prices every answered call, as a run with no
// saved answers would pay. Token counts are those of the paid calls. A null cost means a model in it
// has no listed price.
export type StageUsage = {
  stage: string;
  models: string[];
  calls: number;
  paid: number;
  failed: number;
  input_tokens: number;
  cached_tokens: number;
  output_tokens: number;
  cost_this_run: number | null;
  cost_fresh: number | null;
  seconds_this_run: number;
  seconds_fresh: number;
};

// GET /runs/{run_id}/usage: numbers from the run's call records only, with no prompt or answer.
export type RunUsage = { run_id: string; prices_checked: string; stages: StageUsage[] };

export type ReviewEnvelope = { status: "waiting" | "finished"; review: Review; refused: string | null };

// A preview of the dispatcher's choices (POST /reviews/{thread_id}/preview): the draft that finalize
// would approve, with its changes, or the shown review and why the choices would be refused. Nothing is saved.
// Review again answers in the same form: POST /runs/{run_id}/preview, and /finalize with the saved new version.
export type PreviewEnvelope = { review: Review; refused: string | null };

// One decision of a dispatcher's answer, named after its backend helper.
export type Decision =
  | { decision: "choose_workshop"; task_id: string; workshop_id: string }
  | { decision: "correct"; task_id: string; facts: Record<string, string> }
  | { decision: "complete"; task_id: string; facts: Record<string, string> }
  // Python names an added batch, so it has no task_id.
  | { decision: "add_batch"; facts: Record<string, string>; workshop_id?: string }
  | { decision: "accept_late"; task_id: string; max_days?: number }
  | { decision: "warnings_checked"; task_id: string; row_ids: string[] }
  | { decision: "cancel"; task_id: string }
  | { decision: "clear"; task_id: string };

export type Answer = { decisions: Decision[]; then: "review_again" | "approve_all" };

// Chat bridge: backend/fastapi_routes/chat.py (BACKEND_PROPOSAL.md, section 1). The fields follow
// the mock chat's storage and export (backend/experimentation_notebooks/mock_frontend/PLAN.md).
export type ChatMessage = { message_id: number; sender: string; raw_text: string; received_at_utc: string };

// The dates from config.toml that processing uses, such as "2026-04-01" (GET /chat/dates).
export type ChatDates = { message_date: string; dispatch_date: string };

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
