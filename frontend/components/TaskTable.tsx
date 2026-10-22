import { useState } from "react";
import type { Choices } from "@/lib/choices";
import { days } from "@/lib/format";
import { decisionFor, type Group, outcomeLabel, rowGroup } from "@/lib/plan";
import type { Plan, SummaryRow } from "@/lib/types";

type Filter = Group | "all";

const FILTERS: { filter: Filter; label: string }[] = [
  { filter: "all", label: "All" },
  { filter: "attention", label: "Needs attention" },
  { filter: "suggested", label: "Suggested" },
  { filter: "approved", label: "Approved" },
  { filter: "info", label: "No request" },
];

type Props = { plan: Plan; selectedId: string | null; onSelect: (rowId: string) => void; choices?: Choices };

// The worklist: one row per task, item or message, filtered by the group rowGroup gives it.
export default function TaskTable({ plan, selectedId, onSelect, choices = {} }: Props) {
  const [filter, setFilter] = useState<Filter>("all");
  const inFilter = (row: SummaryRow, chosen: Filter) => chosen === "all" || rowGroup(row, plan) === chosen;
  const rows = plan.summary_rows.filter((row) => inFilter(row, filter));

  return (
    <section>
      <div className="filters" role="group" aria-label="Worklist filter">
        {FILTERS.map((item) => (
          <button key={item.filter} aria-pressed={filter === item.filter} onClick={() => setFilter(item.filter)}>
            {item.label} ({plan.summary_rows.filter((row) => inFilter(row, item.filter)).length})
          </button>
        ))}
      </div>
      <p className="legend">
        <span>Needs attention</span>
        <span className="mark-suggested">Suggested, not final</span>
        <span className="mark-approved">Approved</span>
      </p>
      <div className="table-scroll">
        <table aria-label="Worklist">
          <thead>
            <tr>
              <th>Row</th>
              <th>Order</th>
              <th>Outcome</th>
              <th>Workshop</th>
              <th className="number">Delivery days</th>
              <th className="number">Days available</th>
              <th>Reason</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.id}
                data-group={rowGroup(row, plan)}
                className={row.id === selectedId ? "selected" : undefined}
              >
                <td>
                  <button className="link-button" onClick={() => onSelect(row.id)}>
                    {row.id}
                  </button>
                </td>
                <td className="nowrap">{row.order_id ?? "-"}</td>
                <td>{outcomeLabel(row.outcome)}</td>
                <td>
                  {workshopText(plan, row)}
                  {choices[row.id]?.clear && <span className="unsaved block">Unsaved: undo</span>}
                  {choices[row.id]?.workshop_id && (
                    <span className="unsaved block">Unsaved: {choices[row.id].workshop_id}</span>
                  )}
                </td>
                <td className="number">{days(row.delivery_days)}</td>
                <td className="number">{row.days_available ?? "-"}</td>
                <td className="reason">{row.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length === 0 && <p className="muted">No rows in this filter.</p>}
    </section>
  );
}

// A review row's workshop is only an informational option; a selection comes from its decision record.
// It stays shown under a dispatcher's unsaved choice, because the row's figures are still for it.
function workshopText(plan: Plan, row: SummaryRow) {
  const selected = decisionFor(plan, row.id)?.selected_workshop;
  if (selected) {
    return selected;
  }
  return row.workshop ? `${row.workshop} (option only)` : "-";
}
