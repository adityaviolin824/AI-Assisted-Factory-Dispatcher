// Small synthetic plans for the browser tests. The numbers are made up; the field names and
// outcomes follow the backend's plan.json (see lib/types.ts).
import type {
  ChatMessage,
  DecisionRecord,
  Metrics,
  Plan,
  Review,
  RunDetails,
  RunSummary,
  RunUsage,
  Snapshot,
  StageUsage,
  SummaryRow,
  Task,
} from "@/lib/types";

export const RUN: RunSummary = { run_id: "R1", label: "chat.txt", messages: 4 };
export const OTHER_RUN: RunSummary = { run_id: "R2", label: "other-chat.txt", messages: 4 };

export function runDetails(plan: Plan | null, runId = RUN.run_id): RunDetails {
  return { run_id: runId, plan, dispatcher_plan: null };
}

function metrics(workshopId: string, name: string, etaDays: number, daysUntilDue: number): Metrics {
  return {
    workshop_id: workshopId,
    name,
    queue_days: 1,
    processing_days: etaDays - 2.5,
    expected_rework_days: 0.5,
    lead_days: 1,
    eta_days: etaDays,
    days_until_due: daysUntilDue,
    tardiness_days: Math.max(0, etaDays - daysUntilDue),
    on_time: etaDays <= daysUntilDue,
    defect_rate: 0.05,
    cost_per_piece: 1.2,
    cost: 120,
    share: 1,
  };
}

function task(taskId: string, fields: Partial<Task>): Task {
  return {
    task_id: taskId,
    version: 1,
    description: "Synthetic request",
    source_message_ids: [taskId.split(":")[1]],
    intent: "allocation",
    order_id: null,
    due_date: null,
    urgency_phrase: null,
    deadline_phrase: null,
    preference: "fastest",
    requested_workshop: null,
    excluded_workshops: [],
    wants_split: false,
    missing_details: [],
    doubts_to_clarify: [],
    unhandled_constraints: [],
    information_sufficient: true,
    ...fields,
  };
}

function record(request: Task, fields: Partial<DecisionRecord>): DecisionRecord {
  return {
    task_id: request.task_id,
    version: 1,
    order_id: request.order_id,
    task: request,
    status: "recommendation",
    selected_workshop: null,
    selected_metrics: null,
    closest_option: null,
    option_without_request: null,
    reason: "",
    warnings: [],
    candidate_metrics: {},
    ranking: [],
    rejected_candidates: [],
    ...fields,
  };
}

function row(id: string, outcome: string, fields: Partial<SummaryRow> = {}): SummaryRow {
  return {
    id,
    order_id: null,
    outcome,
    workshop: null,
    delivery_days: null,
    days_available: null,
    reason: `Reason for ${id}.`,
    messages: [id.replace("T:", "").split(":")[0]],
    ...fields,
  };
}

// Four rows: a recommendation (W6), a late request whose closest option (W2) is information only,
// a message with no request, and a request that needs clarification.
export function makePlan(): Plan {
  const suggested = task("T:L0001:J1", { order_id: "ORD-001" });
  const late = task("T:L0002:J1", { order_id: "ORD-002" });
  const unclear = task("T:L0004:J1", { information_sufficient: false, missing_details: ["Order ID for the scarves"] });
  const w6 = metrics("W6", "Nimble Needle", 3.18, 8);
  const snapshot = { category: "TOPS", pieces: 150, status: "IN_PROGRESS", current_stage: "WASHING" };

  return {
    dispatch_date: "2026-04-01",
    processing_complete: true,
    summary_rows: [
      row("T:L0001:J1", "recommendation", { order_id: "ORD-001", workshop: "W6", delivery_days: 3.18, days_available: 8 }),
      row("T:L0002:J1", "review_required", { order_id: "ORD-002", workshop: "W2", delivery_days: 9.5, days_available: 4 }),
      row("L0003", "non_task"),
      row("T:L0004:J1", "needs_clarification"),
    ],
    decisions: [
      record(suggested, {
        selected_workshop: "W6",
        selected_metrics: w6,
        candidate_metrics: { W6: w6, W1: metrics("W1", "QuickStitch", 5.53, 8) },
        ranking: ["W6", "W1"],
        rejected_candidates: [{ workshop_id: "W4", reason: "cannot_make_category=TOPS" }],
        objective: "minimize_tardiness",
        order_snapshot: { order_id: "ORD-001", due_date: "2026-04-09", ...snapshot },
      }),
      record(late, {
        status: "review_required",
        closest_option: metrics("W2", "SteadyHands", 9.5, 4),
        candidate_metrics: { W2: metrics("W2", "SteadyHands", 9.5, 4) },
        rejected_candidates: [{ workshop_id: "W2", reason: "estimated_delivery_after_deadline" }],
        objective: "minimize_tardiness",
        order_snapshot: { order_id: "ORD-002", due_date: "2026-04-05", ...snapshot },
      }),
    ],
    duplicate_order_reviews: [],
    needs_clarification: [unclear],
    reference_tasks: [],
    intake_review: [],
    task_review: [],
    link_review: [],
    non_task_messages: [{ message_id: "L0003", raw_text: "Thanks, see you tomorrow." }],
    not_processed: [],
    review_warnings: {},
    queues_before_plan: { W1: 4, W2: 2.5, W6: 1 },
    queues_after_plan: { W1: 4, W2: 2.5, W6: 2.18 },
  };
}

// A paused review of RUN: the same rows as makePlan, as the dispatcher review returns them.
export function makeReview(changes: Partial<Review> = {}): Review {
  return {
    ...makePlan(),
    source_run: RUN.run_id,
    status: "draft",
    dispatcher_entries: {},
    decision_problems: {},
    final_ids: [],
    unresolved_ids: [],
    ...changes,
  };
}

// Chat messages as the proposed chat endpoints return them. Times are UTC, written like Python's
// isoformat(); 01:02 UTC is 09:02 in Singapore.
export const MESSAGES: ChatMessage[] = [
  {
    message_id: 1,
    sender: "Chen",
    raw_text: "Can someone place ORD-107?\n2000 cardigans, due Mar 16.",
    received_at_utc: "2026-10-21T01:02:03.123456+00:00",
  },
  {
    message_id: 2,
    sender: "Ravi",
    raw_text: "For ORD-107, avoid QuickStitch.",
    received_at_utc: "2026-10-21T01:05:00+00:00",
  },
];

function stageUsage(stage: string, calls: number, paid: number, costs: [number, number], seconds: [number, number]): StageUsage {
  return {
    stage,
    models: ["gpt-5.6-luna"],
    calls,
    paid,
    failed: 0,
    input_tokens: paid * 3000,
    cached_tokens: paid * 500,
    output_tokens: paid * 800,
    cost_this_run: costs[0],
    cost_fresh: costs[1],
    seconds_this_run: seconds[0],
    seconds_fresh: seconds[1],
  };
}

// A run that paid for 3 of its 10 calls; the other 7 came from saved answers.
export function makeUsage(): RunUsage {
  return {
    run_id: RUN.run_id,
    prices_checked: "2026-10-14",
    stages: [
      stageUsage("intake", 4, 1, [0.0007, 0.0028], [40, 160]),
      stageUsage("link", 2, 0, [0, 0.001], [0, 30]),
      stageUsage("verify", 4, 2, [0.0014, 0.0034], [85.4, 171]),
      stageUsage("total", 10, 3, [0.0021, 0.0072], [125.4, 361]),
    ],
  };
}

export function makeSnapshot(changes: Partial<Snapshot> = {}): Snapshot {
  return {
    snapshot_id: "S1",
    exported_at_utc: "2026-10-21T01:06:00+00:00",
    message_count: 2,
    text: "R01 [09:02] Chen: Can someone place ORD-107? 2000 cardigans, due Mar 16.\r\nR02 [09:05] Ravi: For ORD-107, avoid QuickStitch.\r\n",
    lines: [
      { message_id: 1, request_label: "R01", processing_message_id: "L0001" },
      { message_id: 2, request_label: "R02", processing_message_id: "L0002" },
    ],
    processing: "not_started",
    run_id: null,
    thread_id: null,
    error: null,
    ...changes,
  };
}
