import { useRef, useState } from "react";
import { errorText, readRunUsage, runUsageLink } from "@/lib/api";
import { calendarDate, count, dollars, duration, listText } from "@/lib/format";
import type { RunUsage } from "@/lib/types";

type Props = { runId: string };

const STAGE_NAMES: Record<string, string> = {
  intake: "Intake",
  link: "Linking",
  verify: "Verification",
  total: "Total",
};

// The open run's model calls, tokens and estimated model cost, all calculated by the backend from the
// run's call records. They are read only when the section is first opened, so opening a run sends no
// extra request.
export default function UsagePanel({ runId }: Props) {
  const [usage, setUsage] = useState<RunUsage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const requested = useRef(false);

  function load(open: boolean) {
    if (!open || requested.current) {
      return;
    }
    requested.current = true;
    readRunUsage(runId)
      .then(setUsage)
      .catch((caught) => setError(errorText(caught)));
  }

  const total = usage?.stages.find((stage) => stage.stage === "total");
  // Answered calls that this run did not pay for came from saved answers.
  const reused = total ? total.calls - total.failed - total.paid : 0;

  return (
    <section aria-label="Model usage and cost">
      <h2>Model usage and cost</h2>
      <details onToggle={(event) => load(event.currentTarget.open)}>
        <summary>Show calls, tokens and cost</summary>
        {!usage && !error && <p className="muted">Loading model usage...</p>}
        {error && <p className="error">Model usage is unavailable: {error}</p>}
        {usage && total && total.calls === 0 && <p className="muted">This run has no model call records.</p>}
        {usage && total && total.calls > 0 && (
          <>
            <dl className="facts">
              <dt>Estimated model cost this run</dt>
              <dd>{costText(total.cost_this_run)}</dd>
              <dt>Paid model calls</dt>
              <dd>
                {total.paid} of {count(total.calls, "call")}
                {reused > 0 && `; ${reused} reused saved answers at no new cost`}
              </dd>
              <dt>Model time this run</dt>
              <dd>{duration(total.seconds_this_run)}</dd>
              {reused > 0 && (
                <>
                  <dt>With no saved answers</dt>
                  <dd>
                    {costText(total.cost_fresh)}, {duration(total.seconds_fresh)} of model time
                  </dd>
                </>
              )}
              {total.failed > 0 && (
                <>
                  <dt>Failed calls</dt>
                  <dd>{total.failed}, with no recorded usage</dd>
                </>
              )}
              <dt>Dispatcher review and approval</dt>
              <dd>No model calls, $0</dd>
            </dl>
            <p className="muted">
              Estimated from the recorded tokens with the prices checked on {calendarDate(usage.prices_checked)}; not
              a provider invoice. Workshop production costs are separate.
            </p>
            <div className="table-scroll">
              <table aria-label="Model usage by stage">
                <thead>
                  <tr>
                    <th>Stage</th>
                    <th>Models</th>
                    <th className="number">Calls</th>
                    <th className="number">Paid calls</th>
                    <th className="number">Paid input tokens</th>
                    <th className="number">Provider-cached input</th>
                    <th className="number">Paid output tokens</th>
                    <th className="number">Cost this run</th>
                    <th className="number">Cost with no saved answers</th>
                  </tr>
                </thead>
                <tbody>
                  {usage.stages.map((stage) => (
                    <tr key={stage.stage}>
                      <td>{STAGE_NAMES[stage.stage] ?? stage.stage}</td>
                      <td>{listText(stage.models)}</td>
                      <td className="number">{stage.calls}</td>
                      <td className="number">{stage.paid}</td>
                      <td className="number">{stage.input_tokens.toLocaleString("en-GB")}</td>
                      <td className="number">{stage.cached_tokens.toLocaleString("en-GB")}</td>
                      <td className="number">{stage.output_tokens.toLocaleString("en-GB")}</td>
                      <td className="number">{dollars(stage.cost_this_run)}</td>
                      <td className="number">{dollars(stage.cost_fresh)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <a download={`${runId}-usage.json`} href={runUsageLink(runId)}>
              Download usage as JSON (numbers only, no messages)
            </a>
          </>
        )}
      </details>
    </section>
  );
}

// A null cost means a model in the run has no listed price: unavailable, never $0.
function costText(value: number | null) {
  return value == null ? "unavailable: a model in this run has no listed price" : dollars(value);
}
