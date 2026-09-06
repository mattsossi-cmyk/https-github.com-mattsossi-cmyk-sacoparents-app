/**
 * SpecialNeedsV2.jsx — SNC v2 assessment.
 *
 * Flow:
 *   step 0 → category picker (Medical / Educational / Psychological / Multiple)
 *   steps 1..8 → the 8-step workflow, split into per-pathway sub-sections.
 *
 * Autosaves via bulk endpoint, generates the report on completion.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import { toast } from "sonner";
import {
  ArrowLeft, ArrowRight, CheckCircle2, Save, Loader2, Sparkles, Users, X, LayoutList,
} from "lucide-react";
import { logError } from "../lib/logger";


const CHIP = "min-h-[44px] px-4 py-2 text-sm rounded-full border transition-all active:scale-95 data-[selected=true]:bg-[#3D1A78] data-[selected=true]:text-white data-[selected=true]:border-[#3D1A78] data-[selected=true]:shadow-sm border-[#D6CFE8] bg-white text-[#1A1330] hover:border-[#3D1A78]";


function Likert({ id, value, onChange, scale }) {
  const numeric = (scale || []).filter((o) => typeof o.value === "number");
  const nonNumeric = (scale || []).filter((o) => typeof o.value !== "number");
  return (
    <div className="space-y-2" data-testid={`snc2-likert-${id}`}>
      {/* Numeric buttons — evenly sized, easy phone tap targets. */}
      <div className="grid grid-cols-5 gap-2">
        {numeric.map((opt) => {
          const selected = value === opt.value;
          return (
            <button
              key={String(opt.value)}
              type="button"
              data-testid={`snc2-${id}-opt-${opt.value}`}
              data-selected={selected}
              onClick={() => onChange(opt.value)}
              className={`min-h-[48px] rounded-2xl border px-2 py-2 flex flex-col items-center justify-center transition-all text-[#1A1330] active:scale-95 ${
                selected
                  ? "bg-[#3D1A78] text-white border-[#3D1A78] shadow-md"
                  : "bg-white border-[#D6CFE8] hover:border-[#3D1A78]"
              }`}
            >
              <span className="text-base font-bold leading-none">{opt.value}</span>
              <span className={`hidden sm:block text-[10px] leading-tight text-center mt-1 ${selected ? "text-white/80" : "text-[#4B4567]"}`}>
                {opt.label}
              </span>
            </button>
          );
        })}
      </div>
      {/* Legend under the numbers — one line on mobile, doubles as the scale key. */}
      <div className="flex justify-between text-[10px] text-[#8471B3] px-1 sm:hidden">
        {numeric.map((opt) => (
          <span key={`legend-${opt.value}`} className="max-w-[52px] text-center leading-tight">
            {opt.label.replace("Strongly ", "").replace("disagree", "SD").replace("Disagree", "D").replace("Unsure", "?").replace("Agree", "A").replace("SA", "SA")}
          </span>
        ))}
      </div>
      {/* Non-numeric options (N/A) on their own row. */}
      {nonNumeric.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {nonNumeric.map((opt) => {
            const selected = value === opt.value;
            return (
              <button
                key={String(opt.value)}
                type="button"
                data-testid={`snc2-${id}-opt-${opt.value}`}
                data-selected={selected}
                onClick={() => onChange(opt.value)}
                className={`min-h-[44px] px-4 rounded-full border text-sm transition-all ${
                  selected
                    ? "bg-[#3D1A78] text-white border-[#3D1A78]"
                    : "bg-white text-[#4B4567] border-[#D6CFE8] hover:border-[#3D1A78]"
                }`}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

function OptionButtons({ id, value, options, onChange, multi }) {
  const list = Array.isArray(value) ? value : [];
  const isSel = (o) => multi ? list.includes(o) : value === o;
  const toggle = (o) => {
    if (multi) {
      onChange(list.includes(o) ? list.filter((x) => x !== o) : [...list, o]);
    } else {
      onChange(o);
    }
  };
  return (
    <div className="flex flex-wrap gap-2" data-testid={`snc2-opts-${id}`}>
      {(options || []).map((opt) => (
        <button
          key={opt}
          type="button"
          data-testid={`snc2-${id}-opt-${opt.slice(0, 24)}`}
          data-selected={isSel(opt)}
          onClick={() => toggle(opt)}
          className={CHIP}
        >
          {opt}
        </button>
      ))}
    </div>
  );
}


function ItemInput({ item, value, onChange, scale, qid }) {
  const tid = qid || item.id;
  const t = item.type;
  if (t === "likert") return <Likert id={tid} value={value} onChange={onChange} scale={scale} />;
  if (t === "single") return <OptionButtons id={tid} value={value} options={item.options} onChange={onChange} />;
  if (t === "multi") return <OptionButtons id={tid} value={value || []} options={item.options} onChange={onChange} multi />;
  if (t === "textarea") return (
    <textarea data-testid={`snc2-${tid}-input`} rows={3}
      value={value || ""} onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-2xl border border-[#D6CFE8] bg-white px-4 py-3 text-sm text-[#1A1330] focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"/>
  );
  return (
    <input data-testid={`snc2-${tid}-input`}
      value={value || ""} onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-2xl border border-[#D6CFE8] bg-white px-4 py-3 text-sm text-[#1A1330] focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"/>
  );
}


const DEEP_DIVE_DISMISS_KEY = "snc2.deepDiveDismissed";

function readDismissedDeepDives() {
  try {
    const raw = localStorage.getItem(DEEP_DIVE_DISMISS_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch (err) {
    // localStorage disabled/private mode/parse error — safe to treat as
    // "nothing dismissed yet". Warn so a debug session sees it.
    logError("SpecialNeedsV2: could not read deep-dive dismiss state", err);
    return {};
  }
}

function DeepDiveCard({ id, testid, linkTestid, dismissTestid, title, sections, description, route, cta }) {
  const [dismissed, setDismissed] = useState(() => !!readDismissedDeepDives()[id]);
  const setDismiss = (val) => {
    setDismissed(val);
    try {
      const current = readDismissedDeepDives();
      if (val) current[id] = true;
      else delete current[id];
      localStorage.setItem(DEEP_DIVE_DISMISS_KEY, JSON.stringify(current));
    } catch (err) {
      // Storage full or private mode — the dismiss will simply not
      // persist across reloads. Non-fatal, but worth surfacing.
      logError("SpecialNeedsV2: could not persist deep-dive dismiss", err);
    }
  };

  if (dismissed) {
    return (
      <div className="rounded-3xl border border-dashed border-[#D6CFE8] bg-[#FCFBFE] p-5 sm:p-6 opacity-90" data-testid={testid}>
        <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#8471B3] mb-1 flex items-center gap-2">
          Set aside
        </div>
        <h3 className="font-serif text-base text-[#4B4567]">{title}</h3>
        <p className="text-xs text-[#4B4567] mt-1 mb-3 italic">You marked this deep dive as not applicable. You can bring it back any time.</p>
        <button
          type="button"
          onClick={() => setDismiss(false)}
          data-testid={`${dismissTestid}-restore`}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border border-[#3D1A78] text-[#3D1A78] hover:bg-[#EEE9F7]"
        >
          Bring back
        </button>
      </div>
    );
  }

  return (
    <div className="relative rounded-3xl border-2 border-[#3D1A78]/30 bg-gradient-to-br from-[#EEE9F7] to-[#F5F0FA] p-5 sm:p-6" data-testid={testid}>
      <button
        type="button"
        onClick={() => setDismiss(true)}
        aria-label={`Set aside ${title}`}
        data-testid={dismissTestid}
        className="absolute top-3 right-3 inline-flex items-center justify-center w-7 h-7 rounded-full text-[#8471B3] hover:bg-white/70 hover:text-[#3D1A78]"
      >
        <X size={14} />
      </button>
      <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1 flex items-center gap-2">
        <Sparkles size={12} /> Optional · {sections}
      </div>
      <h3 className="font-serif text-lg text-[#1A1330]">{title}</h3>
      <p className="text-xs text-[#4B4567] mt-1 mb-4">{description}</p>
      <div className="flex flex-wrap items-center gap-3">
        <Link
          to={route}
          data-testid={linkTestid}
          className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-full text-sm font-semibold bg-[#3D1A78] text-white hover:brightness-110"
        >
          <Sparkles size={13} /> {cta}
        </Link>
        <button
          type="button"
          onClick={() => setDismiss(true)}
          data-testid={`${dismissTestid}-link`}
          className="text-xs text-[#8471B3] underline hover:text-[#3D1A78]"
        >
          Not applicable to us
        </button>
      </div>
    </div>
  );
}



function CategoryPicker({ catalog, initial, initialChildName, onSubmit }) {
  const [picked, setPicked] = useState(initial || []);
  const [childName, setChildName] = useState(initialChildName || "");
  const toggle = (id) => setPicked((prev) => {
    if (id === "multiple") return prev.includes("multiple") ? prev.filter((p) => p !== "multiple") : ["multiple"];
    const next = prev.includes(id) ? prev.filter((p) => p !== id) : [...prev.filter((p) => p !== "multiple"), id];
    return next;
  });
  const disabled = picked.length === 0;
  return (
    <div data-testid="snc2-picker">
      <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">
        Our child has unique needs
      </div>
      <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight">
        Which of your child&apos;s unique needs are we coordinating?
      </h1>
      <p className="text-sm text-[#4B4567] mt-3 max-w-2xl">
        Your child&apos;s educational, psychological or medical needs do not always
        fit into one category. Select every area that applies. The SA CoParents
        App will help you organise each need, understand professional
        recommendations, identify areas requiring parental coordination, and
        prepare a child-focused plan.
      </p>

      <div className="mt-6 grid gap-3">
        {(catalog || []).map((p) => (
          <button
            key={p.id}
            type="button"
            onClick={() => toggle(p.id)}
            data-testid={`snc2-picker-${p.id}`}
            data-selected={picked.includes(p.id)}
            className="text-left rounded-3xl border-2 border-[#E5E0EE] bg-white p-4 sm:p-5 shadow-sm transition-all hover:border-[#3D1A78] hover:shadow-md active:scale-[0.99] data-[selected=true]:border-[#3D1A78] data-[selected=true]:bg-[#F8F5FC] data-[selected=true]:ring-2 data-[selected=true]:ring-[#3D1A78]/25"
          >
            <div className="flex items-start gap-3">
              <div className={`shrink-0 mt-0.5 w-6 h-6 rounded-full border-2 grid place-items-center ${picked.includes(p.id) ? "bg-[#3D1A78] border-[#3D1A78]" : "border-[#D6CFE8] bg-white"}`}>
                {picked.includes(p.id) && <CheckCircle2 size={18} className="text-white" strokeWidth={3} />}
              </div>
              <div className="min-w-0 flex-1">
                <div className="font-serif text-lg text-[#1A1330]">{p.name}</div>
                <p className="text-sm text-[#4B4567] mt-1">{p.summary}</p>
                {(p.examples || []).length > 0 && (
                  <ul className="mt-2 grid sm:grid-cols-2 gap-x-4 text-xs text-[#4B4567] list-disc pl-5">
                    {p.examples.slice(0, 8).map((ex) => <li key={ex}>{ex}</li>)}
                  </ul>
                )}
              </div>
            </div>
          </button>
        ))}
      </div>

      <div className="mt-6">
        <label className="block text-xs font-semibold uppercase tracking-[0.18em] text-[#3D1A78] mb-2">
          Child&apos;s name or nickname (optional)
        </label>
        <input
          data-testid="snc2-child-name"
          value={childName}
          onChange={(e) => setChildName(e.target.value)}
          className="w-full max-w-md rounded-full border border-[#D6CFE8] bg-white px-4 py-2.5 text-sm text-[#1A1330] focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"
          placeholder="e.g. Alex"
        />
      </div>

      <div className="mt-8">
        <button
          data-testid="snc2-picker-continue"
          disabled={disabled}
          onClick={() => onSubmit(picked, childName)}
          className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-3 min-h-[48px] rounded-full text-sm font-semibold bg-[#3D1A78] text-white hover:brightness-110 disabled:opacity-60"
        >
          <Sparkles size={14} /> Start assessment
        </button>
      </div>

      <div className="mt-10 rounded-3xl border border-[#E5E0EE] bg-white p-5 sm:p-7" data-testid="snc2-deep-dives-block">
        <div
          className="mb-5 rounded-2xl border-2 border-[#B5DFC5] bg-[#F1F9F4] p-4 sm:p-5 flex items-start gap-3"
          data-testid="snc2-deep-dives-optional-banner"
        >
          <div className="shrink-0 h-8 w-8 rounded-full bg-white flex items-center justify-center text-[#1F5C3B] mt-0.5">
            <Sparkles size={14} />
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#1F5C3B]">
              Your core Special Needs Assessment is enough on its own
            </div>
            <p className="text-sm sm:text-[15px] text-[#0F3B25] mt-1 leading-relaxed">
              Once you finish the assessment above, you have a complete
              Special Needs Care Plan. The three deep dives below are{" "}
              <strong>optional</strong> and should only be completed when
              additional coordination detail in that specific area would help
              your family. Skip any that don&apos;t apply.
            </p>
          </div>
        </div>
        <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1 flex items-center gap-2">
          <Sparkles size={12} /> Optional companion deep dives
        </div>
        <h2 className="font-serif text-xl text-[#1A1330]">Pick any, all, or none</h2>
        <p className="text-xs text-[#4B4567] mt-1 mb-5 max-w-2xl">
          These three deep dives are entirely optional add-ons for parents who want extra coordination detail in a specific area. Complete any that apply to your child&apos;s situation — or skip them completely.
        </p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <DeepDiveCard
            id="edu"
            testid="snc2-edu-deep-dive-cta"
            linkTestid="snc2-edu-deep-dive-cta-link"
            dismissTestid="snc2-edu-deep-dive-dismiss"
            title="Educational Needs"
            sections="12 sections · ~10-15 min"
            description="IEP, 504, ARD (Texas), tutoring, or homework coordination across two homes."
            route="/special-needs-v2/educational-deep-dive"
            cta="Open Educational Deep Dive"
          />
          <DeepDiveCard
            id="psych"
            testid="snc2-psych-deep-dive-cta"
            linkTestid="snc2-psych-deep-dive-cta-link"
            dismissTestid="snc2-psych-deep-dive-dismiss"
            title="Psychological / Behavioural"
            sections="11 sections · ~10-15 min"
            description="Therapy, medication, crisis planning, and emotional support across two homes."
            route="/special-needs-v2/psychological-deep-dive"
            cta="Open Psychological Deep Dive"
          />
          <DeepDiveCard
            id="med"
            testid="snc2-med-deep-dive-cta"
            linkTestid="snc2-med-deep-dive-cta-link"
            dismissTestid="snc2-med-deep-dive-dismiss"
            title="Medical · Prescriptions & Medication"
            sections="10 sections · ~10-15 min"
            description="Prescription sharing, refills, administration, school meds, and controlled medications."
            route="/special-needs-v2/medical-deep-dive"
            cta="Open Medical Deep Dive"
          />
        </div>
      </div>

      <div className="mt-10 rounded-3xl border border-[#E5E0EE] bg-[#FCFBFE] p-5 sm:p-7" data-testid="snc2-samples-block">
        <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">Prefer to preview first?</div>
        <h2 className="font-serif text-xl text-[#1A1330] mb-3">Download a Special Needs sample</h2>
        <p className="text-xs text-[#4B4567] mb-4 max-w-2xl">
          See exactly what SA CoParents will build for you before you start. Each sample is a real, branded PDF you can print, share with your mediator, or use as a workbook.
        </p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <a href="/api/insights/samples/snc-sample-assessment.pdf" target="_blank" rel="noreferrer noopener"
            data-testid="snc2-sample-assessment"
            className="rounded-2xl border border-[#E5E0EE] bg-white p-4 hover:border-[#3D1A78] hover:shadow-md transition-all">
            <div className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] mb-1">Blank workbook</div>
            <div className="font-semibold text-sm text-[#1A1330]">Sample Assessment</div>
            <div className="text-xs text-[#4B4567] mt-1">A printable version of every question so you can gather your thoughts first.</div>
          </a>
          <a href="/api/insights/samples/snc-sample-comparison-report.pdf" target="_blank" rel="noreferrer noopener"
            data-testid="snc2-sample-comparison"
            className="rounded-2xl border border-[#E5E0EE] bg-white p-4 hover:border-[#3D1A78] hover:shadow-md transition-all">
            <div className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] mb-1">Both parents</div>
            <div className="font-semibold text-sm text-[#1A1330]">Co-Parent Comparison</div>
            <div className="text-xs text-[#4B4567] mt-1">Neutral side-by-side across all three pathways with alignment pills and shared highlights.</div>
          </a>
        </div>

        <div className="mt-5">
          <div className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] mb-2">Blank assessments — one per needs area</div>
          <div className="grid sm:grid-cols-3 gap-3" data-testid="snc2-sample-pathway-assessments">
            <a href="/api/insights/samples/snc-sample-assessment-medical.pdf" target="_blank" rel="noreferrer noopener"
              data-testid="snc2-sample-assessment-medical"
              className="rounded-2xl border border-[#E5E0EE] bg-white p-4 hover:border-[#3D1A78] hover:shadow-md transition-all">
              <div className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] mb-1">Medical</div>
              <div className="font-semibold text-sm text-[#1A1330]">Blank assessment — medical needs</div>
              <div className="text-xs text-[#4B4567] mt-1">Printable eight-step workbook scoped to medical needs only.</div>
            </a>
            <a href="/api/insights/samples/snc-sample-assessment-educational.pdf" target="_blank" rel="noreferrer noopener"
              data-testid="snc2-sample-assessment-educational"
              className="rounded-2xl border border-[#E5E0EE] bg-white p-4 hover:border-[#3D1A78] hover:shadow-md transition-all">
              <div className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] mb-1">Educational</div>
              <div className="font-semibold text-sm text-[#1A1330]">Blank assessment — educational needs</div>
              <div className="text-xs text-[#4B4567] mt-1">Printable eight-step workbook scoped to educational needs only.</div>
            </a>
            <a href="/api/insights/samples/snc-sample-assessment-psychological.pdf" target="_blank" rel="noreferrer noopener"
              data-testid="snc2-sample-assessment-psychological"
              className="rounded-2xl border border-[#E5E0EE] bg-white p-4 hover:border-[#3D1A78] hover:shadow-md transition-all">
              <div className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] mb-1">Psychological</div>
              <div className="font-semibold text-sm text-[#1A1330]">Blank assessment — psychological / behavioural needs</div>
              <div className="text-xs text-[#4B4567] mt-1">Printable eight-step workbook scoped to psychological or behavioural needs.</div>
            </a>
          </div>
        </div>

        <div className="mt-5">
          <div className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] mb-2">Individual reports — one per needs area</div>
          <div className="grid sm:grid-cols-3 gap-3" data-testid="snc2-sample-individual-reports">
            <a href="/api/insights/samples/snc-sample-individual-report-medical.pdf" target="_blank" rel="noreferrer noopener"
              data-testid="snc2-sample-report-medical"
              className="rounded-2xl border border-[#E5E0EE] bg-white p-4 hover:border-[#3D1A78] hover:shadow-md transition-all">
              <div className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] mb-1">Medical</div>
              <div className="font-semibold text-sm text-[#1A1330]">Individual report — medical needs</div>
              <div className="text-xs text-[#4B4567] mt-1">Nine-section polished PDF focused on medical needs only.</div>
            </a>
            <a href="/api/insights/samples/snc-sample-individual-report-educational.pdf" target="_blank" rel="noreferrer noopener"
              data-testid="snc2-sample-report-educational"
              className="rounded-2xl border border-[#E5E0EE] bg-white p-4 hover:border-[#3D1A78] hover:shadow-md transition-all">
              <div className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] mb-1">Educational</div>
              <div className="font-semibold text-sm text-[#1A1330]">Individual report — educational needs</div>
              <div className="text-xs text-[#4B4567] mt-1">Nine-section polished PDF focused on educational needs only.</div>
            </a>
            <a href="/api/insights/samples/snc-sample-individual-report-psychological.pdf" target="_blank" rel="noreferrer noopener"
              data-testid="snc2-sample-report-psychological"
              className="rounded-2xl border border-[#E5E0EE] bg-white p-4 hover:border-[#3D1A78] hover:shadow-md transition-all">
              <div className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] mb-1">Psychological</div>
              <div className="font-semibold text-sm text-[#1A1330]">Individual report — psychological / behavioural needs</div>
              <div className="text-xs text-[#4B4567] mt-1">Nine-section polished PDF focused on psychological or behavioural needs.</div>
            </a>
          </div>
        </div>

        <div className="mt-5">
          <div className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] mb-2">Optional deep-dive assessments (blank workbooks)</div>
          <div className="grid sm:grid-cols-3 gap-3" data-testid="snc2-sample-deep-dive-assessments">
            <a href="/api/insights/samples/snc-sample-educational-deep-dive-assessment.pdf" target="_blank" rel="noreferrer noopener"
              data-testid="snc2-sample-deep-dive-assessment-educational"
              className="rounded-2xl border border-[#E5E0EE] bg-white p-4 hover:border-[#3D1A78] hover:shadow-md transition-all">
              <div className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] mb-1">Educational · Workbook</div>
              <div className="font-semibold text-sm text-[#1A1330]">12-section Educational assessment</div>
              <div className="text-xs text-[#4B4567] mt-1">Printable question list covering IEP, 504, ARD (Texas), tutoring, and homework.</div>
            </a>
            <a href="/api/insights/samples/snc-sample-psychological-deep-dive-assessment.pdf" target="_blank" rel="noreferrer noopener"
              data-testid="snc2-sample-deep-dive-assessment-psychological"
              className="rounded-2xl border border-[#E5E0EE] bg-white p-4 hover:border-[#3D1A78] hover:shadow-md transition-all">
              <div className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] mb-1">Psychological · Workbook</div>
              <div className="font-semibold text-sm text-[#1A1330]">11-section Psychological / Behavioural assessment</div>
              <div className="text-xs text-[#4B4567] mt-1">Printable question list covering therapy, medication, crisis planning, and emotional support.</div>
            </a>
            <a href="/api/insights/samples/snc-sample-medical-deep-dive-assessment.pdf" target="_blank" rel="noreferrer noopener"
              data-testid="snc2-sample-deep-dive-assessment-medical"
              className="rounded-2xl border border-[#E5E0EE] bg-white p-4 hover:border-[#3D1A78] hover:shadow-md transition-all">
              <div className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] mb-1">Medical · Workbook</div>
              <div className="font-semibold text-sm text-[#1A1330]">10-section Prescription & Medication assessment</div>
              <div className="text-xs text-[#4B4567] mt-1">Printable question list covering prescriptions, refills, school meds, and controlled medications.</div>
            </a>
          </div>
        </div>

        <div className="mt-5">
          <div className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] mb-2">Optional deep-dive reports</div>
          <div className="grid sm:grid-cols-3 gap-3" data-testid="snc2-sample-deep-dives">
            <a href="/api/insights/samples/snc-sample-educational-deep-dive.pdf" target="_blank" rel="noreferrer noopener"
              data-testid="snc2-sample-deep-dive-educational"
              className="rounded-2xl border border-[#E5E0EE] bg-white p-4 hover:border-[#3D1A78] hover:shadow-md transition-all">
              <div className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] mb-1">Educational · Deep Dive</div>
              <div className="font-semibold text-sm text-[#1A1330]">12-section Educational Deep Dive</div>
              <div className="text-xs text-[#4B4567] mt-1">Sample report covering IEP, ARD (Texas), 504, tutoring, and homework coordination.</div>
            </a>
            <a href="/api/insights/samples/snc-sample-psychological-deep-dive.pdf" target="_blank" rel="noreferrer noopener"
              data-testid="snc2-sample-deep-dive-psychological"
              className="rounded-2xl border border-[#E5E0EE] bg-white p-4 hover:border-[#3D1A78] hover:shadow-md transition-all">
              <div className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] mb-1">Psychological · Deep Dive</div>
              <div className="font-semibold text-sm text-[#1A1330]">11-section Psychological / Behavioural Deep Dive</div>
              <div className="text-xs text-[#4B4567] mt-1">Sample report covering therapy, medication, crisis planning, and emotional support.</div>
            </a>
            <a href="/api/insights/samples/snc-sample-medical-deep-dive.pdf" target="_blank" rel="noreferrer noopener"
              data-testid="snc2-sample-deep-dive-medical"
              className="rounded-2xl border border-[#E5E0EE] bg-white p-4 hover:border-[#3D1A78] hover:shadow-md transition-all">
              <div className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] mb-1">Medical · Deep Dive</div>
              <div className="font-semibold text-sm text-[#1A1330]">10-section Prescription & Medication Deep Dive</div>
              <div className="text-xs text-[#4B4567] mt-1">Sample report covering pharmacy coordination, refills, school meds, and controlled medications.</div>
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}


export default function SpecialNeedsV2() {
  const nav = useNavigate();
  const [me, setMe] = useState(null);
  const [catalog, setCatalog] = useState([]);
  const [scale, setScale] = useState([]);
  const [schema, setSchema] = useState(null);
  const [current, setCurrent] = useState(0);
  const [answers, setAnswers] = useState({});
  const [pending, setPending] = useState({});
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState(null);
  const [completing, setCompleting] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [pathRes, meRes] = await Promise.all([
          api.get("/snc2/pathways"),
          api.get("/snc2/me").catch(() => ({ data: { exists: false } })),
        ]);
        setCatalog(pathRes.data?.pathways || []);
        setScale(pathRes.data?.response_scale || []);
        const meDoc = meRes.data?.exists ? meRes.data : null;
        setMe(meDoc);
        setAnswers(meDoc?.answers || {});
        if (meDoc?.selected_pathways?.length) {
          const s = await api.get(`/snc2/schema?pathways=${encodeURIComponent(meDoc.selected_pathways.join(","))}`);
          setSchema(s.data);
        }
      } catch (err) {
        logError("snc2 load", err);
        toast.error("Could not load the assessment.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const flushSave = useCallback(async (changes) => {
    if (!changes || !Object.keys(changes).length) return;
    setSaving(true);
    try {
      await api.post("/snc2/answers/bulk", { answers: changes });
      setSavedAt(new Date());
    } catch (err) {
      logError("snc2 save", err);
      toast.error(err?.response?.data?.detail || "Save failed.");
    } finally {
      setSaving(false);
    }
  }, []);

  useEffect(() => {
    if (!schema) return;
    if (!Object.keys(pending).length) return;
    const t = setTimeout(() => {
      const send = pending;
      setPending({});
      flushSave(send);
    }, 800);
    return () => clearTimeout(t);
  }, [pending, schema, flushSave]);

  const setAnswer = (qid, v) => {
    setAnswers((prev) => ({ ...prev, [qid]: v }));
    setPending((prev) => ({ ...prev, [qid]: v }));
  };

  const submitPicker = async (pathways, childName) => {
    setLoading(true);
    try {
      const sel = await api.post("/snc2/select", { pathways, child_name: childName || null });
      const meDoc = sel.data;
      setMe(meDoc);
      const s = await api.get(`/snc2/schema?pathways=${encodeURIComponent(pathways.join(","))}`);
      setSchema(s.data);
      setCurrent(0);
    } catch (err) {
      logError("snc2 select", err);
      toast.error(err?.response?.data?.detail || "Could not save your selection.");
    } finally {
      setLoading(false);
    }
  };

  const flushAndGo = async (nextIdx) => {
    if (Object.keys(pending).length) {
      const send = pending; setPending({});
      await flushSave(send);
    }
    setCurrent(Math.max(0, Math.min((schema?.steps.length || 1) - 1, nextIdx)));
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const complete = async () => {
    if (Object.keys(pending).length) {
      const send = pending; setPending({});
      await flushSave(send);
    }
    setCompleting(true);
    try {
      await api.post("/snc2/complete");
      await api.post("/snc2/report/generate");
      nav("/special-needs-v2/report");
    } catch (err) {
      logError("snc2 complete", err);
      toast.error(err?.response?.data?.detail || "Could not complete the assessment.");
    } finally {
      setCompleting(false);
    }
  };

  const totalScored = useMemo(() => {
    if (!schema) return { answered: 0, total: 0 };
    let total = 0, answered = 0;
    schema.steps.forEach((s) => s.pathways.forEach((p) => p.items.forEach((it) => {
      if (it.type === "likert") {
        total += 1;
        if (answers[`${s.id}_${p.id}_${it.id}`] !== undefined) answered += 1;
      }
    })));
    return { answered, total };
  }, [schema, answers]);

  if (loading) {
    return <AppShell><div className="max-w-3xl mx-auto px-4 py-10 text-[#4B4567]"><Loader2 className="animate-spin inline" /> Loading…</div></AppShell>;
  }

  // Picker mode
  if (!schema) {
    return (
      <AppShell>
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
          <CategoryPicker catalog={catalog}
            initial={me?.selected_pathways}
            initialChildName={me?.child_name}
            onSubmit={submitPicker} />
        </div>
      </AppShell>
    );
  }

  const step = schema.steps[current];
  const totalSteps = schema.steps.length;
  const pct = totalScored.total > 0 ? Math.round((totalScored.answered / totalScored.total) * 100) : 0;

  return (
    <AppShell>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-10" data-testid="snc2-assessment-root">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <button type="button" onClick={() => setSchema(null)} data-testid="snc2-change-categories" className="text-xs text-[#3D1A78] underline">
            &larr; Change needs categories
          </button>
          <Link to="/special-needs-v2/compare" data-testid="snc2-open-compare"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs border border-[#3D1A78] text-[#3D1A78] hover:bg-[#EEE9F7]">
            <Users size={13} /> Co-Parent Compare
          </Link>
          <Link to="/special-needs-v2/educational-deep-dive" data-testid="snc2-open-edu-deep-dive"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs border border-[#3D1A78] text-[#3D1A78] hover:bg-[#EEE9F7]">
            <Sparkles size={13} /> Educational Deep Dive <span className="text-[10px] text-[#8471B3]">(optional)</span>
          </Link>
          <Link to="/special-needs-v2/psychological-deep-dive" data-testid="snc2-open-psych-deep-dive"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs border border-[#3D1A78] text-[#3D1A78] hover:bg-[#EEE9F7]">
            <Sparkles size={13} /> Psychological Deep Dive <span className="text-[10px] text-[#8471B3]">(optional)</span>
          </Link>
          <Link to="/special-needs-v2/medical-deep-dive" data-testid="snc2-open-med-deep-dive"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs border border-[#3D1A78] text-[#3D1A78] hover:bg-[#EEE9F7]">
            <Sparkles size={13} /> Medical Deep Dive <span className="text-[10px] text-[#8471B3]">(optional)</span>
          </Link>
        </div>
        <div className="mb-4">
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">Our child has unique needs</div>
          <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight">
            Step {step.number}. {step.name}
          </h1>
        </div>

        {/* progress */}
        <div className="mb-6">
          <div className="flex items-center justify-between text-xs text-[#4B4567] mb-2">
            <div data-testid="snc2-progress-label">Step {current + 1} of {totalSteps} · {pct}% ({totalScored.answered}/{totalScored.total} rated)</div>
            <div className="flex items-center gap-3">
              {saving && <span className="inline-flex items-center gap-1 text-[#3D1A78]"><Loader2 size={12} className="animate-spin" /> Saving…</span>}
              {!saving && savedAt && <span className="inline-flex items-center gap-1 text-[#2E7D5F]"><CheckCircle2 size={12} /> Saved</span>}
            </div>
          </div>
          <div className="h-2 w-full bg-[#EEE9F7] rounded-full overflow-hidden">
            <div className="h-full bg-[#3D1A78] transition-all" style={{ width: `${pct}%` }} data-testid="snc2-progress-bar" />
          </div>
        </div>

        {/* step tabs */}
        <div className="mb-6 overflow-x-auto -mx-4 px-4">
          <div className="flex gap-2 min-w-max">
            {schema.steps.map((s, i) => (
              <button key={s.id} data-testid={`snc2-nav-${s.id}`} onClick={() => flushAndGo(i)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all whitespace-nowrap ${
                  i === current ? "bg-[#3D1A78] text-white border-[#3D1A78]" : "bg-white text-[#4B4567] border-[#D6CFE8] hover:border-[#3D1A78]"
                }`}>
                {i + 1}. {s.name}
              </button>
            ))}
          </div>
        </div>

        {/* content */}
        <div className="space-y-6" data-testid={`snc2-step-${step.id}`}>
          {step.pathways.map((pw) => (
            <div key={pw.id} className="bg-white rounded-3xl border border-[#E5E0EE] p-5 sm:p-7 shadow-sm" data-testid={`snc2-step-${step.id}-${pw.id}`}>
              <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-2">{pw.name}</div>
              {pw.items.map((item) => {
                const qid = `${step.id}_${pw.id}_${item.id}`;
                return (
                  <div key={qid} className="py-4 border-b border-[#EEE9F7] last:border-b-0" data-testid={`snc2-item-${qid}`}>
                    <label className="block text-sm text-[#1A1330] mb-3">{item.prompt}</label>
                    <ItemInput item={item} value={answers[qid]} onChange={(v) => setAnswer(qid, v)} scale={scale} qid={qid} />
                  </div>
                );
              })}
            </div>
          ))}
        </div>

        {/* footer nav */}
        <div className="mt-6 sticky bottom-0 -mx-4 sm:mx-0 sm:relative bg-white/95 sm:bg-transparent backdrop-blur-sm sm:backdrop-blur-none border-t border-[#EEE9F7] sm:border-none py-3 sm:py-0 px-4 sm:px-0 flex flex-wrap items-center justify-between gap-3">
          <button data-testid="snc2-prev" onClick={() => flushAndGo(current - 1)} disabled={current === 0}
            className="inline-flex items-center gap-2 px-4 py-2 min-h-[44px] rounded-full text-sm border border-[#D6CFE8] text-[#1A1330] bg-white disabled:opacity-40 hover:border-[#3D1A78]">
            <ArrowLeft size={14} /> Previous
          </button>
          <div className="flex items-center gap-2">
            <button data-testid="snc2-save-later" onClick={async () => { await flushAndGo(current); toast.success("Progress saved."); }}
              className="inline-flex items-center gap-2 px-4 py-2 min-h-[44px] rounded-full text-sm border border-[#D6CFE8] text-[#3D1A78] bg-white hover:border-[#3D1A78]">
              <Save size={14} /> <span className="hidden sm:inline">Save &amp; come back later</span><span className="sm:hidden">Save</span>
            </button>
            {current < totalSteps - 1 ? (
              <button data-testid="snc2-next" onClick={() => flushAndGo(current + 1)}
                className="inline-flex items-center gap-2 px-4 py-2 min-h-[44px] rounded-full text-sm bg-[#3D1A78] text-white hover:brightness-110">
                Next <ArrowRight size={14} />
              </button>
            ) : (
              <button data-testid="snc2-complete" onClick={complete} disabled={completing}
                className="inline-flex items-center gap-2 px-4 py-2 min-h-[44px] rounded-full text-sm bg-[#3D1A78] text-white hover:brightness-110 disabled:opacity-60">
                {completing ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
                <span className="hidden sm:inline">Complete &amp; generate report</span><span className="sm:hidden">Complete</span>
              </button>
            )}
          </div>
        </div>

        <div className="mt-6 text-center">
          <Link to="/dashboard" data-testid="snc2-back-dashboard" className="text-xs text-[#4B4567] underline">Back to dashboard</Link>
        </div>
      </div>
    </AppShell>
  );
}
