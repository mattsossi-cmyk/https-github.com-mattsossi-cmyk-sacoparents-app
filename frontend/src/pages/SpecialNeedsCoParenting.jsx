/**
 * SpecialNeedsCoParenting.jsx — the 13-section Special Needs Co-Parenting Assessment.
 *
 * Renders the assessment as a section-by-section flow with save-and-resume.
 * On completion, routes to /special-needs/report.
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import { toast } from "sonner";
import { ArrowLeft, ArrowRight, CheckCircle2, Save, Loader2 } from "lucide-react";
import { logError } from "../lib/logger";

const RATING_CLASSES =
  "px-3 py-2 text-sm rounded-full border transition-all data-[selected=true]:bg-[#3D1A78] data-[selected=true]:text-white data-[selected=true]:border-[#3D1A78] border-[#D6CFE8] bg-white text-[#1A1330] hover:border-[#3D1A78]";

function RatingRow({ item, value, onChange, scale }) {
  return (
    <div className="py-4 border-b border-[#EEE9F7] last:border-b-0" data-testid={`snc-item-${item.id}`}>
      <div className="text-sm text-[#1A1330] mb-3">{item.prompt}</div>
      <div className="flex flex-wrap gap-2">
        {scale.map((opt) => (
          <button
            key={String(opt.value)}
            type="button"
            data-testid={`snc-${item.id}-opt-${opt.value}`}
            data-selected={value === opt.value}
            onClick={() => onChange(item.id, opt.value)}
            className={RATING_CLASSES}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function MultiSelect({ item, value = [], onChange }) {
  const list = Array.isArray(value) ? value : [];
  const toggle = (opt) => {
    const next = list.includes(opt) ? list.filter((x) => x !== opt) : [...list, opt];
    onChange(item.id, next);
  };
  return (
    <div className="py-4 border-b border-[#EEE9F7] last:border-b-0" data-testid={`snc-item-${item.id}`}>
      <div className="text-sm text-[#1A1330] mb-3">{item.prompt}</div>
      <div className="flex flex-wrap gap-2">
        {item.options.map((opt) => (
          <button
            key={opt}
            type="button"
            data-testid={`snc-${item.id}-opt-${opt.slice(0, 20)}`}
            data-selected={list.includes(opt)}
            onClick={() => toggle(opt)}
            className={RATING_CLASSES}
          >
            {opt}
          </button>
        ))}
      </div>
    </div>
  );
}

function SingleSelect({ item, value, onChange }) {
  return (
    <div className="py-4 border-b border-[#EEE9F7] last:border-b-0" data-testid={`snc-item-${item.id}`}>
      <div className="text-sm text-[#1A1330] mb-3">{item.prompt}</div>
      <div className="flex flex-wrap gap-2">
        {item.options.map((opt) => (
          <button
            key={opt}
            type="button"
            data-testid={`snc-${item.id}-opt-${opt.slice(0, 20)}`}
            data-selected={value === opt}
            onClick={() => onChange(item.id, opt)}
            className={RATING_CLASSES}
          >
            {opt}
          </button>
        ))}
      </div>
    </div>
  );
}

function TextItem({ item, value = "", onChange, multiline = false }) {
  return (
    <div className="py-4 border-b border-[#EEE9F7] last:border-b-0" data-testid={`snc-item-${item.id}`}>
      <label className="block text-sm text-[#1A1330] mb-2">{item.prompt}</label>
      {multiline ? (
        <textarea
          data-testid={`snc-${item.id}-input`}
          value={value}
          onChange={(e) => onChange(item.id, e.target.value)}
          rows={3}
          className="w-full rounded-2xl border border-[#D6CFE8] bg-white px-4 py-3 text-sm text-[#1A1330] focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"
        />
      ) : (
        <input
          data-testid={`snc-${item.id}-input`}
          value={value}
          onChange={(e) => onChange(item.id, e.target.value)}
          className="w-full rounded-2xl border border-[#D6CFE8] bg-white px-4 py-3 text-sm text-[#1A1330] focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"
        />
      )}
    </div>
  );
}

function renderItem(item, answers, setAnswer, likertScale, consistencyScale) {
  const val = answers[item.id];
  switch (item.type) {
    case "likert":
      return <RatingRow key={item.id} item={item} value={val} onChange={setAnswer} scale={likertScale} />;
    case "consistency":
      return <RatingRow key={item.id} item={item} value={val} onChange={setAnswer} scale={consistencyScale} />;
    case "multi":
      return <MultiSelect key={item.id} item={item} value={val} onChange={setAnswer} />;
    case "single":
      return <SingleSelect key={item.id} item={item} value={val} onChange={setAnswer} />;
    case "text":
      return <TextItem key={item.id} item={item} value={val} onChange={setAnswer} />;
    case "textarea":
      return <TextItem key={item.id} item={item} value={val} onChange={setAnswer} multiline />;
    default:
      return null;
  }
}

export default function SpecialNeedsCoParenting() {
  const nav = useNavigate();
  const [schema, setSchema] = useState(null);
  const [answers, setAnswers] = useState({});
  const [current, setCurrent] = useState(0);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState(null);
  const [loading, setLoading] = useState(true);
  const [pendingChanges, setPendingChanges] = useState({});
  const [completing, setCompleting] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [sRes, mRes] = await Promise.all([
          api.get("/snc/schema"),
          api.get("/snc/me").catch(() => ({ data: { exists: false } })),
        ]);
        setSchema(sRes.data);
        const existing = mRes.data?.exists ? mRes.data.answers || {} : {};
        setAnswers(existing);
        // Jump to the first section that has at least one unanswered scored/intake item.
        const secs = sRes.data.sections;
        const idx = secs.findIndex((s) =>
          s.items.some(
            (it) =>
              (it.type === "likert" || it.type === "consistency") &&
              existing[it.id] === undefined
          )
        );
        setCurrent(idx >= 0 ? idx : 0);
      } catch (err) {
        logError("snc load", err);
        toast.error("Could not load the assessment.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const flushSave = useCallback(async (changes) => {
    if (!changes || Object.keys(changes).length === 0) return;
    setSaving(true);
    try {
      await api.post("/snc/answers/bulk", { answers: changes });
      setSavedAt(new Date());
    } catch (err) {
      logError("snc save", err);
      toast.error("Save failed. Your changes are kept locally.");
    } finally {
      setSaving(false);
    }
  }, []);

  // Debounced autosave whenever pendingChanges grows.
  useEffect(() => {
    if (!schema) return;
    if (Object.keys(pendingChanges).length === 0) return;
    const t = setTimeout(() => {
      const toSend = pendingChanges;
      setPendingChanges({});
      flushSave(toSend);
    }, 900);
    return () => clearTimeout(t);
  }, [pendingChanges, schema, flushSave]);

  const setAnswer = useCallback((qid, value) => {
    setAnswers((prev) => ({ ...prev, [qid]: value }));
    setPendingChanges((prev) => ({ ...prev, [qid]: value }));
  }, []);

  const sections = schema?.sections || [];
  const section = sections[current];
  const totalSections = sections.length;

  const overallProgress = useMemo(() => {
    if (!schema) return { answered: 0, total: 0 };
    let total = 0;
    let answered = 0;
    sections.forEach((s) =>
      s.items.forEach((it) => {
        if (it.type === "likert" || it.type === "consistency") {
          total += 1;
          if (answers[it.id] !== undefined) answered += 1;
        }
      })
    );
    return { answered, total };
  }, [schema, sections, answers]);

  const goToSection = async (idx) => {
    // Flush any queued changes before nav.
    if (Object.keys(pendingChanges).length > 0) {
      const toSend = pendingChanges;
      setPendingChanges({});
      await flushSave(toSend);
    }
    setCurrent(Math.max(0, Math.min(totalSections - 1, idx)));
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const saveNow = async () => {
    if (Object.keys(pendingChanges).length > 0) {
      const toSend = pendingChanges;
      setPendingChanges({});
      await flushSave(toSend);
    }
    toast.success("Progress saved. You can come back anytime.");
  };

  const complete = async () => {
    if (Object.keys(pendingChanges).length > 0) {
      const toSend = pendingChanges;
      setPendingChanges({});
      await flushSave(toSend);
    }
    setCompleting(true);
    try {
      await api.post("/snc/complete");
      await api.post("/snc/report/generate");
      nav("/special-needs/report");
    } catch (err) {
      logError("snc complete", err);
      toast.error("Could not complete the assessment.");
    } finally {
      setCompleting(false);
    }
  };

  if (loading) {
    return (
      <AppShell>
        <div className="max-w-3xl mx-auto px-4 py-10 text-[#4B4567]">
          <Loader2 className="animate-spin" /> Loading assessment…
        </div>
      </AppShell>
    );
  }

  if (!schema || !section) {
    return (
      <AppShell>
        <div className="max-w-3xl mx-auto px-4 py-10 text-[#4B4567]">
          Assessment schema could not load. Please refresh.
        </div>
      </AppShell>
    );
  }

  const pct = overallProgress.total > 0
    ? Math.round((overallProgress.answered / overallProgress.total) * 100)
    : 0;

  return (
    <AppShell>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-10" data-testid="snc-assessment-root">
        {/* Header */}
        <div className="mb-6">
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">
            Special Needs Co-Parenting Assessment
          </div>
          <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight">
            Build a child-focused plan across both homes.
          </h1>
          <p className="text-sm text-[#4B4567] mt-2">
            13 sections. Save anytime. This is an educational planning tool — not
            a diagnosis, not a determination of parental fitness, not legal advice.
          </p>
        </div>

        {/* Progress bar */}
        <div className="mb-6">
          <div className="flex items-center justify-between text-xs text-[#4B4567] mb-2">
            <div data-testid="snc-progress-label">
              Section {current + 1} of {totalSections} · Overall {pct}% ({overallProgress.answered}/{overallProgress.total} rated)
            </div>
            <div className="flex items-center gap-3">
              {saving && (
                <span className="inline-flex items-center gap-1 text-[#3D1A78]">
                  <Loader2 size={12} className="animate-spin" /> Saving…
                </span>
              )}
              {!saving && savedAt && (
                <span className="inline-flex items-center gap-1 text-[#2E7D5F]">
                  <CheckCircle2 size={12} /> Saved
                </span>
              )}
            </div>
          </div>
          <div className="h-2 w-full bg-[#EEE9F7] rounded-full overflow-hidden">
            <div
              className="h-full bg-[#3D1A78] transition-all"
              style={{ width: `${pct}%` }}
              data-testid="snc-progress-bar"
            />
          </div>
        </div>

        {/* Section tabs */}
        <div className="mb-6 overflow-x-auto -mx-4 px-4">
          <div className="flex gap-2 min-w-max">
            {sections.map((s, i) => (
              <button
                key={s.id}
                data-testid={`snc-nav-${s.id}`}
                onClick={() => goToSection(i)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all whitespace-nowrap ${
                  i === current
                    ? "bg-[#3D1A78] text-white border-[#3D1A78]"
                    : "bg-white text-[#4B4567] border-[#D6CFE8] hover:border-[#3D1A78]"
                }`}
              >
                {i + 1}. {s.name}
              </button>
            ))}
          </div>
        </div>

        {/* Section content */}
        <div
          className="bg-white rounded-3xl border border-[#E5E0EE] p-5 sm:p-8 shadow-sm"
          data-testid={`snc-section-${section.id}`}
        >
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-2">
            Section {section.number} of 13
          </div>
          <h2 className="font-serif text-2xl text-[#1A1330] mb-1">{section.name}</h2>
          {section.note && (
            <p className="text-xs text-[#8471B3] italic mt-2 mb-4">{section.note}</p>
          )}
          {section.id === "s11" && (
            <div
              className="mb-4 p-4 rounded-2xl bg-[#F8EDE4] border border-[#EBD9C4] text-sm text-[#7A4A2E]"
              data-testid="snc-safety-note"
            >
              This section is captured privately in your report and is never
              shared automatically with the other parent. Positive responses will
              also guide you to the full Family Violence &amp; Communication
              Safety Assessment.
            </div>
          )}
          <div className="mt-4">
            {section.items.map((it) =>
              renderItem(it, answers, setAnswer, schema.response_scale, schema.consistency_scale)
            )}
          </div>
        </div>

        {/* Footer nav */}
        <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
          <button
            data-testid="snc-prev"
            onClick={() => goToSection(current - 1)}
            disabled={current === 0}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm border border-[#D6CFE8] text-[#1A1330] bg-white disabled:opacity-40 hover:border-[#3D1A78]"
          >
            <ArrowLeft size={14} /> Previous
          </button>
          <div className="flex items-center gap-3">
            <button
              data-testid="snc-save-later"
              onClick={saveNow}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm border border-[#D6CFE8] text-[#3D1A78] bg-white hover:border-[#3D1A78]"
            >
              <Save size={14} /> Save &amp; come back later
            </button>
            {current < totalSections - 1 ? (
              <button
                data-testid="snc-next"
                onClick={() => goToSection(current + 1)}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm bg-[#3D1A78] text-white hover:brightness-110"
              >
                Next <ArrowRight size={14} />
              </button>
            ) : (
              <button
                data-testid="snc-complete"
                onClick={complete}
                disabled={completing}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm bg-[#3D1A78] text-white hover:brightness-110 disabled:opacity-60"
              >
                {completing ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
                Complete &amp; generate report
              </button>
            )}
          </div>
        </div>

        <div className="mt-6 text-center">
          <Link to="/dashboard" className="text-xs text-[#4B4567] underline" data-testid="snc-back-dashboard">
            Back to dashboard
          </Link>
        </div>
      </div>
    </AppShell>
  );
}
