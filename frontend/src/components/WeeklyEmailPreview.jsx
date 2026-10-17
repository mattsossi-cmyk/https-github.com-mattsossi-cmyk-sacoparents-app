import React, { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import {
  Mail, Loader2, ChevronDown, ChevronUp, Send, ShieldCheck,
  Sparkles, RefreshCw, CheckCircle2, Feather, Save, Check,
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
  const [noteDraft, setNoteDraft] = useState("");
  const [noteSaved, setNoteSaved] = useState("");
  const [noteMax, setNoteMax] = useState(280);
  const [noteSaving, setNoteSaving] = useState(false);
  const [noteJustSaved, setNoteJustSaved] = useState(false);

  const load = useCallback(async () => {
    try {
      const [previewR, noteR] = await Promise.all([
        api.get("/dashboard/weekly-email/preview"),
        api.get("/dashboard/weekly-email/note"),
      ]);
      setData(previewR.data || null);
      const n = noteR?.data || {};
      const savedText = (n.note || "").toString();
      setNoteSaved(savedText);
      setNoteDraft(savedText);
      if (typeof n.max_chars === "number") setNoteMax(n.max_chars);
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

  async function saveNote() {
    setNoteSaving(true);
    try {
      const r = await api.post("/dashboard/weekly-email/note", {
        note: noteDraft,
      });
      const saved = (r?.data?.note || "").toString();
      setNoteSaved(saved);
      setNoteDraft(saved);
      setNoteJustSaved(true);
      window.setTimeout(() => setNoteJustSaved(false), 1800);
      toast.success(
        saved
          ? "Note saved — it'll ride along on Sunday."
          : "Note cleared.",
      );
    } catch (err) {
      logError("save weekly note failed:", err);
      toast.error("Couldn't save your note. Try again in a moment.");
    } finally {
      setNoteSaving(false);
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
          <div className="text-[0.625rem] uppercase tracking-[0.22em] text-[#3D1A78] font-bold flex items-center gap-1.5">
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
          <div className="text-[0.625rem] uppercase tracking-[0.22em] text-[#6E6787] font-bold mb-2">
            Subject
          </div>
          <div className="text-sm font-semibold text-[#1A1330] mb-4">
            Your Sunday co-parenting progress snapshot
          </div>

          {/* Purple pill card matching the actual email */}
          <div className="rounded-2xl border border-[#D6CFE8] bg-[#F5F1FB] p-4">
            <div className="text-[0.625rem] uppercase tracking-[0.18em] text-[#3D1A78] font-bold">
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

          {/* Handwritten personal note — parents can add a short line
              that rides along on Sunday's email. Auto-clears after send. */}
          {(() => {
            const remaining = Math.max(0, noteMax - noteDraft.length);
            const dirty = noteDraft !== noteSaved;
            const overLimit = noteDraft.length > noteMax;
            const showSavedPreview = noteSaved && !dirty && !data.sent_this_week;
            return (
              <div
                className="mt-4 rounded-2xl border border-[#E4D8B8] bg-[#FFF9EB] p-4"
                data-testid="weekly-email-note-composer"
              >
                <div className="flex items-center gap-2 text-[0.625rem] uppercase tracking-[0.18em] text-[#8A6B12] font-bold">
                  <Feather size={12} /> Add a note (goes in Sunday&apos;s email)
                </div>
                <p className="text-[0.6875rem] text-[#6E5910] mt-1">
                  Optional handwritten line — think of it as a Post-it to your future self.
                  {data.sent_this_week
                    ? " This week's email already went out — save a note now and it'll appear on next Sunday's send."
                    : " Clears automatically once the Sunday email fires."}
                </p>
                <textarea
                  value={noteDraft}
                  onChange={(e) => setNoteDraft(e.target.value.slice(0, noteMax))}
                  maxLength={noteMax}
                  rows={3}
                  placeholder="e.g. Proud of us for showing up this week. Onwards."
                  className="mt-3 w-full rounded-xl border border-[#E4D8B8] bg-white p-3 text-sm text-[#3B2A05] focus:outline-none focus:border-[#8A6B12] focus:ring-2 focus:ring-[#F0DFA9] transition"
                  data-testid="weekly-email-note-textarea"
                  style={{ fontFamily: "'Caveat', 'Bradley Hand', cursive", fontSize: "18px", lineHeight: "1.4" }}
                />
                <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
                  <span
                    className={`text-[0.6875rem] font-semibold ${overLimit ? "text-[#B4223B]" : "text-[#8A6B12]"}`}
                    data-testid="weekly-email-note-counter"
                  >
                    {remaining} chars left
                  </span>
                  <div className="flex items-center gap-2">
                    {noteJustSaved && (
                      <span
                        className="inline-flex items-center gap-1 text-[0.6875rem] font-semibold text-[#1F5C3B]"
                        data-testid="weekly-email-note-saved-flash"
                      >
                        <Check size={12} /> Saved
                      </span>
                    )}
                    <button
                      type="button"
                      onClick={saveNote}
                      disabled={noteSaving || (!dirty)}
                      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition-all ${
                        (!dirty || noteSaving)
                          ? "bg-[#F0E4C4] text-[#8A6B12] cursor-not-allowed"
                          : "bg-[#8A6B12] text-white hover:brightness-110"
                      }`}
                      data-testid="weekly-email-note-save"
                    >
                      {noteSaving ? (
                        <Loader2 size={11} className="animate-spin" />
                      ) : (
                        <Save size={11} />
                      )}
                      {noteDraft.trim() === "" && noteSaved ? "Clear note" : "Save note"}
                    </button>
                  </div>
                </div>
                {showSavedPreview && (
                  <div
                    className="mt-3 rounded-xl border border-dashed border-[#E4D8B8] bg-white/70 px-3 py-2"
                    data-testid="weekly-email-note-preview"
                  >
                    <div className="text-[0.625rem] uppercase tracking-[0.18em] text-[#8A6B12] font-bold mb-1">
                      Preview in the email
                    </div>
                    <div
                      className="text-[#3B2A05]"
                      style={{ fontFamily: "'Caveat', 'Bradley Hand', cursive", fontSize: "18px", lineHeight: "1.45" }}
                    >
                      &ldquo;{noteSaved}&rdquo;
                    </div>
                  </div>
                )}
              </div>
            );
          })()}

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
                    key={`mile-${i}-${String(m).slice(0, 30)}`}
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

          {/* Community cheer digest (anonymised) */}
          {((p.cheers_received?.length || 0) > 0 ||
            (p.community_pulse?.length || 0) > 0) && (
            <div
              className="mt-4 rounded-xl border border-[#F4D0DE] bg-[#FEF5F8] px-3.5 py-3"
              data-testid="weekly-email-preview-cheers"
            >
              <div className="text-[0.625rem] uppercase tracking-[0.18em] text-[#B8125A] font-bold">
                {p.wall_opted_in ? "Community cheers" : "From the community"}
              </div>
              {p.cheers_received?.length > 0 && (
                <>
                  <div className="mt-1.5 text-[0.8125rem] text-[#4B4567]">
                    <strong className="text-[#1A1330]">
                      {p.cheers_received_total ?? 0} cheer
                      {(p.cheers_received_total ?? 0) === 1 ? "" : "s"}
                    </strong>{" "}
                    landed on your milestones this week.
                  </div>
                  <ul
                    className="mt-2 space-y-1"
                    data-testid="weekly-email-preview-cheers-received"
                  >
                    {p.cheers_received.slice(0, 5).map((r) => (
                      <li
                        key={`${r.badge_type}-${r.earned_at}`}
                        className="text-[0.8125rem] text-[#1A1330] flex items-baseline gap-1.5"
                      >
                        <span className="text-[#B8125A]">♥</span>
                        <span>
                          <strong>{r.cheer_count}</strong> on:{" "}
                          <em className="not-italic text-[#4B4567]">
                            {String(r.badge_label || "").replace(/\.$/, "")}
                          </em>
                        </span>
                      </li>
                    ))}
                  </ul>
                </>
              )}
              {p.community_pulse?.length > 0 && (
                <div
                  className={`text-[0.75rem] text-[#4B4567] ${p.cheers_received?.length ? "mt-2.5 pt-2.5 border-t border-dashed border-[#D6CFE8]" : "mt-1.5"}`}
                  data-testid="weekly-email-preview-community-pulse"
                >
                  Most-cheered community moment this week:{" "}
                  <em className="not-italic text-[#3D1A78]">
                    {String(p.community_pulse[0].badge_label || "").replace(
                      /\.$/,
                      "",
                    )}
                  </em>{" "}
                  · <strong>{p.community_pulse[0].cheer_count} cheers</strong>.
                </div>
              )}
            </div>
          )}

          <div className="mt-4 text-[0.6875rem] text-[#6E6787] italic">
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
                className="inline-flex items-center gap-1 text-[0.6875rem] font-semibold text-[#1F5C3B] px-2 py-1 rounded-full bg-[#F1F9F4] border border-[#B5DFC5]"
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
