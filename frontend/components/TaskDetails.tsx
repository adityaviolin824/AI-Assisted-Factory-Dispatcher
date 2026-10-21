import { amount, days, listText, percent } from "@/lib/format";
import { decisionFor, outcomeLabel, rowEvidence, taskFor } from "@/lib/plan";
import type { DecisionRecord, Metrics, Plan, SummaryRow, Task } from "@/lib/types";

type Props = { plan: Plan; row: SummaryRow; onSelect: (rowId: string) => void; children?: React.ReactNode };

// Everything the plan records about one row: its outcome and reason, the original messages,
// the request facts, open questions, warnings and the workshop comparison. During a review,
// children holds the dispatcher's choices for the row, shown after its reason and warnings.
export default function TaskDetails({ plan, row, onSelect, children }: Props) {
  const record = decisionFor(plan, row.id);
  const task = taskFor(plan, row.id);
  const evidence = rowEvidence(plan, row.id);
  const warnedBy = plan.review_warnings?.[row.id] ?? [];
  const link = plan.link_review.find((review) => review.item_id === row.id);

  return (
    <section className="details" aria-label={`Details of ${row.id}`}>
      <h2>{row.id}</h2>
      <p>
        <strong>{outcomeLabel(row.outcome)}</strong>{" "}
        <span className="muted">
          ({row.outcome}
          {row.final ? ", final" : ""})
        </span>
      </p>
      <p>{row.reason}</p>

      {warnedBy.length > 0 && (
        <div className="notice">
          Provisional: these unresolved inputs may change this request:{" "}
          {warnedBy.map((rowId) => (
            <button key={rowId} className="link-button" onClick={() => onSelect(rowId)}>
              {rowId}
            </button>
          ))}
        </div>
      )}
      {children}

      <h3>Source messages</h3>
      <p className="muted">Messages: {listText(row.messages)}</p>
      {evidence.length > 0 ? (
        <ul className="quotes">
          {evidence.map((item, index) => (
            <li key={index}>
              <span className="message-id">{item.message_id}</span>
              <span className="spoken">{item.text}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">The plan holds no quoted text for this row.</p>
      )}

      {link && (
        <p>
          <strong>Possible tasks, not confirmed:</strong> {listText(link.candidate_task_ids)}
        </p>
      )}

      {task && <TaskFacts task={task} record={record} />}
      {task && <Blockers task={task} />}
      {record && <Comparison record={record} />}
    </section>
  );
}

function TaskFacts({ task, record }: { task: Task; record: DecisionRecord | null }) {
  const order = record?.order_snapshot;
  const missing = "not in this response";
  const corrected = task.dispatcher;
  return (
    <>
      <h3>Request facts</h3>
      <dl className="facts">
        <dt>Task</dt>
        <dd>
          {task.task_id}, version {task.version}
        </dd>
        <dt>Order</dt>
        <dd>{task.order_id ?? "unknown"}</dd>
        <dt>Pieces (orders.csv)</dt>
        <dd>{order ? order.pieces : missing}</dd>
        <dt>Category</dt>
        <dd>{order ? order.category : missing}</dd>
        <dt>Order status</dt>
        <dd>{order ? `${order.status}, ${order.current_stage}` : missing}</dd>
        <dt>Deadline from chat</dt>
        <dd>{task.due_date ?? "none: the orders.csv due date applies"}</dd>
        <dt>Deadline used</dt>
        <dd>{order ? order.due_date : missing}</dd>
        <dt>Preference</dt>
        <dd>{task.preference}</dd>
        <dt>Intent</dt>
        <dd>{task.intent}</dd>
        <dt>Requested workshop</dt>
        <dd>{task.requested_workshop ?? "none"}</dd>
        <dt>Excluded workshops</dt>
        <dd>{listText(task.excluded_workshops)}</dd>
        <dt>Split requested</dt>
        <dd>{task.wants_split ? "yes" : "no"}</dd>
      </dl>
      {corrected && (
        <p>
          <strong>Corrected by the dispatcher:</strong>{" "}
          {Object.entries(corrected.facts)
            .map(([name, value]) => `${name} ${corrected.recorded[name] ?? "none"} -> ${value}`)
            .join("; ")}
        </p>
      )}
    </>
  );
}

// Missing facts, open questions and unsupported conditions, as verification recorded them.
function Blockers({ task }: { task: Task }) {
  const items = [
    ...task.missing_details.map((text) => ["Missing", text]),
    ...task.doubts_to_clarify.map((text) => ["Question", text]),
    ...task.unhandled_constraints.map((text) => ["Unsupported", text]),
  ];
  if (items.length === 0) {
    return null;
  }
  return (
    <>
      <h3>Open blockers</h3>
      <ul>
        {items.map(([kind, text], index) => (
          <li key={index}>
            <strong>{kind}:</strong> {text}
          </li>
        ))}
      </ul>
    </>
  );
}

// Every workshop the decision considered, with Python's estimates, ranking and rejection reasons.
function Comparison({ record }: { record: DecisionRecord }) {
  const rejected = new Map(record.rejected_candidates.map((item) => [item.workshop_id, item.reason]));
  const selected = record.selected_workshop;
  // The selected workshop first, then the ranked ones, then every other estimated or rejected
  // workshop, each listed once.
  const listed = [selected, ...record.ranking, ...Object.keys(record.candidate_metrics), ...rejected.keys()];
  const workshopIds = [...new Set(listed.filter((workshopId) => workshopId !== null))];
  if (workshopIds.length === 0) {
    return <p className="muted">No workshop was estimated for this request.</p>;
  }

  const options: [string, Metrics | null | undefined][] = [
    ["Closest late option", record.closest_option],
    ["Late option to accept", record.late_option],
    ["Best on-time option without the request", record.option_without_request],
  ];

  function status(workshopId: string) {
    if (workshopId === selected) {
      return "Selected";
    }
    if (rejected.has(workshopId)) {
      return `Rejected: ${rejected.get(workshopId)}`;
    }
    const rank = record.ranking.indexOf(workshopId);
    return rank >= 0 ? `Ranked ${rank + 1}` : "Estimated";
  }

  return (
    <>
      <h3>Workshop comparison</h3>
      {record.objective && <p className="muted">Ranked under {record.objective}.</p>}
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Workshop</th>
              <th>Status</th>
              <th className="number">Delivery days</th>
              <th className="number">Days available</th>
              <th className="number">Days late</th>
              <th className="number">Queue</th>
              <th className="number">Production</th>
              <th className="number">Rework</th>
              <th className="number">Transport</th>
              <th className="number">Cost</th>
              <th className="number">Defect rate</th>
            </tr>
          </thead>
          <tbody>
            {workshopIds.map((workshopId) => {
              const metrics = workshopId === selected ? record.selected_metrics : record.candidate_metrics[workshopId];
              return (
                <tr key={workshopId} className={workshopId === selected ? "selected" : undefined}>
                  <td>
                    {workshopId} {metrics?.name}
                  </td>
                  <td>{status(workshopId)}</td>
                  <td className="number">{days(metrics?.eta_days)}</td>
                  <td className="number">{metrics?.days_until_due ?? "-"}</td>
                  <td className="number">{days(metrics?.tardiness_days)}</td>
                  <td className="number">{days(metrics?.queue_days)}</td>
                  <td className="number">{days(metrics?.processing_days)}</td>
                  <td className="number">{days(metrics?.expected_rework_days)}</td>
                  <td className="number">{metrics?.lead_days ?? "-"}</td>
                  <td className="number">{amount(metrics?.cost)}</td>
                  <td className="number">{percent(metrics?.defect_rate)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {options.map(
        ([label, option]) =>
          option && (
            <p key={label}>
              <strong>{label} (information only, not selected):</strong> {option.workshop_id} {option.name}, delivery
              in {days(option.eta_days)} of {option.days_until_due} days, {days(option.tardiness_days)} days late,
              cost {amount(option.cost)}.
            </p>
          ),
      )}
    </>
  );
}
