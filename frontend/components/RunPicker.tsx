import { count } from "@/lib/format";
import type { RunSummary } from "@/lib/types";

type Props = { runs: RunSummary[]; runId: string; onChange: (runId: string) => void; disabled?: boolean };

export default function RunPicker({ runs, runId, onChange, disabled = false }: Props) {
  return (
    <label>
      Saved run
      <select value={runId} disabled={disabled} onChange={(event) => onChange(event.target.value)}>
        <option value="">Choose a run</option>
        {runs.map((run) => (
          <option key={run.run_id} value={run.run_id}>
            {run.run_id}: {run.label} ({count(run.messages, "message")})
          </option>
        ))}
      </select>
    </label>
  );
}
