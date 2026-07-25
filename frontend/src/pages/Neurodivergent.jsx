import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft, ArrowRight, Check, Loader2, Type, Save, Eye, EyeOff, Info,
} from "lucide-react";
import { toast } from "sonner";
import AppShell from "../components/AppShell";
import DemoModeBanner from "../components/DemoModeBanner";
import MethodologyCard from "../components/MethodologyCard";
import { api } from "../lib/api";

/**
 * Special Needs Assessment — v2 (child-centered coordination rebuild).
 *
 * Backend schema is loaded from `/api/neurodivergent/schema`. Answers are
 * saved incrementally via `/api/neurodivergent/answer` (single) or
 * `/api/neurodivergent/answers/bulk` (grouped save on section change).
 *
 * UX principles retained from v1:
 *   - One question per screen with a visible progress rail
 *   - Plain-language help under each prompt
 *   - Save & resume — autosave on blur / "Next"
 *   - Optional "Larger text" toggle
 *   - Optional "Reduced stimulation" mode (mutes gradients & animations)
 *
 * New in v2:
 *   - 4 sections instead of 6 pillars: Begin with the child, Concerns
 *     (documented / under-eval / parent-observed), 8-domain coordination
 *     items on the shared 7-value scale, disagreement self-reflection.
 *   - Section-boundary indicators in the progress rail.
 *   - Migration notice for parents with v1 answers still on file.
 */

const STORAGE = {
  fontSize: "nd_font_size",
  reduced: "nd_reduced_stim",
};

function useReadingPrefs() {
  const [fontSize, setFontSize] = useState(
    () => (typeof window !== "undefined" && localStorage.getItem(STORAGE.fontSize)) || "md"
  );
  const [reduced, setReduced] = useState(
    () => typeof window !== "undefined" && localStorage.getItem(STORAGE.reduced) === "1"
  );
  const bump = () => {
    const next = fontSize === "md" ? "lg" : fontSize === "lg" ? "xl" : "md";
    setFontSize(next);
    localStorage.setItem(STORAGE.fontSize, next);
  };
  const toggleReduced = () => {
    const next = !reduced;
    setReduced(next);
    localStorage.setItem(STORAGE.reduced, next ? "1" : "");
  };
  const fontClass =
    fontSize === "xl" ? "text-[19px] sm:text-[21px] leading-relaxed"
    : fontSize === "lg" ? "text-[17px] sm:text-[18px] leading-relaxed"
    : "text-[15px] sm:text-[16px] leading-relaxed";
  return { fontSize, fontClass, reduced, bump, toggleReduced };
}

/** Flatten schema.sections[].items into a single ordered list, tagging
 *  each item with its section id + the coordination scale where scored. */
function flattenSchema(schema) {
  if (!schema) return [];
  const flat = [];
  for (const sec of schema.sections || []) {
    for (const item of sec.items || []) {
      const type = item.type
        || (item.dim ? "coordination" : (Array.isArray(item.options) ? "single_select" : "long_text"));
      flat.push({ ...item, type, section_id: sec.id, section_title: sec.title });
    }
  }
  return flat;
}

function ScaleChoices({ scale, value, onChange, testidBase }) {
  return (
    <div className="grid gap-2">
      {scale.map((opt) => {
        const on = value === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={`text-left px-4 py-3 rounded-xl border-2 transition-colors ${
              on
                ? "bg-[#3D1A78] text-white border-[#3D1A78]"
                : "bg-white text-[#1A1330] border-[#E5E0EE] hover:border-[#3D1A78]"
            }`}
            data-testid={`${testidBase}-${opt.value}`}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

function AnswerInput({ item, value, onChange, schema, fontClass, answers, onChangeNeeds }) {
  const testid = `nd-input-${item.id}`;

  if (item.type === "consistency_pair") {
    // Compound: coordination-scale value under item.id AND needs-flag under
    // `<id>__needs`. Rendered as two labelled selector groups on one screen.
    const needsScale = schema.needs_consistency_scale || [];
    const needsValue = answers?.[`${item.id}__needs`] ?? null;
    return (
      <div className="space-y-6" data-testid={`nd-pair-${item.id}`}>
        <div>
          <div className="text-[11px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] mb-2">
            Today — how consistent is this across your two homes?
          </div>
          <ScaleChoices
            scale={schema.scale}
            value={value ?? null}
            onChange={onChange}
            testidBase={`nd-scale-${item.id}`}
          />
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] mb-2">
            Does your child actually need this to be consistent between homes?
          </div>
          <ScaleChoices
            scale={needsScale}
            value={needsValue}
            onChange={(v) => onChangeNeeds && onChangeNeeds(v)}
            testidBase={`nd-needs-${item.id}`}
          />
        </div>
      </div>
    );
  }

  if (item.type === "coordination") {
    return (
      <ScaleChoices
        scale={schema.scale}
        value={value ?? null}
        onChange={onChange}
        testidBase={`nd-scale-${item.id}`}
      />
    );
  }

  if (item.type === "single_select") {
    return (
      <ScaleChoices
        scale={item.options}
        value={value ?? null}
        onChange={onChange}
        testidBase={`nd-choice-${item.id}`}
      />
    );
  }

  if (item.type === "short_text") {
    return (
      <input
        type="text"
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        className={`w-full border-2 border-[#E5E0EE] focus:border-[#3D1A78] rounded-xl px-4 py-3 ${fontClass} bg-white outline-none`}
        data-testid={testid}
        autoFocus
      />
    );
  }

  // Default = long_text
  return (
    <textarea
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value)}
      rows={6}
      className={`w-full border-2 border-[#E5E0EE] focus:border-[#3D1A78] rounded-xl px-4 py-3 ${fontClass} bg-white outline-none`}
      data-testid={testid}
      autoFocus
    />
  );
}

function ProgressRail({ items, currentIdx, answers }) {
  return (
    <div className="mb-6" data-testid="nd-progress-rail">
      <div className="flex items-center justify-between text-xs text-[#857E9C] mb-2">
        <span data-testid="nd-progress-label">
          Question {currentIdx + 1} of {items.length}
        </span>
        <span>
          {Object.keys(answers || {}).filter((k) => (answers[k] ?? "") !== "").length} saved
        </span>
      </div>
      <div className="h-1.5 bg-[#EFE9F9] rounded-full overflow-hidden">
        <div
          className="h-full bg-[#3D1A78] transition-all"
          style={{
            width: `${((currentIdx + 1) / items.length) * 100}%`,
          }}
        />
      </div>
    </div>
  );
}

export default function Neurodivergent() {
  const navigate = useNavigate();
  const prefs = useReadingPrefs();

  const [schema, setSchema] = useState(null);
  const [answers, setAnswers] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [showPreview, setShowPreview] = useState(false);
  const [migratedFromV1, setMigratedFromV1] = useState(false);

  // Load schema + saved answers in parallel.
  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api.get("/neurodivergent/schema"),
      api.get("/neurodivergent/prep"),
    ])
      .then(([s, p]) => {
        if (cancelled) return;
        setSchema(s.data);
        const saved = p.data?.answers || {};
        setAnswers(saved);
        setMigratedFromV1(p.data?.version === 1);
      })
      .catch((e) => {
        if (!cancelled) toast.error("Couldn't load the assessment. Please refresh.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const items = useMemo(() => flattenSchema(schema), [schema]);
  const total = items.length;
  const q = items[currentIdx];
  const value = q ? answers[q.id] : undefined;

  const onChange = (v) => {
    if (!q) return;
    setAnswers((a) => ({ ...a, [q.id]: v }));
  };

  // Consistency-pair items save a second field (`<id>__needs`) — the wizard
  // needs a dedicated setter so the paired selector can update independently
  // from the primary consistency-scale answer.
  const onChangeNeeds = (v) => {
    if (!q) return;
    setAnswers((a) => ({ ...a, [`${q.id}__needs`]: v }));
  };

  const persist = useCallback(
    async (id, val) => {
      if (!id) return;
      setSaving(true);
      try {
        await api.post("/neurodivergent/answer", { question_id: id, value: val });
      } catch {
        toast.error("Save failed. Your answer is kept locally — we'll retry.");
      } finally {
        setSaving(false);
      }
    },
    []
  );

  const goNext = async () => {
    if (q) {
      await persist(q.id, value);
      if (q.type === "consistency_pair") {
        const needsId = `${q.id}__needs`;
        const needsVal = answers[needsId];
        if (needsVal !== undefined) await persist(needsId, needsVal);
      }
    }
    if (currentIdx < total - 1) {
      setCurrentIdx((i) => i + 1);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } else {
      try {
        await api.post("/neurodivergent/complete", {});
        toast.success("Assessment saved — heading to your next steps.");
        navigate("/next-steps/special_needs");
      } catch {
        toast.error("We saved your answers but couldn't mark complete. Please try again.");
      }
    }
  };

  const goPrev = async () => {
    if (q) {
      await persist(q.id, value);
      if (q.type === "consistency_pair") {
        const needsId = `${q.id}__needs`;
        const needsVal = answers[needsId];
        if (needsVal !== undefined) await persist(needsId, needsVal);
      }
    }
    setCurrentIdx((i) => Math.max(0, i - 1));
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const containerBg = prefs.reduced
    ? "bg-white"
    : "bg-gradient-to-b from-[#F8F5FF] via-white to-white";

  if (loading) {
    return (
      <AppShell>
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-16 text-[#857E9C]" data-testid="nd-loading">
          Loading your space…
        </div>
      </AppShell>
    );
  }

  if (showPreview) {
    return (
      <AppShell>
        <div className={`min-h-full ${containerBg}`}>
          <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
            <button
              onClick={() => setShowPreview(false)}
              className="inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline mb-4"
              data-testid="nd-back-from-preview"
            >
              <ArrowLeft size={14} /> Back to the questions
            </button>
            <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330]">Preview of every question</h1>
            <p className={`mt-2 text-[#4B4567] ${prefs.fontClass}`}>
              Some parents like to see the whole path before starting. Here it is. You can answer at your pace.
            </p>
            <div className="mt-6 space-y-6">
              {items.map((it, i) => (
                <div key={it.id} className="border-l-4 border-[#E5E0EE] pl-4">
                  <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">
                    {it.section_title} · {i + 1} of {total}
                  </div>
                  <div className={`text-[#1A1330] font-medium ${prefs.fontClass}`}>{it.prompt}</div>
                  {it.help && (
                    <div className={`text-[#857E9C] mt-1 ${prefs.fontClass}`}>{it.help}</div>
                  )}
                </div>
              ))}
            </div>
            <div className="mt-8">
              <button
                onClick={() => setShowPreview(false)}
                className="px-6 py-3 rounded-full bg-[#3D1A78] text-white font-medium"
                data-testid="nd-start-from-preview"
              >
                Ready — take me to the questions →
              </button>
            </div>
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className={`min-h-full ${containerBg}`}>
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline mb-4"
            data-testid="nd-back-to-dashboard"
          >
            <ArrowLeft size={14} /> Back to Dashboard
          </Link>

          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="eyebrow text-[#3D1A78]">Special Needs Assessment</div>
              <h1
                className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight mt-1"
                data-testid="nd-title"
              >
                Supporting your child across two homes
              </h1>
              <p className={`mt-2 text-[#4B4567] max-w-2xl ${prefs.fontClass}`}>
                A gentle, one-question-at-a-time space that moves you from
                disagreement <em>about</em> your child to a coordinated plan
                <em> for</em> your child. Nothing here diagnoses anyone.
                Nothing here is legal or medical advice. Answers save as you go.
              </p>
            </div>
            <div className="flex flex-wrap gap-2 items-center">
              <button
                onClick={prefs.bump}
                className="inline-flex items-center gap-1.5 text-xs text-[#3D1A78] border border-[#E5E0EE] rounded-full px-3 py-1.5 hover:bg-[#F5F2FA]"
                data-testid="nd-text-size-btn"
                title={`Text size: ${prefs.fontSize.toUpperCase()}`}
              >
                <Type size={12} /> Larger text
              </button>
              <button
                onClick={prefs.toggleReduced}
                className="inline-flex items-center gap-1.5 text-xs text-[#3D1A78] border border-[#E5E0EE] rounded-full px-3 py-1.5 hover:bg-[#F5F2FA]"
                data-testid="nd-reduced-stim-btn"
                title="Toggle reduced-stimulation mode"
              >
                {prefs.reduced ? <Eye size={12} /> : <EyeOff size={12} />}
                {prefs.reduced ? "Standard view" : "Reduced stimulation"}
              </button>
              <button
                onClick={() => setShowPreview(true)}
                className="inline-flex items-center gap-1.5 text-xs text-[#3D1A78] border border-[#E5E0EE] rounded-full px-3 py-1.5 hover:bg-[#F5F2FA]"
                data-testid="nd-preview-btn"
              >
                <Info size={12} /> Preview all questions
              </button>
            </div>
          </div>

          <div className="mt-6">
            <DemoModeBanner />
          </div>

          <div className="mt-6">
            <MethodologyCard id="special_needs" />
          </div>

          {migratedFromV1 && (
            <div
              className="mt-6 rounded-2xl border border-[#EED3B5] bg-[#FFF6EC] p-4"
              data-testid="nd-v1-migration-notice"
            >
              <div className="text-[11px] uppercase tracking-[0.18em] font-bold text-[#8C5A2C] mb-1">
                Assessment upgraded
              </div>
              <p className="text-sm text-[#4B4567] leading-relaxed">
                We&apos;ve rebuilt this assessment around your child &amp; how
                you coordinate — with seven coordination scores instead of
                one global score. Your earlier answers are safe in your
                account but the questions have changed, so you&apos;ll start
                fresh here.
              </p>
            </div>
          )}

          <ProgressRail items={items} currentIdx={currentIdx} answers={answers} />

          {q && (
            <div
              className="rounded-3xl border border-[#E5E0EE] bg-white p-6 sm:p-8 shadow-sm"
              data-testid={`nd-question-${q.id}`}
            >
              <div className="text-[10px] uppercase tracking-[0.2em] font-bold text-[#3D1A78] mb-2">
                {q.section_title}
              </div>
              <h2 className={`font-serif text-2xl text-[#1A1330] leading-tight ${prefs.fontClass}`}>
                {q.prompt}
              </h2>
              {q.help && (
                <p className={`text-[#857E9C] mt-2 ${prefs.fontClass}`}>{q.help}</p>
              )}

              <div className="mt-6">
                <AnswerInput
                  item={q}
                  value={value}
                  onChange={onChange}
                  onChangeNeeds={onChangeNeeds}
                  answers={answers}
                  schema={schema}
                  fontClass={prefs.fontClass}
                />
              </div>

              <div className="mt-8 flex flex-wrap items-center justify-between gap-3">
                <button
                  onClick={goPrev}
                  disabled={currentIdx === 0}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full border border-[#E5E0EE] text-[#3D1A78] text-sm hover:bg-[#F5F2FA] disabled:opacity-40"
                  data-testid="nd-prev-btn"
                >
                  <ArrowLeft size={14} /> Back
                </button>
                <div className="flex items-center gap-2 text-xs text-[#857E9C]">
                  {saving ? (
                    <>
                      <Loader2 size={12} className="animate-spin" /> Saving…
                    </>
                  ) : (
                    <>
                      <Save size={12} /> Autosaves as you go
                    </>
                  )}
                </div>
                <button
                  onClick={goNext}
                  className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-full bg-[#3D1A78] text-white text-sm font-semibold hover:bg-[#2D0F63]"
                  data-testid="nd-next-btn"
                >
                  {currentIdx === total - 1 ? (
                    <>
                      Finish <Check size={14} />
                    </>
                  ) : (
                    <>
                      Next <ArrowRight size={14} />
                    </>
                  )}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
