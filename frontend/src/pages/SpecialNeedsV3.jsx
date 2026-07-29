import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft, ArrowRight, Check, Loader2, Save, RotateCcw, Sparkles,
  AlertTriangle, TrendingUp, MessageCircle, FileText, Download, Share2,
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
const SAMPLE_PDF_URL = "/api/insights/special-needs-dynamic-sample.pdf";

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

function ResultsView({ report, scores, schema, onRestart, onDownloadPdf, onShare, downloading, sharing }) {
  const sectionById = useMemo(() => {
    const m = {};
    (schema?.sections || []).forEach((s) => { m[s.id] = s; });
    return m;
  }, [schema]);

  const overall = report?.overall_rating || scores?.overall_rating || "—";
  const overallSummary = report?.overall_summary || "";
  const strengths = report?.strengths || [];
  const growth = report?.growth_areas || [];
  const toolkit = report?.communication_toolkit || [];
  const nextSteps = report?.next_steps || [];
  const sections = report?.sections || scores?.sections || [];

  return (
    <div className="space-y-6" data-testid="snv3-results">
      {/* Overall banner + action buttons */}
      <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6 sm:p-8">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="min-w-0 flex-1">
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">
              Your Special Needs Co-Parenting Report · 10 principles
            </div>
            <h2 className="font-serif text-2xl sm:text-3xl text-[#1A1330]" data-testid="snv3-overall">
              {overall}
            </h2>
            {overallSummary && (
              <p className="text-sm text-[#4B4567] mt-2 max-w-2xl leading-relaxed">
                {overallSummary}
              </p>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={onDownloadPdf}
              disabled={downloading}
              className="inline-flex items-center gap-1.5 text-sm font-semibold text-white bg-[#3D1A78] hover:bg-[#2D0F63] disabled:opacity-50 rounded-full px-4 py-2"
              data-testid="snv3-download-pdf-btn"
            >
              {downloading ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />} PDF
            </button>
            <button
              onClick={onShare}
              disabled={sharing}
              className="inline-flex items-center gap-1.5 text-sm font-semibold text-[#3D1A78] border border-[#E5E0EE] hover:border-[#3D1A78] disabled:opacity-50 rounded-full px-4 py-2"
              data-testid="snv3-share-btn"
            >
              {sharing ? <Loader2 size={14} className="animate-spin" /> : <Share2 size={14} />} Share
            </button>
            <button
              onClick={onRestart}
              className="inline-flex items-center gap-1.5 text-sm text-[#3D1A78] border border-[#E5E0EE] hover:border-[#3D1A78] rounded-full px-4 py-2"
              data-testid="snv3-restart-btn"
            >
              <RotateCcw size={14} /> Retake
            </button>
          </div>
        </div>
      </div>

      {/* Strengths */}
      {strengths.length > 0 && (
        <div className="rounded-3xl border border-[#B8DDC6] bg-[#E4F4EC] p-6" data-testid="snv3-strengths">
          <div className="flex items-center gap-2 text-[#1F5C3B] font-bold text-xs uppercase tracking-[0.18em] mb-3">
            <TrendingUp size={14} /> Strengths
          </div>
          <ul className="space-y-2.5">
            {strengths.map((s) => (
              <li key={s.section_id} className="text-[#1A1330]" data-testid={`snv3-strength-${s.section_id}`}>
                <div className="font-semibold">{s.title}</div>
                {s.detail && <div className="text-sm text-[#4B4567]">{s.detail}</div>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Priority focus / Growth areas */}
      {growth.length > 0 && (
        <div className="rounded-3xl border border-[#F0B6A0] bg-[#FEF1EC] p-6" data-testid="snv3-priority">
          <div className="flex items-center gap-2 text-[#C2481F] font-bold text-xs uppercase tracking-[0.18em] mb-3">
            <AlertTriangle size={14} /> Priority focus areas
          </div>
          <ul className="space-y-3">
            {growth.map((g) => (
              <li key={g.section_id} data-testid={`snv3-growth-${g.section_id}`}>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-semibold text-[#1A1330]">{g.title}</span>
                  {g.rating && (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full border border-[#F0B6A0] bg-white text-[#C2481F]">
                      {g.rating}
                    </span>
                  )}
                </div>
                {g.why_it_matters && <div className="text-sm text-[#4B4567] mt-1"><span className="font-semibold text-[#1A1330]">Why:</span> {g.why_it_matters}</div>}
                {g.first_step && <div className="text-sm text-[#4B4567] mt-0.5"><span className="font-semibold text-[#1A1330]">First step:</span> {g.first_step}</div>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Communication toolkit */}
      {toolkit.length > 0 && (
        <div className="rounded-3xl border border-[#CFC1EA] bg-[#EFE9F9] p-6" data-testid="snv3-toolkit">
          <div className="flex items-center gap-2 text-[#3D1A78] font-bold text-xs uppercase tracking-[0.18em] mb-3">
            <MessageCircle size={14} /> Communication toolkit
          </div>
          <p className="text-sm text-[#4B4567] mb-3">
            Highlighted because Principle 3 (Maintain Open, Child-Focused Communication) is currently Fair or Needs Improvement.
          </p>
          <ul className="space-y-2.5">
            {toolkit.map((tip, i) => (
              <li key={i} className="text-[#1A1330]" data-testid={`snv3-tip-${i}`}>
                <div className="font-semibold">{tip.title}</div>
                {tip.detail && <div className="text-sm text-[#4B4567]">{tip.detail}</div>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Principle-by-principle detail */}
      <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6 sm:p-8">
        <h3 className="font-serif text-xl text-[#1A1330] mb-4">Principle-by-principle detail</h3>
        <div className="space-y-3">
          {sections.map((sec) => {
            const meta = sectionById[sec.id];
            const tone = RATING_TONE[sec.rating] || RATING_TONE.Fair;
            return (
              <div key={sec.id} className="border border-[#E5E0EE] rounded-2xl p-4" data-testid={`snv3-sec-${sec.id}`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-0.5">
                      Principle {sec.number}
                    </div>
                    <div className="font-semibold text-[#1A1330]">{sec.name}</div>
                    {(sec.goal || meta?.goal) && (
                      <div className="text-xs text-[#4B4567] mt-0.5">{sec.goal || meta.goal}</div>
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
                {(sec.findings || []).length > 0 && (
                  <div className="mt-3">
                    <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-1">Findings</div>
                    <ul className="text-sm text-[#1A1330] list-disc pl-4 space-y-0.5">
                      {sec.findings.map((f, i) => <li key={i}>{f}</li>)}
                    </ul>
                  </div>
                )}
                {(sec.recommendations || []).length > 0 && (
                  <div className="mt-3">
                    <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-1">Recommendations</div>
                    <ul className="text-sm text-[#1A1330] list-disc pl-4 space-y-0.5">
                      {sec.recommendations.map((f, i) => <li key={i}>{f}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Next steps */}
      {nextSteps.length > 0 && (
        <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6" data-testid="snv3-next-steps">
          <h3 className="font-serif text-xl text-[#1A1330] mb-3">Recommended next steps</h3>
          <ol className="list-decimal pl-5 space-y-1.5 text-[#1A1330]">
            {nextSteps.map((s, i) => (
              <li key={i} data-testid={`snv3-step-${i}`}>{s}</li>
            ))}
          </ol>
        </div>
      )}

      <p className="text-xs text-[#857E9C] italic text-center px-6">
        {report?.disclaimer || "This assessment is educational and does not replace professional advice or diagnostic evaluation."}
      </p>
    </div>
  );
}

export default function SpecialNeedsV3() {
  const [schema, setSchema] = useState(null);
  const [answers, setAnswers] = useState({});
  const [scores, setScores] = useState(null);
  const [report, setReport] = useState(null);
  const [reportId, setReportId] = useState(null);
  const [completed, setCompleted] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [sharing, setSharing] = useState(false);
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
          // Try to load an existing report; ignore 404.
          try {
            const { data: rep } = await api.get("/special-needs-v3/report");
            if (rep && rep.report_id) {
              setReport(rep.report);
              setReportId(rep.report_id);
            }
          } catch { /* no report yet */ }
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
      // Auto-generate the full deterministic report so the rich results render.
      try {
        const { data: rep } = await api.post("/special-needs-v3/report/generate");
        setReport(rep.report);
        setReportId(rep.report_id);
      } catch {
        toast.error("Scored, but couldn't build the report right now.");
      }
      toast.success("Assessment complete — here are your results.");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Couldn't finalize the assessment.");
    } finally {
      setCompleting(false);
    }
  };

  const downloadPdf = async () => {
    setDownloading(true);
    try {
      const res = await api.get("/special-needs-v3/report/pdf", { responseType: "blob" });
      const url = window.URL.createObjectURL(res.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = "Special_Needs_Report.pdf";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error("Couldn't download the PDF. Please try again.");
    } finally {
      setDownloading(false);
    }
  };

  const share = async () => {
    if (!reportId) return;
    setSharing(true);
    try {
      const { data } = await api.post(`/special-needs-v3/report/${reportId}/share-link`, {});
      const url = `${window.location.origin}${data.viewer_path}`;
      try {
        await navigator.clipboard.writeText(url);
        toast.success("Share link copied to clipboard");
      } catch {
        toast.info(url);
      }
    } catch {
      toast.error("Couldn't create a share link.");
    } finally {
      setSharing(false);
    }
  };

  const restart = async () => {
    if (!window.confirm("Retake the assessment? Your current answers will be cleared.")) return;
    try {
      await api.delete("/special-needs-v3/me");
      setAnswers({});
      setScores(null);
      setReport(null);
      setReportId(null);
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
            <ResultsView
              report={report}
              scores={scores}
              schema={schema}
              onRestart={restart}
              onDownloadPdf={downloadPdf}
              onShare={share}
              downloading={downloading}
              sharing={sharing}
            />
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
