import React, { useEffect, useState } from "react";
import { CalendarHeart, Send } from "lucide-react";
import { toast } from "sonner";
import { api } from "../lib/api";
import { logError } from "../lib/logger";
import { WeeklyNotePreview } from "./WeeklyNotePreview";

const pct = (n, d) => (d ? Math.round((n / d) * 100) : 0);
const weekLabel = (iso) =>
  `Week of ${new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" })}`;

const Big = ({ label, value, hint, testid }) => (
  <div className="rounded-2xl border border-[#E5E0EE] bg-[#FAF8FD] p-4" data-testid={testid}>
    <div className="text-[10px] uppercase tracking-[0.15em] text-[#857E9C]">{label}</div>
    <div className="font-serif text-3xl text-[#1A1330] mt-1">{value}</div>
    <div className="text-xs text-[#857E9C] mt-1">{hint}</div>
  </div>
);

const Row = ({ w }) => (
  <tr className="border-t border-[#F0ECF6]" data-testid={`admin-weekly-note-row-${w.week_key}`}>
    <td className="py-2 pr-3 text-[#1A1330] font-semibold">
      {weekLabel(w.sent_on)}
      {w.counting && (
        <span className="block sm:inline-block sm:ml-2 mt-1 sm:mt-0 w-fit text-[10px] font-semibold text-amber-700 bg-amber-50 border border-amber-200 rounded-full px-2 py-0.5">
          still counting
        </span>
      )}
    </td>
    <td className="py-2 pr-3 text-right">{w.sent}</td>
    <td className="py-2 pr-3 text-right">
      {w.progressed} <span className="text-[#857E9C]">({pct(w.progressed, w.sent)}%)</span>
    </td>
    <td className="py-2 text-right">
      {w.clicked} <span className="text-[#857E9C]">({pct(w.clicked, w.sent)}%)</span>
    </td>
  </tr>
);

function SampleButton() {
  const [busy, setBusy] = useState(false);
  const send = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/admin/self-journey-weekly/sample");
      toast.success(`Sample weekly note sent to ${data.sent_to}`);
    } catch (e) {
      logError("weekly note sample failed", e);
      toast.error(e?.response?.data?.detail || "Couldn't send the sample right now.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <button
      type="button"
      onClick={send}
      disabled={busy}
      data-testid="admin-weekly-note-sample"
      className="inline-flex items-center gap-1.5 px-3 py-2 rounded-full bg-[#3D1A78] hover:bg-[#2c1259] text-white text-xs font-semibold disabled:opacity-60 transition-colors"
    >
      <Send size={13} />
      {busy ? "Sending…" : "Email me a sample"}
    </button>
  );
}

export default function WeeklyNoteStatsTile() {
  const [data, setData] = useState(null);

  useEffect(() => {
    api
      .get("/admin/self-journey-weekly/stats")
      .then(({ data: d }) => setData(d))
      .catch((e) => logError("weekly note stats load failed", e));
  }, []);

  const weeks = data?.weeks || [];
  const t = data?.totals || { sent: 0, progressed: 0, clicked: 0 };
  return (
    <div className="card-soft p-6" data-testid="admin-weekly-note-tile">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <div className="eyebrow flex items-center gap-2">
            <CalendarHeart size={12} className="text-[#3D1A78]" />
            Weekly Self Journey note · Last 8 weeks
          </div>
          <div className="font-serif text-xl text-[#1A1330] mt-1">Do parents come back after their note?</div>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <WeeklyNotePreview />
          <SampleButton />
        </div>
      </div>
      <p className="text-xs text-[#857E9C] mt-1 mb-4">
        "Made progress" means any Self Journey step within 7 days of the note. "Clicked" means they tapped
        "Open my Self Journey" in the email.
      </p>
      {weeks.length === 0 ? (
        <div
          className="rounded-2xl border border-dashed border-[#E5E0EE] bg-[#FAF8FD] p-6 text-center text-sm text-[#4B4567]"
          data-testid="admin-weekly-note-empty"
        >
          No weekly notes have gone out yet. The first notes go out on Sunday at 5:00 pm Central, to parents
          who made Self Journey progress that week. Numbers will appear here after that.
        </div>
      ) : (
        <>
          <div className="grid sm:grid-cols-3 gap-4 mb-5">
            <Big label="Notes sent" value={t.sent} hint={`${weeks.length} week${weeks.length === 1 ? "" : "s"}`} testid="admin-weekly-note-total-sent" />
            <Big label="Made progress" value={`${pct(t.progressed, t.sent)}%`} hint={`${t.progressed} parent${t.progressed === 1 ? "" : "s"} came back`} testid="admin-weekly-note-total-progressed" />
            <Big label="Clicked the button" value={`${pct(t.clicked, t.sent)}%`} hint={`${t.clicked} parent${t.clicked === 1 ? "" : "s"} tapped through`} testid="admin-weekly-note-total-clicked" />
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs sm:text-sm" data-testid="admin-weekly-note-table">
              <thead>
                <tr className="text-[10px] uppercase tracking-[0.15em] text-[#857E9C]">
                  <th className="text-left pb-2 font-semibold">Week</th>
                  <th className="text-right pb-2 pr-3 font-semibold">Sent</th>
                  <th className="text-right pb-2 pr-3 font-semibold">Progress</th>
                  <th className="text-right pb-2 font-semibold">Clicked</th>
                </tr>
              </thead>
              <tbody>
                {weeks.map((w) => (
                  <Row key={w.week_key} w={w} />
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
