/**
 * SpecialNeedsV2EducationalDeepDive.jsx
 *
 * Optional deep-dive companion to the lighter SNC v2 educational pathway.
 * Twelve sections, option-based questions where possible, section 3 (ARD)
 * only shown when the child's school state is Texas.
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import { toast } from "sonner";
import {
  ArrowLeft, ArrowRight, CheckCircle2, Loader2, Save, Sparkles,
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
        <LikertRow value={value} onChange={onChange} testid={`psych-deep-${key}`} />
      )}
      {item.type === "single" && (
        <SingleRow options={item.options || []} value={value} onChange={onChange}
          testid={`psych-deep-${key}`} />
      )}
      {item.type === "multi" && (
        <MultiRow options={item.options || []} value={value} onChange={onChange}
          testid={`psych-deep-${key}`} />
      )}
      {(item.type === "textarea" || item.type === "text") && (
        <TextRow value={value} onChange={onChange} testid={`psych-deep-${key}`} />
      )}
    </div>
  );
}


export default function SpecialNeedsV2PsychologicalDeepDive() {
  const navigate = useNavigate();
  const [schema, setSchema] = useState(null);
  const [responses, setResponses] = useState({});
  const [current, setCurrent] = useState(0);
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(async () => {
    setLoaded(false);
    try {
      const [s, m] = await Promise.all([
        api.get("/psych-deep/schema"),
        api.get("/psych-deep/me"),
      ]);
      setSchema(s.data);
      const existing = m.data?.assessment?.responses || {};
      setResponses(existing);
    } catch (err) {
      logError("edu-deep load", err);
      toast.error(err?.response?.data?.detail || "Could not load the deep dive.");
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

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

  const setAnswer = (key, value) => {
    setResponses((prev) => ({ ...prev, [key]: value }));
  };

  const save = async () => {
    setBusy(true);
    try {
      await api.post("/psych-deep/answers/bulk", { answers: responses });
      toast.success("Saved");
    } catch (err) {
      logError("edu-deep save", err);
      toast.error(err?.response?.data?.detail || "Could not save.");
    } finally { setBusy(false); }
  };

  const finish = async () => {
    setBusy(true);
    try {
      await api.post("/psych-deep/answers/bulk", { answers: responses });
      await api.post("/psych-deep/complete");
      await api.post("/psych-deep/report/generate");
      toast.success("Report ready.");
      navigate("/special-needs-v2/psychological-deep-dive/report");
    } catch (err) {
      logError("edu-deep finish", err);
      toast.error(err?.response?.data?.detail || "Could not generate the report.");
    } finally { setBusy(false); }
  };

  if (!loaded) {
    return (
      <AppShell>
        <div className="max-w-3xl mx-auto p-10 text-sm text-[#4B4567]">
          <Loader2 className="animate-spin inline" size={14} /> Loading Psychological Deep Dive...
        </div>
      </AppShell>
    );
  }

  if (!section) {
    return (
      <AppShell>
        <div className="max-w-3xl mx-auto p-10">
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">
            Psychological Deep Dive
          </div>
          <h1 className="font-serif text-3xl text-[#1A1330]">All done!</h1>
          <p className="text-sm text-[#4B4567] mt-2 max-w-xl">
            Generate the report to see which sections need follow-up and which are strengths.
          </p>
          <button onClick={finish} disabled={busy} data-testid="psych-deep-finish-empty"
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
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-10" data-testid="psych-deep-root">
        <div className="mb-4 flex items-center justify-between gap-2 flex-wrap">
          <Link to="/special-needs-v2" data-testid="psych-deep-back"
            className="inline-flex items-center gap-1 text-xs text-[#4B4567] underline">
            <ArrowLeft size={12} /> Back to Special Needs
          </Link>
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
            Psychological Needs · Deep Dive
          </div>
        </div>

        <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight">
          {section.number}. {section.name}
        </h1>
        {section.purpose && (
          <p className="text-sm text-[#4B4567] mt-2 italic">{section.purpose}</p>
        )}

        <div className="mt-4 flex flex-wrap items-center gap-2" data-testid="psych-deep-progress">
          {visibleSections.map((s, i) => (
            <button
              key={s.id}
              onClick={() => setCurrent(i)}
              className={`px-2.5 py-1 rounded-full text-[10px] font-semibold border transition-colors
                ${i === current
                  ? "bg-[#3D1A78] text-white border-[#3D1A78]"
                  : "bg-white text-[#3D1A78] border-[#E5E0EE] hover:bg-[#EEE9F7]"}`}
              data-testid={`psych-deep-goto-${s.id}`}
            >
              {s.number}
            </button>
          ))}
        </div>

        <div className="mt-6 bg-white rounded-3xl border border-[#E5E0EE] p-5 sm:p-7 shadow-sm">
          {section.items.map((it) => (
            <Item
              key={it.id}
              item={it}
              sectionId={section.id}
              value={responses[`${section.id}_${it.id}`]}
              onChange={(v) => setAnswer(`${section.id}_${it.id}`, v)}
            />
          ))}
        </div>

        <div className="mt-6 sticky bottom-4 bg-white/85 backdrop-blur border border-[#E5E0EE] rounded-full p-2 flex items-center justify-between gap-2" data-testid="psych-deep-nav">
          <button
            disabled={first}
            onClick={() => setCurrent(current - 1)}
            data-testid="psych-deep-prev"
            className="inline-flex items-center gap-1 px-4 py-2 rounded-full text-sm border border-[#E5E0EE] text-[#3D1A78] disabled:opacity-40"
          >
            <ArrowLeft size={13} /> Previous
          </button>
          <button
            onClick={save}
            disabled={busy}
            data-testid="psych-deep-save"
            className="inline-flex items-center gap-1 px-4 py-2 rounded-full text-sm border border-[#3D1A78] text-[#3D1A78] hover:bg-[#EEE9F7] disabled:opacity-60"
          >
            {busy ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />} Save
          </button>
          {last ? (
            <button
              onClick={finish}
              disabled={busy}
              data-testid="psych-deep-finish"
              className="inline-flex items-center gap-1 px-4 py-2 rounded-full text-sm bg-[#3D1A78] text-white hover:brightness-110 disabled:opacity-60"
            >
              {busy ? <Loader2 size={13} className="animate-spin" /> : <CheckCircle2 size={13} />} Generate report
            </button>
          ) : (
            <button
              onClick={() => setCurrent(current + 1)}
              data-testid="psych-deep-next"
              className="inline-flex items-center gap-1 px-4 py-2 rounded-full text-sm bg-[#3D1A78] text-white hover:brightness-110"
            >
              Next <ArrowRight size={13} />
            </button>
          )}
        </div>

        <p className="text-[11px] text-[#4B4567] mt-8 italic max-w-3xl">
          This deep dive is optional. It reflects only your perspective and does not diagnose, provide legal advice, or determine parental fitness.
        </p>
      </div>
    </AppShell>
  );
}
