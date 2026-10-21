import { amount, days, listText, percent } from "@/lib/format";
import type { Plan, WorkshopProfile } from "@/lib/types";

type Props = { plan: Plan; profiles: Record<string, WorkshopProfile> | undefined };

// One row per workshop: what it can make, whether it may take work, its capacity, and its queue
// before and after the work this plan reserves.
export default function QueueTable({ plan, profiles }: Props) {
  return (
    <section>
      <h2>Workshops and queues</h2>
      <p className="muted">
        A tentative plan over the snapshot of {plan.dispatch_date}: queue days before the plan and after the
        production and expected rework it reserves. Nothing is sent to a workshop.
      </p>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Workshop</th>
              <th>Status</th>
              <th>Makes</th>
              <th className="number">Max batch</th>
              <th className="number">Pieces per day</th>
              <th className="number">Pickup days</th>
              <th className="number">Defect rate</th>
              <th className="number">Cost per piece</th>
              <th className="number">Queue before</th>
              <th className="number">Queue after</th>
            </tr>
          </thead>
          <tbody>
            {Object.keys(plan.queues_before_plan).map((workshopId) => {
              const profile = profiles?.[workshopId];
              return (
                <tr key={workshopId}>
                  <td>
                    {workshopId} {profile?.name}
                  </td>
                  <td>{profile?.status ?? "-"}</td>
                  <td>{profile ? listText(profile.makes) : "-"}</td>
                  <td className="number">{profile ? (profile.max_batch ?? "no limit") : "-"}</td>
                  <td className="number">{profile?.capacity ?? "-"}</td>
                  <td className="number">{profile?.lead_days ?? "-"}</td>
                  <td className="number">{percent(profile?.defect_rate)}</td>
                  <td className="number">{amount(profile?.cost)}</td>
                  <td className="number">{days(plan.queues_before_plan[workshopId])}</td>
                  <td className="number">{days(plan.queues_after_plan[workshopId])}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
