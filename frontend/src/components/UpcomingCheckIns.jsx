import { Link } from "react-router-dom";
import { CalendarClock } from "lucide-react";

const dayLabel = (iso) => {
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const d = new Date(`${iso}T00:00:00`);
  const diff = Math.round((d - today) / 86400000);
  if (diff < 0) return `Overdue · ${iso}`;
  if (diff === 0) return "Today";
  if (diff === 1) return "Tomorrow";
  return d.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
};

export const UpcomingCheckIns = ({ cases }) => {
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const limit = new Date(today); limit.setDate(limit.getDate() + 7);
  const rows = (cases || [])
    .filter((j) => j.is_creator && !j.archived && j.session_outcome?.follow_up_date)
    .filter((j) => new Date(`${j.session_outcome.follow_up_date}T00:00:00`) <= limit)
    .sort((a, b) => a.session_outcome.follow_up_date.localeCompare(b.session_outcome.follow_up_date));
  if (rows.length === 0) return null;
  return (
    <div className="mb-6 rounded-lg border border-align-blue/40 bg-align-blue/5 p-4" data-testid="upcoming-checkins">
      <div className="flex items-center gap-2 text-sm font-semibold">
        <CalendarClock className="h-4 w-4 text-align-blue" /> Follow-ups this week
        <span className="ml-1 rounded-full bg-align-blue/15 px-2 py-0.5 text-xs" data-testid="upcoming-checkins-count">{rows.length}</span>
      </div>
      <ul className="mt-2 divide-y divide-border/60 text-sm" data-testid="upcoming-checkins-list">
        {rows.map((j) => {
          const overdue = new Date(`${j.session_outcome.follow_up_date}T00:00:00`) < today;
          return (
            <li key={j.id} className="flex flex-wrap items-center justify-between gap-2 py-2" data-testid={`upcoming-checkin-${j.id}`}>
              <div className="min-w-0">
                <Link to={`/joint/${j.id}`} className="font-semibold tracking-wider text-brand-purple hover:underline" data-testid={`upcoming-checkin-code-${j.id}`}>{j.case_code || j.id.slice(0, 8)}</Link>
                <span className="ml-2 text-muted-foreground">{j.subject_label}{j.child_name ? ` · ${j.child_name}` : ""}</span>
                {j.session_outcome.chosen_steps?.length > 0 && <div className="truncate text-xs text-muted-foreground max-w-md">{j.session_outcome.chosen_steps.join(" · ")}</div>}
              </div>
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${overdue ? "bg-red-50 text-red-700" : "bg-white text-align-blue border border-align-blue/40"}`} data-testid={`upcoming-checkin-when-${j.id}`}>{dayLabel(j.session_outcome.follow_up_date)}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
};
