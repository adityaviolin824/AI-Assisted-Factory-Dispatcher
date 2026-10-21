import { days } from "@/lib/format";
import { outcomeLabel, SELECTED_OUTCOMES } from "@/lib/plan";
import type { RowChange, RowState } from "@/lib/types";

// What the dispatcher's choices changed when the plan was approved, as the backend listed it.
export default function ChangesTable({ changes }: { changes: RowChange[] }) {
  return (
    <section>
      <h2>What changed</h2>
      <p className="muted lede">
        Python planned once with the dispatcher&apos;s choices, so other tasks may have moved around them. Listed:
        every row whose outcome, workshop or delivery estimate differs from the review shown before approval.
      </p>
      {changes.length === 0 ? (
        <p className="muted">The choices changed no row&apos;s outcome, workshop or delivery estimate.</p>
      ) : (
        <div className="table-scroll">
          <table aria-label="What changed">
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
                  <td>{stateText(change.before)}</td>
                  <td>{stateText(change.after)}</td>
                  <td className="reason">{change.after.reason}</td>
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
function stateText(state: RowState) {
  const parts = [outcomeLabel(state.outcome)];
  if (state.workshop) {
    parts.push(SELECTED_OUTCOMES.includes(state.outcome) ? state.workshop : `${state.workshop} (option only)`);
  }
  if (state.delivery_days != null) {
    parts.push(`${days(state.delivery_days)} days`);
  }
  return parts.join(", ");
}
