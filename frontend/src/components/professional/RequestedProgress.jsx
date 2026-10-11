import React from "react";
import { CheckCircle2, Circle, CircleDashed } from "lucide-react";

const META = {
  done: { label: "Done", cls: "bg-[#E6F4EC] text-[#1F5C3B] border-[#B5DFC5]", Icon: CheckCircle2 },
  in_progress: { label: "In progress", cls: "bg-[#FFF6E5] text-[#8A5B00] border-[#F0D9A8]", Icon: CircleDashed },
  todo: { label: "Not started", cls: "bg-[#F1EEF7] text-[#4B4567] border-[#E5E0EE]", Icon: Circle },
};

const day = (iso) => {
  const d = iso ? new Date(iso) : null;
  return d && !Number.isNaN(d.getTime())
    ? d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })
    : "";
};

// Status-only view of what a professional asked a parent to complete. Never shows answers.
export const RequestedProgress = ({ rows, testid }) => {
  if (!rows) {
    return <p className="text-[11px] text-[#857E9C] mt-2" data-testid={`${testid}-not-joined`}>Hasn&rsquo;t joined yet</p>;
  }
  if (!rows.length) return null;
  const done = rows.filter((r) => r.status === "done").length;
  return (
    <div className="mt-2.5" data-testid={testid}>
      <div className="text-[10px] uppercase tracking-[0.15em] font-bold text-[#857E9C] mb-1.5" data-testid={`${testid}-count`}>
        Requested · {done} of {rows.length} done
      </div>
      <ul className="space-y-1">
        {rows.map((r) => {
          const m = META[r.status] || META.todo;
          return (
            <li key={r.key} className="flex items-center justify-between gap-2 text-[12px]" data-testid={`${testid}-${r.key}`}>
              <span className="text-[#1A1330] truncate">{r.title}</span>
              <span className={`shrink-0 inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10.5px] font-semibold ${m.cls}`} data-testid={`${testid}-${r.key}-status`}>
                <m.Icon size={10} aria-hidden /> {m.label}
                {r.status === "done" && r.finished_at ? ` · ${day(r.finished_at)}` : ""}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
};

export const fmtDay = day;
