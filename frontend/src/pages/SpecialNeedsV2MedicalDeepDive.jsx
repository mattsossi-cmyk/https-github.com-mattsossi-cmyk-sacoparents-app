/**
 * SpecialNeedsV2MedicalDeepDive.jsx
 *
 * Optional deep-dive companion focused on prescription sharing and medication
 * coordination between homes. Ten sections, option-based questions.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import SectionCoachCard from "../components/deepdive/SectionCoachCard";
import {
  FocusModeToggle,
  FocusItemProgress,
} from "../components/deepdive/FocusModePanel";
import { api } from "../lib/api";
import { toast } from "sonner";
import {
  ArrowLeft, ArrowRight, Check, CheckCircle2, Loader2, Sparkles,
} from "lucide-react";
import { logError } from "../lib/logger";


function LikertRow({ value, onChange, testid }) {
  const opts = [1, 2, 3, 4, 5];
  return (
    <div className="mt-2 grid grid-cols-6 gap-1.5" data-testid={testid}>
      {opts.map((v) => (
        <button
          key={v}
          type="button"
          onClick={() => onChange(v)}
          className={`h-11 rounded-full text-sm font-semibold border transition-all
            ${value === v
              ? "bg-[#3D1A78] text-white border-[#3D1A78]"
              : "bg-white text-[#1A1330] border-[#E5E0EE] hover:border-[#3D1A78]"}`}
          data-testid={`${testid}-${v}`}
        >
          {v}
        </button>
      ))}
      <button
        type="button"
        onClick={() => onChange("na")}
        className={`h-11 rounded-full text-xs font-semibold border transition-all
          ${value === "na"
            ? "bg-[#3D1A78] text-white border-[#3D1A78]"
            : "bg-white text-[#8471B3] border-[#E5E0EE] hover:border-[#3D1A78]"}`}
        data-testid={`${testid}-na`}
      >
        N/A
      </button>
    </div>
  );
}

function SingleRow({ options, value, onChange, testid }) {
  return (
    <div className="mt-2 flex flex-wrap gap-1.5" data-testid={testid}>
      {options.map((opt) => (
        <button
          key={opt}
          type="button"
          onClick={() => onChange(opt)}
          className={`px-3 py-2 min-h-[40px] rounded-full text-xs font-medium border transition-all
            ${value === opt
              ? "bg-[#3D1A78] text-white border-[#3D1A78]"
              : "bg-white text-[#1A1330] border-[#E5E0EE] hover:border-[#3D1A78]"}`}
        >
          {opt}
        </button>
      ))}
    </div>
  );
}

function MultiRow({ options, value, onChange, testid }) {
  const arr = Array.isArray(value) ? value : [];
  const toggle = (opt) => {
    if (arr.includes(opt)) onChange(arr.filter((o) => o !== opt));
    else onChange([...arr, opt]);
  };
  return (
    <div className="mt-2 flex flex-wrap gap-1.5" data-testid={testid}>
      {options.map((opt) => (
        <button
          key={opt}
          type="button"
          onClick={() => toggle(opt)}
          className={`px-3 py-2 min-h-[40px] rounded-full text-xs font-medium border transition-all
            ${arr.includes(opt)
              ? "bg-[#3D1A78] text-white border-[#3D1A78]"
              : "bg-white text-[#1A1330] border-[#E5E0EE] hover:border-[#3D1A78]"}`}
        >
          {opt}
        </button>
      ))}
    </div>
  );
}

function TextRow({ value, onChange, testid }) {
  return (
    <textarea
      value={value || ""}
      onChange={(e) => onChange(e.target.value)}
      placeholder="Optional — write anything else you want the report to note"
      className="mt-2 w-full min-h-[80px] rounded-2xl border border-[#E5E0EE] p-3 text-sm outline-none focus:border-[#3D1A78]"
      data-testid={testid}
    />
  );
}

function Item({ item, sectionId, value, onChange }) {
  const key = `${sectionId}_${item.id}`;
  return (
    <div className="mt-4">
      <div className="text-sm font-semibold text-[#1A1330]">{item.prompt}</div>
      {item.type === "likert" && (
        <LikertRow value={value} onChange={onChange} testid={`med-deep-${key}`} />
      )}
      {item.type === "single" && (
        <SingleRow options={item.options || []} value={value} onChange={onChange}
          testid={`med-deep-${key}`} />
      )}
      {item.type === "multi" && (
        <MultiRow options={item.options || []} value={value} onChange={onChange}
          testid={`med-deep-${key}`} />
      )}
      {(item.type === "textarea" || item.type === "text") && (
        <TextRow value={value} onChange={onChange} testid={`med-deep-${key}`} />
      )}
    </div>
  );
}


export default function SpecialNeedsV2MedicalDeepDive() {
  const navigate = useNavigate();
  const [schema, setSchema] = useState(null);
  const [responses, setResponses] = useState({});
  const [current, setCurrent] = useState(0);
  const [qIdx, setQIdx] = useState(0);
  const [focusMode, setFocusMode] = useState(true);
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [saveState, setSaveState] = useState("idle"); // idle | saving | saved
  const saveTimer = useRef(null);
  const firstApplyRef = useRef(true);

  const load = useCallback(async () => {
    setLoaded(false);
    try {
      const [s, m] = await Promise.all([
        api.get("/med-deep/schema"),
        api.get("/med-deep/me"),
      ]);
      setSchema(s.data);
      const existing = m.data?.assessment?.responses || {};
      setResponses(existing);
    } catch (err) {
      logError("med-deep load", err);
      toast.error(err?.response?.data?.detail || "Could not load the deep dive.");
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Debounced auto-save: 800ms after the last change
  useEffect(() => {
    if (!loaded) return;
    if (firstApplyRef.current) { firstApplyRef.current = false; return; }
    if (saveTimer.current) clearTimeout(saveTimer.current);
    setSaveState("saving");
    saveTimer.current = setTimeout(async () => {
      try {
        await api.post("/med-deep/answers/bulk", { answers: responses });
        setSaveState("saved");
      } catch (err) {
        logError("med-deep autosave", err);
        setSaveState("idle");
      }
    }, 800);
    return () => saveTimer.current && clearTimeout(saveTimer.current);
  }, [responses, loaded]);

  const visibleSections = useMemo(() => {
    if (!schema) return [];
    return (schema.sections || []).filter((s) => {
      if (s.gate) {
        const gk = `${s.id}_${s.gate.item}`;
        if (responses[gk] !== s.gate.value) return false;
      }
      return true;
    });
  }, [schema, responses]);

  const section = visibleSections[current];

  // Section-level answered counts
  const sectionStats = useMemo(() => {
    const stats = {};
    for (const s of visibleSections) {
      const total = (s.items || []).length;
      const answered = (s.items || []).filter((it) => {
        const v = responses[`${s.id}_${it.id}`];
        return v !== undefined && v !== null && v !== "" && !(Array.isArray(v) && v.length === 0);
      }).length;
      stats[s.id] = { total, answered, pct: total ? answered / total : 0 };
    }
    return stats;
  }, [visibleSections, responses]);

  const overallPct = useMemo(() => {
    let a = 0, t = 0;
    for (const s of visibleSections) {
      a += sectionStats[s.id]?.answered || 0;
      t += sectionStats[s.id]?.total || 0;
    }
    return t ? Math.round((a / t) * 100) : 0;
  }, [visibleSections, sectionStats]);

  const setAnswer = (key, value) => {
    setResponses((prev) => ({ ...prev, [key]: value }));
  };

  const finish = async () => {
    setBusy(true);
    try {
      await api.post("/med-deep/answers/bulk", { answers: responses });
      await api.post("/med-deep/complete");
      await api.post("/med-deep/report/generate");
      toast.success("Report ready.");
      navigate("/special-needs-v2/medical-deep-dive/report");
    } catch (err) {
      logError("med-deep finish", err);
      toast.error(err?.response?.data?.detail || "Could not generate the report.");
    } finally { setBusy(false); }
  };

  if (!loaded) {
    return (
      <AppShell>
        <div className="max-w-3xl mx-auto p-10 text-sm text-[#4B4567]">
          <Loader2 className="animate-spin inline" size={14} /> Loading Medication Coordination Deep Dive...
        </div>
      </AppShell>
    );
  }

  if (!section) {
    return (
      <AppShell>
        <div className="max-w-3xl mx-auto p-10">
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">
            Medical · Prescription Deep Dive
          </div>
          <h1 className="font-serif text-3xl text-[#1A1330]">All done!</h1>
          <p className="text-sm text-[#4B4567] mt-2 max-w-xl">
            Generate the report to see which medication coordination areas need follow-up and which are strengths.
          </p>
          <button onClick={finish} disabled={busy} data-testid="med-deep-finish-empty"
            className="mt-6 inline-flex items-center gap-2 px-5 py-3 rounded-full bg-[#3D1A78] text-white text-sm">
            {busy ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />} Generate report
          </button>
        </div>
      </AppShell>
    );
  }

  const first = current === 0;
  const last = current === visibleSections.length - 1;

  return (
    <AppShell>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-10" data-testid="med-deep-root">
        <div className="mb-4 flex items-center justify-between gap-2 flex-wrap">
          <Link to="/special-needs-v2" data-testid="med-deep-back"
            className="inline-flex items-center gap-1 text-xs text-[#4B4567] underline">
            <ArrowLeft size={12} /> Back to Special Needs
          </Link>
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
            Medical Needs · Prescription Deep Dive
          </div>
        </div>

        <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight flex items-start justify-between gap-3">
          <span>{section.number}. {section.name}</span>
          <FocusModeToggle
            focusMode={focusMode}
            onToggle={() => setFocusMode((v) => !v)}
            testid="med-deep-toggle-focus"
          />
        </h1>
        {section.purpose && (
          <p className="text-sm text-[#4B4567] mt-2 italic">{section.purpose}</p>
        )}

        {focusMode && section.items.length > 0 && (
          <FocusItemProgress
            qIdx={Math.min(qIdx, section.items.length - 1)}
            total={section.items.length}
            sectionIdx={current}
            sectionTotal={visibleSections.length}
            testid="med-deep-focus-progress"
          />
        )}

        {/* Meta row: section counter + section answered badge + save state */}
        <div className="mt-3 flex items-center gap-3 flex-wrap text-[11px] text-[#4B4567]" data-testid="med-deep-meta">
          <span className="font-semibold text-[#3D1A78]">Section {current + 1} of {visibleSections.length}</span>
          <span className="text-[#8471B3]">·</span>
          <span data-testid="med-deep-section-progress">
            {sectionStats[section.id]?.answered || 0} of {sectionStats[section.id]?.total || 0} answered in this section
          </span>
          <span className="text-[#8471B3]">·</span>
          <span data-testid="med-deep-save-state" className={
            saveState === "saving" ? "text-[#8A5B00]"
            : saveState === "saved" ? "text-[#1F5C3B]"
            : "text-[#8471B3]"
          }>
            {saveState === "saving" ? (<><Loader2 size={10} className="inline animate-spin" /> Saving…</>)
             : saveState === "saved" ? (<><Check size={10} className="inline" /> Saved</>)
             : "Auto-saves as you answer"}
          </span>
        </div>

        {/* Overall progress bar */}
        <div className="mt-3" data-testid="med-deep-overall-progress">
          <div className="flex items-center gap-2 text-[10px] text-[#8471B3]">
            <div className="flex-1 h-1.5 rounded-full bg-[#EEE9F7] overflow-hidden">
              <div className="h-full bg-gradient-to-r from-[#3D1A78] to-[#6B3FA0] transition-all" style={{ width: `${overallPct}%` }} />
            </div>
            <span className="font-semibold text-[#3D1A78]">{overallPct}%</span>
          </div>
        </div>

        {/* Section pips (colour-coded by answered progress) */}
        <div className="mt-4 flex flex-wrap items-center gap-2" data-testid="med-deep-progress">
          {visibleSections.map((s, i) => {
            const st = sectionStats[s.id] || { answered: 0, total: 0, pct: 0 };
            const fullyAnswered = st.total > 0 && st.answered === st.total;
            const partial = st.answered > 0 && !fullyAnswered;
            let cls = "bg-white text-[#3D1A78] border-[#E5E0EE] hover:bg-[#EEE9F7]";
            if (i === current) cls = "bg-[#3D1A78] text-white border-[#3D1A78]";
            else if (fullyAnswered) cls = "bg-[#1F5C3B] text-white border-[#1F5C3B]";
            else if (partial) cls = "bg-[#FFF6E5] text-[#8A5B00] border-[#F0D9A8]";
            return (
              <button
                key={s.id}
                onClick={() => { setCurrent(i); setQIdx(0); }}
                title={s.name}
                aria-label={`${s.name} — ${st.answered} of ${st.total} answered`}
                className={`px-2.5 py-1 rounded-full text-[10px] font-semibold border transition-colors ${cls}`}
                data-testid={`med-deep-goto-${s.id}`}
              >
                {s.number}
              </button>
            );
          })}
        </div>

        <div className="mt-6 bg-white rounded-3xl border border-[#E5E0EE] p-5 sm:p-7 shadow-sm">
          {(focusMode
            ? [section.items[Math.min(qIdx, section.items.length - 1)]].filter(Boolean)
            : section.items
          ).map((it) => (
            <Item
              key={it.id}
              item={it}
              sectionId={section.id}
              value={responses[`${section.id}_${it.id}`]}
              onChange={(v) => setAnswer(`${section.id}_${it.id}`, v)}
            />
          ))}
        </div>

        <SectionCoachCard
          apiPrefix="/med-deep"
          testidBase="med-deep"
          sectionId={section.id}
          sectionName={section.name}
        />

        <div className="mt-6 sticky bottom-4 bg-white/85 backdrop-blur border border-[#E5E0EE] rounded-full p-2 flex items-center justify-between gap-2" data-testid="med-deep-nav">
          <button
            disabled={focusMode ? (first && qIdx === 0) : first}
            onClick={() => {
              if (focusMode) {
                if (qIdx > 0) {
                  setQIdx(qIdx - 1);
                } else if (!first) {
                  const prevSection = visibleSections[current - 1];
                  setCurrent(current - 1);
                  setQIdx(Math.max(0, (prevSection?.items?.length || 1) - 1));
                }
              } else {
                setCurrent(current - 1);
              }
            }}
            data-testid="med-deep-prev"
            className="inline-flex items-center gap-1 px-4 py-2 rounded-full text-sm border border-[#E5E0EE] text-[#3D1A78] disabled:opacity-40"
          >
            <ArrowLeft size={13} /> Previous
          </button>
          {focusMode && qIdx < section.items.length - 1 ? (
            <button
              onClick={() => setQIdx(qIdx + 1)}
              data-testid="med-deep-next"
              className="inline-flex items-center gap-1 px-4 py-2 rounded-full text-sm bg-[#3D1A78] text-white hover:brightness-110"
            >
              Next <ArrowRight size={13} />
            </button>
          ) : last ? (
            <button
              onClick={finish}
              disabled={busy}
              data-testid="med-deep-finish"
              className="inline-flex items-center gap-1 px-4 py-2 rounded-full text-sm bg-[#3D1A78] text-white hover:brightness-110 disabled:opacity-60"
            >
              {busy ? <Loader2 size={13} className="animate-spin" /> : <CheckCircle2 size={13} />} Generate report
            </button>
          ) : (
            <button
              onClick={() => { setCurrent(current + 1); setQIdx(0); }}
              data-testid="med-deep-next"
              className="inline-flex items-center gap-1 px-4 py-2 rounded-full text-sm bg-[#3D1A78] text-white hover:brightness-110"
            >
              Next <ArrowRight size={13} />
            </button>
          )}
        </div>

        <p className="text-[11px] text-[#4B4567] mt-8 italic max-w-3xl">
          This deep dive is optional. It reflects only your perspective and does not diagnose,
          provide medical advice, prescribe, or determine parental fitness. In a medical
          emergency call 911 or the poison control centre.
        </p>
      </div>
    </AppShell>
  );
}
