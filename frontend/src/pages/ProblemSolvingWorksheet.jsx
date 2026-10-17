import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Home,
  CheckCircle2,
  ShieldAlert,
  Save,
  Lightbulb,
} from "lucide-react";
import { toast } from "sonner";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

const PROMPTS = [
  {
    id: "parenting_issue",
    label: "1. What is the parenting issue?",
    hint: "Example: exchange time, school event, medical decision, extracurricular activity.",
    rows: 3,
  },
  {
    id: "child_need",
    label: "2. What does the child need?",
    hint: "Safety, stability, routine, emotional support, medical care, school success.",
    rows: 3,
  },
  {
    id: "my_concern",
    label: "3. What is my concern?",
    hint: "Keep it factual.",
    rows: 3,
  },
  {
    id: "other_parent_concern",
    label: "4. What is the other parent likely concerned about?",
    hint: "This is not agreement. It is perspective-taking.",
    rows: 3,
  },
  {
    id: "safest_pathway",
    label: "5. What communication pathway is safest?",
    hint: "No direct contact / written only / third-party assisted / direct discussion.",
    rows: 2,
  },
];

const OPTIONS = [
  { id: "option_a", label: "Option A", rows: 2 },
  { id: "option_b", label: "Option B", rows: 2 },
  { id: "option_c", label: "Option C", rows: 2 },
];

const TAIL = [
  {
    id: "best_option",
    label: "7. Which option best protects the child and lowers conflict?",
    hint: "Pick from A, B, or C and explain briefly.",
    rows: 2,
  },
  {
    id: "boundary",
    label: "8. What boundary is needed?",
    hint: "Time, location, tone, third party, written record, no direct contact.",
    rows: 2,
  },
  {
    id: "next_step",
    label: "9. What is the next safe step?",
    hint: "One concrete action you can take in the next 24-72 hours.",
    rows: 2,
  },
];

function quickExit() {
  try {
    window.location.replace("https://www.google.com");
  } catch (_e) {
    window.location.href = "https://www.google.com";
  }
}

function Textarea({ id, label, hint, rows, value, onChange }) {
  return (
    <div className="rounded-2xl border border-[#E5E0EE] bg-white p-4 sm:p-5">
      <label htmlFor={id} className="block text-sm font-bold text-[#1A1330] mb-1">
        {label}
      </label>
      {hint && (
        <p className="text-xs text-[#6E6787] mb-2 leading-relaxed">{hint}</p>
      )}
      <textarea
        id={id}
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
        rows={rows}
        data-testid={`worksheet-${id}-input`}
        className="w-full rounded-xl border border-[#E5E0EE] bg-[#F8F7FC] px-3 py-2.5 text-sm text-[#1A1330] focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"
      />
    </div>
  );
}

export default function ProblemSolvingWorksheet() {
  const navigate = useNavigate();
  const [data, setData] = useState({});
  const [saving, setSaving] = useState(false);
  const [savedId, setSavedId] = useState(null);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    api
      .get("/safety-assessment/problem-solving/me")
      .then((r) => setHistory(r.data || []))
      .catch((err) => {
        logError("History load failed:", err);
      });
  }, []);

  const set = (id) => (v) => setData((prev) => ({ ...prev, [id]: v }));

  const submit = async () => {
    setSaving(true);
    try {
      const r = await api.post("/safety-assessment/problem-solving", data);
      setSavedId(r.data.worksheet_id);
      setHistory((prev) => [r.data, ...prev]);
      toast.success("Worksheet saved.");
    } catch (err) {
      logError("Save worksheet failed:", err);
      toast.error("Couldn’t save the worksheet. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen gentle-bg" data-testid="problem-solving-page">
      <div className="sticky top-0 z-40 backdrop-blur-md bg-[#C28771]/10 border-b border-[#C28771]/25">
        <div className="max-w-3xl mx-auto px-6 py-3 flex items-center justify-between gap-3">
          <Link
            to="/safety"
            className="inline-flex items-center gap-2 text-sm text-[#4B4567] hover:text-[#1A1330]"
            data-testid="worksheet-back-link"
          >
            <ArrowLeft size={14} />
            Back to Safety
          </Link>
          <button
            type="button"
            onClick={quickExit}
            className="inline-flex items-center gap-2 rounded-full bg-[#9A5D47] hover:bg-[#7F4B39] text-white px-4 py-2 text-sm font-medium shadow-sm"
            data-testid="worksheet-quick-exit"
          >
            <Home size={14} />
            Quick exit
          </button>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        <div className="mb-6">
          <div className="inline-flex items-center gap-2 text-[11px] uppercase tracking-[0.22em] text-[#3D1A78] font-bold mb-3">
            <Lightbulb size={12} /> Problem-Solving Worksheet
          </div>
          <h1 className="font-bold text-3xl sm:text-4xl text-[#1A1330] tracking-tight mb-3">
            Work through one decision at a time
          </h1>
          <p className="text-sm text-[#4B4567] leading-relaxed">
            Use this when you need to make a parenting decision and want to stay
            calm, child-focused, and safe. You can save as many of these as you
            want — your most recent five are listed below.
          </p>
        </div>

        <div className="rounded-2xl bg-[#FCE3DC] border border-[#9A3A23]/25 text-[#9A3A23] p-4 mb-6 text-xs flex items-start gap-2">
          <ShieldAlert size={14} className="shrink-0 mt-0.5" />
          <span>
            If using this worksheet causes fear or retaliation, do not share it
            with the other parent. Save it for your attorney, advocate, or
            mediator instead.
          </span>
        </div>

        <div className="space-y-3 mb-6">
          {PROMPTS.map((p) => (
            <Textarea
              key={p.id}
              id={p.id}
              label={p.label}
              hint={p.hint}
              rows={p.rows}
              value={data[p.id]}
              onChange={set(p.id)}
            />
          ))}

          <div className="rounded-2xl border border-[#E5E0EE] bg-white p-4 sm:p-5">
            <div className="text-sm font-bold text-[#1A1330] mb-1">
              6. What are three possible options?
            </div>
            <p className="text-xs text-[#6E6787] mb-3 leading-relaxed">
              Brainstorm three. They don&rsquo;t need to be perfect.
            </p>
            <div className="space-y-3">
              {OPTIONS.map((o) => (
                <div key={o.id}>
                  <label htmlFor={`worksheet-${o.id}`} className="block text-xs font-bold text-[#3D1A78] mb-1">{o.label}</label>
                  <textarea
                    id={`worksheet-${o.id}`}
                    value={data[o.id] || ""}
                    onChange={(e) => set(o.id)(e.target.value)}
                    rows={o.rows}
                    data-testid={`worksheet-${o.id}-input`}
                    className="w-full rounded-xl border border-[#E5E0EE] bg-[#F8F7FC] px-3 py-2.5 text-sm text-[#1A1330] focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"
                  />
                </div>
              ))}
            </div>
          </div>

          {TAIL.map((p) => (
            <Textarea
              key={p.id}
              id={p.id}
              label={p.label}
              hint={p.hint}
              rows={p.rows}
              value={data[p.id]}
              onChange={set(p.id)}
            />
          ))}
        </div>

        <div className="flex flex-wrap gap-3 justify-between">
          <Link
            to="/safety"
            className="inline-flex items-center gap-2 rounded-full bg-white border border-[#E5E0EE] text-[#4B4567] px-5 py-2.5 text-sm font-semibold hover:bg-[#F8F7FC]"
            data-testid="worksheet-to-resources-link"
          >
            <ArrowLeft size={14} /> Back to resources
          </Link>
          <button
            type="button"
            onClick={submit}
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-6 py-2.5 text-sm font-semibold shadow-md disabled:opacity-60"
            data-testid="worksheet-save-button"
          >
            <Save size={14} />
            {saving ? "Saving…" : savedId ? "Save another copy" : "Save worksheet"}
          </button>
        </div>

        {savedId && (
          <div
            className="mt-6 rounded-2xl bg-[#DCEEDF] border border-[#3C7858]/30 text-[#1F5C3B] p-4 flex items-start gap-2"
            data-testid="worksheet-saved-banner"
          >
            <CheckCircle2 size={16} className="shrink-0 mt-0.5" />
            <div className="text-sm">
              Saved to your account. You can come back to it any time from this
              page.
            </div>
          </div>
        )}

        {history.length > 0 && (
          <div className="mt-10">
            <div className="text-[11px] uppercase tracking-[0.2em] text-[#6E6787] font-bold mb-3">
              Recent worksheets
            </div>
            <div className="space-y-3">
              {history.slice(0, 5).map((h) => (
                <div
                  key={h.worksheet_id}
                  className="rounded-2xl border border-[#E5E0EE] bg-white p-4"
                  data-testid={`worksheet-history-${h.worksheet_id}`}
                >
                  <div className="text-xs text-[#6E6787] mb-1">
                    {new Date(h.created_at).toLocaleString()}
                  </div>
                  <div className="text-sm text-[#1A1330] font-bold mb-1 truncate">
                    {h.parenting_issue || "Untitled issue"}
                  </div>
                  {h.next_step && (
                    <div className="text-xs text-[#4B4567] line-clamp-2">
                      Next step: {h.next_step}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
