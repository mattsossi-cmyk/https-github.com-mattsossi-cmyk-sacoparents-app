import React, { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import {
  Mail, Loader2, ChevronDown, ChevronUp, Send, ShieldCheck,
  Sparkles, RefreshCw, CheckCircle2,
} from "lucide-react";
import { toast } from "sonner";
import { logError } from "../lib/logger";

/**
 * WeeklyEmailPreview — inline dashboard card that mirrors the Sunday
 * progress email pixel-for-pixel so parents can see exactly what will
 * land in their inbox. Includes a "Send it to me now" action for
 * on-demand copies.
 */
const DOW_NAMES = [
  "Monday", "Tuesday", "Wednesday", "Thursday",
  "Friday", "Saturday", "Sunday",
];

function daysUntilSunday(weekday) {
  if (typeof weekday !== "number") return null;
  if (weekday === 6) return 0;
  return 6 - weekday;
}

export default function WeeklyEmailPreview() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [sending, setSending] = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await api.get("/dashboard/weekly-email/preview");
      setData(r.data || null);
    } catch (err) {
      logError("weekly email preview failed:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function sendNow() {
    setSending(true);
    try {
      const r = await api.post("/dashboard/weekly-email/send", { force: true });
      if (r.data?.already_sent === false) {
        toast.success("Sent — check your inbox in a moment.");
      } else {
        toast.success("Fresh copy on its way.");
      }
      load();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      toast.error(
        typeof detail === "string"
          ? detail
          : "Couldn't send the email right now. Try again shortly.",
      );
    } finally {
      setSending(false);
    }
  }

  if (loading) {
    return (
      <section
        className="rounded-3xl border border-[#E5E0EE] bg-white p-5 shadow-sm flex items-center gap-2 text-sm text-[#4B4567]"
        data-testid="weekly-email-preview-loading"
      >
        <Loader2 size={14} className="animate-spin" />
        Preparing your Sunday snapshot preview…
      </section>
    );
  }
  if (!data || !data.preview) return null;

  const p = data.preview;
  const daysLeft = daysUntilSunday(data.weekday_utc);
  const weekdayName = DOW_NAMES[data.weekday_utc] || "";
  const streakLine = p.streak_days > 0
    ? `${p.streak_days}-day dashboard streak — consistency is your superpower.`
    : "A new week's a great time to start a streak.";
  const alignLine = typeof p.alignment_pct === "number"
    ? `Latest alignment with your co-parent: ${p.alignment_pct}%.`
    : "";

  return (
    <section
      className="rounded-3xl border border-[#E5E0EE] bg-white p-5 sm:p-6 shadow-sm"
      data-testid="weekly-email-preview"
      data-sent-this-week={data.sent_this_week ? "1" : "0"}
    >
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-start gap-3 text-left"
        data-testid="weekly-email-preview-toggle"
      >
        <div className="shrink-0 h-9 w-9 rounded-full bg-[#F5F1FB] flex items-center justify-center text-[#3D1A78]">
          <Mail size={16} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[10px] uppercase tracking-[0.22em] text-[#3D1A78] font-bold flex items-center gap-1.5">
            <Sparkles size={11} /> Sunday email preview
          </div>
          <div className="font-serif text-lg text-[#1A1330] leading-snug mt-0.5">
            {data.sent_this_week
              ? "This week's email is already on its way."
              : data.is_sunday_utc
                ? "Today is Sunday — your snapshot fires next."
                : daysLeft === 1
                  ? `Your snapshot goes out tomorrow (Sunday).`
                  : `Your next snapshot goes out in ${daysLeft} day${daysLeft === 1 ? "" : "s"} on Sunday.`}
          </div>
          <div className="text-xs text-[#4B4567] mt-0.5">
            {open ? "Tap to hide the preview." : `Tap to see exactly what parents on ${weekdayName} will read.`}
          </div>
        </div>
        <div className="shrink-0 text-[#3D1A78]">
          {open ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </div>
      </button>

      {open && (
        <div
          className="mt-5 rounded-2xl border border-[#E5E0EE] bg-[#FCFBFE] p-4 sm:p-5"
          data-testid="weekly-email-preview-body"
        >
          {/* Subject-line mock */}
          <div className="text-[10px] uppercase tracking-[0.22em] text-[#857E9C] font-bold mb-2">
            Subject
          </div>
          <div className="text-sm font-semibold text-[#1A1330] mb-4">
            Your Sunday co-parenting progress snapshot
          </div>

          {/* Purple pill card matching the actual email */}
          <div className="rounded-2xl border border-[#D6CFE8] bg-[#F5F1FB] p-4">
            <div className="text-[10px] uppercase tracking-[0.18em] text-[#3D1A78] font-bold">
              Weekly progress
            </div>
            <div
              className="font-serif text-2xl text-[#1A1330] font-extrabold mt-1 leading-tight"
              data-testid="weekly-email-preview-count"
            >
              {p.completed_count} of {p.total} milestones lit.
            </div>
            <div className="text-xs text-[#4B4567] mt-2">{streakLine}</div>
            {alignLine && (
              <div
                className="text-xs text-[#4B4567] mt-1"
                data-testid="weekly-email-preview-alignment"
              >
                {alignLine}
              </div>
            )}
          </div>

          {/* Milestone list */}
          {p.milestones_this_week?.length > 0 ? (
            <>
              <div className="mt-4 text-sm text-[#1A1330]">
                This week you lit:
              </div>
              <ul
                className="mt-2 space-y-1.5"
                data-testid="weekly-email-preview-milestones"
              >
                {p.milestones_this_week.map((m, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-sm text-[#1A1330]"
                  >
                    <CheckCircle2
                      size={14}
                      className="shrink-0 mt-0.5 text-[#1F5C3B]"
                    />
                    <span>{m}</span>
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <div
              className="mt-4 text-sm text-[#4B4567]"
              data-testid="weekly-email-preview-empty"
            >
              No new milestones lit this week — small steps still count.
            </div>
          )}

          <div className="mt-4 text-[11px] text-[#857E9C] italic">
            Small, steady work is what mediators love to see.
          </div>

          {/* Actions */}
          <div className="mt-5 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={sendNow}
              disabled={sending}
              className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full text-xs font-semibold bg-[#3D1A78] text-white hover:brightness-110 transition-all ${sending ? "opacity-60 cursor-progress" : ""}`}
              data-testid="weekly-email-preview-send-now"
            >
              {sending ? (
                <Loader2 size={12} className="animate-spin" />
              ) : (
                <Send size={12} />
              )}
              {data.sent_this_week ? "Send me another copy" : "Send it to me now"}
            </button>
            <button
              type="button"
              onClick={load}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full text-xs font-semibold border border-[#E5E0EE] text-[#3D1A78] bg-white hover:bg-[#F1EEF7] transition-all"
              data-testid="weekly-email-preview-refresh"
              title="Recompute the preview from your latest progress"
            >
              <RefreshCw size={12} /> Refresh preview
            </button>
            {data.sent_this_week && (
              <span
                className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#1F5C3B] px-2 py-1 rounded-full bg-[#F1F9F4] border border-[#B5DFC5]"
                data-testid="weekly-email-preview-already-sent"
              >
                <ShieldCheck size={11} /> Already sent this week
              </span>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
