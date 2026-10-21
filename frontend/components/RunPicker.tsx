import type { RunSummary } from "@/lib/types";

type Props = { runs: RunSummary[]; runId: string; onChange: (runId: string) => void };

export default function RunPicker({ runs, runId, onChange }: Props) {
  return (
    <label>
      Saved run
      <select value={runId} onChange={(event) => onChange(event.target.value)}>
        <option value="">Choose a run</option>
        {runs.map((run) => (
          <option key={run.run_id} value={run.run_id}>
            {run.run_id}: {run.label} ({run.messages} messages)
          </option>
        ))}
      </select>
    </label>
  );
}
