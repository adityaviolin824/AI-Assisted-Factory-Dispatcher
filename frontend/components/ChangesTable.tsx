import { days } from "@/lib/format";
import { outcomeLabel, SELECTED_OUTCOMES } from "@/lib/plan";
import type { RowChange, RowState } from "@/lib/types";

type Props = { changes: RowChange[]; preview?: boolean };

// What the dispatcher's choices changed when the plan was approved, as the backend listed it. In a
// preview, what they would change: nothing of a preview is saved.
export default function ChangesTable({ changes, preview = false }: Props) {
  const name = preview ? "What would change" : "What changed";
  return (
    <section className={preview ? "preview" : undefined}>
      <h2>{preview ? "Preview, not saved" : "What changed"}</h2>
      <p className="muted lede">
        {preview
          ? "Python calculated your choices once, as Approve all would, and saved nothing. The worklist shows this preview; changing any choice hides it. Listed: every row whose outcome, workshop or delivery estimate would differ from the review."
          : "Python planned once with the dispatcher's choices, so other tasks may have moved around them. Listed: every row whose outcome, workshop or delivery estimate differs from the review shown before approval."}
      </p>
      {changes.length === 0 ? (
        <p className="muted">
          {preview
            ? "Your choices would change no row's outcome, workshop or delivery estimate."
            : "The choices changed no row's outcome, workshop or delivery estimate."}
        </p>
      ) : (
        <div className="table-scroll">
          <table aria-label={name}>
            <thead>
              <tr>
                <th>Row</th>
                <th>Order</th>
                <th>Before</th>
                <th>After</th>
                <th>Why</th>
              </tr>
            </thead>
            <tbody>
              {changes.map((change) => (
                <tr key={change.id}>
                  <td className="nowrap">{change.id}</td>
                  <td className="nowrap">{change.order_id ?? "-"}</td>
                  <td>{change.before ? stateText(change.before) : "New batch, added by the dispatcher"}</td>
                  <td>{change.after ? stateText(change.after) : "Removed by the dispatcher"}</td>
                  <td className="reason">{change.after ? change.after.reason : "The dispatcher removed this added batch."}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

// A row that needs review or clarification has no workshop, or only an option, and may have no estimate.
// Approval only approves selected rows, so an approved row's workshop is selected too (Review again
// compares approved plans).
function stateText(state: RowState) {
  const parts = [outcomeLabel(state.outcome)];
  if (state.workshop) {
    const selected = SELECTED_OUTCOMES.includes(state.outcome) || state.outcome === "approved";
    parts.push(selected ? state.workshop : `${state.workshop} (option only)`);
  }
  if (state.delivery_days != null) {
    parts.push(`${days(state.delivery_days)} days`);
  }
  return parts.join(", ");
}
