import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft, ArrowRight, Check, Loader2, Save, RotateCcw, Sparkles,
  AlertTriangle, TrendingUp, MessageCircle, FileText, Download,
} from "lucide-react";
import { toast } from "sonner";
import AppShell from "../components/AppShell";
import DemoModeBanner from "../components/DemoModeBanner";
import { api } from "../lib/api";

/**
 * Special Needs Assessment — v3 (10-principle framework).
 *
 * Section-by-section flow (10 principles × 6 questions). 5-point Likert scale.
 * Autosaves per principle via POST /special-needs-v3/answers/bulk.
 * On completion, POST /complete returns deterministic scores which are then
 * rendered inline (no dynamic PDF yet — that's a Phase 4 task).
 */

const RATING_TONE = {
  Excellent: { bg: "bg-[#E4F4EC]", text: "text-[#1F5C3B]", border: "border-[#B8DDC6]" },
  Good: { bg: "bg-[#EFE9F9]", text: "text-[#3D1A78]", border: "border-[#CFC1EA]" },
  Fair: { bg: "bg-[#FFF7E3]", text: "text-[#8C5A2C]", border: "border-[#F5C147]" },
  "Needs Improvement": { bg: "bg-[#FEF1EC]", text: "text-[#C2481F]", border: "border-[#F0B6A0]" },
};

function LikertRow({ scale, value, onChange, testidBase }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-5 gap-2">
      {scale.map((opt) => {
        const on = value === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            data-testid={`${testidBase}-${opt.value}`}
            className={`text-sm font-medium px-3 py-2.5 rounded-xl border-2 transition-colors ${
              on
                ? "bg-[#3D1A78] text-white border-[#3D1A78]"
                : "bg-white text-[#1A1330] border-[#E5E0EE] hover:border-[#3D1A78]"
            }`}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

function Progress({ answered, total }) {
  const pct = Math.min(100, Math.round((answered / total) * 100));
  return (
    <div className="mb-6" data-testid="snv3-progress">
      <div className="flex items-center justify-between text-xs text-[#857E9C] mb-2">
        <span data-testid="snv3-progress-label">
          {answered} of {total} answered
        </span>
        <span>{pct}%</span>
      </div>
      <div className="h-1.5 bg-[#EFE9F9] rounded-full overflow-hidden">
        <div className="h-full bg-[#3D1A78] transition-all" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

const SAMPLE_HTML_URL = "/special-needs-report.html";
const SAMPLE_PDF_URL = "/api/insights/special-needs-report.pdf";

function SampleReportCallout({ variant = "default" }) {
  const isCompact = variant === "compact";
  return (
    <div
      className={`rounded-2xl border border-[#CFC1EA] bg-[#F5F0FE] ${isCompact ? "p-4" : "p-5"}`}
      data-testid="snv3-sample-report-callout"
    >
      <div className="flex items-start gap-3">
        <div className="shrink-0 w-9 h-9 rounded-full bg-white grid place-items-center text-[#3D1A78] border border-[#CFC1EA]">
          <FileText size={16} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[10px] uppercase tracking-[0.2em] font-bold text-[#3D1A78] mb-0.5">
            Sample report
          </div>
          <div className="font-semibold text-[#1A1330]">
            See what a completed Special Needs report looks like
          </div>
          <p className="text-xs sm:text-sm text-[#4B4567] mt-1 leading-relaxed">
            A branded, fictional SA CoParents sample using the 10-principle
            framework. Great to preview before you finish, or to share with
            your co-parent, mediator, or Parenting Facilitator.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <a
              href={SAMPLE_HTML_URL}
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#3D1A78] bg-white border border-[#CFC1EA] hover:border-[#3D1A78] rounded-full px-3 py-1.5"
              data-testid="snv3-sample-view-btn"
            >
              <FileText size={12} /> View sample (HTML)
            </a>
            <a
              href={SAMPLE_PDF_URL}
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-white bg-[#3D1A78] hover:bg-[#2D0F63] rounded-full px-3 py-1.5"
              data-testid="snv3-sample-pdf-btn"
            >
              <Download size={12} /> Download sample PDF
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

function ResultsView({ scores, schema, onRestart }) {
  const sectionById = useMemo(() => {
    const m = {};
    (schema?.sections || []).forEach((s) => { m[s.id] = s; });
    return m;
  }, [schema]);

  const overall = scores?.overall_rating || "—";
  const strongest = (scores?.strongest_section_ids || []).map((id) => sectionById[id]).filter(Boolean);
  const priority = (scores?.priority_focus || []).map((id) => sectionById[id]).filter(Boolean);

  return (
    <div className="space-y-6" data-testid="snv3-results">
      <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6 sm:p-8">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">
              Your Special Needs assessment results
            </div>
            <h2 className="font-serif text-2xl sm:text-3xl text-[#1A1330]" data-testid="snv3-overall">
              {overall}
            </h2>
            <p className="text-sm text-[#4B4567] mt-2 max-w-2xl">
              A snapshot of how you&apos;re currently supporting your child across the 10
              special-needs co-parenting principles. Not a diagnosis. Not legal advice.
            </p>
          </div>
          <button
            onClick={onRestart}
            className="inline-flex items-center gap-2 text-sm text-[#3D1A78] border border-[#E5E0EE] hover:border-[#3D1A78] rounded-full px-4 py-2"
            data-testid="snv3-restart-btn"
          >
            <RotateCcw size={14} /> Retake assessment
          </button>
        </div>
      </div>

      {strongest.length > 0 && (
        <div className="rounded-3xl border border-[#B8DDC6] bg-[#E4F4EC] p-6" data-testid="snv3-strongest">
          <div className="flex items-center gap-2 text-[#1F5C3B] font-bold text-xs uppercase tracking-[0.18em] mb-2">
            <TrendingUp size={14} /> Your strongest area
          </div>
          <div className="text-lg font-serif text-[#1A1330]">
            {strongest.map((s) => `Principle ${s.number}: ${s.name}`).join(" · ")}
          </div>
        </div>
      )}

      {priority.length > 0 && (
        <div className="rounded-3xl border border-[#F0B6A0] bg-[#FEF1EC] p-6" data-testid="snv3-priority">
          <div className="flex items-center gap-2 text-[#C2481F] font-bold text-xs uppercase tracking-[0.18em] mb-2">
            <AlertTriangle size={14} /> Priority focus
          </div>
          <ul className="space-y-1.5">
            {priority.map((s) => (
              <li key={s.id} className="text-[#1A1330]">
                <span className="font-semibold">Principle {s.number}: {s.name}</span>
                {s.goal && <span className="text-[#4B4567]"> — {s.goal}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {scores?.show_communication_toolkit && (
        <div className="rounded-3xl border border-[#CFC1EA] bg-[#EFE9F9] p-6" data-testid="snv3-toolkit">
          <div className="flex items-center gap-2 text-[#3D1A78] font-bold text-xs uppercase tracking-[0.18em] mb-2">
            <MessageCircle size={14} /> Communication toolkit recommended
          </div>
          <p className="text-sm text-[#1A1330] leading-relaxed">
            Your responses on <strong>Principle 3 (Maintain Open, Child-Focused Communication)</strong> suggest
            structured tools would help. Consider using shared calendars/apps, a written change-log
            for medications and therapies, and scheduled child-focused check-ins with the other parent.
          </p>
        </div>
      )}

      <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6 sm:p-8">
        <h3 className="font-serif text-xl text-[#1A1330] mb-4">Principle-by-principle breakdown</h3>
        <div className="space-y-3">
          {(scores?.sections || []).map((sec) => {
            const meta = sectionById[sec.id];
            const tone = RATING_TONE[sec.rating] || RATING_TONE.Fair;
            return (
              <div
                key={sec.id}
                className="flex items-start justify-between gap-3 border border-[#E5E0EE] rounded-2xl p-4"
                data-testid={`snv3-sec-${sec.id}`}
              >
                <div className="min-w-0 flex-1">
                  <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-0.5">
                    Principle {sec.number}
                  </div>
                  <div className="font-semibold text-[#1A1330]">{sec.name}</div>
                  {meta?.goal && (
                    <div className="text-xs text-[#4B4567] mt-0.5">{meta.goal}</div>
                  )}
                </div>
                <div className="shrink-0 text-right">
                  {sec.rating ? (
                    <span
                      className={`inline-block text-xs font-bold px-2.5 py-1 rounded-full border ${tone.bg} ${tone.text} ${tone.border}`}
                      data-testid={`snv3-rating-${sec.id}`}
                    >
                      {sec.rating}
                    </span>
                  ) : (
                    <span className="text-xs text-[#857E9C] italic">Not answered</span>
                  )}
                  {typeof sec.avg === "number" && (
                    <div className="text-[11px] text-[#857E9C] mt-1">Avg {sec.avg} / 4</div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <p className="text-xs text-[#857E9C] italic text-center px-6">
        This assessment is educational and does not replace professional advice or diagnostic evaluation.
        SA CoParents supports families preparing for mediation and everyday co-parenting decisions.
      </p>
    </div>
  );
}

export default function SpecialNeedsV3() {
  const [schema, setSchema] = useState(null);
  const [answers, setAnswers] = useState({});
  const [scores, setScores] = useState(null);
  const [completed, setCompleted] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [sectionIdx, setSectionIdx] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [s, me] = await Promise.all([
        api.get("/special-needs-v3/schema"),
        api.get("/special-needs-v3/me"),
      ]);
      setSchema(s.data);
      if (me.data?.exists) {
        setAnswers(me.data.answers || {});
        if (me.data.completed && me.data.scores) {
          setScores(me.data.scores);
          setCompleted(true);
        }
      }
    } catch {
      toast.error("Couldn't load the assessment. Please refresh.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const sections = schema?.sections || [];
  const total = schema?.total_questions || 0;
  const answeredCount = Object.keys(answers).length;
  const section = sections[sectionIdx];

  const setAnswer = (qid, v) => {
    setAnswers((a) => ({ ...a, [qid]: v }));
  };

  const persistSection = async (sec) => {
    if (!sec) return true;
    const payload = {};
    for (const q of sec.questions) {
      if (typeof answers[q.id] === "number") payload[q.id] = answers[q.id];
    }
    if (Object.keys(payload).length === 0) return true;
    setSaving(true);
    try {
      await api.post("/special-needs-v3/answers/bulk", { answers: payload });
      return true;
    } catch {
      toast.error("Save failed. Your answers are kept locally — we'll retry.");
      return false;
    } finally {
      setSaving(false);
    }
  };

  const sectionAnsweredCount = section
    ? section.questions.filter((q) => typeof answers[q.id] === "number").length
    : 0;
  const sectionComplete = section ? sectionAnsweredCount === section.questions.length : false;

  const goNext = async () => {
    await persistSection(section);
    if (sectionIdx < sections.length - 1) {
      setSectionIdx((i) => i + 1);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const goPrev = async () => {
    await persistSection(section);
    setSectionIdx((i) => Math.max(0, i - 1));
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const finish = async () => {
    const ok = await persistSection(section);
    if (!ok) return;
    if (answeredCount < total) {
      toast.error(`Please answer all ${total} questions before finishing. (${answeredCount}/${total})`);
      return;
    }
    setCompleting(true);
    try {
      const { data } = await api.post("/special-needs-v3/complete", {});
      setScores(data.scores);
      setCompleted(true);
      toast.success("Assessment complete — here are your results.");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Couldn't finalize the assessment.");
    } finally {
      setCompleting(false);
    }
  };

  const restart = async () => {
    if (!window.confirm("Retake the assessment? Your current answers will be cleared.")) return;
    try {
      await api.delete("/special-needs-v3/me");
      setAnswers({});
      setScores(null);
      setCompleted(false);
      setSectionIdx(0);
      toast.success("Ready when you are.");
    } catch {
      toast.error("Couldn't reset. Please try again.");
    }
  };

  if (loading) {
    return (
      <AppShell>
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-16 text-[#857E9C]" data-testid="snv3-loading">
          Loading your space…
        </div>
      </AppShell>
    );
  }

  if (completed && scores) {
    return (
      <AppShell>
        <div className="min-h-full bg-gradient-to-b from-[#F8F5FF] via-white to-white">
          <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline mb-4"
              data-testid="snv3-back-to-dashboard"
            >
              <ArrowLeft size={14} /> Back to Dashboard
            </Link>
            <ResultsView scores={scores} schema={schema} onRestart={restart} />
            <div className="mt-6">
              <SampleReportCallout variant="compact" />
            </div>
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="min-h-full bg-gradient-to-b from-[#F8F5FF] via-white to-white">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline mb-4"
            data-testid="snv3-back-to-dashboard"
          >
            <ArrowLeft size={14} /> Back to Dashboard
          </Link>

          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="eyebrow text-[#3D1A78]">Special Needs Assessment · 10 Principles</div>
              <h1
                className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight mt-1"
                data-testid="snv3-title"
              >
                Supporting your special-needs child across two homes
              </h1>
              <p className="mt-2 text-[#4B4567] max-w-2xl text-[15px] leading-relaxed">
                A single-parent, 10-principle assessment aligned with best-practice
                special-needs co-parenting research. 60 questions on a 5-point scale.
                Autosaves as you go. Not a diagnosis. Not legal advice.
              </p>
            </div>
          </div>

          <div className="mt-6">
            <DemoModeBanner />
          </div>

          <div className="mt-6">
            <SampleReportCallout />
          </div>

          <div className="mt-8">
            <Progress answered={answeredCount} total={total} />
          </div>

          {section && (
            <div
              className="rounded-3xl border border-[#E5E0EE] bg-white p-6 sm:p-8 shadow-sm"
              data-testid={`snv3-section-${section.id}`}
            >
              <div className="flex items-start gap-3 mb-4">
                <div className="shrink-0 w-10 h-10 rounded-full bg-[#F1EBFA] grid place-items-center text-[#3D1A78] font-bold">
                  {section.number}
                </div>
                <div className="min-w-0">
                  <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-0.5">
                    Principle {section.number} of {sections.length}
                  </div>
                  <h2 className="font-serif text-xl sm:text-2xl text-[#1A1330] leading-tight" data-testid="snv3-section-name">
                    {section.name}
                  </h2>
                  {section.goal && (
                    <p className="text-sm text-[#4B4567] mt-1.5">{section.goal}</p>
                  )}
                </div>
              </div>

              <div className="mt-6 space-y-6">
                {section.questions.map((q, i) => (
                  <div key={q.id} data-testid={`snv3-question-${q.id}`}>
                    <div className="flex items-start gap-2 mb-3">
                      <span className="text-[11px] font-bold text-[#3D1A78] mt-0.5 shrink-0">
                        {section.number}.{i + 1}
                      </span>
                      <p className="text-[15px] text-[#1A1330] leading-relaxed">
                        {q.prompt}
                        {q.reverse && (
                          <span className="ml-2 text-[10px] uppercase tracking-[0.14em] text-[#857E9C]">
                            (reverse-scored)
                          </span>
                        )}
                      </p>
                    </div>
                    <LikertRow
                      scale={schema.response_scale}
                      value={answers[q.id]}
                      onChange={(v) => setAnswer(q.id, v)}
                      testidBase={`snv3-scale-${q.id}`}
                    />
                  </div>
                ))}
              </div>

              <div className="mt-8 flex flex-wrap items-center justify-between gap-3">
                <button
                  onClick={goPrev}
                  disabled={sectionIdx === 0}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full border border-[#E5E0EE] text-[#3D1A78] text-sm hover:bg-[#F5F2FA] disabled:opacity-40"
                  data-testid="snv3-prev-btn"
                >
                  <ArrowLeft size={14} /> Back
                </button>

                <div className="flex items-center gap-2 text-xs text-[#857E9C]">
                  {saving || completing ? (
                    <>
                      <Loader2 size={12} className="animate-spin" />
                      {completing ? "Scoring…" : "Saving…"}
                    </>
                  ) : (
                    <>
                      <Save size={12} /> Autosaves as you go
                    </>
                  )}
                </div>

                {sectionIdx < sections.length - 1 ? (
                  <button
                    onClick={goNext}
                    disabled={!sectionComplete}
                    className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-full bg-[#3D1A78] text-white text-sm font-semibold hover:bg-[#2D0F63] disabled:opacity-50"
                    data-testid="snv3-next-btn"
                    title={!sectionComplete ? "Answer every question in this principle to continue" : ""}
                  >
                    Next <ArrowRight size={14} />
                  </button>
                ) : (
                  <button
                    onClick={finish}
                    disabled={completing || answeredCount < total}
                    className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-full bg-[#3D1A78] text-white text-sm font-semibold hover:bg-[#2D0F63] disabled:opacity-50"
                    data-testid="snv3-finish-btn"
                  >
                    {completing ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                    Finish &amp; see results
                  </button>
                )}
              </div>

              <div className="mt-4 text-[11px] text-[#857E9C]">
                {sectionAnsweredCount}/{section.questions.length} answered in this principle
              </div>
            </div>
          )}

          <div className="mt-6 rounded-2xl bg-[#F8F5FF] border border-[#E5E0EE] p-4">
            <div className="flex items-start gap-2 text-xs text-[#4B4567]">
              <Sparkles size={14} className="text-[#3D1A78] shrink-0 mt-0.5" />
              <span>
                This assessment is a reflective tool. It doesn&apos;t diagnose,
                grade, or recommend legal action. It gives you a clear starting
                point for conversations with your co-parent, mediator, or
                Parenting Facilitator.
              </span>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
